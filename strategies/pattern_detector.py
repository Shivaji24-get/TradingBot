"""Simplified pattern detection for stock scanning."""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any


class PatternDetector:
    """Detects chart patterns in price data."""

    def __init__(self, min_pattern_size: int = 5, confidence_threshold: float = 0.7):
        self.min_pattern_size = min_pattern_size
        self.confidence_threshold = confidence_threshold

    def detect_flag_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect bull/bear flag patterns."""
        if len(df) < self.min_pattern_size * 2:
            return None

        price_changes = df["close"].pct_change()
        volatility = df["high"] - df["low"]

        for i in range(self.min_pattern_size, len(df) - self.min_pattern_size):
            pole = price_changes[i-self.min_pattern_size:i].sum()
            flag_volatility = volatility[i:i+self.min_pattern_size].mean()
            pre_flag_volatility = volatility[i-self.min_pattern_size:i].mean()

            # Strong move followed by consolidation
            if abs(pole) > 0.05 and flag_volatility < pre_flag_volatility * 0.5:
                direction = "bullish" if pole > 0 else "bearish"
                confidence = min(abs(pole) * 10, 1.0)
                return {"name": "flag", "direction": direction, "confidence": confidence}
        return None

    def detect_triangle_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect symmetrical triangle pattern."""
        if len(df) < self.min_pattern_size * 3:
            return None

        for i in range(self.min_pattern_size * 2, len(df) - self.min_pattern_size):
            window = df.iloc[i-self.min_pattern_size*2:i]

            highs = window["high"].values
            lows = window["low"].values
            x = np.arange(len(window))

            high_fit = np.polyfit(x, highs, 1)
            low_fit = np.polyfit(x, lows, 1)

            high_slope = high_fit[0]
            low_slope = low_fit[0]

            # Converging trendlines
            if -0.001 < high_slope < 0 and 0 < low_slope < 0.001:
                direction = "bullish" if window["close"].iloc[-1] > window["close"].iloc[0] else "bearish"
                return {"name": "triangle", "direction": direction, "confidence": 0.8}
        return None

    def detect_pennant_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect pennant pattern."""
        if len(df) < self.min_pattern_size * 3:
            return None

        for i in range(self.min_pattern_size * 3, len(df) - self.min_pattern_size):
            # Mast (sharp move)
            mast_window = df.iloc[i-self.min_pattern_size*3:i-self.min_pattern_size*2]
            mast_move = (mast_window["close"].iloc[-1] - mast_window["close"].iloc[0]) / mast_window["close"].iloc[0]

            if abs(mast_move) > 0.05:
                # Pennant (converging)
                pennant_window = df.iloc[i-self.min_pattern_size*2:i]
                highs = pennant_window["high"].values
                lows = pennant_window["low"].values
                x = np.arange(len(pennant_window))

                high_fit = np.polyfit(x, highs, 1)
                low_fit = np.polyfit(x, lows, 1)

                high_slope = high_fit[0]
                low_slope = low_fit[0]

                # Converging lines after strong move
                if high_slope < -0.001 and low_slope > 0.001:
                    direction = "bullish" if mast_move > 0 else "bearish"
                    confidence = min(abs(mast_move) * 10, 1.0)
                    return {"name": "pennant", "direction": direction, "confidence": confidence}
        return None

    def detect_all(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect all patterns in the data."""
        patterns = []

        for detector in [self.detect_flag_pattern, self.detect_triangle_pattern, self.detect_pennant_pattern]:
            result = detector(df)
            if result and result["confidence"] >= self.confidence_threshold:
                patterns.append(result)

        return patterns

    def get_combined_signal(self, patterns: List[Dict[str, Any]]) -> str:
        """Get trading signal from detected patterns."""
        if not patterns:
            return "HOLD"

        # Sort by confidence and return top pattern's signal
        patterns.sort(key=lambda x: x["confidence"], reverse=True)
        top = patterns[0]

        return "BUY" if top["direction"] == "bullish" else "SELL"

    def format_pattern(self, pattern: Dict[str, Any]) -> str:
        """Format pattern for display."""
        icon = "📈" if pattern["direction"] == "bullish" else "📉"
        return f"{icon} {pattern['name']} ({pattern['confidence']:.0%})"
