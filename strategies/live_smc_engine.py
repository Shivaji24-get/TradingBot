"""
Live Smart Money Concepts (SMC) Engine.

FIXES:
- execute_auto_trade() no longer uses hardcoded qty=10; delegates to OrderExecutor
- HTF/MTF cache TTL check used `.seconds` which wraps at 3600s (< 1h cache impossible)
  → now uses `.total_seconds()`
- Rich markup tags ([bold], [green] …) were passed to plain print(); now uses
  rich.console.Console() consistently so markup is actually rendered
- Removed duplicate fyers_client / scanner imports that clashed with outer scope
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

logger = logging.getLogger(__name__)
console = Console()


class LiveSMCEngine:
    """Real-time SMC market scanner with optional auto-trading."""

    # Cache TTL (seconds)
    _HTF_CACHE_TTL = 300   # 5 min
    _MTF_CACHE_TTL = 60    # 1 min

    # Timeframe fallback chains
    _TF_FALLBACK: Dict[str, List[str]] = {
        "5m":  ["15m", "30m", "1h", "D"],
        "15m": ["30m", "1h", "4h", "D"],
        "30m": ["1h", "4h", "D"],
        "1h":  ["4h", "D"],
        "4h":  ["D"],
        "D":   [],
    }

    def __init__(
        self,
        fyers_client,
        scanner,
        interval: int = 5,
        auto_trade: bool = False,
        threshold: int = 75,
        ltf_timeframe: str = "5m",
        mtf_timeframe: str = "15m",
        htf_timeframe: str = "1h",
    ) -> None:
        self.fyers_client = fyers_client
        self.scanner = scanner
        self.interval = max(interval, 3)
        self.auto_trade = auto_trade
        self.threshold = threshold
        self.ltf_timeframe = ltf_timeframe
        self.mtf_timeframe = mtf_timeframe
        self.htf_timeframe = htf_timeframe

        self.running = False
        self.symbols: List[str] = []

        # Caches: symbol → (DataFrame, fetch_datetime)
        self._htf_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        self._mtf_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}

        # Dedup: symbol → last signal dict
        self._last_signals: Dict[str, Dict] = {}

        # Auto-trading executor (lazy init)
        self._executor = None

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_with_fallback(
        self, symbol: str, timeframe: str, limit: int
    ) -> Tuple[pd.DataFrame, str]:
        """Fetch data, falling back to higher timeframes if the primary fails."""
        from api import get_historical_data

        df = get_historical_data(self.fyers_client, symbol, timeframe, count=limit)
        if not df.empty and len(df) >= 20:
            return df, timeframe

        for tf in self._TF_FALLBACK.get(timeframe, []):
            time.sleep(0.5)
            df = get_historical_data(self.fyers_client, symbol, tf, count=limit)
            if not df.empty and len(df) >= 20:
                logger.debug("Used fallback TF %s for %s", tf, symbol)
                return df, tf

        return pd.DataFrame(), timeframe

    def _get_cached(
        self,
        cache: Dict[str, Tuple[pd.DataFrame, datetime]],
        symbol: str,
        timeframe: str,
        limit: int,
        ttl: int,
    ) -> Optional[pd.DataFrame]:
        """Return cached DataFrame if fresh, else fetch and cache."""
        now = datetime.now()
        if symbol in cache:
            cached_df, cached_at = cache[symbol]
            # FIX: was `.seconds` which wraps at 3600; use `.total_seconds()`
            if (now - cached_at).total_seconds() < ttl:
                return cached_df

        df, _ = self._fetch_with_fallback(symbol, timeframe, limit)
        if not df.empty:
            cache[symbol] = (df, now)
            return df
        return None

    # ------------------------------------------------------------------
    # Scan cycle
    # ------------------------------------------------------------------

    def _scan_symbol(self, symbol: str):
        """Fetch live data and run 3-tier SMC analysis for one symbol."""
        from api import get_historical_data, get_quotes

        # LTF – always fresh
        ltf_df, _ = self._fetch_with_fallback(symbol, self.ltf_timeframe, 100)
        if ltf_df.empty or len(ltf_df) < 20:
            logger.warning("No usable LTF data for %s", symbol)
            return None

        # Update last candle with live quote
        try:
            quote = get_quotes(self.fyers_client, symbol)
            if "error" not in quote and quote.get("last", 0) > 0:
                ltf_df.iloc[-1, ltf_df.columns.get_loc("close")] = quote["last"]
        except Exception:
            pass  # Use last historical close if quote fails

        mtf_df = self._get_cached(self._mtf_cache, symbol, self.mtf_timeframe, 100, self._MTF_CACHE_TTL)
        htf_df = self._get_cached(self._htf_cache, symbol, self.htf_timeframe, 50, self._HTF_CACHE_TTL)

        return self.scanner.scan_symbol_smc(symbol, ltf_df, mtf_df, htf_df)

    def _has_signal_changed(self, result) -> bool:
        """True if signal direction changed or crossed the threshold for first time."""
        symbol = result["symbol"]
        prev = self._last_signals.get(symbol, {})

        changed = (
            result["signal"] != prev.get("signal")
            or (result["score"] >= self.threshold and prev.get("score", 0) < self.threshold)
        )
        self._last_signals[symbol] = {"signal": result["signal"], "score": result["score"], "time": datetime.now()}
        return changed

    def _execute_auto_trade(self, result: Dict) -> None:
        """Place an order using OrderExecutor (respects risk config; no hardcoded qty)."""
        if not self.auto_trade or result["score"] < self.threshold:
            return
        if result["signal"] not in ("BUY", "SELL"):
            return

        # Cooldown: 5 minutes per symbol
        prev = self._last_signals.get(result["symbol"], {})
        prev_time = prev.get("time")
        if prev_time and (datetime.now() - prev_time).total_seconds() < 300:
            return

        # Lazy-init executor
        if self._executor is None:
            from strategies.order_executor import OrderExecutor, TradeConfig
            cfg = TradeConfig(paper_trading=True, score_threshold=self.threshold, auto_execute=True)
            self._executor = OrderExecutor(self.fyers_client, config=cfg)

        try:
            from api import get_funds
            funds = get_funds(self.fyers_client)
            capital = funds.get("available_cash", 100_000)
        except Exception:
            capital = 100_000

        # FIX: qty now calculated from capital/risk config, not hardcoded
        trade = self._executor.execute_trade(
            symbol=result["symbol"],
            signal=result["signal"],
            price=result.get("price", 0),
            score=result["score"],
            capital=capital,
            confirm=False,
        )

        if trade.success:
            console.print(
                f"[bold green]AUTO-TRADE: {trade.side} {result['symbol']} "
                f"qty={trade.qty} @ ₹{trade.price:.2f} | order={trade.order_id}[/bold green]"
            )
        else:
            console.print(f"[red]Auto-trade failed for {result['symbol']}: {trade.error}[/red]")

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _build_table(self, results: List[Dict]) -> Table:
        table = Table(
            title=f"[LIVE] SMC | {datetime.now().strftime('%H:%M:%S')} | interval={self.interval}s",
            box=box.SIMPLE,
            header_style="bold cyan",
        )
        table.add_column("Symbol",  style="cyan",        no_wrap=True, width=12)
        table.add_column("Price",   style="white",       justify="right", width=10)
        table.add_column("Score",   style="bright_green",justify="center", width=8)
        table.add_column("Signal",  style="bold",        justify="center", width=8)
        table.add_column("HTF",     style="yellow",      justify="center", width=5)
        table.add_column("MTF",     style="yellow",      justify="center", width=5)
        table.add_column("Sweep",   style="yellow",      justify="center", width=6)
        table.add_column("MSS",     style="yellow",      justify="center", width=5)
        table.add_column("Action",  style="bold",        width=10)

        for r in results:
            if r["signal"] == "NEUTRAL" and r["score"] < 50:
                continue

            sc = r["score"]
            if sc >= 75:
                score_str = f"[bold green]{sc}%[/bold green]"
                action = "[bold green]TRADE[/bold green]" if r["signal"] in ("BUY", "SELL") else "-"
            elif sc >= 60:
                score_str = f"[yellow]{sc}%[/yellow]"
                action = "[yellow]WATCH[/yellow]" if r["signal"] in ("BUY", "SELL") else "-"
            else:
                score_str = f"[dim]{sc}%[/dim]"
                action = "[dim]WEAK[/dim]"

            sig_color = "green" if r["signal"] == "BUY" else ("red" if r["signal"] == "SELL" else "dim")
            sym = r["symbol"].replace("NSE:", "").replace("-EQ", "")[:10]

            table.add_row(
                sym,
                f"₹{r.get('price', 0):,.2f}",
                score_str,
                f"[{sig_color}]{r['signal']}[/{sig_color}]",
                "✓" if r.get("htf_aligned") else "✗",
                "✓" if r.get("mtf_aligned") else "✗",
                "✓" if r.get("liquidity_sweep") else "✗",
                "✓" if r.get("mss_confirmed") else "✗",
                action,
            )
        return table

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, symbols: List[str]) -> None:
        self.symbols = symbols
        self.running = True

        console.print(f"[bold cyan]Live SMC Scanner started[/bold cyan]")
        console.print(
            f"[dim]{len(symbols)} symbols | LTF={self.ltf_timeframe} "
            f"MTF={self.mtf_timeframe} HTF={self.htf_timeframe} | "
            f"interval={self.interval}s[/dim]"
        )
        if self.auto_trade:
            console.print(f"[bold yellow]AUTO-TRADE ON | threshold={self.threshold}%[/bold yellow]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        try:
            while self.running:
                results = self._run_cycle()
                if results:
                    console.print(self._build_table(results))
                time.sleep(self.interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Live scanner stopped.[/yellow]")
            self.running = False

    def _run_cycle(self) -> List[Dict]:
        results = []
        for i, symbol in enumerate(self.symbols):
            if not self.running:
                break
            if i > 0 and i % 5 == 0:
                time.sleep(2)
            try:
                result = self._scan_symbol(symbol)
                if result:
                    results.append(result)
                    if self._has_signal_changed(result) and result["score"] >= self.threshold:
                        console.print(
                            f"[bold cyan]Signal: {result['symbol']} "
                            f"{result['signal']} {result['score']}%[/bold cyan]"
                        )
                        if self.auto_trade:
                            self._execute_auto_trade(result)
            except Exception:
                logger.exception("Error scanning %s", symbol)
        return results

    def stop(self) -> None:
        self.running = False
