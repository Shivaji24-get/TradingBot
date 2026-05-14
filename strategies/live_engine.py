import time
import logging
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from rich.console import Console

from .indicators import IndicatorValues, calculate_all_indicators
from .signal_scorer import SignalScorer, SignalScore

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class LiveTick:
    symbol: str
    price: float
    timestamp: datetime
    volume: int = 0


class LiveEngine:
    def __init__(self, fyers_client, scanner, interval: int = 5,
                 auto_trade: bool = False, threshold: int = 75):
        self.fyers_client = fyers_client
        self.scanner = scanner
        self.interval = max(interval, 3)
        self.running = False
        self.price_history: Dict[str, List[LiveTick]] = {}
        self.signal_scorer = SignalScorer()
        self.auto_trade = auto_trade
        self.threshold = threshold
        self.executed_signals: Dict[str, str] = {}

    def _fetch_quote(self, symbol: str) -> Optional[LiveTick]:
        try:
            from api import get_quotes
            q = get_quotes(self.fyers_client, symbol)
            if "error" not in q:
                return LiveTick(symbol, q.get("last", 0.0), datetime.now(), q.get("volume", 0))
        except Exception as e:
            logger.error("Quote error for %s: %s", symbol, e)
        return None

    def _update_history(self, tick: LiveTick):
        self.price_history.setdefault(tick.symbol, []).append(tick)
        if len(self.price_history[tick.symbol]) > 100:
            self.price_history[tick.symbol] = self.price_history[tick.symbol][-100:]

    def _build_df(self, symbol: str) -> Optional[pd.DataFrame]:
        ticks = self.price_history.get(symbol, [])
        if len(ticks) < 14:
            return None
        return pd.DataFrame([
            {"timestamp": t.timestamp, "close": t.price, "high": t.price,
             "low": t.price, "open": t.price, "volume": t.volume}
            for t in ticks
        ])

    def start(self, symbols: List[str], callback: Optional[Callable] = None):
        self.running = True
        console.print(f"[green]Live scan: {len(symbols)} symbols | interval={self.interval}s[/green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        try:
            while self.running:
                for symbol in symbols:
                    if not self.running:
                        break
                    tick = self._fetch_quote(symbol)
                    if not tick:
                        continue
                    self._update_history(tick)
                    df = self._build_df(symbol)
                    if df is None:
                        continue
                    indicators = calculate_all_indicators(df)
                    score = self.signal_scorer.calculate_score(df, indicators, [])
                    sc_color = "green" if score.total_score >= 75 else ("yellow" if score.total_score >= 50 else "red")
                    sig_color = "green" if score.signal == "BUY" else ("red" if score.signal == "SELL" else "white")
                    console.print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] [cyan]{symbol}[/cyan] "
                        f"₹{tick.price:.2f} | [{sc_color}]{score.total_score}%[/{sc_color}] "
                        f"| [{sig_color}]{score.signal}[/{sig_color}]"
                    )
                    if callback:
                        callback(symbol, indicators, score, None)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            pass
        console.print("[yellow]Live scan stopped[/yellow]")
        self.running = False

    def stop(self):
        self.running = False
