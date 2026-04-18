"""
Live Smart Money Concepts (SMC) Engine
Real-time scanning with HTF/LTF alignment, FVG, OB, MSS, and Liquidity detection
"""
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box

from .smart_money import SmartMoneyStrategy, SMCResult
from api import get_historical_data, get_quotes

logger = logging.getLogger(__name__)
console = Console()


class LiveSMCEngine:
    """
    Live SMC Scanner Engine for real-time market scanning.
    
    Features:
    - Continuous polling of live data
    - HTF bias calculation (cached for efficiency)
    - Real-time SMC condition updates
    - Score-based signal generation
    - Auto-trading support for high-confidence signals
    """
    
    def __init__(self, fyers_client, scanner, interval: int = 5, 
                 auto_trade: bool = False, threshold: int = 75,
                 ltf_timeframe: str = "5m", htf_timeframe: Optional[str] = None):
        """
        Initialize Live SMC Engine.
        
        Args:
            fyers_client: Fyers API client instance
            scanner: StockScanner instance with SMC enabled
            interval: Polling interval in seconds
            auto_trade: Enable automatic order placement
            threshold: Minimum score for auto-trading
            ltf_timeframe: Lower timeframe for analysis
            htf_timeframe: Higher timeframe for bias (auto-calculated if None)
        """
        self.fyers_client = fyers_client
        self.scanner = scanner
        self.interval = max(interval, 3)  # Minimum 3 seconds
        self.auto_trade = auto_trade
        self.threshold = threshold
        self.ltf_timeframe = ltf_timeframe
        
        # Auto-calculate HTF if not provided
        if htf_timeframe is None and scanner.smc_strategy:
            self.htf_timeframe = scanner.smc_strategy.get_htf_timeframe(ltf_timeframe)
        else:
            self.htf_timeframe = htf_timeframe or "1h"
        
        # State management
        self.running = False
        self.symbols: List[str] = []
        self.htf_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}  # Cache HTF data
        self.htf_cache_ttl = 300  # HTF cache TTL in seconds (5 minutes)
        self.last_signals: Dict[str, Dict] = {}  # Track last signals to avoid duplicates
        
        # Timeframe fallback priority
        self.timeframe_priority = {
            "5m": ["15m", "30m", "1h", "D"],
            "15m": ["30m", "1h", "4h", "D"],
            "30m": ["1h", "4h", "D"],
            "1h": ["4h", "D", "W"],
            "4h": ["D", "W"],
            "D": []
        }
        
    def get_best_timeframe_data(self, symbol: str, timeframe: str, limit: int) -> Tuple[pd.DataFrame, str]:
        """
        Fetch data with automatic timeframe fallback.
        
        Returns:
            Tuple of (DataFrame, actual_timeframe_used)
        """
        # Try primary timeframe first
        df = get_historical_data(self.fyers_client, symbol, timeframe, count=limit)
        if not df.empty and len(df) >= 20:
            return df, timeframe
        
        # Try fallback timeframes
        fallbacks = self.timeframe_priority.get(timeframe, [])
        for tf in fallbacks:
            time.sleep(0.5)  # Rate limiting between attempts
            df = get_historical_data(self.fyers_client, symbol, tf, count=limit)
            if not df.empty and len(df) >= 20:
                logger.info(f"Using fallback timeframe {tf} for {symbol}")
                return df, tf
        
        return pd.DataFrame(), timeframe
    
    def get_htf_data_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Get HTF data with caching to reduce API calls.
        
        Returns:
            HTF DataFrame or None
        """
        now = datetime.now()
        
        # Check cache
        if symbol in self.htf_cache:
            cached_df, cached_time = self.htf_cache[symbol]
            if (now - cached_time).seconds < self.htf_cache_ttl:
                return cached_df
        
        # Fetch fresh HTF data
        htf_df, _ = self.get_best_timeframe_data(symbol, self.htf_timeframe, 50)
        
        if not htf_df.empty:
            self.htf_cache[symbol] = (htf_df, now)
        
        return htf_df if not htf_df.empty else None
    
    def fetch_live_data(self, symbol: str) -> Dict:
        """
        Fetch live data for a symbol using quotes + recent history.
        
        Returns:
            Dictionary with live data and LTF DataFrame
        """
        result = {
            "symbol": symbol,
            "ltf_df": pd.DataFrame(),
            "htf_df": None,
            "current_price": 0,
            "success": False
        }
        
        try:
            # Get LTF historical data for SMC calculations
            ltf_df, actual_ltf = self.get_best_timeframe_data(symbol, self.ltf_timeframe, 100)
            
            if ltf_df.empty or len(ltf_df) < 20:
                logger.warning(f"No LTF data for {symbol}")
                return result
            
            # Get live quote for current price
            quote = get_quotes(self.fyers_client, symbol)
            
            if "error" in quote:
                logger.warning(f"Quote error for {symbol}: {quote['error']}")
                # Use last close as current price
                current_price = ltf_df['close'].iloc[-1]
            else:
                current_price = quote.get("last", ltf_df['close'].iloc[-1])
            
            # Update last candle with live price
            ltf_df.loc[ltf_df.index[-1], 'close'] = current_price
            if current_price > ltf_df['high'].iloc[-1]:
                ltf_df.loc[ltf_df.index[-1], 'high'] = current_price
            if current_price < ltf_df['low'].iloc[-1]:
                ltf_df.loc[ltf_df.index[-1], 'low'] = current_price
            
            # Get cached HTF data
            htf_df = self.get_htf_data_cached(symbol)
            
            result["ltf_df"] = ltf_df
            result["htf_df"] = htf_df
            result["current_price"] = current_price
            result["success"] = True
            
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
        
        return result
    
    def scan_symbol_live(self, symbol: str) -> Optional[SMCResult]:
        """
        Perform live SMC scan on a single symbol.
        
        Returns:
            SMCResult or None
        """
        # Fetch live data
        live_data = self.fetch_live_data(symbol)
        
        if not live_data["success"]:
            return None
        
        # Perform SMC analysis
        smc_result = self.scanner.smc_strategy.analyze(
            live_data["ltf_df"], 
            live_data["htf_df"]
        )
        smc_result.symbol = symbol
        
        return smc_result
    
    def format_live_output(self, results: List[SMCResult]) -> Table:
        """
        Format live results for display.
        
        Returns:
            Rich Table with live data
        """
        table = Table(
            title=f"[LIVE] SMC Scanner | {datetime.now().strftime('%H:%M:%S')} | Interval: {self.interval}s",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Symbol", style="cyan", no_wrap=True, width=12)
        table.add_column("Price", style="white", justify="right", width=10)
        table.add_column("Score", style="bright_green", justify="center", width=8)
        table.add_column("Signal", style="bold", justify="center", width=8)
        table.add_column("HTF", style="yellow", justify="center", width=5)
        table.add_column("Sweep", style="yellow", justify="center", width=6)
        table.add_column("MSS", style="yellow", justify="center", width=5)
        table.add_column("FVG", style="yellow", justify="center", width=5)
        table.add_column("Action", style="bold", width=10)
        
        for r in results:
            if r.signal == "NEUTRAL" and r.score < 50:
                continue  # Skip weak neutral signals
            
            # Color coding
            signal_color = "green" if r.signal == "BUY" else ("red" if r.signal == "SELL" else "dim")
            
            # Score color
            if r.score >= 75:
                score_str = f"[bold green]{r.score}%[/bold green]"
                action = "[bold green]TRADE[/bold green]" if r.signal in ["BUY", "SELL"] else "-"
            elif r.score >= 60:
                score_str = f"[yellow]{r.score}%[/yellow]"
                action = "[yellow]WATCH[/yellow]" if r.signal in ["BUY", "SELL"] else "-"
            elif r.score >= 50:
                score_str = f"[dim]{r.score}%[/dim]"
                action = "[dim]WEAK[/dim]"
            else:
                score_str = f"[dim]{r.score}%[/dim]"
                action = "-"
            
            # Indicators
            htf = "✓" if r.htf_aligned else "✗"
            sweep = "✓" if r.liquidity_sweep else "✗"
            mss = "✓" if r.mss_confirmed else "✗"
            fvg = "✓" if r.fvg_present else "✗"
            
            symbol_short = r.symbol.replace("NSE:", "").replace("-EQ", "")[:10]
            
            table.add_row(
                symbol_short,
                f"₹{r.details.get('current_price', 0):,.2f}",
                score_str,
                f"[{signal_color}]{r.signal}[/{signal_color}]",
                htf,
                sweep,
                mss,
                fvg,
                action
            )
        
        return table
    
    def check_signal_change(self, result: SMCResult) -> bool:
        """
        Check if signal has changed or score improved significantly.
        
        Returns:
            True if significant change detected
        """
        symbol = result.symbol
        
        if symbol not in self.last_signals:
            self.last_signals[symbol] = {
                "signal": result.signal,
                "score": result.score,
                "time": datetime.now()
            }
            return result.score >= 75  # New high-probability signal
        
        last = self.last_signals[symbol]
        
        # Check for signal change
        if result.signal != last["signal"] and result.signal in ["BUY", "SELL"]:
            self.last_signals[symbol] = {
                "signal": result.signal,
                "score": result.score,
                "time": datetime.now()
            }
            return True
        
        # Check for score improvement (e.g., 65 → 80)
        if result.score >= 75 and last["score"] < 75:
            self.last_signals[symbol] = {
                "signal": result.signal,
                "score": result.score,
                "time": datetime.now()
            }
            return True
        
        # Update cache
        self.last_signals[symbol]["score"] = result.score
        
        return False
    
    def execute_auto_trade(self, result: SMCResult):
        """
        Execute automatic trade for high-confidence signals.
        """
        if not self.auto_trade or result.score < self.threshold:
            return
        
        if result.signal not in ["BUY", "SELL"]:
            return
        
        # Check cooldown (prevent duplicate trades)
        symbol = result.symbol
        if symbol in self.last_signals:
            last_time = self.last_signals[symbol].get("time")
            if last_time and (datetime.now() - last_time).seconds < 300:  # 5 min cooldown
                return
        
        try:
            from api import place_order
            
            side = result.signal  # BUY or SELL
            qty = 10  # Default qty - should be calculated based on risk
            
            console.print(f"[bold green]🚀 AUTO-TRADE: {side} {symbol} @ {result.details.get('current_price', 0)}[/bold green]")
            
            order_result = place_order(
                self.fyers_client,
                symbol,
                qty,
                side.lower(),
                "MARKET",
                "MIS"
            )
            
            if "order_id" in order_result:
                console.print(f"[green]✓ Order placed: {order_result['order_id']}[/green]")
                # Update last signal time
                self.last_signals[symbol] = {
                    "signal": result.signal,
                    "score": result.score,
                    "time": datetime.now()
                }
            else:
                console.print(f"[red]✗ Order failed: {order_result.get('error', 'Unknown error')}[/red]")
                
        except Exception as e:
            logger.error(f"Auto-trade error for {symbol}: {e}")
            console.print(f"[red]Auto-trade error: {e}[/red]")
    
    def run_single_scan(self) -> List[SMCResult]:
        """
        Run a single scan cycle on all symbols.
        
        Returns:
            List of SMCResults
        """
        results = []
        
        for i, symbol in enumerate(self.symbols):
            try:
                # Rate limiting
                if i > 0 and i % 5 == 0:
                    time.sleep(2)
                
                result = self.scan_symbol_live(symbol)
                
                if result:
                    results.append(result)
                    
                    # Check for significant signal changes
                    if self.check_signal_change(result):
                        if result.score >= 75:
                            console.print(f"[bold cyan]🎯 HIGH PROBABILITY SETUP: {symbol} | {result.signal} | Score: {result.score}%[/bold cyan]")
                        
                        # Execute auto-trade if enabled
                        if self.auto_trade:
                            self.execute_auto_trade(result)
                
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
                continue
        
        return results
    
    def start(self, symbols: List[str]):
        """
        Start the live SMC scanner.
        
        Args:
            symbols: List of symbols to scan
        """
        self.symbols = symbols
        self.running = True
        
        console.print(f"[bold cyan]🚀 Starting Live SMC Scanner[/bold cyan]")
        console.print(f"[dim]Symbols: {len(symbols)} | LTF: {self.ltf_timeframe} | HTF: {self.htf_timeframe} | Interval: {self.interval}s[/dim]")
        
        if self.auto_trade:
            console.print(f"[bold yellow]⚠️  AUTO-TRADE ENABLED | Threshold: {self.threshold}%[/bold yellow]")
        
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        try:
            while self.running:
                # Run scan cycle
                results = self.run_single_scan()
                
                # Display results
                if results:
                    table = self.format_live_output(results)
                    console.print(table)
                    console.print()  # Empty line
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Live scanner stopped by user[/yellow]")
            self.running = False
        except Exception as e:
            logger.error(f"Live scanner error: {e}")
            console.print(f"\n[red]❌ Live scanner error: {e}[/red]")
            self.running = False
    
    def stop(self):
        """Stop the live scanner."""
        self.running = False
