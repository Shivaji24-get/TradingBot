"""
Trading Scheduler – Market-aware job scheduling.

FIXES:
- Replaced `tz = tz.gettz(timezone)` (shadowed import) with `zone = dateutil_tz.gettz(...)`
- Fixed get_time_until_open / get_time_until_close to use proper timezone-aware arithmetic
- Removed duplicate is_market_open() function (use utils/scheduler.py instead)
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from dateutil import tz as dateutil_tz

logger = logging.getLogger(__name__)

_IST = dateutil_tz.gettz("Asia/Kolkata")


class MarketStatus(Enum):
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

    def _zone(self):
        # FIX: previously `tz = tz.gettz(timezone)` shadowed module import
        return dateutil_tz.gettz(self.timezone) or _IST

    def get_status(self, now: Optional[datetime] = None) -> MarketStatus:
        if now is None:
            now = datetime.now(self._zone())

        if now.weekday() >= 5:
            return MarketStatus.CLOSED

        t = now.time()
        if t < self.pre_market_start:
            return MarketStatus.CLOSED
        if t < self.market_open:
            return MarketStatus.PRE_MARKET
        if t <= self.market_close:
            return MarketStatus.OPEN
        if t <= self.post_market_end:
            return MarketStatus.POST_MARKET
        return MarketStatus.CLOSED

    def is_trading_hours(self, now: Optional[datetime] = None) -> bool:
        return self.get_status(now) == MarketStatus.OPEN

    def get_time_until_open(self, now: Optional[datetime] = None) -> int:
        """Seconds until next market open (0 if already open)."""
        if now is None:
            now = datetime.now(self._zone())

        if self.is_trading_hours(now):
            return 0

        next_open = now.replace(
            hour=self.market_open.hour,
            minute=self.market_open.minute,
            second=0,
            microsecond=0,
        )

        # Advance if today's open is already past
        if now.time() >= self.market_open:
            next_open += timedelta(days=1)

        # Skip weekends
        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)

        return max(0, int((next_open - now).total_seconds()))

    def get_time_until_close(self, now: Optional[datetime] = None) -> int:
        """Seconds until market close (0 if already closed)."""
        if now is None:
            now = datetime.now(self._zone())

        if not self.is_trading_hours(now):
            return 0

        close = now.replace(
            hour=self.market_close.hour,
            minute=self.market_close.minute,
            second=0,
            microsecond=0,
        )
        return max(0, int((close - now).total_seconds()))


@dataclass
class ScheduledJob:
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
    """Background job scheduler with market-hours awareness."""

    def __init__(self, market_session: Optional[MarketSession] = None) -> None:
        self.market_session = market_session or MarketSession()
        self.jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ jobs

    def add_job(
        self,
        job_id: str,
        callback: Callable,
        interval_seconds: int,
        name: Optional[str] = None,
        run_once: bool = False,
        market_hours_only: bool = False,
        enabled: bool = True,
    ) -> ScheduledJob:
        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            callback=callback,
            interval_seconds=interval_seconds,
            enabled=enabled,
            run_once=run_once,
            market_hours_only=market_hours_only,
        )
        self.jobs[job_id] = job
        logger.info("Scheduled job '%s' every %ds", job_id, interval_seconds)
        return job

    def remove_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False

    def enable_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            return True
        return False

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="TradingScheduler")
        self._thread.start()
        logger.info("TradingScheduler started")

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("TradingScheduler stopped")

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------ internal

    def _run(self) -> None:
        zone = self.market_session._zone()
        while self._running and not self._stop_event.is_set():
            now = datetime.now(zone)
            for job in list(self.jobs.values()):
                if not job.enabled:
                    continue
                if job.market_hours_only and not self.market_session.is_trading_hours(now):
                    continue
                if job.next_run is None or now >= job.next_run:
                    self._execute_job(job, now)
                    if job.run_once:
                        job.enabled = False
                    else:
                        job.last_run = now
                        job.next_run = now + timedelta(seconds=job.interval_seconds)
            self._stop_event.wait(0.5)

    def _execute_job(self, job: ScheduledJob, now: datetime) -> None:
        try:
            logger.debug("Executing job '%s'", job.id)
            job.callback()
            job.last_run = now
        except Exception:
            logger.exception("Job '%s' raised an exception", job.id)

    # ------------------------------------------------------------------ helpers

    def get_market_status(self) -> Dict[str, Any]:
        zone = self.market_session._zone()
        now = datetime.now(zone)
        status = self.market_session.get_status(now)
        return {
            "status": status.name,
            "is_trading_hours": status == MarketStatus.OPEN,
            "time_until_open": self.market_session.get_time_until_open(now),
            "time_until_close": self.market_session.get_time_until_close(now),
            "current_time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
        }

    def wait_for_market_open(self, check_interval: int = 60) -> bool:
        while self._running:
            if self.market_session.is_trading_hours():
                logger.info("Market is now open")
                return True
            time.sleep(check_interval)
        return False
