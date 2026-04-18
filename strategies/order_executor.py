"""Auto-order execution with risk controls."""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TradeConfig:
    """Configuration for trade execution."""
    # Score threshold for execution (0-100)
    score_threshold: int = 75

    # Position sizing
    position_size_percent: float = 10.0  # % of capital per trade
    max_position_value: float = 50000.0   # Max ₹ per trade
    min_position_value: float = 10000.0   # Min ₹ per trade

    # Risk controls
    stop_loss_percent: float = 2.0        # Default SL %
    target_profit_percent: float = 4.0    # Default target %
    max_trades_per_day: int = 5
    max_concurrent_positions: int = 3

    # Trading hours
    auto_execute: bool = False           # Require confirmation by default


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    order_id: Optional[str]
    symbol: str
    side: str
    qty: int
    price: float
    stop_loss: float
    target: float
    error: Optional[str] = None


class OrderExecutor:
    """Handles auto-order placement with risk management."""

    def __init__(self, fyers_client, config: Optional[TradeConfig] = None):
        self.fyers_client = fyers_client
        self.config = config or TradeConfig()
        self.trades_today: int = 0
        self.active_positions: Dict[str, Dict] = {}
        self.daily_pnl: float = 0.0

    def calculate_position_size(self, capital: float, price: float,
                               score: int) -> int:
        """
        Calculate position size based on capital and score.

        Higher score = larger position (up to max)
        """
        # Base position size (% of capital)
        base_value = capital * (self.config.position_size_percent / 100)

        # Scale by score (75% -> 1.0x, 100% -> 1.5x)
        score_multiplier = 0.5 + (score / 100)

        position_value = base_value * score_multiplier

        # Apply limits
        position_value = min(position_value, self.config.max_position_value)
        position_value = max(position_value, self.config.min_position_value)

        # Calculate quantity
        qty = int(position_value / price)

        # Ensure minimum 1 share
        return max(qty, 1)

    def calculate_stop_loss(self, price: float, side: str,
                           atr: Optional[float] = None) -> float:
        """
        Calculate stop-loss price.

        Args:
            price: Entry price
            side: BUY or SELL
            atr: Optional ATR for volatility-based SL

        Returns:
            Stop-loss price
        """
        if side == "BUY":
            # SL below entry
            sl_price = price * (1 - self.config.stop_loss_percent / 100)
        else:
            # SL above entry for short
            sl_price = price * (1 + self.config.stop_loss_percent / 100)

        # Round to 2 decimal places
        return round(sl_price, 2)

    def calculate_target(self, price: float, side: str) -> float:
        """Calculate profit target price."""
        if side == "BUY":
            target = price * (1 + self.config.target_profit_percent / 100)
        else:
            target = price * (1 - self.config.target_profit_percent / 100)

        return round(target, 2)

    def can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed based on risk controls."""
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Max trades per day ({self.config.max_trades_per_day}) reached"

        if len(self.active_positions) >= self.config.max_concurrent_positions:
            return False, f"Max positions ({self.config.max_concurrent_positions}) reached"

        return True, "OK"

    def execute_trade(self, symbol: str, signal: str, price: float,
                      score: int, capital: float,
                      confirm: bool = True) -> TradeResult:
        """
        Execute a trade with full risk management.

        Args:
            symbol: Stock symbol
            signal: BUY or SELL
            price: Current price
            score: Signal score (0-100)
            capital: Available capital
            confirm: If True, log only and don't place order

        Returns:
            TradeResult with execution details
        """
        from api import place_order, get_funds

        # Check trading permission
        can_trade, reason = self.can_trade()
        if not can_trade:
            return TradeResult(
                success=False, order_id=None,
                symbol=symbol, side=signal, qty=0, price=price,
                stop_loss=0, target=0, error=reason
            )

        # Calculate position size
        qty = self.calculate_position_size(capital, price, score)

        # Calculate SL and target
        stop_loss = self.calculate_stop_loss(price, signal)
        target = self.calculate_target(price, signal)

        # Get available funds
        try:
            funds = get_funds(self.fyers_client)
            available = funds.get("available_cash", 0)

            required = qty * price
            if required > available:
                return TradeResult(
                    success=False, order_id=None,
                    symbol=symbol, side=signal, qty=qty, price=price,
                    stop_loss=stop_loss, target=target,
                    error=f"Insufficient funds. Required: ₹{required:.2f}, Available: ₹{available:.2f}"
                )
        except Exception as e:
            logger.error(f"Error checking funds: {e}")

        # If not auto-executing, just return planned trade
        if confirm and not self.config.auto_execute:
            return TradeResult(
                success=True, order_id="PENDING",
                symbol=symbol, side=signal, qty=qty, price=price,
                stop_loss=stop_loss, target=target,
                error="Confirmation required - use --auto-execute to place order"
            )

        # Place the order
        try:
            result = place_order(
                self.fyers_client,
                symbol=symbol,
                qty=qty,
                side=signal.lower(),
                order_type="MARKET",
                product_type="MIS"
            )

            if "error" in result:
                return TradeResult(
                    success=False, order_id=None,
                    symbol=symbol, side=signal, qty=qty, price=price,
                    stop_loss=stop_loss, target=target,
                    error=result["error"]
                )

            # Track the trade
            order_id = result.get("order_id", "UNKNOWN")
            self.trades_today += 1
            self.active_positions[symbol] = {
                "order_id": order_id,
                "side": signal,
                "qty": qty,
                "entry": price,
                "stop_loss": stop_loss,
                "target": target,
                "timestamp": datetime.now()
            }

            return TradeResult(
                success=True, order_id=order_id,
                symbol=symbol, side=signal, qty=qty, price=price,
                stop_loss=stop_loss, target=target
            )

        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return TradeResult(
                success=False, order_id=None,
                symbol=symbol, side=signal, qty=qty, price=price,
                stop_loss=stop_loss, target=target,
                error=str(e)
            )

    def close_position(self, symbol: str) -> bool:
        """Close an active position."""
        if symbol not in self.active_positions:
            return False

        position = self.active_positions[symbol]
        opposite_side = "SELL" if position["side"] == "BUY" else "BUY"

        try:
            from api import place_order
            result = place_order(
                self.fyers_client,
                symbol=symbol,
                qty=position["qty"],
                side=opposite_side.lower(),
                order_type="MARKET",
                product_type="MIS"
            )

            if "error" not in result:
                del self.active_positions[symbol]
                return True

        except Exception as e:
            logger.error(f"Error closing position: {e}")

        return False

    def get_position_summary(self) -> Dict:
        """Get summary of active positions."""
        return {
            "active_positions": len(self.active_positions),
            "trades_today": self.trades_today,
            "max_trades": self.config.max_trades_per_day,
            "positions": self.active_positions
        }

    def reset_daily_stats(self):
        """Reset daily trading statistics."""
        self.trades_today = 0
        self.daily_pnl = 0.0
