"""
Auto-order execution with risk controls.

FIXES:
- execute_auto_trade in live_smc_engine used hardcoded qty=10; position sizing
  now always comes from calculate_position_size() which respects risk config
- can_trade() return type annotation fixed (tuple[bool, str] → Tuple[bool, str])
- paper_trading flag default changed to True (safe default)
- Added input validation for symbol, qty, price
- Removed duplicate position tracking that could overwrite tracker state
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TradeConfig:
    """Runtime configuration for the order executor."""

    paper_trading: bool = True            # Always default to paper (safe)
    score_threshold: int = 75

    # Position sizing
    position_size_percent: float = 10.0   # % of capital per trade
    max_position_value: float = 50_000.0
    min_position_value: float = 5_000.0

    # Risk controls
    stop_loss_percent: float = 2.0
    target_profit_percent: float = 4.0
    max_trades_per_day: int = 5
    max_concurrent_positions: int = 3

    # Execution mode
    auto_execute: bool = False            # Require confirmation by default


@dataclass
class TradeResult:
    """Outcome of a single trade execution attempt."""

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
    """Handles order placement with integrated risk management."""

    def __init__(
        self,
        fyers_client,
        tracker=None,
        config: Optional[TradeConfig] = None,
    ) -> None:
        self.fyers_client = fyers_client
        self.tracker = tracker
        self.config = config or TradeConfig()

        self.trades_today: int = 0
        self.active_positions: Dict[str, Dict] = {}
        self.daily_pnl: float = 0.0

    # ------------------------------------------------------------------
    # Risk checks
    # ------------------------------------------------------------------

    def can_trade(self) -> Tuple[bool, str]:
        """Return (allowed, reason) based on current risk state."""
        if self.trades_today >= self.config.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.config.max_trades_per_day})"
        if len(self.active_positions) >= self.config.max_concurrent_positions:
            return False, f"Max concurrent positions reached ({self.config.max_concurrent_positions})"
        return True, "OK"

    # ------------------------------------------------------------------
    # Sizing & levels
    # ------------------------------------------------------------------

    def calculate_position_size(
        self, capital: float, price: float, score: int
    ) -> int:
        """
        Risk-proportional position sizing.

        Higher signal score → slightly larger position (up to 1.5× base).
        Always clamped to [min_position_value, max_position_value].
        """
        if price <= 0 or capital <= 0:
            return 1

        base_value = capital * (self.config.position_size_percent / 100)
        # Score-based multiplier: score=75 → ×1.0, score=100 → ×1.25
        multiplier = 0.5 + (min(score, 100) / 100)
        position_value = base_value * multiplier

        position_value = max(self.config.min_position_value, min(self.config.max_position_value, position_value))
        qty = max(1, int(position_value / price))
        return qty

    def calculate_stop_loss(self, price: float, side: str) -> float:
        pct = self.config.stop_loss_percent / 100
        return round(price * (1 - pct) if side == "BUY" else price * (1 + pct), 2)

    def calculate_target(self, price: float, side: str) -> float:
        pct = self.config.target_profit_percent / 100
        return round(price * (1 + pct) if side == "BUY" else price * (1 - pct), 2)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_trade(
        self,
        symbol: str,
        signal: str,
        price: float,
        score: int,
        capital: float,
        confirm: bool = True,
    ) -> TradeResult:
        """
        Execute (or simulate) a trade with full risk management.

        FIX: qty is now always calculated from capital/risk config,
        never hardcoded.
        """
        if not symbol:
            return self._error_result(symbol, signal, 0, price, "Empty symbol")
        if price <= 0:
            return self._error_result(symbol, signal, 0, price, f"Invalid price: {price}")

        # Log signal
        if self.tracker:
            try:
                self.tracker.add_signal(symbol, signal, score, price)
            except Exception:
                logger.exception("Failed to log signal for %s", symbol)

        allowed, reason = self.can_trade()
        if not allowed:
            return self._error_result(symbol, signal, 0, price, reason)

        qty = self.calculate_position_size(capital, price, score)
        stop_loss = self.calculate_stop_loss(price, signal)
        target = self.calculate_target(price, signal)

        # Require confirmation unless auto_execute is explicitly on
        if confirm and not self.config.auto_execute:
            return TradeResult(
                success=True,
                order_id="PENDING_CONFIRM",
                symbol=symbol,
                side=signal,
                qty=qty,
                price=price,
                stop_loss=stop_loss,
                target=target,
                error="Awaiting user confirmation",
            )

        order_id = f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if not self.config.paper_trading:
            result = self._place_live_order(symbol, signal, qty, price, capital)
            if not result.success:
                return result
            order_id = result.order_id or order_id

        # Track position
        if self.tracker:
            try:
                self.tracker.add_position(
                    symbol=symbol,
                    side=signal,
                    entry_price=price,
                    qty=qty,
                    order_id=order_id,
                    stop_loss=stop_loss,
                    take_profit=target,
                    strategy="OrderExecutor",
                    paper=self.config.paper_trading,
                )
            except Exception:
                logger.exception("Failed to track position for %s", symbol)

        self.trades_today += 1
        self.active_positions[symbol] = {
            "order_id": order_id,
            "side": signal,
            "qty": qty,
            "entry": price,
            "stop_loss": stop_loss,
            "target": target,
            "timestamp": datetime.now(),
        }

        logger.info(
            "%s %s %s qty=%d @ %.2f SL=%.2f TP=%.2f [%s]",
            "PAPER" if self.config.paper_trading else "LIVE",
            signal, symbol, qty, price, stop_loss, target, order_id,
        )

        return TradeResult(
            success=True,
            order_id=order_id,
            symbol=symbol,
            side=signal,
            qty=qty,
            price=price,
            stop_loss=stop_loss,
            target=target,
        )

    def _place_live_order(
        self, symbol: str, signal: str, qty: int, price: float, capital: float
    ) -> TradeResult:
        """Place a real order via the Fyers API."""
        from api import get_funds, place_order

        try:
            funds = get_funds(self.fyers_client)
            available = funds.get("available_cash", 0)
            if qty * price > available:
                return self._error_result(
                    symbol, signal, qty, price,
                    f"Insufficient funds: need ₹{qty * price:.0f}, have ₹{available:.0f}",
                )
        except Exception as e:
            return self._error_result(symbol, signal, qty, price, f"Funds check failed: {e}")

        try:
            result = place_order(
                self.fyers_client,
                symbol=symbol,
                qty=qty,
                side=signal.lower(),
                order_type="MARKET",
                product_type="MIS",
            )
            if "error" in result:
                return self._error_result(symbol, signal, qty, price, result["error"])
            return TradeResult(
                success=True,
                order_id=result.get("order_id", "UNKNOWN"),
                symbol=symbol, side=signal, qty=qty, price=price,
                stop_loss=self.calculate_stop_loss(price, signal),
                target=self.calculate_target(price, signal),
            )
        except Exception as e:
            return self._error_result(symbol, signal, qty, price, str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_result(
        symbol: str, side: str, qty: int, price: float, error: str
    ) -> TradeResult:
        return TradeResult(
            success=False, order_id=None,
            symbol=symbol, side=side, qty=qty, price=price,
            stop_loss=0.0, target=0.0, error=error,
        )

    def close_position(self, symbol: str) -> bool:
        if symbol not in self.active_positions:
            return False
        pos = self.active_positions[symbol]
        opposite = "SELL" if pos["side"] == "BUY" else "BUY"
        try:
            from api import place_order
            result = place_order(
                self.fyers_client,
                symbol=symbol,
                qty=pos["qty"],
                side=opposite.lower(),
                order_type="MARKET",
                product_type="MIS",
            )
            if "error" not in result:
                del self.active_positions[symbol]
                return True
        except Exception:
            logger.exception("Error closing position %s", symbol)
        return False

    def reset_daily_stats(self) -> None:
        self.trades_today = 0
        self.daily_pnl = 0.0

    def get_position_summary(self) -> Dict:
        return {
            "active_positions": len(self.active_positions),
            "trades_today": self.trades_today,
            "max_trades": self.config.max_trades_per_day,
            "positions": self.active_positions,
        }
