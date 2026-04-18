import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, config: Dict[str, Any]):
        self.risk_per_trade = config.get("risk_per_trade", 0.02)
        self.max_positions = config.get("max_positions", 5)
        self.stop_loss_pct = config.get("stop_loss_percentage", 2.0)
        self.take_profit_pct = config.get("take_profit_percentage", 3.0)
        self.max_daily_loss = config.get("max_daily_loss", 0.05)
        self.daily_pnl = 0.0
        self.positions: Dict[str, Dict] = {}
    
    def can_trade(self) -> bool:
        if len(self.positions) >= self.max_positions:
            logger.warning("Max positions reached")
            return False
        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning("Daily loss limit reached")
            return False
        return True
    
    def calculate_position_size(self, capital: float, entry_price: float) -> int:
        max_loss = capital * self.risk_per_trade
        stop_loss_amount = entry_price * (self.stop_loss_pct / 100)
        if stop_loss_amount > 0:
            position_size = int(max_loss / stop_loss_amount)
            return max(1, position_size)
        return 1
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        if side.upper() == "BUY":
            return entry_price * (1 - self.stop_loss_pct / 100)
        return entry_price * (1 + self.stop_loss_pct / 100)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        if side.upper() == "BUY":
            return entry_price * (1 + self.take_profit_pct / 100)
        return entry_price * (1 - self.take_profit_pct / 100)
    
    def check_exit(self, position: Dict, current_price: float) -> bool:
        entry = position["entry_price"]
        sl = position.get("stop_loss", 0)
        tp = position.get("take_profit", 0)
        
        if position["side"].upper() == "BUY":
            if current_price <= sl:
                logger.info(f"Stop loss triggered: {current_price} <= {sl}")
                return True
            if current_price >= tp:
                logger.info(f"Take profit triggered: {current_price} >= {tp}")
                return True
        else:
            if current_price >= sl:
                logger.info(f"Stop loss triggered: {current_price} >= {sl}")
                return True
            if current_price <= tp:
                logger.info(f"Take profit triggered: {current_price} <= {tp}")
                return True
        return False
    
    def add_position(self, symbol: str, side: str, entry_price: float, qty: int):
        self.positions[symbol] = {
            "side": side,
            "entry_price": entry_price,
            "qty": qty,
            "stop_loss": self.calculate_stop_loss(entry_price, side),
            "take_profit": self.calculate_take_profit(entry_price, side),
            "timestamp": datetime.now()
        }
    
    def remove_position(self, symbol: str, exit_price: float) -> float:
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos["side"].upper() == "BUY":
                pnl = (exit_price - pos["entry_price"]) * pos["qty"]
            else:
                pnl = (pos["entry_price"] - exit_price) * pos["qty"]
            self.daily_pnl += pnl
            del self.positions[symbol]
            return pnl
        return 0.0
    
    def update_daily_pnl(self, pnl: float):
        self.daily_pnl += pnl
    
    def reset_daily(self):
        self.daily_pnl = 0.0
        self.positions.clear()