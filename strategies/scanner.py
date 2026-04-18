"""Enhanced stock scanner supporting both historical and live modes."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .parser import StrategyParser
from .pattern_detector import PatternDetector
from .indicators import calculate_all_indicators, evaluate_strategy, IndicatorValues
from .signal_scorer import SignalScorer, SignalScore


class StockScanner:
    """Unified scanner for historical backtesting and live trading."""

    def __init__(self, config_path: str = "strategy.json", enable_patterns: bool = True, enable_scoring: bool = True):
        self.parser = StrategyParser(config_path)
        # Use new simplified pattern detector with lower threshold
        self.pattern_detector = PatternDetector(min_pattern_size=5, confidence_threshold=0.5) if enable_patterns else None
        # Signal scorer for probability-based trading
        self.signal_scorer = SignalScorer() if enable_scoring else None
    
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