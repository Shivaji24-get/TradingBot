"""
Retry Mechanisms - Resilient operation handling.

Implements retry with exponential backoff, circuit breaker pattern,
and rate limiting - inspired by Career-Ops robust automation patterns.
"""

import logging
import time
import random
from typing import Callable, Any, Optional, Type
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()      # Normal operation
    OPEN = auto()        # Failing, reject calls
    HALF_OPEN = auto()   # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    on_retry: Optional[Callable[[int, Exception], None]] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascade failures by opening the circuit after
    a threshold of failures, allowing the system to recover.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Rejecting calls, waiting for timeout
    - HALF_OPEN: Testing with limited calls
    
    Usage:
        breaker = CircuitBreaker()
        
        @breaker
        def api_call():
            return requests.get(url)
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
        self.config = config or CircuitBreakerConfig()
        self.name = name
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.consecutive_successes = 0
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f"Circuit {self.name} entering HALF_OPEN state")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return True
    
    def record_success(self):
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.config.success_threshold:
                self._close_circuit()
        else:
            self.failures = max(0, self.failures - 1)
    
    def record_failure(self):
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self._open_circuit()
        elif self.failures >= self.config.failure_threshold:
            self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit."""
        self.state = CircuitState.OPEN
        logger.warning(
            f"Circuit {self.name} OPENED after {self.failures} failures"
        )
    
    def _close_circuit(self):
        """Close the circuit."""
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.half_open_calls = 0
        self.consecutive_successes = 0
        logger.info(f"Circuit {self.name} CLOSED - service recovered")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitBreakerOpen(
                    f"Circuit {self.name} is OPEN - service unavailable"
                )
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise e
        
        return wrapper
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryHandler:
    """
    Retry handler with exponential backoff.
    
    Usage:
        config = RetryConfig(max_attempts=3, initial_delay=1.0)
        handler = RetryHandler(config)
        
        @handler.retry
        def api_call():
            return requests.get(url)
        
        # Or manual usage
        result = handler.execute(api_call)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception after all retries exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    logger.error(
                        f"Function failed after {self.config.max_attempts} attempts: {e}"
                    )
                    raise
                
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    f"Attempt {attempt}/{self.config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                
                if self.config.on_retry:
                    self.config.on_retry(attempt, e)
                
                time.sleep(delay)
        
        if last_exception:
            raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = self.config.initial_delay * (
            self.config.exponential_base ** (attempt - 1)
        )
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add random jitter (±25%)
            jitter = delay * 0.25
            delay = delay + random.uniform(-jitter, jitter)
        
        return max(0, delay)
    
    def retry(self, func: Callable) -> Callable:
        """Decorator to wrap function with retry logic."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper


class RateLimiter:
    """
    Simple rate limiter for API calls.
    
    Usage:
        limiter = RateLimiter(calls_per_second=10)
        
        @limiter
        def api_call():
            return requests.get(url)
    """
    
    def __init__(self, calls_per_second: float = 10.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time: Optional[float] = None
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            self._wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    
    def _wait_if_needed(self):
        """Wait if calls are too frequent."""
        if self.last_call_time is not None:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with rate limiting."""
        self._wait_if_needed()
        return func(*args, **kwargs)


# Convenience decorators

def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,)
):
    """Decorator for retry with exponential backoff."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        retryable_exceptions=retryable_exceptions
    )
    handler = RetryHandler(config)
    return handler.retry


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,)
):
    """Decorator for adding retry logic to functions."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        retryable_exceptions=retryable_exceptions
    )
    handler = RetryHandler(config)
    return handler.retry


def with_circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    name: str = "default"
):
    """Decorator for adding circuit breaker to functions."""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    breaker = CircuitBreaker(config, name=name)
    return breaker


def with_rate_limit(calls_per_second: float = 10.0):
    """Decorator for adding rate limiting to functions."""
    limiter = RateLimiter(calls_per_second)
    return limiter


# Combined resilience decorator

def resilient(
    max_attempts: int = 3,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    calls_per_second: float = 10.0
):
    """
    Combined decorator for retry, circuit breaker, and rate limiting.
    
    Usage:
        @resilient(max_attempts=3, failure_threshold=5)
        def api_call():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        # Apply rate limiter
        limiter = RateLimiter(calls_per_second)
        limited_func = limiter(func)
        
        # Apply retry
        retry_config = RetryConfig(max_attempts=max_attempts)
        retry_handler = RetryHandler(retry_config)
        retry_func = retry_handler.retry(limited_func)
        
        # Apply circuit breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        breaker = CircuitBreaker(cb_config, name=func.__name__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not breaker.can_execute():
                raise CircuitBreakerOpen(f"Circuit for {func.__name__} is OPEN")
            
            try:
                result = retry_func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                raise e
        
        return wrapper
    
    return decorator
