"""
Market scheduling utilities.

FIXES:
- Removed re-import of `tz` inside is_market_open() that shadowed module-level import
- Eliminated potential NameError when dateutil not available
- Added weekend-aware helper
"""

import logging
from datetime import datetime, time as dt_time, timedelta
from typing import Optional

from dateutil import tz as dateutil_tz

logger = logging.getLogger(__name__)

_IST = dateutil_tz.gettz("Asia/Kolkata")


def _now_ist() -> datetime:
    """Return current datetime in IST."""
    return datetime.now(_IST)


def is_market_open(
    open_time: str = "09:15",
    close_time: str = "15:30",
    timezone: str = "Asia/Kolkata",
) -> bool:
    """
    Return True when the Indian equity market is currently open.

    Args:
        open_time:  Market open  in "HH:MM" format (default 09:15 IST).
        close_time: Market close in "HH:MM" format (default 15:30 IST).
        timezone:   IANA timezone name (default Asia/Kolkata).

    Returns:
        bool – True if current time falls within the trading window on a weekday.
    """
    # FIX: was `tz = tz.gettz(timezone)` which shadowed the module-level import
    zone = dateutil_tz.gettz(timezone) if timezone != "Asia/Kolkata" else _IST
    now = datetime.now(zone)

    # Skip weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False

    try:
        open_h, open_m = map(int, open_time.split(":"))
        close_h, close_m = map(int, close_time.split(":"))
    except ValueError:
        logger.error("Invalid time format. Expected HH:MM, got open=%s close=%s", open_time, close_time)
        return False

    market_open = dt_time(open_h, open_m)
    market_close = dt_time(close_h, close_m)
    current = now.time()

    return market_open <= current <= market_close


def wait_for_market_open(
    open_time: str = "09:15",
    check_interval_seconds: int = 60,
) -> None:
    """Block until the market opens. Logs status every check interval."""
    import time

    while not is_market_open(open_time=open_time):
        logger.info("Market closed. Waiting for %s IST...", open_time)
        time.sleep(check_interval_seconds)
    logger.info("Market is now open.")


def get_time_until_open(open_time: str = "09:15") -> int:
    """
    Return seconds until the next market open.

    Returns 0 if market is currently open.
    """
    now = _now_ist()
    if is_market_open(open_time=open_time):
        return 0

    open_h, open_m = map(int, open_time.split(":"))
    next_open = now.replace(hour=open_h, minute=open_m, second=0, microsecond=0)

    # If today's open has already passed, advance to next trading day
    if now >= next_open:
        next_open += timedelta(days=1)

    # Skip weekends
    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)

    return max(0, int((next_open - now).total_seconds()))
