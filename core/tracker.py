"""
Trading Tracker - Activity tracking module.

Inspired by Career-Ops tracker pattern (data/applications.md).
Maintains structured records of all trading activities including
trades, positions, and signals.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a completed trade."""
    id: str
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    exit_price: float
    qty: int
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    status: str  # WIN, LOSS, BREAKEVEN
    order_id: str
    exit_order_id: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: Optional[str] = None
    notes: Optional[str] = None
    paper: bool = False


@dataclass
class PositionRecord:
    """Record of an active position."""
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
    
    def update_price(self, current_price: float):
        """Update current price and unrealized P&L."""
        self.current_price = current_price
        if self.side == "BUY":
            self.unrealized_pnl = (current_price - self.entry_price) * self.qty
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.qty


@dataclass
class SignalRecord:
    """Record of a generated signal."""
    id: str
    symbol: str
    signal: str  # BUY, SELL, HOLD
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
    Tracks all trading activities in structured format.
    
    Inspired by Career-Ops data/applications.md pattern.
    Maintains:
    - Trade history (completed trades with P&L)
    - Position log (active and closed positions)
    - Signal history (all generated signals)
    
    Data is stored in:
    - data/trades.md - Completed trades
    - data/positions.md - Position history
    - data/signals.md - Signal history
    - data/scan_history.tsv - Scan records
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.trades: List[TradeRecord] = []
        self.positions: Dict[str, PositionRecord] = {}
        self.signals: List[SignalRecord] = []
        
        self._trade_counter = 0
        self._signal_counter = 0
        
        self._load_existing_data()
        
        logger.info(f"TradingTracker initialized with data directory: {data_dir}")
    
    def _load_existing_data(self):
        """Load existing tracking data."""
        # Load trades
        trades_file = self.data_dir / "trades.md"
        if trades_file.exists():
            self._parse_trades_file(trades_file)
        else:
            self._create_trades_file()
        
        # Load positions
        positions_file = self.data_dir / "positions.md"
        if positions_file.exists():
            self._parse_positions_file(positions_file)
        else:
            self._create_positions_file()
        
        # Load signals
        signals_file = self.data_dir / "signals.md"
        if signals_file.exists():
            self._parse_signals_file(signals_file)
        else:
            self._create_signals_file()
    
    def _create_trades_file(self):
        """Create initial trades tracking file."""
        content = """# Trade History

Complete history of all executed trades with P&L.

| # | Date | Symbol | Side | Entry | Exit | Qty | P&L | P&L% | Status | Strategy | Paper | Notes |
|---|------|--------|------|-------|------|-----|-----|------|--------|----------|-------|-------|
"""
        (self.data_dir / "trades.md").write_text(content)
    
    def _create_positions_file(self):
        """Create initial positions tracking file."""
        content = """# Position History

Active and closed positions.

| # | Date | Symbol | Side | Entry | Current/Exit | Qty | Unrealized/Realized P&L | Status | Strategy | Paper | Notes |
|---|------|--------|------|-------|--------------|-----|------------------------|--------|----------|-------|-------|
"""
        (self.data_dir / "positions.md").write_text(content)
    
    def _create_signals_file(self):
        """Create initial signals tracking file."""
        content = """# Signal History

All generated signals with outcomes.

| # | Date | Symbol | Signal | Score | Price | Executed | Outcome | Notes |
|---|------|--------|--------|-------|-------|----------|---------|-------|
"""
        (self.data_dir / "signals.md").write_text(content)
    
    def _parse_trades_file(self, filepath: Path):
        """Parse existing trades file."""
        # Implementation would parse markdown table
        # For now, just set counter based on file length
        lines = filepath.read_text().split('\n')
        data_lines = [l for l in lines if l.startswith('|') and not l.startswith('|---')]
        self._trade_counter = max(0, len(data_lines) - 1)  # Subtract header
    
    def _parse_positions_file(self, filepath: Path):
        """Parse existing positions file."""
        pass  # Similar to trades parsing
    
    def _parse_signals_file(self, filepath: Path):
        """Parse existing signals file."""
        lines = filepath.read_text().split('\n')
        data_lines = [l for l in lines if l.startswith('|') and not l.startswith('|---')]
        self._signal_counter = max(0, len(data_lines) - 1)
    
    def add_trade(self, trade: TradeRecord) -> str:
        """
        Add a completed trade to history.
        
        Args:
            trade: TradeRecord with trade details
            
        Returns:
            Trade ID
        """
        self._trade_counter += 1
        trade.id = f"{self._trade_counter:03d}"
        self.trades.append(trade)
        
        # Append to file
        self._append_trade_to_file(trade)
        
        logger.info(f"Trade recorded: {trade.id} - {trade.symbol} {trade.side} P&L: ₹{trade.pnl:.2f}")
        return trade.id
    
    def _append_trade_to_file(self, trade: TradeRecord):
        """Append trade to markdown file."""
        line = f"| {trade.id} | {trade.entry_time.strftime('%Y-%m-%d %H:%M')} | " \
               f"{trade.symbol} | {trade.side} | {trade.entry_price:.2f} | " \
               f"{trade.exit_price:.2f} | {trade.qty} | {trade.pnl:.2f} | " \
               f"{trade.pnl_pct:.2f}% | {trade.status} | {trade.strategy or '-'} | " \
               f"{'Yes' if trade.paper else 'No'} | {trade.notes or '-'} |"
        
        filepath = self.data_dir / "trades.md"
        content = filepath.read_text()
        content += line + '\n'
        filepath.write_text(content)
    
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
        paper: bool = False
    ) -> str:
        """
        Add a new position.
        
        Args:
            symbol: Trading symbol
            side: BUY or SELL
            entry_price: Entry price
            qty: Quantity
            order_id: Order ID
            stop_loss: Stop loss price
            take_profit: Take profit price
            strategy: Strategy name
            paper: Paper trading flag
            
        Returns:
            Position ID
        """
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
            unrealized_pnl=0.0,
            strategy=strategy,
            paper=paper
        )
        
        self.positions[symbol] = position
        
        # Append to file
        self._append_position_to_file(position, "OPEN")
        
        logger.info(f"Position opened: {position_id} - {symbol} {side} @ {entry_price}")
        return position_id
    
    def _append_position_to_file(self, position: PositionRecord, status: str):
        """Append position to markdown file."""
        line = f"| {position.id} | {position.entry_time.strftime('%Y-%m-%d %H:%M')} | " \
               f"{position.symbol} | {position.side} | {position.entry_price:.2f} | " \
               f"{position.current_price:.2f} | {position.qty} | " \
               f"{position.unrealized_pnl:.2f} | {status} | " \
               f"{position.strategy or '-'} | {'Yes' if position.paper else 'No'} | - |"
        
        filepath = self.data_dir / "positions.md"
        content = filepath.read_text()
        content += line + '\n'
        filepath.write_text(content)
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_order_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[TradeRecord]:
        """
        Close a position and record as completed trade.
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_order_id: Exit order ID
            notes: Optional notes
            
        Returns:
            TradeRecord if position was found and closed
        """
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate P&L
        if position.side == "BUY":
            pnl = (exit_price - position.entry_price) * position.qty
        else:
            pnl = (position.entry_price - exit_price) * position.qty
        
        pnl_pct = (pnl / (position.entry_price * position.qty)) * 100
        
        # Determine status
        if pnl > 0:
            status = "WIN"
        elif pnl < 0:
            status = "LOSS"
        else:
            status = "BREAKEVEN"
        
        # Create trade record
        trade = TradeRecord(
            id="",  # Will be assigned by add_trade
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            qty=position.qty,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=pnl,
            pnl_pct=pnl_pct,
            status=status,
            order_id=position.order_id,
            exit_order_id=exit_order_id,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            strategy=position.strategy,
            notes=notes,
            paper=position.paper
        )
        
        # Add to trades
        self.add_trade(trade)
        
        # Remove from positions
        del self.positions[symbol]
        
        # Update position file
        self._append_position_to_file(position, "CLOSED")
        
        logger.info(f"Position closed: {symbol} P&L: ₹{pnl:.2f} ({pnl_pct:.2f}%)")
        
        return trade
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update current price for a position."""
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)
    
    def add_signal(
        self,
        symbol: str,
        signal: str,
        score: float,
        price: float,
        indicators: Optional[Dict[str, float]] = None,
        patterns: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Record a generated signal.
        
        Args:
            symbol: Trading symbol
            signal: BUY, SELL, or HOLD
            score: Signal score (0-100)
            price: Current price
            indicators: Technical indicators
            patterns: Detected patterns
            notes: Optional notes
            
        Returns:
            Signal ID
        """
        self._signal_counter += 1
        signal_id = f"{self._signal_counter:03d}"
        
        signal_record = SignalRecord(
            id=signal_id,
            symbol=symbol,
            signal=signal,
            score=score,
            timestamp=datetime.now(),
            price=price,
            indicators=indicators or {},
            patterns=patterns or [],
            executed=False,
            notes=notes
        )
        
        self.signals.append(signal_record)
        
        # Append to file
        self._append_signal_to_file(signal_record)
        
        return signal_id
    
    def _append_signal_to_file(self, signal: SignalRecord):
        """Append signal to markdown file."""
        line = f"| {signal.id} | {signal.timestamp.strftime('%Y-%m-%d %H:%M')} | " \
               f"{signal.symbol} | {signal.signal} | {signal.score:.1f} | " \
               f"{signal.price:.2f} | {'Yes' if signal.executed else 'No'} | " \
               f"{signal.execution_result or '-'} | {signal.notes or '-'} |"
        
        filepath = self.data_dir / "signals.md"
        content = filepath.read_text()
        content += line + '\n'
        filepath.write_text(content)
    
    def update_signal_executed(self, signal_id: str, result: str):
        """Mark a signal as executed with result."""
        for signal in self.signals:
            if signal.id == signal_id:
                signal.executed = True
                signal.execution_result = result
                break
    
    def get_active_positions(self) -> Dict[str, PositionRecord]:
        """Get all active positions."""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[PositionRecord]:
        """Get position for a specific symbol."""
        return self.positions.get(symbol)
    
    def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[TradeRecord]:
        """
        Get trades with optional filters.
        
        Args:
            symbol: Filter by symbol
            start_date: Filter by start date
            end_date: Filter by end date
            status: Filter by status (WIN, LOSS, BREAKEVEN)
            
        Returns:
            List of matching TradeRecord
        """
        filtered = self.trades
        
        if symbol:
            filtered = [t for t in filtered if t.symbol == symbol]
        
        if start_date:
            filtered = [t for t in filtered if t.entry_time >= start_date]
        
        if end_date:
            filtered = [t for t in filtered if t.exit_time <= end_date]
        
        if status:
            filtered = [t for t in filtered if t.status == status]
        
        return filtered
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get summary for a specific day.
        
        Args:
            date: Date to summarize (default: today)
            
        Returns:
            Dictionary with summary statistics
        """
        if date is None:
            date = datetime.now()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        daily_trades = self.get_trades(start_date=start_of_day, end_date=end_of_day)
        
        wins = [t for t in daily_trades if t.status == "WIN"]
        losses = [t for t in daily_trades if t.status == "LOSS"]
        
        total_pnl = sum(t.pnl for t in daily_trades)
        win_count = len(wins)
        loss_count = len(losses)
        total_count = len(daily_trades)
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'total_trades': total_count,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_count / total_count * 100 if total_count > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': sum(t.pnl for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t.pnl for t in losses) / len(losses) if losses else 0,
            'active_positions': len(self.positions)
        }
    
    def export_to_json(self, filepath: str, data_type: str = "trades"):
        """
        Export tracking data to JSON.
        
        Args:
            filepath: Output file path
            data_type: 'trades', 'positions', or 'signals'
        """
        if data_type == "trades":
            data = [asdict(t) for t in self.trades]
        elif data_type == "positions":
            data = {k: asdict(v) for k, v in self.positions.items()}
        elif data_type == "signals":
            data = [asdict(s) for s in self.signals]
        else:
            raise ValueError(f"Unknown data type: {data_type}")
        
        # Convert datetime objects to strings
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        with open(filepath, 'w') as f:
            json.dump(data, f, default=serialize_datetime, indent=2)
        
        logger.info(f"Exported {data_type} to {filepath}")
