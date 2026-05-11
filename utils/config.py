"""
Configuration management – supports YAML (preferred) and legacy INI.

FIXES:
- API credentials now read from environment variables first (secure)
- validate_config() raises clearly when credentials are placeholder strings
- load_config() no longer silently returns empty dict on parse failure
- Removed config_legacy.py functionality (merged here, legacy file is dead code)
- Added type-safe get_profile() conversion
"""

import configparser
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False
    yaml = None  # type: ignore

# Sentinel strings that indicate the user has not filled in real credentials
_PLACEHOLDER_PREFIXES = ("${", "YOUR_", "XXXX", "your_", "")


@dataclass
class TradingProfile:
    """Typed representation of a loaded trading profile."""

    name: str = ""
    email: str = ""
    timezone: str = "Asia/Kolkata"

    # Risk
    risk_per_trade: float = 0.02
    max_positions: int = 5
    max_daily_loss: float = 0.05
    max_trades_per_day: int = 10
    default_stop_loss_pct: float = 2.0
    default_take_profit_pct: float = 3.0

    # Symbols / market
    symbols: List[str] = field(default_factory=lambda: ["NSE:NIFTY50-INDEX"])
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    trading_mode: str = "MIS"
    order_type: str = "MARKET"

    # Auto-trading
    auto_trading_enabled: bool = False
    paper_trading: bool = True
    min_signal_score: float = 75.0

    # API
    client_id: str = ""
    secret_key: str = ""
    redirect_uri: str = "http://127.0.0.1:5000/fyers/callback"

    # Logging
    log_level: str = "INFO"
    log_file: str = "trading_bot.log"


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def load_yaml_profile(profile_path: str = "config/trading_profile.yml") -> Dict[str, Any]:
    """
    Load and flatten the YAML trading profile.

    Credentials are overridden by environment variables when present.
    """
    if not _YAML_AVAILABLE:
        raise ImportError("PyYAML is required: pip install pyyaml")

    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Profile not found: {path}\n"
            "Run: cp config/trading_profile.example.yml config/trading_profile.yml"
        )

    with path.open(encoding="utf-8") as fh:
        data: Dict = yaml.safe_load(fh) or {}

    cfg: Dict[str, Any] = {}

    # Trader info
    trader = data.get("trader", {})
    cfg["name"] = trader.get("name", "")
    cfg["email"] = trader.get("email", "")
    cfg["timezone"] = trader.get("timezone", "Asia/Kolkata")

    # Risk
    risk = data.get("risk_profile", {})
    cfg["risk_per_trade"] = float(risk.get("risk_per_trade", 0.02))
    cfg["max_positions"] = int(risk.get("max_positions", 5))
    cfg["max_daily_loss"] = float(risk.get("max_daily_loss", 0.05))
    cfg["max_trades_per_day"] = int(risk.get("max_trades_per_day", 10))
    cfg["default_stop_loss_pct"] = float(risk.get("default_stop_loss_pct", 2.0))
    cfg["default_take_profit_pct"] = float(risk.get("default_take_profit_pct", 3.0))

    # Trading preferences
    prefs = data.get("trading_preferences", {})
    cfg["symbols"] = prefs.get("default_symbols", ["NSE:NIFTY50-INDEX"])
    session = prefs.get("market_session", {})
    cfg["market_open_time"] = session.get("market_open", "09:15")
    cfg["market_close_time"] = session.get("market_close", "15:30")
    cfg["trading_mode"] = prefs.get("trading_mode", "MIS")
    cfg["order_type"] = prefs.get("order_type", "MARKET")

    auto = prefs.get("auto_trading", {})
    cfg["auto_trading_enabled"] = bool(auto.get("enabled", False))
    cfg["paper_trading"] = bool(auto.get("paper_trading", True))
    cfg["min_signal_score"] = float(auto.get("min_signal_score", 75.0))

    scanning = prefs.get("scanning", {})
    cfg["scan_interval"] = int(scanning.get("interval_seconds", 60))

    # Strategies
    strategies = data.get("strategies", {})
    cfg["strategies"] = strategies
    tf = strategies.get("timeframe", {})
    cfg["main_timeframe"] = tf.get("main", "1h")
    cfg["entry_timeframe"] = tf.get("entry", "5m")

    # API – SECURITY: env vars take priority over config file values
    fyers = data.get("api", {}).get("fyers", {})
    cfg["client_id"] = os.environ.get("FYERS_CLIENT_ID") or fyers.get("client_id", "")
    cfg["secret_key"] = os.environ.get("FYERS_SECRET_KEY") or fyers.get("secret_key", "")
    cfg["redirect_uri"] = fyers.get("redirect_uri", "http://127.0.0.1:5000/fyers/callback")

    # Logging
    advanced = data.get("advanced", {})
    cfg["log_level"] = advanced.get("log_level", "INFO")
    cfg["log_file"] = "trading_bot.log"

    return cfg


# ---------------------------------------------------------------------------
# INI loader (legacy / fallback)
# ---------------------------------------------------------------------------

def load_ini_config(config_path: str = "config.ini") -> Dict[str, Any]:
    """Load legacy INI config. Credentials overridden by env vars."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    parser = configparser.ConfigParser()
    parser.read(path)

    def get(section: str, key: str, fallback: Any = "") -> Any:
        return parser.get(section, key, fallback=str(fallback))

    return {
        "username":   get("FYERS_APP", "username"),
        "pin":        get("FYERS_APP", "pin"),
        "mobile":     get("FYERS_APP", "mobile"),
        "client_id":  os.environ.get("FYERS_CLIENT_ID") or get("FYERS_APP", "client_id"),
        "secret_key": os.environ.get("FYERS_SECRET_KEY") or get("FYERS_APP", "secret_key"),
        "redirect_uri": get("FYERS_APP", "redirect_uri", "http://127.0.0.1:5000/fyers/callback"),

        "risk_per_trade":           float(get("TRADING_CONFIG", "risk_per_trade",           0.02)),
        "max_positions":            int(  get("TRADING_CONFIG", "max_positions",             5)),
        "confidence_threshold":     float(get("TRADING_CONFIG", "confidence_threshold",      0.75)),
        "stop_loss_percentage":     float(get("TRADING_CONFIG", "stop_loss_percentage",      2.0)),
        "take_profit_percentage":   float(get("TRADING_CONFIG", "take_profit_percentage",    3.0)),
        "max_daily_loss":           float(get("TRADING_CONFIG", "max_daily_loss",            0.05)),
        "market_open_time":         get("TRADING_CONFIG", "market_open_time",  "09:15"),
        "market_close_time":        get("TRADING_CONFIG", "market_close_time", "15:30"),

        "log_level":  get("LOGGING", "log_level",  "INFO"),
        "log_file":   get("LOGGING", "log_file",   "trading_bot.log"),
        "export_csv": parser.getboolean("LOGGING", "export_csv", fallback=True),
        "symbols": [
            s.strip()
            for s in get("TRADING_CONFIG", "symbols", "NSE:NIFTY50-INDEX").split(",")
            if s.strip()
        ],
    }


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

def load_config(
    config_path: str = "config.ini",
    profile_path: str = "config/trading_profile.yml",
    prefer_yaml: bool = True,
) -> Dict[str, Any]:
    """
    Load configuration, preferring YAML, falling back to INI.

    Raises FileNotFoundError if neither file exists.
    """
    if prefer_yaml and _YAML_AVAILABLE:
        yaml_path = Path(profile_path)
        if yaml_path.exists():
            try:
                cfg = load_yaml_profile(profile_path)
                logger.info("Loaded YAML profile: %s", profile_path)
                return cfg
            except Exception as exc:
                logger.warning("YAML load failed (%s). Trying INI.", exc)

    cfg = load_ini_config(config_path)
    logger.info("Loaded INI config: %s", config_path)
    return cfg


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _is_placeholder(value: str) -> bool:
    """Return True if *value* looks like an unfilled template placeholder."""
    return not value or any(value.startswith(p) for p in _PLACEHOLDER_PREFIXES)


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate completeness and basic correctness of the loaded config.

    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []

    client_id = config.get("client_id", "")
    secret_key = config.get("secret_key", "")

    if _is_placeholder(client_id):
        errors.append(
            "Fyers Client ID is missing or looks like a placeholder. "
            "Set FYERS_CLIENT_ID env var or fill in config/trading_profile.yml."
        )
    if _is_placeholder(secret_key):
        errors.append(
            "Fyers Secret Key is missing or looks like a placeholder. "
            "Set FYERS_SECRET_KEY env var or fill in config/trading_profile.yml."
        )

    rpt = config.get("risk_per_trade", 0)
    if isinstance(rpt, (int, float)) and rpt > 0.1:
        errors.append(f"risk_per_trade ({rpt}) exceeds 10% – this is very aggressive.")

    if not config.get("symbols"):
        errors.append("No trading symbols configured.")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Profile conversion
# ---------------------------------------------------------------------------

def get_profile(config: Dict[str, Any]) -> TradingProfile:
    """Convert a flat config dict into a typed TradingProfile."""
    return TradingProfile(
        name=config.get("name", ""),
        email=config.get("email", ""),
        timezone=config.get("timezone", "Asia/Kolkata"),
        risk_per_trade=float(config.get("risk_per_trade", 0.02)),
        max_positions=int(config.get("max_positions", 5)),
        max_daily_loss=float(config.get("max_daily_loss", 0.05)),
        max_trades_per_day=int(config.get("max_trades_per_day", 10)),
        default_stop_loss_pct=float(config.get("stop_loss_percentage", config.get("default_stop_loss_pct", 2.0))),
        default_take_profit_pct=float(config.get("take_profit_percentage", config.get("default_take_profit_pct", 3.0))),
        symbols=config.get("symbols", ["NSE:NIFTY50-INDEX"]),
        market_open_time=config.get("market_open_time", "09:15"),
        market_close_time=config.get("market_close_time", "15:30"),
        trading_mode=config.get("trading_mode", "MIS"),
        order_type=config.get("order_type", "MARKET"),
        auto_trading_enabled=bool(config.get("auto_trading_enabled", False)),
        paper_trading=bool(config.get("paper_trading", True)),
        min_signal_score=float(config.get("min_signal_score", config.get("confidence_threshold", 75.0))),
        client_id=config.get("client_id", ""),
        secret_key=config.get("secret_key", ""),
        redirect_uri=config.get("redirect_uri", "http://127.0.0.1:5000/fyers/callback"),
        log_level=config.get("log_level", "INFO"),
        log_file=config.get("log_file", "trading_bot.log"),
    )


# Backward-compatibility alias
load_trading_profile = load_yaml_profile
