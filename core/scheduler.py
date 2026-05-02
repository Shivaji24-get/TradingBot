"""
Trading Scheduler - Job scheduling and timing module.

Inspired by Career-Ops automation patterns.
Handles:
- Market session detection
- Periodic task scheduling
- Background job execution
- Daily reset operations
"""

import logging
import time
import threading
from typing import Callable, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
from dateutil import tz
from enum import Enum, auto

logger = logging.getLogger(__name__)

IST = tz.gettz("Asia/Kolkata")


class MarketStatus(Enum):
    """Market session status."""
    PRE_MARKET = auto()
    OPEN = auto()
    POST_MARKET = auto()
    CLOSED = auto()


@dataclass
class MarketSession:
    """Trading session configuration."""
    pre_market_start: dt_time = field(default_factory=lambda: dt_time(9, 0))
    market_open: dt_time = field(default_factory=lambda: dt_time(9, 15))
    market_close: dt_time = field(default_factory=lambda: dt_time(15, 30))
    post_market_end: dt_time = field(default_factory=lambda: dt_time(16, 0))
    timezone: str = "Asia/Kolkata"
    
    def get_status(self, now: Optional[datetime] = None) -> MarketStatus:
        """Get current market status."""
        if now is None:
            now = datetime.now(IST)
        
        current_time = now.time()
        
        # Weekend check
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return MarketStatus.CLOSED
        
        if current_time < self.pre_market_start:
            return MarketStatus.CLOSED
        elif current_time < self.market_open:
            return MarketStatus.PRE_MARKET
        elif current_time <= self.market_close:
            return MarketStatus.OPEN
        elif current_time <= self.post_market_end:
            return MarketStatus.POST_MARKET
        else:
            return MarketStatus.CLOSED
    
    def is_trading_hours(self, now: Optional[datetime] = None) -> bool:
        """Check if currently in trading hours."""
        status = self.get_status(now)
        return status == MarketStatus.OPEN
    
    def get_time_until_open(self, now: Optional[datetime] = None) -> int:
        """Get seconds until market opens."""
        if now is None:
            now = datetime.now(IST)
        
        if self.is_trading_hours(now):
            return 0
        
        current_time = now.time()
        
        # If before market open today
        if current_time < self.market_open:
            next_open = now.replace(
                hour=self.market_open.hour,
                minute=self.market_open.minute,
                second=0,
                microsecond=0
            )
        else:
            # Next day
            next_day = now + timedelta(days=1)
            # Skip weekends
            while next_day.weekday() >= 5:
                next_day += timedelta(days=1)
            
            next_open = next_day.replace(
                hour=self.market_open.hour,
                minute=self.market_open.minute,
                second=0,
                microsecond=0
            )
        
        return int((next_open - now).total_seconds())
    
    def get_time_until_close(self, now: Optional[datetime] = None) -> int:
        """Get seconds until market closes."""
        if now is None:
            now = datetime.now(IST)
        
        if not self.is_trading_hours(now):
            return 0
        
        close_time = now.replace(
            hour=self.market_close.hour,
            minute=self.market_close.minute,
            second=0,
            microsecond=0
        )
        
        return int((close_time - now).total_seconds())


@dataclass
class ScheduledJob:
    """Represents a scheduled job."""
    id: str
    name: str
    callback: Callable
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    run_once: bool = False
    market_hours_only: bool = False


class TradingScheduler:
    """
    Scheduler for trading-related tasks.
    
    Features:
    - Periodic task execution
    - Market hours awareness
    - Background threading
    - Job management (add/remove/enable/disable)
    
    Usage:
        scheduler = TradingScheduler()
        scheduler.add_job('scan', scan_market, interval=60)
        scheduler.start()
    """
    
    def __init__(self, market_session: Optional[MarketSession] = None):
        self.market_session = market_session or MarketSession()
        self.jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info("TradingScheduler initialized")
    
    def add_job(
        self,
        job_id: str,
        callback: Callable,
        interval_seconds: int,
        name: Optional[str] = None,
        run_once: bool = False,
        market_hours_only: bool = False,
        enabled: bool = True
    ) -> ScheduledJob:
        """
        Add a scheduled job.
        
        Args:
            job_id: Unique identifier for the job
            callback: Function to execute
            interval_seconds: Seconds between executions
            name: Human-readable name
            run_once: If True, job runs only once
            market_hours_only: If True, only runs during market hours
            enabled: Initial enabled state
            
        Returns:
            ScheduledJob instance
        """
        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            callback=callback,
            interval_seconds=interval_seconds,
            enabled=enabled,
            run_once=run_once,
            market_hours_only=market_hours_only
        )
        
        self.jobs[job_id] = job
        logger.info(f"Added job '{job_id}' with interval {interval_seconds}s")
        
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Removed job '{job_id}'")
            return True
        return False
    
    def enable_job(self, job_id: str) -> bool:
        """Enable a scheduled job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            logger.info(f"Enabled job '{job_id}'")
            return True
        return False
    
    def disable_job(self, job_id: str) -> bool:
        """Disable a scheduled job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            logger.info(f"Disabled job '{job_id}'")
            return True
        return False
    
    def start(self):
        """Start the scheduler in background thread."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        logger.info("TradingScheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("TradingScheduler stopped")
    
    def _run(self):
        """Main scheduler loop."""
        while self._running and not self._stop_event.is_set():
            now = datetime.now(IST)
            
            for job in self.jobs.values():
                if not job.enabled:
                    continue
                
                # Check market hours restriction
                if job.market_hours_only:
                    if not self.market_session.is_trading_hours(now):
                        continue
                
                # Check if it's time to run
                if job.next_run is None or now >= job.next_run:
                    self._execute_job(job)
                    
                    if job.run_once:
                        job.enabled = False
                    else:
                        job.last_run = now
                        job.next_run = now + timedelta(seconds=job.interval_seconds)
            
            # Sleep briefly
            self._stop_event.wait(0.1)
    
    def _execute_job(self, job: ScheduledJob):
        """Execute a single job."""
        try:
            logger.debug(f"Executing job '{job.id}'")
            job.callback()
            job.last_run = datetime.now(IST)
        except Exception as e:
            logger.error(f"Job '{job.id}' failed: {e}", exc_info=True)
    
    def wait_for_market_open(self, check_interval: int = 60) -> bool:
        """
        Block until market opens.
        
        Args:
            check_interval: Seconds between checks
            
        Returns:
            True when market is open
        """
        logger.info("Waiting for market open...")
        
        while self._running:
            if self.market_session.is_trading_hours():
                logger.info("Market is now open")
                return True
            
            time.sleep(check_interval)
        
        return False
    
    def wait_for_market_close(self, check_interval: int = 60) -> bool:
        """
        Block until market closes.
        
        Args:
            check_interval: Seconds between checks
            
        Returns:
            True when market is closed
        """
        logger.info("Waiting for market close...")
        
        while self._running:
            if not self.market_session.is_trading_hours():
                logger.info("Market is now closed")
                return True
            
            time.sleep(check_interval)
        
        return False
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status information."""
        now = datetime.now(IST)
        status = self.market_session.get_status(now)
        
        return {
            'status': status.name,
            'is_trading_hours': status == MarketStatus.OPEN,
            'time_until_open': self.market_session.get_time_until_open(now),
            'time_until_close': self.market_session.get_time_until_close(now),
            'current_time': now.strftime('%H:%M:%S'),
            'date': now.strftime('%Y-%m-%d')
        }
    
    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get status of all jobs."""
        now = datetime.now(IST)
        
        return [
            {
                'id': job.id,
                'name': job.name,
                'enabled': job.enabled,
                'last_run': job.last_run.strftime('%H:%M:%S') if job.last_run else None,
                'next_run': job.next_run.strftime('%H:%M:%S') if job.next_run else None,
                'interval': job.interval_seconds,
                'market_hours_only': job.market_hours_only
            }
            for job in self.jobs.values()
        ]
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running


# Convenience functions

def is_market_open(
    open_time: str = "09:15",
    close_time: str = "15:30",
    timezone: str = "Asia/Kolkata"
) -> bool:
    """
    Check if market is currently open.
    
    Args:
        open_time: Market open time (HH:MM)
        close_time: Market close time (HH:MM)
        timezone: IANA timezone name
        
    Returns:
        True if market is open
    """
    tz = tz.gettz(timezone)
    now = datetime.now(tz)
    
    # Weekend check
    if now.weekday() >= 5:
        return False
    
    # Parse times
    open_h, open_m = map(int, open_time.split(':'))
    close_h, close_m = map(int, close_time.split(':'))
    
    market_open = dt_time(open_h, open_m)
    market_close = dt_time(close_h, close_m)
    
    current_time = now.time()
    
    return market_open <= current_time <= market_close


def wait_for_market_open(
    open_time: str = "09:15",
    check_interval: int = 60,
    timezone: str = "Asia/Kolkata"
) -> bool:
    """
    Block until market opens.
    
    Args:
        open_time: Market open time (HH:MM)
        check_interval: Seconds between checks
        timezone: IANA timezone name
        
    Returns:
        True when market opens
    """
    session = MarketSession(
        market_open=dt_time(*map(int, open_time.split(':'))),
        timezone=timezone
    )
    
    scheduler = TradingScheduler(session)
    return scheduler.wait_for_market_open(check_interval)
