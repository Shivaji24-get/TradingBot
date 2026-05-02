"""
Configuration Management - Enhanced config loader.

Inspired by Career-Ops profile.yml pattern.
Supports both legacy INI format and new YAML profile system.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TradingProfile:
    """Structured trading profile configuration."""
    # Trader info
    name: str = ""
    email: str = ""
    timezone: str = "Asia/Kolkata"
    
    # Risk settings
    risk_per_trade: float = 0.02
    max_positions: int = 5
    max_daily_loss: float = 0.05
    max_trades_per_day: int = 10
    default_stop_loss_pct: float = 2.0
    default_take_profit_pct: float = 3.0
    
    # Trading preferences
    symbols: list = None
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    trading_mode: str = "MIS"
    order_type: str = "MARKET"
    
    # Auto-trading
    auto_trading_enabled: bool = False
    paper_trading: bool = True
    min_signal_score: float = 75.0
    
    # API settings
    client_id: str = ""
    secret_key: str = ""
    redirect_uri: str = "http://127.0.0.1:5000/fyers/callback"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "trading_bot.log"
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]


def load_yaml_profile(profile_path: str = "config/trading_profile.yml") -> Dict[str, Any]:
    """
    Load YAML trading profile (Career-Ops pattern).
    
    Args:
        profile_path: Path to YAML profile file
        
    Returns:
        Configuration dictionary
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML required for YAML config. Install with: pip install pyyaml")
    
    profile_path = Path(profile_path)
    
    if not profile_path.exists():
        example_path = Path("config/trading_profile.example.yml")
        if example_path.exists():
            logger.warning(
                f"Profile not found at {profile_path}. "
                f"Please copy {example_path} to {profile_path} and customize."
            )
        raise FileNotFoundError(f"Profile not found: {profile_path}")
    
    with open(profile_path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    
    # Flatten YAML structure into flat config dict
    config = {}
    
    # Trader info
    if 'trader' in yaml_data:
        trader = yaml_data['trader']
        config['name'] = trader.get('name', '')
        config['email'] = trader.get('email', '')
        config['timezone'] = trader.get('timezone', 'Asia/Kolkata')
    
    # Risk profile
    if 'risk_profile' in yaml_data:
        risk = yaml_data['risk_profile']
        config['risk_per_trade'] = risk.get('risk_per_trade', 0.02)
        config['max_positions'] = risk.get('max_positions', 5)
        config['max_daily_loss'] = risk.get('max_daily_loss', 0.05)
        config['max_trades_per_day'] = risk.get('max_trades_per_day', 10)
        config['default_stop_loss_pct'] = risk.get('default_stop_loss_pct', 2.0)
        config['default_take_profit_pct'] = risk.get('default_take_profit_pct', 3.0)
    
    # Trading preferences
    if 'trading_preferences' in yaml_data:
        prefs = yaml_data['trading_preferences']
        config['symbols'] = prefs.get('default_symbols', ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"])
        
        if 'market_session' in prefs:
            session = prefs['market_session']
            config['market_open_time'] = session.get('market_open', '09:15')
            config['market_close_time'] = session.get('market_close', '15:30')
        
        config['trading_mode'] = prefs.get('trading_mode', 'MIS')
        config['order_type'] = prefs.get('order_type', 'MARKET')
        
        if 'auto_trading' in prefs:
            auto = prefs['auto_trading']
            config['auto_trading_enabled'] = auto.get('enabled', False)
            config['paper_trading'] = auto.get('paper_trading', True)
            config['min_signal_score'] = auto.get('min_signal_score', 75.0)
    
    # API settings
    if 'api' in yaml_data and 'fyers' in yaml_data['api']:
        fyers = yaml_data['api']['fyers']
        config['client_id'] = fyers.get('client_id', '')
        config['redirect_uri'] = fyers.get('redirect_uri', 'http://127.0.0.1:5000/fyers/callback')
        # Secret key should come from environment or secure storage
        config['secret_key'] = os.getenv('FYERS_SECRET_KEY', '')
    
    # Logging
    if 'advanced' in yaml_data and 'log_level' in yaml_data['advanced']:
        config['log_level'] = yaml_data['advanced']['log_level']
    
    # Environment variable overrides
    config['client_id'] = os.getenv('FYERS_CLIENT_ID', config.get('client_id', ''))
    config['secret_key'] = os.getenv('FYERS_SECRET_KEY', config.get('secret_key', ''))
    
    return config


def load_ini_config(config_path: str = "config.ini") -> Dict[str, Any]:
    """
    Load legacy INI config (backward compatibility).
    
    Args:
        config_path: Path to INI config file
        
    Returns:
        Configuration dictionary
    """
    import configparser
    
    config = configparser.ConfigParser()
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path)
    
    return {
        "username": config.get("FYERS_APP", "username", fallback=""),
        "pin": config.get("FYERS_APP", "pin", fallback=""),
        "mobile": config.get("FYERS_APP", "mobile", fallback=""),
        "client_id": config.get("FYERS_APP", "client_id", fallback=""),
        "secret_key": config.get("FYERS_APP", "secret_key", fallback=""),
        "redirect_uri": config.get("FYERS_APP", "redirect_uri", fallback="http://127.0.0.1:5000/fyers/callback"),
        "risk_per_trade": config.getfloat("TRADING_CONFIG", "risk_per_trade", fallback=0.02),
        "max_positions": config.getint("TRADING_CONFIG", "max_positions", fallback=5),
        "confidence_threshold": config.getfloat("TRADING_CONFIG", "confidence_threshold", fallback=0.75),
        "stop_loss_percentage": config.getfloat("TRADING_CONFIG", "stop_loss_percentage", fallback=2.0),
        "take_profit_percentage": config.getfloat("TRADING_CONFIG", "take_profit_percentage", fallback=3.0),
        "max_daily_loss": config.getfloat("TRADING_CONFIG", "max_daily_loss", fallback=0.05),
        "market_open_time": config.get("TRADING_CONFIG", "market_open_time", fallback="09:15"),
        "market_close_time": config.get("TRADING_CONFIG", "market_close_time", fallback="15:30"),
        "log_level": config.get("LOGGING", "log_level", fallback="INFO"),
        "log_file": config.get("LOGGING", "log_file", fallback="trading_bot.log"),
        "export_csv": config.getboolean("LOGGING", "export_csv", fallback=True),
        "symbols": config.get("TRADING_CONFIG", "symbols", fallback="NSE:NIFTY50-INDEX,NSE:BANKNIFTY-INDEX").split(",")
    }


def load_config(
    config_path: str = "config.ini",
    profile_path: str = "config/trading_profile.yml",
    prefer_yaml: bool = True
) -> Dict[str, Any]:
    """
    Load configuration with automatic format detection.
    
    Priority (if prefer_yaml=True):
    1. YAML profile (if exists)
    2. INI config (fallback)
    3. Environment variables (always override)
    
    Args:
        config_path: Path to INI config file
        profile_path: Path to YAML profile
        prefer_yaml: Whether to prefer YAML format
        
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # Try YAML first if preferred
    if prefer_yaml and YAML_AVAILABLE:
        yaml_path = Path(profile_path)
        if yaml_path.exists():
            try:
                config = load_yaml_profile(profile_path)
                logger.info(f"Loaded YAML profile from {profile_path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load YAML profile: {e}. Falling back to INI.")
    
    # Fall back to INI
    try:
        config = load_ini_config(config_path)
        logger.info(f"Loaded INI config from {config_path}")
    except FileNotFoundError:
        if not config:  # No config loaded yet
            logger.error(f"No configuration found. Please create {profile_path} or {config_path}")
            raise
    
    return config


def get_profile(config: Dict[str, Any]) -> TradingProfile:
    """
    Convert config dict to TradingProfile dataclass.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        TradingProfile instance
    """
    return TradingProfile(
        name=config.get('name', ''),
        email=config.get('email', ''),
        timezone=config.get('timezone', 'Asia/Kolkata'),
        risk_per_trade=config.get('risk_per_trade', 0.02),
        max_positions=config.get('max_positions', 5),
        max_daily_loss=config.get('max_daily_loss', 0.05),
        max_trades_per_day=config.get('max_trades_per_day', 10),
        default_stop_loss_pct=config.get('stop_loss_percentage', 2.0),
        default_take_profit_pct=config.get('take_profit_percentage', 3.0),
        symbols=config.get('symbols', ["NSE:NIFTY50-INDEX", "NSE:BANKNIFTY-INDEX"]),
        market_open_time=config.get('market_open_time', '09:15'),
        market_close_time=config.get('market_close_time', '15:30'),
        trading_mode=config.get('trading_mode', 'MIS'),
        order_type=config.get('order_type', 'MARKET'),
        auto_trading_enabled=config.get('auto_trading_enabled', False),
        paper_trading=config.get('paper_trading', True),
        min_signal_score=config.get('confidence_threshold', 75.0),
        client_id=config.get('client_id', ''),
        secret_key=config.get('secret_key', ''),
        redirect_uri=config.get('redirect_uri', 'http://127.0.0.1:5000/fyers/callback'),
        log_level=config.get('log_level', 'INFO'),
        log_file=config.get('log_file', 'trading_bot.log')
    )


def validate_config(config: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate configuration completeness.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    required_fields = [
        ('client_id', 'Fyers Client ID'),
        ('secret_key', 'Fyers Secret Key'),
    ]
    
    for field, name in required_fields:
        if not config.get(field):
            errors.append(f"Missing required field: {name} ({field})")
    
    # Validate numeric ranges
    if config.get('risk_per_trade', 0) > 0.1:
        errors.append("risk_per_trade should not exceed 10% (0.1)")
    
    if config.get('max_positions', 0) < 1:
        errors.append("max_positions must be at least 1")
    
    if not config.get('symbols'):
        errors.append("No trading symbols configured")
    
    return len(errors) == 0, errors


# Backward compatibility alias
load_trading_profile = load_yaml_profile
