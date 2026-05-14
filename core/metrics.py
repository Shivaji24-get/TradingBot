"""Performance metrics collection and reporting."""
import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradingMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    avg_trade_pnl: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_trade_duration: float = 0.0
    total_signals: int = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class DailySnapshot:
    date: str
    trades: int = 0
    pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    cumulative_pnl: float = 0.0
    drawdown: float = 0.0


class MetricsCollector:
    def __init__(self, tracker: Any, risk_free_rate: float = 0.06):
        self.tracker = tracker
        self.risk_free_rate = risk_free_rate

    def calculate_metrics(self, start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> TradingMetrics:
        trades = self.tracker.get_trades(start_date=start_date, end_date=end_date)
        if not trades:
            return TradingMetrics(start_date=start_date, end_date=end_date)

        m = TradingMetrics(start_date=start_date or trades[0].entry_time,
                           end_date=end_date or datetime.now())
        m.total_trades = len(trades)
        wins   = [t for t in trades if t.status == "WIN"]
        losses = [t for t in trades if t.status == "LOSS"]
        m.winning_trades   = len(wins)
        m.losing_trades    = len(losses)
        m.breakeven_trades = len(trades) - len(wins) - len(losses)
        m.gross_profit = sum(t.pnl for t in wins)
        m.gross_loss   = abs(sum(t.pnl for t in losses))
        m.net_pnl      = sum(t.pnl for t in trades)
        done = m.winning_trades + m.losing_trades
        if done:
            m.win_rate  = m.winning_trades / done * 100
            m.loss_rate = m.losing_trades  / done * 100
        if wins:
            m.avg_profit = m.gross_profit / len(wins)
        if losses:
            m.avg_loss = m.gross_loss / len(losses)
        if trades:
            m.avg_trade_pnl = m.net_pnl / len(trades)
        m.profit_factor = (m.gross_profit / m.gross_loss) if m.gross_loss > 0 else float("inf")
        m.max_drawdown, m.max_drawdown_pct = self._drawdown(trades)
        m.max_consecutive_wins, m.max_consecutive_losses = self._consecutive(trades)
        durations = [(t.exit_time - t.entry_time).total_seconds() / 60 for t in trades]
        if durations:
            m.avg_trade_duration = sum(durations) / len(durations)
        m.sharpe_ratio = self._sharpe(trades)
        return m

    def _drawdown(self, trades) -> tuple:
        if not trades:
            return 0.0, 0.0
        peak, max_dd, cum = 0.0, 0.0, 0.0
        for t in sorted(trades, key=lambda x: x.exit_time):
            cum += t.pnl
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
        return max_dd, (max_dd / peak * 100) if peak > 0 else 0.0

    def _consecutive(self, trades) -> tuple:
        max_w = max_l = cur_w = cur_l = 0
        for t in sorted(trades, key=lambda x: x.exit_time):
            if t.status == "WIN":
                cur_w += 1; cur_l = 0; max_w = max(max_w, cur_w)
            elif t.status == "LOSS":
                cur_l += 1; cur_w = 0; max_l = max(max_l, cur_l)
        return max_w, max_l

    def _sharpe(self, trades) -> float:
        if not trades:
            return 0.0
        daily: Dict[str, float] = {}
        for t in trades:
            day = t.exit_time.strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0.0) + t.pnl
        if len(daily) < 2:
            return 0.0
        returns = list(daily.values())
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / len(returns)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return ((avg - self.risk_free_rate / 252) / std) * math.sqrt(252)

    def get_daily_series(self, days: int = 30) -> List[DailySnapshot]:
        end = datetime.now()
        start = end - timedelta(days=days)
        trades = self.tracker.get_trades(start_date=start, end_date=end)
        daily: Dict[str, dict] = {}
        for t in trades:
            d = t.exit_time.strftime("%Y-%m-%d")
            if d not in daily:
                daily[d] = {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0}
            daily[d]["trades"] += 1
            daily[d]["pnl"]    += t.pnl
            if t.status == "WIN":   daily[d]["wins"]   += 1
            elif t.status == "LOSS": daily[d]["losses"] += 1
        snapshots, cum, peak = [], 0.0, 0.0
        for date in sorted(daily):
            d = daily[date]
            cum += d["pnl"]
            if cum > peak:
                peak = cum
            snapshots.append(DailySnapshot(date=date, trades=d["trades"], pnl=d["pnl"],
                                           wins=d["wins"], losses=d["losses"],
                                           cumulative_pnl=cum, drawdown=peak - cum))
        return snapshots

    def generate_report(self, output_path: Optional[str] = None, format: str = "markdown") -> str:
        m = self.calculate_metrics()
        daily = self.get_daily_series(30)
        if format == "json":
            report = json.dumps({
                "generated_at": datetime.now().isoformat(),
                "metrics": {
                    "total_trades": m.total_trades, "win_rate": round(m.win_rate, 2),
                    "net_pnl": round(m.net_pnl, 2), "profit_factor": round(m.profit_factor, 2),
                    "sharpe_ratio": round(m.sharpe_ratio, 2),
                    "max_drawdown_pct": round(m.max_drawdown_pct, 2),
                },
                "daily_series": [{"date": s.date, "pnl": round(s.pnl, 2),
                                   "cumulative_pnl": round(s.cumulative_pnl, 2)} for s in daily],
            }, indent=2)
        else:
            lines = [
                "# Trading Performance Report", "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
                "## Summary", "",
                f"- **Total Trades:** {m.total_trades}",
                f"- **Win Rate:** {m.win_rate:.2f}%",
                f"- **Net P&L:** ₹{m.net_pnl:,.2f}",
                f"- **Profit Factor:** {m.profit_factor:.2f}",
                f"- **Sharpe Ratio:** {m.sharpe_ratio:.2f}",
                f"- **Max Drawdown:** ₹{m.max_drawdown:,.2f} ({m.max_drawdown_pct:.2f}%)", "",
                "## Daily Performance", "",
                "| Date | Trades | P&L | Cumulative |",
                "|------|--------|-----|------------|",
            ]
            for s in daily:
                lines.append(f"| {s.date} | {s.trades} | ₹{s.pnl:,.2f} | ₹{s.cumulative_pnl:,.2f} |")
            report = "\n".join(lines)

        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
        return report
