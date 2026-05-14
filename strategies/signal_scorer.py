import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SignalScore:
    total_score: int
    signal: str
    confidence: str
    rsi_score: int
    trend_score: int
    volume_score: int
    pattern_score: int
    rsi_value: float
    trend_direction: str
    volume_ratio: float
    patterns_detected: List[str]


class SignalScorer:
    HIGH_CONFIDENCE_THRESHOLD = 75
    MEDIUM_CONFIDENCE_THRESHOLD = 50

    def _rsi_score(self, rsi: float):
        if rsi < 30:
            return 30, "BUY"
        if rsi > 70:
            return 30, "SELL"
        dist = abs(rsi - 50)
        return int((dist / 20) * 30), ("BUY" if rsi < 50 else "SELL")

    def _trend_score(self, df: pd.DataFrame):
        if len(df) < 50:
            return 15, "NEUTRAL"
        sma20 = df["close"].rolling(20).mean().iloc[-1]
        sma50 = df["close"].rolling(50).mean().iloc[-1]
        price = df["close"].iloc[-1]
        bullish = sma20 > sma50
        above = price > sma20
        if bullish and above:
            return 30, "BULLISH"
        if not bullish and not above:
            return 30, "BEARISH"
        return 20, ("WEAK_BULLISH" if bullish else "WEAK_BEARISH")

    def _volume_score(self, df: pd.DataFrame):
        if len(df) < 20 or "volume" not in df.columns:
            return 10, 1.0
        avg = df["volume"].iloc[-20:-1].mean()
        cur = df["volume"].iloc[-1]
        if avg == 0:
            return 10, 1.0
        ratio = cur / avg
        score = 20 if ratio >= 2.0 else (15 if ratio >= 1.5 else (10 if ratio >= 1.2 else 5))
        return score, ratio

    def _pattern_score(self, patterns: List[Dict[str, Any]]):
        if not patterns:
            return 0, []
        top = max(patterns, key=lambda p: p.get("confidence", 0))
        return min(int(top.get("confidence", 0) * 20), 20), [p.get("name", "") for p in patterns]

    def calculate_score(self, df: pd.DataFrame, indicators: Any,
                        patterns: Optional[List[Dict]] = None) -> SignalScore:
        rsi_sc, rsi_dir = self._rsi_score(indicators.rsi)
        trend_sc, trend_dir = self._trend_score(df)
        vol_sc, vol_ratio = self._volume_score(df)
        pat_sc, pat_names = self._pattern_score(patterns or [])
        total = min(100, rsi_sc + trend_sc + vol_sc + pat_sc)

        if rsi_dir == "BUY" and "BULLISH" in trend_dir:
            signal = "BUY"
        elif rsi_dir == "SELL" and "BEARISH" in trend_dir:
            signal = "SELL"
        elif total >= 60 and rsi_dir in ("BUY", "SELL"):
            signal = rsi_dir
        else:
            signal = "HOLD"

        conf = ("HIGH" if total >= self.HIGH_CONFIDENCE_THRESHOLD
                else ("MEDIUM" if total >= self.MEDIUM_CONFIDENCE_THRESHOLD else "LOW"))

        return SignalScore(
            total_score=total, signal=signal, confidence=conf,
            rsi_score=rsi_sc, trend_score=trend_sc, volume_score=vol_sc, pattern_score=pat_sc,
            rsi_value=indicators.rsi, trend_direction=trend_dir,
            volume_ratio=vol_ratio, patterns_detected=pat_names,
        )

    def should_execute(self, score: SignalScore, threshold: int = 75) -> bool:
        return score.total_score >= threshold and score.signal in ("BUY", "SELL")
