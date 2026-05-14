import numpy as np
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Pattern:
    name: str
    confidence: float
    direction: str
    start_idx: int
    end_idx: int


class PatternAnalyzer:
    def __init__(self, min_pattern_size: int = 5, confidence_threshold: float = 0.7):
        self.min_pattern_size = min_pattern_size
        self.confidence_threshold = confidence_threshold

    def detect_flag_pattern(self, df: pd.DataFrame) -> Optional[Pattern]:
        changes = df["close"].pct_change()
        volatility = df["high"] - df["low"]
        for i in range(self.min_pattern_size, len(df) - self.min_pattern_size):
            pole = changes[i - self.min_pattern_size:i].sum()
            flag_vol = volatility[i:i + self.min_pattern_size].mean()
            pre_vol = volatility[i - self.min_pattern_size:i].mean()
            if abs(pole) > 0.05 and flag_vol < pre_vol * 0.5:
                return Pattern("flag", min(abs(pole) * 10, 1.0),
                                "bullish" if pole > 0 else "bearish",
                                i - self.min_pattern_size, i + self.min_pattern_size)
        return None

    def detect_triangle_pattern(self, df: pd.DataFrame) -> Optional[Pattern]:
        for i in range(self.min_pattern_size * 2, len(df) - self.min_pattern_size):
            window = df.iloc[i - self.min_pattern_size * 2:i]
            x = np.arange(len(window))
            high_slope = np.polyfit(x, window["high"].values, 1)[0]
            low_slope = np.polyfit(x, window["low"].values, 1)[0]
            if -0.001 < high_slope < 0 and 0 < low_slope < 0.001:
                direction = "bullish" if window["close"].iloc[-1] > window["close"].iloc[0] else "bearish"
                return Pattern("triangle", 0.8, direction,
                                i - self.min_pattern_size * 2, i)
        return None

    def detect_pennant_pattern(self, df: pd.DataFrame) -> Optional[Pattern]:
        for i in range(self.min_pattern_size * 3, len(df) - self.min_pattern_size):
            mast = df.iloc[i - self.min_pattern_size * 3:i - self.min_pattern_size * 2]
            mast_move = (mast["close"].iloc[-1] - mast["close"].iloc[0]) / mast["close"].iloc[0]
            if abs(mast_move) > 0.05:
                pennant = df.iloc[i - self.min_pattern_size * 2:i]
                x = np.arange(len(pennant))
                hs = np.polyfit(x, pennant["high"].values, 1)[0]
                ls = np.polyfit(x, pennant["low"].values, 1)[0]
                if hs < -0.001 and ls > 0.001:
                    return Pattern("pennant", min(abs(mast_move) * 10, 1.0),
                                    "bullish" if mast_move > 0 else "bearish",
                                    i - self.min_pattern_size * 3, i)
        return None

    def analyze_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        patterns = []
        for fn in [self.detect_flag_pattern, self.detect_triangle_pattern, self.detect_pennant_pattern]:
            p = fn(df)
            if p and p.confidence >= self.confidence_threshold:
                patterns.append(p)
        return patterns

    def get_trading_signal(self, patterns: List[Pattern], current_position: bool = False) -> str:
        if not patterns:
            return "HOLD"
        top = max(patterns, key=lambda p: p.confidence)
        if top.direction == "bullish":
            return "HOLD" if current_position else "BUY"
        return "SELL" if current_position else "HOLD"
