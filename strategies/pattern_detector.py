import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any
from .mss_detector import MSSDetector
from .harmonic_detector import HarmonicDetector


class PatternDetector:
    def __init__(self, min_pattern_size: int = 5, confidence_threshold: float = 0.7):
        self.min_pattern_size = min_pattern_size
        self.confidence_threshold = confidence_threshold
        self.harmonic_detector = HarmonicDetector(swing_lookback=min_pattern_size)

    def detect_harmonic_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        analysis = self.harmonic_detector.get_harmonic_analysis(df)
        if analysis["has_pattern"] and analysis["confidence"] >= self.confidence_threshold:
            return {"name": analysis["latest_pattern"], "direction": analysis["direction"],
                    "confidence": analysis["confidence"]}
        return None

    def detect_flag_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(df) < self.min_pattern_size * 2:
            return None
        changes = df["close"].pct_change()
        volatility = df["high"] - df["low"]
        for i in range(self.min_pattern_size, len(df) - self.min_pattern_size):
            pole = changes[i - self.min_pattern_size:i].sum()
            flag_vol = volatility[i:i + self.min_pattern_size].mean()
            pre_vol = volatility[i - self.min_pattern_size:i].mean()
            if abs(pole) > 0.05 and flag_vol < pre_vol * 0.5:
                return {"name": "flag", "direction": "bullish" if pole > 0 else "bearish",
                        "confidence": min(abs(pole) * 10, 1.0)}
        return None

    def detect_triangle_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(df) < self.min_pattern_size * 3:
            return None
        for i in range(self.min_pattern_size * 2, len(df) - self.min_pattern_size):
            window = df.iloc[i - self.min_pattern_size * 2:i]
            x = np.arange(len(window))
            hs = np.polyfit(x, window["high"].values, 1)[0]
            ls = np.polyfit(x, window["low"].values, 1)[0]
            if -0.001 < hs < 0 and 0 < ls < 0.001:
                direction = "bullish" if window["close"].iloc[-1] > window["close"].iloc[0] else "bearish"
                return {"name": "triangle", "direction": direction, "confidence": 0.8}
        return None

    def detect_pennant_pattern(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if len(df) < self.min_pattern_size * 3:
            return None
        for i in range(self.min_pattern_size * 3, len(df) - self.min_pattern_size):
            mast = df.iloc[i - self.min_pattern_size * 3:i - self.min_pattern_size * 2]
            move = (mast["close"].iloc[-1] - mast["close"].iloc[0]) / mast["close"].iloc[0]
            if abs(move) > 0.05:
                pennant = df.iloc[i - self.min_pattern_size * 2:i]
                x = np.arange(len(pennant))
                hs = np.polyfit(x, pennant["high"].values, 1)[0]
                ls = np.polyfit(x, pennant["low"].values, 1)[0]
                if hs < -0.001 and ls > 0.001:
                    return {"name": "pennant", "direction": "bullish" if move > 0 else "bearish",
                            "confidence": min(abs(move) * 10, 1.0)}
        return None

    def detect_all(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        patterns = []
        for fn in [self.detect_flag_pattern, self.detect_triangle_pattern,
                   self.detect_pennant_pattern, self.detect_harmonic_patterns]:
            r = fn(df)
            if r and r["confidence"] >= self.confidence_threshold:
                patterns.append(r)
        return patterns

    def get_combined_signal(self, patterns: List[Dict[str, Any]]) -> str:
        if not patterns:
            return "HOLD"
        top = max(patterns, key=lambda p: p["confidence"])
        return "BUY" if top["direction"] == "bullish" else "SELL"

    def format_pattern(self, pattern: Dict[str, Any]) -> str:
        icon = "📈" if pattern["direction"] == "bullish" else "📉"
        return f"{icon} {pattern['name']} ({pattern['confidence']:.0%})"
