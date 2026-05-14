"""Retry, circuit breaker, and rate limiting utilities."""
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    on_retry: Optional[Callable] = None


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
        self.config = config or CircuitBreakerConfig()
        self.name = name
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.consecutive_successes = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - (self.last_failure_time or 0) >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        return True

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failures = 0
                self.half_open_calls = 0
                self.consecutive_successes = 0
        else:
            self.failures = max(0, self.failures - 1)

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN or self.failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit '%s' OPENED", self.name)

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitBreakerOpen(f"Circuit '{self.name}' is OPEN")
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        return wrapper


class RetryHandler:
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exc = None
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.config.retryable_exceptions as e:
                last_exc = e
                if attempt == self.config.max_attempts:
                    raise
                delay = self._delay(attempt)
                logger.warning("Attempt %d/%d failed: %s. Retrying in %.1fs",
                               attempt, self.config.max_attempts, e, delay)
                if self.config.on_retry:
                    self.config.on_retry(attempt, e)
                time.sleep(delay)
        if last_exc:
            raise last_exc

    def _delay(self, attempt: int) -> float:
        d = min(self.config.initial_delay * (self.config.exponential_base ** (attempt - 1)),
                self.config.max_delay)
        if self.config.jitter:
            d += random.uniform(-d * 0.25, d * 0.25)
        return max(0, d)

    def retry(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper


class RateLimiter:
    def __init__(self, calls_per_second: float = 10.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call: Optional[float] = None

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            self._wait()
            return func(*args, **kwargs)
        return wrapper

    def _wait(self):
        if self.last_call is not None:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


def retry_with_backoff(max_attempts: int = 3, initial_delay: float = 1.0,
                       retryable_exceptions: tuple = (Exception,)):
    cfg = RetryConfig(max_attempts=max_attempts, initial_delay=initial_delay,
                      retryable_exceptions=retryable_exceptions)
    return RetryHandler(cfg).retry


with_retry = retry_with_backoff
