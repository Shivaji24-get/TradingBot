import json
from pathlib import Path
from typing import Dict, Any

class StrategyParser:
    def __init__(self, config_path: str = "strategy.json"):
        self.config_path = Path(__file__).parent.parent / config_path
    
    def load_strategy(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return self._default_strategy()
        with open(self.config_path, "r") as f:
            return json.load(f)
    
    def _default_strategy(self) -> Dict[str, Any]:
        return {
            "name": "RSI Momentum",
            "indicators": {"rsi": {"period": 14}, "sma": {"period": 20}},
            "entry": {"rsi_less_than": 30},
            "exit": {"rsi_greater_than": 70},
            "symbols": ["NSE:SBIN-EQ", "NSE:RELIANCE-EQ", "NSE:INFY-EQ"],
            "timeframe": "D",
            "limit": 30
        }
    
    def get_indicators(self) -> Dict[str, Any]:
        return self.load_strategy().get("indicators", {})
    
    def get_entry_conditions(self) -> Dict[str, Any]:
        return self.load_strategy().get("entry", {})
    
    def get_exit_conditions(self) -> Dict[str, Any]:
        return self.load_strategy().get("exit", {})
    
    def get_symbols(self) -> list:
        return self.load_strategy().get("symbols", [])
    
    def get_timeframe(self) -> str:
        return self.load_strategy().get("timeframe", "D")
    
    def get_limit(self) -> int:
        return self.load_strategy().get("limit", 30)