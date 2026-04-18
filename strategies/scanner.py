"""Enhanced stock scanner supporting both historical and live modes."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .parser import StrategyParser
from .pattern_detector import PatternDetector
from .indicators import calculate_all_indicators, evaluate_strategy, IndicatorValues
from .signal_scorer import SignalScorer, SignalScore
from .smart_money import SmartMoneyStrategy


class StockScanner:
    """Unified scanner for historical backtesting and live trading."""

    def __init__(self, config_path: str = "strategy.json", enable_patterns: bool = True, 
                 enable_scoring: bool = True, enable_smc: bool = False):
        self.parser = StrategyParser(config_path)
        # Use new simplified pattern detector with lower threshold
        self.pattern_detector = PatternDetector(min_pattern_size=5, confidence_threshold=0.5) if enable_patterns else None
        # Signal scorer for probability-based trading
        self.signal_scorer = SignalScorer() if enable_scoring else None
        # Smart Money Concepts strategy
        self.smc_strategy = SmartMoneyStrategy() if enable_smc else None
    
    def calculate_indicators(self, df: pd.DataFrame) -> IndicatorValues:
        """Calculate indicators using shared module."""
        return calculate_all_indicators(df)
    
    def check_entry(self, indicators: IndicatorValues, conditions: Dict) -> bool:
        """Check if entry conditions are met."""
        if not conditions:
            return False
        for key, value in conditions.items():
            if key == "rsi_less_than" and indicators.rsi >= value:
                return False
            elif key == "volume_greater_than" and indicators.volume <= value:
                return False
        return True
    
    def generate_signal(self, indicators: IndicatorValues, entry_conditions: Dict, exit_conditions: Dict) -> str:
        """Generate trading signal based on conditions."""
        if self.check_entry(indicators, entry_conditions):
            return "BUY"
        elif self.check_entry(indicators, exit_conditions):
            return "SELL"
        return "HOLD"
    
    def scan_symbol(self, symbol: str, historical_data: pd.DataFrame) -> Optional[Dict]:
        if historical_data.empty or len(historical_data) < 20:
            return None

        indicators = self.calculate_indicators(historical_data)
        signal = self.generate_signal(indicators, self.parser.get_entry_conditions(), self.parser.get_exit_conditions())

        result = {
            "symbol": symbol,
            "price": indicators.price,
            "signal": signal,
            "rsi": round(indicators.rsi, 2),
            "sma_20": round(indicators.sma_20, 2),
            "volume": int(indicators.volume)
        }

        # Add pattern detection if enabled
        patterns = []
        if self.pattern_detector and len(historical_data) >= 50:
            patterns = self.pattern_detector.detect_all(historical_data)
            if patterns:
                top_pattern = max(patterns, key=lambda p: p["confidence"])
                result["pattern"] = top_pattern["name"]
                result["pattern_confidence"] = round(top_pattern["confidence"], 2)
                result["pattern_direction"] = top_pattern["direction"]
                # Generate pattern-based signal if no indicator signal
                if signal == "HOLD":
                    result["pattern_signal"] = self.pattern_detector.get_combined_signal([top_pattern])
            else:
                result["pattern"] = None  # Explicitly mark no pattern found

        # Add probability scoring if enabled
        if self.signal_scorer:
            score = self.signal_scorer.calculate_score(historical_data, indicators, patterns)
            result["score"] = score.total_score
            result["score_confidence"] = score.confidence
            result["score_breakdown"] = {
                "rsi": score.rsi_score,
                "trend": score.trend_score,
                "volume": score.volume_score,
                "pattern": score.pattern_score
            }
            # Override signal with scored signal if available
            if score.signal != "HOLD":
                result["signal"] = score.signal
                result["signal_source"] = "scored"

        return result
    
    def scan_all(self, fyers_client, symbols: List[str] = None, timeframe: str = None, limit: int = None) -> List[Dict]:
        from api import get_historical_data
        import logging

        logger = logging.getLogger(__name__)

        if limit is None:
            limit = self.parser.get_limit() or 30

        if symbols is None:
            symbols = self.parser.get_symbols()
        if timeframe is None:
            timeframe = self.parser.get_timeframe() or "D"

        print(f"Scanning {len(symbols)} symbols | Timeframe: {timeframe} | Limit: {limit}")
        print(f"Symbols: {symbols}")

        results = []
        for symbol in symbols:
            try:
                print(f"Fetching {symbol}...", end=" ")
                df = get_historical_data(fyers_client, symbol, timeframe, count=limit)
                print(f"Got {len(df)} candles")

                if df.empty:
                    print(f"  [SKIP] No data for {symbol}")
                    continue

                result = self.scan_symbol(symbol, df)
                if result:
                    pattern_str = ""
                    if result.get("pattern"):
                        pattern_str = f" | Pattern: {result['pattern']} ({result['pattern_direction']})"
                    print(f"  [SIGNAL] {result['signal']} - RSI: {result['rsi']}{pattern_str}")
                    results.append(result)
                else:
                    print(f"  [SKIP] Insufficient data")
            except Exception as e:
                print(f"  [ERROR] {e}")
                logger.error(f"Scan error for {symbol}: {e}")
                continue

        print(f"Scan complete. Found {len(results)} signals.")
        return results
    
    def scan_symbol_smc(self, symbol: str, ltf_df: pd.DataFrame, htf_df: Optional[pd.DataFrame] = None) -> Optional[Dict]:
        """
        Scan a symbol using Smart Money Concepts strategy.
        
        Args:
            symbol: Stock symbol
            ltf_df: Lower Time Frame DataFrame
            htf_df: Higher Time Frame DataFrame (optional)
            
        Returns:
            SMC result dictionary
        """
        if not self.smc_strategy:
            return None
        
        if ltf_df.empty or len(ltf_df) < 20:
            return None
        
        # Perform SMC analysis
        smc_result = self.smc_strategy.analyze(ltf_df, htf_df)
        smc_result.symbol = symbol
        
        # Build result dictionary
        result = {
            "symbol": symbol,
            "price": ltf_df['close'].iloc[-1],
            "signal": smc_result.signal,
            "score": smc_result.score,
            "htf_aligned": smc_result.htf_aligned,
            "liquidity_sweep": smc_result.liquidity_sweep,
            "mss_confirmed": smc_result.mss_confirmed,
            "fvg_present": smc_result.fvg_present,
            "ob_present": smc_result.ob_present,
            "pattern": smc_result.pattern,
            "details": smc_result.details
        }
        
        return result
    
    def scan_all_smc(self, fyers_client, symbols: List[str] = None, 
                     ltf_timeframe: str = "5m", htf_timeframe: Optional[str] = None,
                     ltf_limit: int = 100, htf_limit: int = 50,
                     min_score: int = 50) -> List[Dict]:
        """
        Scan multiple symbols using Smart Money Concepts strategy with HTF/LTF alignment.
        
        Args:
            fyers_client: Fyers API client
            symbols: List of symbols to scan
            ltf_timeframe: Lower Time Frame (e.g., "5m")
            htf_timeframe: Higher Time Frame (e.g., "15m", "1h"). If None, auto-calculated.
            ltf_limit: Number of candles for LTF
            htf_limit: Number of candles for HTF
            min_score: Minimum score to include in results (default 50)
            
        Returns:
            List of SMC scan results
        """
        from api import get_historical_data
        import logging
        import time
        
        logger = logging.getLogger(__name__)
        
        if not self.smc_strategy:
            print("ERROR: SMC strategy not enabled. Initialize scanner with enable_smc=True")
            return []
        
        if symbols is None:
            symbols = self.parser.get_symbols()
        
        # Auto-calculate HTF if not provided
        if htf_timeframe is None:
            htf_timeframe = self.smc_strategy.get_htf_timeframe(ltf_timeframe)
        
        print(f"SMC Scan | LTF: {ltf_timeframe} | HTF: {htf_timeframe} | Symbols: {len(symbols)} | Min Score: {min_score}%")
        
        # Timeframe fallback priority (if primary LTF has no data)
        timeframe_fallback = ["5m", "15m", "30m", "1h", "4h", "D"]
        
        results = []
        for i, symbol in enumerate(symbols):
            try:
                # Rate limiting: Add delay every 5 symbols
                if i > 0 and i % 5 == 0:
                    time.sleep(2)
                
                print(f"Scanning {symbol}...")
                
                # Fetch LTF data with fallback
                ltf_df = pd.DataFrame()
                actual_ltf = ltf_timeframe
                
                for tf in timeframe_fallback:
                    if timeframe_fallback.index(tf) >= timeframe_fallback.index(ltf_timeframe):
                        ltf_df = get_historical_data(fyers_client, symbol, tf, count=ltf_limit)
                        if not ltf_df.empty and len(ltf_df) >= 20:
                            actual_ltf = tf
                            if tf != ltf_timeframe:
                                print(f"  [INFO] Using fallback timeframe: {tf}")
                            break
                        time.sleep(0.5)  # Small delay between timeframe attempts
                
                if ltf_df.empty or len(ltf_df) < 20:
                    print(f"  [SKIP] No LTF data for {symbol} (tried multiple timeframes)")
                    continue
                
                # Fetch HTF data
                htf_df = get_historical_data(fyers_client, symbol, htf_timeframe, count=htf_limit)
                time.sleep(0.5)  # Rate limiting between LTF and HTF
                
                # Perform SMC scan
                result = self.scan_symbol_smc(symbol, ltf_df, htf_df if not htf_df.empty else None)
                
                if result:
                    # Include if score >= min_score (default 50, not 75)
                    if result['score'] >= min_score:
                        htf_status = "✓" if result['htf_aligned'] else "✗"
                        sweep_status = "✓" if result['liquidity_sweep'] else "✗"
                        mss_status = "✓" if result['mss_confirmed'] else "✗"
                        fvg_status = "✓" if result['fvg_present'] else "✗"
                        
                        # Show different labels based on score
                        if result['score'] >= 75:
                            label = "[STRONG]"
                            color = "green"
                        elif result['score'] >= 60:
                            label = "[MODERATE]"
                            color = "yellow"
                        else:
                            label = "[WEAK]"
                            color = "dim"
                        
                        print(f"  {label} {result['signal']} | Score: {result['score']}% | "
                              f"HTF:{htf_status} Sweep:{sweep_status} MSS:{mss_status} FVG:{fvg_status}")
                        results.append(result)
                    else:
                        # Show score breakdown for debugging
                        details = result.get('details', {})
                        htf_score = details.get('htf', {}).get('score', 0)
                        liq_score = details.get('liquidity', {}).get('score', 0)
                        mss_score = details.get('mss', {}).get('score', 0)
                        fvg_score = details.get('fvg', {}).get('score', 0)
                        print(f"  [SKIP] Score {result['score']}% below {min_score}% (HTF:{htf_score} Liq:{liq_score} MSS:{mss_score} FVG:{fvg_score})")
                else:
                    print(f"  [SKIP] No SMC setup")
                    
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    print(f"  [RATE LIMIT] Waiting 5 seconds...")
                    time.sleep(5)
                    # Retry this symbol
                    i -= 1
                    continue
                print(f"  [ERROR] {e}")
                logger.error(f"SMC scan error for {symbol}: {e}")
                continue
        
        print(f"SMC Scan complete. Found {len(results)} setups with score >= {min_score}%.")
        return results