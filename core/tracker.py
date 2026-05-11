"""
Trading Tracker – Activity tracking module.

FIXES:
- _append_*_to_file() now appends a single line instead of read-entire-file-then-rewrite
  (previously O(n) reads on every single trade write)
- Added validation: exit_price > 0 in close_position()
- Added validation: qty > 0 in add_position()
- Datetime serialisation in export_to_json() now handles all datetime fields correctly
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    qty: int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    status: str            # WIN | LOSS | BREAKEVEN
    order_id: str
    exit_order_id: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None
    notes: Optional[str] = None
    paper: bool = False


@dataclass
class PositionRecord:
    id: str
    symbol: str
    side: str
    entry_price: float
    qty: int
    entry_time: datetime
    order_id: str
    stop_loss: float
    take_profit: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    strategy: Optional[str] = None
    paper: bool = False

    def update_price(self, current_price: float) -> None:
        self.current_price = current_price
        if self.side == "BUY":
            self.unrealized_pnl = (current_price - self.entry_price) * self.qty
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.qty


@dataclass
class SignalRecord:
    id: str
    symbol: str
    signal: str
    score: float
    timestamp: datetime
    price: float
    indicators: Dict[str, float] = field(default_factory=dict)
    patterns: List[str] = field(default_factory=list)
    executed: bool = False
    execution_result: Optional[str] = None
    notes: Optional[str] = None


class TradingTracker:
    """
    Tracks trades, positions, and signals using markdown flat files.

    Data directory layout:
        data/trades.md    – completed trades
        data/positions.md – position lifecycle
        data/signals.md   – signal history
    """

    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades: List[TradeRecord] = []
        self.positions: Dict[str, PositionRecord] = {}
        self.signals: List[SignalRecord] = []

        self._trade_counter: int = 0
        self._signal_counter: int = 0

        self._init_files()

    # ------------------------------------------------------------------
    # File initialisation
    # ------------------------------------------------------------------

    def _init_files(self) -> None:
        """Create tracking markdown files if they do not already exist."""
        self._ensure_file(
            "trades.md",
            "# Trade History\n\n"
            "| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | P&L% "
            "| Status | Strategy | Paper | Notes |\n"
            "|---|------|--------|------|-------|------|-----|-----|------|"
            "--------|----------|-------|-------|\n",
        )
        self._ensure_file(
            "positions.md",
            "# Position History\n\n"
            "| # | Date | Symbol | Side | Entry | Current/Exit | Qty "
            "| Unrealized/Realized P&L | Status | Strategy | Paper | Notes |\n"
            "|---|------|--------|------|-------|--------------|-----|"
            "------------------------|--------|----------|-------|-------|\n",
        )
        self._ensure_file(
            "signals.md",
            "# Signal History\n\n"
            "| # | Date | Symbol | Signal | Score | Price | Executed | Outcome | Notes |\n"
            "|---|------|--------|--------|-------|-------|----------|---------|-------|\n",
        )
        # Set counters based on existing data
        self._trade_counter = self._count_rows("trades.md")
        self._signal_counter = self._count_rows("signals.md")

    def _ensure_file(self, filename: str, header: str) -> None:
        path = self.data_dir / filename
        if not path.exists():
            path.write_text(header, encoding="utf-8")

    def _count_rows(self, filename: str) -> int:
        """Count data rows (non-header table lines) in a markdown file."""
        path = self.data_dir / filename
        if not path.exists():
            return 0
        lines = path.read_text(encoding="utf-8").splitlines()
        return sum(1 for l in lines if l.startswith("|") and not l.startswith("|---"))

    # ------------------------------------------------------------------
    # Efficient file append (FIX: no longer reads entire file)
    # ------------------------------------------------------------------

    def _append_line(self, filename: str, line: str) -> None:
        path = self.data_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    def add_trade(self, trade: TradeRecord) -> str:
        self._trade_counter += 1
        trade.id = f"{self._trade_counter:03d}"
        self.trades.append(trade)
        self._append_line("trades.md", self._format_trade_row(trade))
        logger.info("Trade #%s recorded: %s %s P&L=₹%.2f", trade.id, trade.symbol, trade.side, trade.pnl)
        return trade.id

    def _format_trade_row(self, t: TradeRecord) -> str:
        return (
            f"| {t.id} | {t.entry_time.strftime('%Y-%m-%d %H:%M')} | {t.symbol} "
            f"| {t.side} | {t.entry_price:.2f} | {t.exit_price:.2f} | {t.qty} "
            f"| {t.pnl:.2f} | {t.pnl_pct:.2f}% | {t.status} "
            f"| {t.strategy or '-'} | {'Yes' if t.paper else 'No'} | {t.notes or '-'} |"
        )

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        qty: int,
        order_id: str,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        strategy: Optional[str] = None,
        paper: bool = False,
    ) -> str:
        if qty <= 0:
            raise ValueError(f"qty must be > 0, got {qty}")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be > 0, got {entry_price}")

        position_id = f"POS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        position = PositionRecord(
            id=position_id,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            qty=qty,
            entry_time=datetime.now(),
            order_id=order_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=entry_price,
            strategy=strategy,
            paper=paper,
        )
        self.positions[symbol] = position
        self._append_line("positions.md", self._format_position_row(position, "OPEN"))
        logger.info("Position opened: %s %s @ %.2f qty=%d", symbol, side, entry_price, qty)
        return position_id

    def _format_position_row(self, p: PositionRecord, status: str) -> str:
        return (
            f"| {p.id} | {p.entry_time.strftime('%Y-%m-%d %H:%M')} | {p.symbol} "
            f"| {p.side} | {p.entry_price:.2f} | {p.current_price:.2f} | {p.qty} "
            f"| {p.unrealized_pnl:.2f} | {status} "
            f"| {p.strategy or '-'} | {'Yes' if p.paper else 'No'} | - |"
        )

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_order_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[TradeRecord]:
        if exit_price <= 0:
            raise ValueError(f"exit_price must be > 0, got {exit_price}")

        position = self.positions.get(symbol)
        if position is None:
            logger.warning("No open position found for %s", symbol)
            return None

        if position.side == "BUY":
            pnl = (exit_price - position.entry_price) * position.qty
        else:
            pnl = (position.entry_price - exit_price) * position.qty

        cost_basis = position.entry_price * position.qty
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0

        if pnl > 0:
            status = "WIN"
        elif pnl < 0:
            status = "LOSS"
        else:
            status = "BREAKEVEN"

        trade = TradeRecord(
            id="",
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            qty=position.qty,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            status=status,
            order_id=position.order_id,
            exit_order_id=exit_order_id,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            strategy=position.strategy,
            notes=notes,
            paper=position.paper,
        )

        self.add_trade(trade)
        del self.positions[symbol]
        self._append_line("positions.md", self._format_position_row(position, "CLOSED"))
        logger.info("Position closed: %s P&L=₹%.2f (%.2f%%)", symbol, pnl, pnl_pct)
        return trade

    def update_position_price(self, symbol: str, current_price: float) -> None:
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def add_signal(
        self,
        symbol: str,
        signal: str,
        score: float,
        price: float,
        indicators: Optional[Dict[str, float]] = None,
        patterns: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> str:
        self._signal_counter += 1
        signal_id = f"{self._signal_counter:03d}"
        record = SignalRecord(
            id=signal_id,
            symbol=symbol,
            signal=signal,
            score=score,
            timestamp=datetime.now(),
            price=price,
            indicators=indicators or {},
            patterns=patterns or [],
            notes=notes,
        )
        self.signals.append(record)
        self._append_line("signals.md", self._format_signal_row(record))
        return signal_id

    def _format_signal_row(self, s: SignalRecord) -> str:
        return (
            f"| {s.id} | {s.timestamp.strftime('%Y-%m-%d %H:%M')} | {s.symbol} "
            f"| {s.signal} | {s.score:.1f} | {s.price:.2f} "
            f"| {'Yes' if s.executed else 'No'} | {s.execution_result or '-'} "
            f"| {s.notes or '-'} |"
        )

    def update_signal_executed(self, signal_id: str, result: str) -> None:
        for s in self.signals:
            if s.id == signal_id:
                s.executed = True
                s.execution_result = result
                return

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_positions(self) -> Dict[str, PositionRecord]:
        return dict(self.positions)

    def get_position(self, symbol: str) -> Optional[PositionRecord]:
        return self.positions.get(symbol)

    def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
    ) -> List[TradeRecord]:
        result = self.trades
        if symbol:
            result = [t for t in result if t.symbol == symbol]
        if start_date:
            result = [t for t in result if t.entry_time >= start_date]
        if end_date:
            result = [t for t in result if t.exit_time <= end_date]
        if status:
            result = [t for t in result if t.status == status]
        return result

    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        date = date or datetime.now()
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        daily = self.get_trades(start_date=start, end_date=end)

        wins = [t for t in daily if t.status == "WIN"]
        losses = [t for t in daily if t.status == "LOSS"]
        total = len(daily)

        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": (len(wins) / total * 100) if total else 0.0,
            "total_pnl": sum(t.pnl for t in daily),
            "avg_win": (sum(t.pnl for t in wins) / len(wins)) if wins else 0.0,
            "avg_loss": (sum(t.pnl for t in losses) / len(losses)) if losses else 0.0,
            "active_positions": len(self.positions),
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_to_json(self, filepath: str, data_type: str = "trades") -> None:
        data_map = {
            "trades": lambda: [asdict(t) for t in self.trades],
            "positions": lambda: {k: asdict(v) for k, v in self.positions.items()},
            "signals": lambda: [asdict(s) for s in self.signals],
        }
        if data_type not in data_map:
            raise ValueError(f"Unknown data_type '{data_type}'. Choose from: {list(data_map)}")

        data = data_map[data_type]()

        def _serialise(obj: Any) -> str:
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, default=_serialise, indent=2)

        logger.info("Exported %s to %s", data_type, filepath)
