"""Signal scoring system for probability-based trading."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class SignalScore:
    """Container for signal scoring results."""
    total_score: int  # 0-100
    signal: str  # BUY, SELL, or HOLD
    confidence: str  # HIGH (>=75), MEDIUM (50-74), LOW (<50)

    # Component scores
    rsi_score: int
    trend_score: int
    volume_score: int
    pattern_score: int

    # Details
    rsi_value: float
    trend_direction: str
    volume_ratio: float
    patterns_detected: List[str]


class SignalScorer:
    """
    Calculates probability scores for trading signals.
    Weights: RSI (30%) + Trend (30%) + Volume (20%) + Pattern (20%)
    """

    # Weight configuration
    WEIGHTS = {
        "rsi": 0.30,
        "trend": 0.30,
        "volume": 0.20,
        "pattern": 0.20
    }

    # Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 75
    MEDIUM_CONFIDENCE_THRESHOLD = 50

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with custom weights if provided.

        Args:
            weights: Optional dict with keys: rsi, trend, volume, pattern
        """
        if weights:
            self.WEIGHTS = weights

    def _calculate_rsi_score(self, rsi: float) -> tuple[int, str]:
        """
        Calculate RSI component score (0-30 points).

        Returns:
            (score, implied_direction)
        """
        # RSI < 30: Oversold (BUY signal) - max points
        # RSI > 70: Overbought (SELL signal) - max points
        # Middle: Scale down

        if rsi < 30:
            # Oversold - strong BUY signal
            score = 30
            direction = "BUY"
        elif rsi > 70:
            # Overbought - strong SELL signal
            score = 30
            direction = "SELL"
        else:
            # Neutral zone - partial score based on distance from 50
            distance_from_neutral = abs(rsi - 50)
            score = int((distance_from_neutral / 20) * 30)
            direction = "BUY" if rsi < 50 else "SELL"

        return min(score, 30), direction

    def _calculate_trend_score(self, df: pd.DataFrame) -> tuple[int, str]:
        """
        Calculate trend component score (0-30 points).
        Based on SMA20 vs SMA50 and price momentum.

        Returns:
            (score, trend_direction)
        """
        if len(df) < 50:
            return 15, "NEUTRAL"

        # Calculate SMAs
        sma_20 = df["close"].rolling(window=20).mean().iloc[-1]
        sma_50 = df["close"].rolling(window=50).mean().iloc[-1]
        current_price = df["close"].iloc[-1]

        # Price vs SMA20 (short-term momentum)
        price_vs_sma20 = (current_price - sma_20) / sma_20

        # SMA20 vs SMA50 (trend direction)
        sma_bullish = sma_20 > sma_50

        # Calculate score
        if sma_bullish and price_vs_sma20 > 0:
            # Strong uptrend
            score = 30
            direction = "BULLISH"
        elif not sma_bullish and price_vs_sma20 < 0:
            # Strong downtrend
            score = 30
            direction = "BEARISH"
        elif sma_bullish:
            # Weak uptrend (price below SMA20)
            score = 20
            direction = "WEAK_BULLISH"
        else:
            # Weak downtrend (price above SMA20)
            score = 20
            direction = "WEAK_BEARISH"

        return score, direction

    def _calculate_volume_score(self, df: pd.DataFrame) -> tuple[int, float]:
        """
        Calculate volume component score (0-20 points).
        Based on volume spike vs average.

        Returns:
            (score, volume_ratio)
        """
        if len(df) < 20 or "volume" not in df.columns:
            return 10, 1.0

        # Calculate average volume (excluding current)
        avg_volume = df["volume"].iloc[-20:-1].mean()
        current_volume = df["volume"].iloc[-1]

        if avg_volume == 0:
            return 10, 1.0

        volume_ratio = current_volume / avg_volume

        # Score based on volume spike
        if volume_ratio >= 2.0:
            score = 20  # Major spike
        elif volume_ratio >= 1.5:
            score = 15  # Moderate spike
        elif volume_ratio >= 1.2:
            score = 10  # Minor spike
        else:
            score = 5   # Normal volume

        return score, volume_ratio

    def _calculate_pattern_score(self, patterns: List[Dict[str, Any]]) -> tuple[int, List[str]]:
        """
        Calculate pattern component score (0-20 points).

        Returns:
            (score, list of pattern names)
        """
        if not patterns:
            return 0, []

        # Get top pattern
        top_pattern = max(patterns, key=lambda p: p.get("confidence", 0))
        confidence = top_pattern.get("confidence", 0)

        # Score based on pattern confidence
        score = int(confidence * 20)
        pattern_names = [p.get("name", "unknown") for p in patterns]

        return min(score, 20), pattern_names

    def calculate_score(self, df: pd.DataFrame, indicators: Any,
                       patterns: Optional[List[Dict]] = None) -> SignalScore:
        """
        Calculate overall signal score.

        Args:
            df: Price DataFrame
            indicators: IndicatorValues object
            patterns: Optional list of detected patterns

        Returns:
            SignalScore with all components
        """
        # Calculate component scores
        rsi_score, rsi_direction = self._calculate_rsi_score(indicators.rsi)
        trend_score, trend_direction = self._calculate_trend_score(df)
        volume_score, volume_ratio = self._calculate_volume_score(df)
        pattern_score, pattern_names = self._calculate_pattern_score(patterns or [])

        # Calculate weighted total (0-100)
        total_score = int(
            rsi_score +
            trend_score +
            volume_score +
            pattern_score
        )

        # Determine signal direction
        # If both RSI and trend agree, that's strong confirmation
        if rsi_direction == "BUY" and "BULLISH" in trend_direction:
            signal = "BUY"
        elif rsi_direction == "SELL" and "BEARISH" in trend_direction:
            signal = "SELL"
        elif total_score >= 60:
            # Score is high but mixed signals - use RSI as tiebreaker
            signal = rsi_direction if rsi_direction in ["BUY", "SELL"] else "HOLD"
        else:
            signal = "HOLD"

        # Determine confidence level
        if total_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence = "HIGH"
        elif total_score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return SignalScore(
            total_score=total_score,
            signal=signal,
            confidence=confidence,
            rsi_score=rsi_score,
            trend_score=trend_score,
            volume_score=volume_score,
            pattern_score=pattern_score,
            rsi_value=indicators.rsi,
            trend_direction=trend_direction,
            volume_ratio=volume_ratio,
            patterns_detected=pattern_names
        )

    def should_execute(self, score: SignalScore, threshold: int = 75) -> bool:
        """Check if signal meets execution threshold."""
        return score.total_score >= threshold and score.signal in ["BUY", "SELL"]

    def format_score(self, score: SignalScore) -> str:
        """Format score for display."""
        emoji = {
            "HIGH": "🟢",
            "MEDIUM": "🟡",
            "LOW": "🔴"
        }.get(score.confidence, "⚪")

        return f"{emoji} Score: {score.total_score}% | Signal: {score.signal}"
