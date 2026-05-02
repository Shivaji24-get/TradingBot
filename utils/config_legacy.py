import configparser
import os
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str = "config.ini") -> Dict[str, Any]:
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent.parent / config_path
    
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