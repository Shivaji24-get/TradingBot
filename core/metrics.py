"""
Metrics Collection - Performance analytics module.

Inspired by Career-Ops reporting and analytics patterns.
Collects and calculates trading performance metrics including:
- Win/loss ratios
- Risk-adjusted returns (Sharpe ratio)
- Maximum drawdown
- Trade frequency and duration
- Signal accuracy
"""

import logging
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TradingMetrics:
    """Complete trading performance metrics."""
    # Basic stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    
    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    
    # Percentages
    win_rate: float = 0.0
    loss_rate: float = 0.0
    
    # Averages
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    avg_trade_pnl: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Consecutive
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    current_consecutive: int = 0
    
    # Duration
    avg_trade_duration: float = 0.0  # minutes
    
    # Signal metrics
    total_signals: int = 0
    executed_signals: int = 0
    signal_accuracy: float = 0.0
    
    # Period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class DailySnapshot:
    """Daily performance snapshot."""
    date: str
    trades: int = 0
    pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    cumulative_pnl: float = 0.0
    drawdown: float = 0.0


class MetricsCollector:
    """
    Collects and calculates trading performance metrics.
    
    Usage:
        collector = MetricsCollector(tracker)
        metrics = collector.calculate_metrics()
        daily = collector.get_daily_series()
    """
    
    def __init__(self, tracker: Any, risk_free_rate: float = 0.06):
        """
        Initialize metrics collector.
        
        Args:
            tracker: TradingTracker instance
            risk_free_rate: Annual risk-free rate (default: 6% for India)
        """
        self.tracker = tracker
        self.risk_free_rate = risk_free_rate
        self.daily_snapshots: List[DailySnapshot] = []
        
        logger.info("MetricsCollector initialized")
    
    def calculate_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TradingMetrics:
        """
        Calculate comprehensive trading metrics.
        
        Args:
            start_date: Start of period (default: all history)
            end_date: End of period (default: now)
            
        Returns:
            TradingMetrics with calculated statistics
        """
        trades = self.tracker.get_trades(start_date=start_date, end_date=end_date)
        
        if not trades:
            return TradingMetrics(start_date=start_date, end_date=end_date)
        
        metrics = TradingMetrics(
            start_date=start_date or trades[0].entry_time,
            end_date=end_date or datetime.now()
        )
        
        # Basic counts
        metrics.total_trades = len(trades)
        
        wins = [t for t in trades if t.status == "WIN"]
        losses = [t for t in trades if t.status == "LOSS"]
        breakevens = [t for t in trades if t.status == "BREAKEVEN"]
        
        metrics.winning_trades = len(wins)
        metrics.losing_trades = len(losses)
        metrics.breakeven_trades = len(breakevens)
        
        # P&L calculations
        metrics.gross_profit = sum(t.pnl for t in wins)
        metrics.gross_loss = abs(sum(t.pnl for t in losses))
        metrics.net_pnl = sum(t.pnl for t in trades)
        
        # Win/Loss rates
        completed_trades = metrics.winning_trades + metrics.losing_trades
        if completed_trades > 0:
            metrics.win_rate = (metrics.winning_trades / completed_trades) * 100
            metrics.loss_rate = (metrics.losing_trades / completed_trades) * 100
        
        # Averages
        if wins:
            metrics.avg_profit = metrics.gross_profit / len(wins)
        if losses:
            metrics.avg_loss = metrics.gross_loss / len(losses)
        if trades:
            metrics.avg_trade_pnl = metrics.net_pnl / len(trades)
        
        # Profit factor
        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        else:
            metrics.profit_factor = float('inf') if metrics.gross_profit > 0 else 0
        
        # Drawdown calculation
        metrics.max_drawdown, metrics.max_drawdown_pct = self._calculate_drawdown(trades)
        
        # Consecutive wins/losses
        metrics.max_consecutive_wins, metrics.max_consecutive_losses = \
            self._calculate_consecutive(trades)
        
        # Average trade duration
        durations = []
        for trade in trades:
            duration = (trade.exit_time - trade.entry_time).total_seconds() / 60
            durations.append(duration)
        
        if durations:
            metrics.avg_trade_duration = sum(durations) / len(durations)
        
        # Signal metrics
        if self.tracker.signals:
            signals_in_period = [
                s for s in self.tracker.signals
                if (start_date is None or s.timestamp >= start_date) and
                   (end_date is None or s.timestamp <= end_date)
            ]
            metrics.total_signals = len(signals_in_period)
            metrics.executed_signals = sum(1 for s in signals_in_period if s.executed)
            
            if metrics.executed_signals > 0:
                # Signal accuracy: how many executed signals resulted in wins
                executed_wins = sum(
                    1 for t in wins
                    if any(s.executed and s.symbol == t.symbol 
                           for s in signals_in_period)
                )
                metrics.signal_accuracy = (executed_wins / metrics.executed_signals) * 100
        
        # Sharpe ratio (simplified - daily returns)
        metrics.sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        return metrics
    
    def _calculate_drawdown(self, trades: List[Any]) -> tuple[float, float]:
        """
        Calculate maximum drawdown.
        
        Returns:
            Tuple of (max drawdown amount, max drawdown percentage)
        """
        if not trades:
            return 0.0, 0.0
        
        # Sort by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        peak = 0.0
        max_dd = 0.0
        current_pnl = 0.0
        
        for trade in sorted_trades:
            current_pnl += trade.pnl
            
            if current_pnl > peak:
                peak = current_pnl
            
            drawdown = peak - current_pnl
            if drawdown > max_dd:
                max_dd = drawdown
        
        # Calculate percentage
        if peak > 0:
            max_dd_pct = (max_dd / peak) * 100
        else:
            max_dd_pct = 0.0
        
        return max_dd, max_dd_pct
    
    def _calculate_consecutive(self, trades: List[Any]) -> tuple[int, int]:
        """
        Calculate maximum consecutive wins and losses.
        
        Returns:
            Tuple of (max consecutive wins, max consecutive losses)
        """
        if not trades:
            return 0, 0
        
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in sorted_trades:
            if trade.status == "WIN":
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.status == "LOSS":
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
    
    def _calculate_sharpe_ratio(self, trades: List[Any]) -> float:
        """
        Calculate simplified Sharpe ratio based on daily returns.
        
        Uses daily P&L as returns. Annualized.
        """
        if not trades:
            return 0.0
        
        # Group trades by day
        daily_returns: Dict[str, float] = {}
        
        for trade in trades:
            day = trade.exit_time.strftime('%Y-%m-%d')
            if day not in daily_returns:
                daily_returns[day] = 0.0
            daily_returns[day] += trade.pnl
        
        if len(daily_returns) < 2:
            return 0.0
        
        returns = list(daily_returns.values())
        avg_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Daily risk-free rate (annual / 252 trading days)
        daily_rf = self.risk_free_rate / 252
        
        # Sharpe ratio (annualized)
        sharpe = ((avg_return - daily_rf) / std_dev) * math.sqrt(252)
        
        return sharpe
    
    def get_daily_series(
        self,
        days: int = 30
    ) -> List[DailySnapshot]:
        """
        Get daily performance series.
        
        Args:
            days: Number of days to include
            
        Returns:
            List of DailySnapshot
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        trades = self.tracker.get_trades(start_date=start_date, end_date=end_date)
        
        # Group by date
        daily_data: Dict[str, Dict] = {}
        
        for trade in trades:
            date = trade.exit_time.strftime('%Y-%m-%d')
            
            if date not in daily_data:
                daily_data[date] = {
                    'trades': 0,
                    'pnl': 0.0,
                    'wins': 0,
                    'losses': 0
                }
            
            daily_data[date]['trades'] += 1
            daily_data[date]['pnl'] += trade.pnl
            
            if trade.status == "WIN":
                daily_data[date]['wins'] += 1
            elif trade.status == "LOSS":
                daily_data[date]['losses'] += 1
        
        # Build series with cumulative P&L
        snapshots = []
        cumulative_pnl = 0.0
        peak = 0.0
        
        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            cumulative_pnl += data['pnl']
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            
            drawdown = peak - cumulative_pnl
            
            snapshot = DailySnapshot(
                date=date,
                trades=data['trades'],
                pnl=data['pnl'],
                wins=data['wins'],
                losses=data['losses'],
                cumulative_pnl=cumulative_pnl,
                drawdown=drawdown
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def generate_report(
        self,
        output_path: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """
        Generate metrics report.
        
        Args:
            output_path: Output file path (optional)
            format: 'json' or 'markdown'
            
        Returns:
            Report content as string
        """
        metrics = self.calculate_metrics()
        daily = self.get_daily_series(days=30)
        
        if format == "json":
            report = self._generate_json_report(metrics, daily)
        elif format == "markdown":
            report = self._generate_markdown_report(metrics, daily)
        else:
            raise ValueError(f"Unknown format: {format}")
        
        if output_path:
            Path(output_path).write_text(report)
            logger.info(f"Metrics report saved to {output_path}")
        
        return report
    
    def _generate_json_report(
        self,
        metrics: TradingMetrics,
        daily: List[DailySnapshot]
    ) -> str:
        """Generate JSON report."""
        data = {
            'generated_at': datetime.now().isoformat(),
            'metrics': {
                'total_trades': metrics.total_trades,
                'winning_trades': metrics.winning_trades,
                'losing_trades': metrics.losing_trades,
                'win_rate': round(metrics.win_rate, 2),
                'net_pnl': round(metrics.net_pnl, 2),
                'gross_profit': round(metrics.gross_profit, 2),
                'gross_loss': round(metrics.gross_loss, 2),
                'profit_factor': round(metrics.profit_factor, 2),
                'sharpe_ratio': round(metrics.sharpe_ratio, 2),
                'max_drawdown': round(metrics.max_drawdown, 2),
                'max_drawdown_pct': round(metrics.max_drawdown_pct, 2),
                'avg_trade_pnl': round(metrics.avg_trade_pnl, 2),
                'avg_trade_duration_min': round(metrics.avg_trade_duration, 2),
            },
            'daily_series': [
                {
                    'date': s.date,
                    'trades': s.trades,
                    'pnl': round(s.pnl, 2),
                    'cumulative_pnl': round(s.cumulative_pnl, 2),
                    'drawdown': round(s.drawdown, 2)
                }
                for s in daily
            ]
        }
        
        return json.dumps(data, indent=2)
    
    def _generate_markdown_report(
        self,
        metrics: TradingMetrics,
        daily: List[DailySnapshot]
    ) -> str:
        """Generate Markdown report."""
        lines = [
            "# Trading Performance Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Period:** {metrics.start_date.strftime('%Y-%m-%d') if metrics.start_date else 'N/A'} to {metrics.end_date.strftime('%Y-%m-%d') if metrics.end_date else 'N/A'}",
            "",
            "## Summary Statistics",
            "",
            f"- **Total Trades:** {metrics.total_trades}",
            f"- **Win Rate:** {metrics.win_rate:.2f}%",
            f"- **Net P&L:** ₹{metrics.net_pnl:,.2f}",
            f"- **Profit Factor:** {metrics.profit_factor:.2f}",
            f"- **Sharpe Ratio:** {metrics.sharpe_ratio:.2f}",
            "",
            "## Risk Metrics",
            "",
            f"- **Max Drawdown:** ₹{metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2f}%)",
            f"- **Average Profit:** ₹{metrics.avg_profit:,.2f}",
            f"- **Average Loss:** ₹{metrics.avg_loss:,.2f}",
            f"- **Max Consecutive Wins:** {metrics.max_consecutive_wins}",
            f"- **Max Consecutive Losses:** {metrics.max_consecutive_losses}",
            "",
            "## Recent Daily Performance (Last 30 Days)",
            "",
            "| Date | Trades | P&L | Cumulative | Drawdown |",
            "|------|--------|-----|------------|----------|"
        ]
        
        for snapshot in daily[-30:]:  # Last 30 days
            lines.append(
                f"| {snapshot.date} | {snapshot.trades} | "
                f"₹{snapshot.pnl:,.2f} | ₹{snapshot.cumulative_pnl:,.2f} | "
                f"₹{snapshot.drawdown:,.2f} |"
            )
        
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by TradingBot MetricsCollector*")
        
        return '\n'.join(lines)
    
    def get_summary_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for logging/monitoring."""
        metrics = self.calculate_metrics()
        
        return {
            'total_trades': metrics.total_trades,
            'win_rate': round(metrics.win_rate, 2),
            'net_pnl': round(metrics.net_pnl, 2),
            'profit_factor': round(metrics.profit_factor, 2),
            'sharpe_ratio': round(metrics.sharpe_ratio, 2),
            'max_drawdown_pct': round(metrics.max_drawdown_pct, 2),
            'active_positions': len(self.tracker.get_active_positions())
        }
