"""Live streaming engine for real-time stock scanning with auto-trading."""
import time
import signal
import logging
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

from .indicators import IndicatorValues, format_signal_line
from .pattern_analyzer import PatternAnalyzer
from .signal_scorer import SignalScorer, SignalScore
from .order_executor import OrderExecutor, TradeConfig


logger = logging.getLogger(__name__)


@dataclass
class LiveTick:
    """Represents a live market tick."""
    symbol: str
    price: float
    timestamp: datetime
    volume: int = 0


class LiveEngine:
    """
    Real-time scanning engine that continuously fetches live data,
    recalculates indicators, generates signals, and optionally executes trades.
    """

    def __init__(self, fyers_client, scanner, interval: int = 5,
                 auto_trade: bool = False, threshold: int = 75):
        """
        Initialize live engine.

        Args:
            fyers_client: Fyers API client instance
            scanner: StockScanner instance for signal generation
            interval: Polling interval in seconds (default: 5)
            auto_trade: Enable automatic order placement
            threshold: Minimum score threshold for auto-trading
        """
        self.fyers_client = fyers_client
        self.scanner = scanner
        self.interval = max(interval, 3)  # Minimum 3 seconds to avoid rate limits
        self.running = False
        self.price_history: Dict[str, List[LiveTick]] = {}
        self.max_history = 100  # Keep last 100 ticks per symbol
        self.pattern_analyzer = PatternAnalyzer(min_pattern_size=5, confidence_threshold=0.7)
        self.signal_scorer = SignalScorer()

        # Auto-trading setup
        self.auto_trade = auto_trade
        self.threshold = threshold
        if auto_trade:
            config = TradeConfig(score_threshold=threshold, auto_execute=False)
            self.order_executor = OrderExecutor(fyers_client, config)
        else:
            self.order_executor = None

        # Track executed orders to avoid duplicates
        self.executed_signals: Dict[str, str] = {}

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n[yellow]Stopping live scan...[/yellow]")
        self.stop()

    def _fetch_live_quote(self, symbol: str) -> Optional[LiveTick]:
        """Fetch live quote for a symbol."""
        try:
            from api import get_quotes
            quote = get_quotes(self.fyers_client, symbol)

            if "error" in quote:
                logger.error(f"Quote error for {symbol}: {quote['error']}")
                return None

            return LiveTick(
                symbol=symbol,
                price=quote.get("last", 0.0),
                timestamp=datetime.now(),
                volume=quote.get("volume", 0)
            )
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    def _update_history(self, tick: LiveTick):
        """Update price history for a symbol."""
        if tick.symbol not in self.price_history:
            self.price_history[tick.symbol] = []

        self.price_history[tick.symbol].append(tick)

        # Keep only last N ticks
        if len(self.price_history[tick.symbol]) > self.max_history:
            self.price_history[tick.symbol] = self.price_history[tick.symbol][-self.max_history:]

    def _calculate_live_indicators(self, symbol: str) -> Optional[IndicatorValues]:
        """Calculate indicators from live price history."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 14:
            return None

        ticks = self.price_history[symbol]

        # Create DataFrame from tick history
        df = pd.DataFrame([
            {
                "timestamp": t.timestamp,
                "close": t.price,
                "volume": t.volume,
                "high": t.price,
                "low": t.price,
                "open": t.price
            }
            for t in ticks
        ])

        return self.scanner.calculate_indicators(df)

    def _detect_live_pattern(self, symbol: str) -> Optional[str]:
        """Detect patterns from live price history."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 50:
            return None

        ticks = self.price_history[symbol]
        df = pd.DataFrame([
            {
                "timestamp": t.timestamp,
                "close": t.price,
                "high": t.price,
                "low": t.price,
                "volume": t.volume
            }
            for t in ticks
        ])

        patterns = self.pattern_analyzer.analyze_patterns(df)
        if patterns:
            top_pattern = max(patterns, key=lambda p: p.confidence)
            direction_icon = "📈" if top_pattern.direction == "bullish" else "📉"
            return f"{direction_icon} {top_pattern.name} ({top_pattern.confidence:.0%})"

        return None

    def _print_live_output(self, symbol: str, indicators: IndicatorValues,
                           signal: str, pattern_info: Optional[str] = None):
        """Print live scan output with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        pattern_str = f" | {pattern_info}" if pattern_info else ""

        # Color code the signal
        signal_color = {
            "BUY": "[green]",
            "SELL": "[red]",
            "HOLD": "[white]"
        }.get(signal, "[white]")

        print(f"[{timestamp}] [cyan]{symbol}[/cyan] | "
              f"Price: [yellow]₹{indicators.price:.2f}[/yellow] | "
              f"RSI: {indicators.rsi:.1f} | "
              f"Signal: {signal_color}{signal}[/{signal_color}]"
              f"{pattern_str}")

    def _calculate_live_score(self, symbol: str) -> Optional[SignalScore]:
        """Calculate signal score from live price history."""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return None

        ticks = self.price_history[symbol]
        df = pd.DataFrame([
            {
                "timestamp": t.timestamp,
                "close": t.price,
                "high": t.price,
                "low": t.price,
                "volume": t.volume
            }
            for t in ticks
        ])

        indicators = self.scanner.calculate_indicators(df)

        # Detect patterns
        patterns = []
        if len(df) >= 50:
            patterns = self.pattern_analyzer.analyze_patterns(df)
            patterns = [{"name": p.name, "confidence": p.confidence, "direction": p.direction} for p in patterns]

        return self.signal_scorer.calculate_score(df, indicators, patterns)

    def _execute_trade(self, symbol: str, score: SignalScore, price: float):
        """Execute trade if conditions are met."""
        if not self.order_executor:
            return None

        # Check if we already executed this signal
        signal_key = f"{symbol}_{score.signal}"
        if signal_key in self.executed_signals:
            return None

        # Check score threshold
        if score.total_score < self.threshold:
            return None

        # Get available capital
        try:
            from api import get_funds
            funds = get_funds(self.fyers_client)
            capital = funds.get("available_cash", 100000)
        except:
            capital = 100000

        # Execute trade
        result = self.order_executor.execute_trade(
            symbol=symbol,
            signal=score.signal,
            price=price,
            score=score.total_score,
            capital=capital,
            confirm=not self.auto_trade  # Require confirmation unless --auto-trade
        )

        if result.success and result.order_id:
            self.executed_signals[signal_key] = result.order_id
            return result

        return None

    def start(self, symbols: List[str], callback: Optional[Callable] = None):
        """
        Start live scanning with optional auto-trading.

        Args:
            symbols: List of symbols to monitor
            callback: Optional callback function for each tick
        """
        if not symbols:
            print("[red]No symbols specified for live scan[/red]")
            return

        self.running = True

        print(f"[green]Starting live scan for {len(symbols)} symbols...[/green]")
        print(f"[cyan]Interval: {self.interval}s | Press Ctrl+C to stop[/cyan]")

        if self.auto_trade:
            print(f"[yellow]Auto-trading ENABLED | Threshold: {self.threshold}% | Use --auto-execute for real orders[/yellow]")
        print()

        # Print header
        print(f"{'Time':<10} {'Symbol':<20} {'Price':<12} {'Score':<8} {'Signal':<8} {'Pattern'}")
        print("-" * 80)

        try:
            while self.running:
                for symbol in symbols:
                    if not self.running:
                        break

                    # Fetch live quote
                    tick = self._fetch_live_quote(symbol)
                    if not tick:
                        continue

                    # Update history
                    self._update_history(tick)

                    # Calculate indicators and score
                    indicators = self._calculate_live_indicators(symbol)
                    score = self._calculate_live_score(symbol)

                    if not indicators or not score:
                        continue

                    # Detect patterns
                    pattern_info = self._detect_live_pattern(symbol)

                    # Print output with score
                    self._print_live_output_with_score(symbol, indicators, score, pattern_info)

                    # Auto-execute if enabled and score meets threshold
                    if self.auto_trade and score.signal in ["BUY", "SELL"]:
                        trade_result = self._execute_trade(symbol, score, indicators.price)
                        if trade_result and trade_result.success:
                            print(f"  [green]→ ORDER PLACED | ID: {trade_result.order_id} | "
                                  f"Qty: {trade_result.qty} | SL: ₹{trade_result.stop_loss}[/green]")

                    # Call custom callback if provided
                    if callback:
                        callback(symbol, indicators, score, pattern_info)

                if self.running:
                    time.sleep(self.interval)

        except Exception as e:
            logger.error(f"Live engine error: {e}")
            raise

    def _print_live_output_with_score(self, symbol: str, indicators: IndicatorValues,
                                       score: SignalScore, pattern_info: Optional[str] = None):
        """Print live scan output with timestamp and score."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        pattern_str = f" | {pattern_info}" if pattern_info else ""

        # Color code the signal and score
        signal_color = {
            "BUY": "[green]",
            "SELL": "[red]",
            "HOLD": "[white]"
        }.get(score.signal, "[white]")

        score_color = "green" if score.total_score >= 75 else ("yellow" if score.total_score >= 50 else "red")

        print(f"[{timestamp}] [cyan]{symbol}[/cyan] | "
              f"Price: [yellow]₹{indicators.price:.2f}[/yellow] | "
              f"[{score_color}]{score.total_score}%[/{score_color}] | "
              f"{signal_color}{score.signal}[/{signal_color}]"
              f"{pattern_str}")

    def stop(self):
        """Stop the live engine."""
        self.running = False
        print("\n[green]Live scan stopped[/green]")
