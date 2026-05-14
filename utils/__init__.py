"""
Utils package – shared utilities for TradingBot.

FIXES:
- NotificationManager import made explicit and safe (won't crash if requests not installed)
- Removed duplicate is_market_open from scheduler (now single source of truth)
- All public symbols listed in __all__
"""

from .config import load_config, validate_config, get_profile
from .exporter import export_to_csv
from .logger import setup_logging
from .scheduler import is_market_open, wait_for_market_open, get_time_until_open

try:
    from .notifications import NotificationManager
except ImportError:
    NotificationManager = None  # type: ignore

__all__ = [
    "load_config",
    "validate_config",
    "get_profile",
    "export_to_csv",
    "setup_logging",
    "is_market_open",
    "wait_for_market_open",
    "get_time_until_open",
    "NotificationManager",
]
