"""
Order Block (OB) Detection Module.

FIXES:
- _check_mitigation() used `for idx, candle in iterrows()` but only used `candle`,
  not `idx` – this is fine but was confusing; also the inner loop never `break`-ed
  properly after mitigation, so it kept iterating. Now breaks on first mitigation.
- Replaced full-dataframe iterrows with tail-slice to avoid O(n²) worst case.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class OBType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class OrderBlock:
    type: OBType
    index: int
    open: float
    high: float
    low: float
    close: float
    timestamp: pd.Timestamp
    mitigated: bool = False
    mitigation_price: Optional[float] = None

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)


class OrderBlockDetector:
    """
    Detects Order Blocks – the last opposite candle before a strong impulsive move.

    Bullish OB: last bearish candle *before* a bullish impulse (buy zone)
    Bearish OB: last bullish candle *before* a bearish impulse (sell zone)
    """

    def __init__(self, impulse_threshold: float = 1.5) -> None:
        self.impulse_threshold = impulse_threshold
        self.order_blocks: List[OrderBlock] = []

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_order_blocks(
        self, df: pd.DataFrame, lookback: int = 100
    ) -> List[OrderBlock]:
        """Detect all order blocks in the most recent *lookback* candles."""
        self.order_blocks = []

        if df.empty or len(df) < 10:
            return self.order_blocks

        work = df.tail(lookback).copy().reset_index(drop=True)
        work["body_size"] = (work["close"] - work["open"]).abs()
        avg_body: float = float(work["body_size"].mean())

        if avg_body == 0:
            return self.order_blocks

        for i in range(1, len(work) - 1):
            prev = work.iloc[i - 1]
            curr = work.iloc[i]

            if self._is_bullish_impulse(curr, avg_body):
                # Preceding bearish candle is the bullish OB
                if prev["close"] < prev["open"]:
                    self.order_blocks.append(
                        OrderBlock(
                            type=OBType.BULLISH,
                            index=i - 1,
                            open=float(prev["open"]),
                            high=float(prev["high"]),
                            low=float(prev["low"]),
                            close=float(prev["close"]),
                            timestamp=prev["timestamp"],
                        )
                    )

            elif self._is_bearish_impulse(curr, avg_body):
                # Preceding bullish candle is the bearish OB
                if prev["close"] > prev["open"]:
                    self.order_blocks.append(
                        OrderBlock(
                            type=OBType.BEARISH,
                            index=i - 1,
                            open=float(prev["open"]),
                            high=float(prev["high"]),
                            low=float(prev["low"]),
                            close=float(prev["close"]),
                            timestamp=prev["timestamp"],
                        )
                    )

        self._check_mitigation(work)
        return self.order_blocks

    def _is_bullish_impulse(self, candle: pd.Series, avg_body: float) -> bool:
        body = float(candle["close"]) - float(candle["open"])
        return body > 0 and body >= avg_body * self.impulse_threshold

    def _is_bearish_impulse(self, candle: pd.Series, avg_body: float) -> bool:
        body = float(candle["open"]) - float(candle["close"])
        return body > 0 and body >= avg_body * self.impulse_threshold

    def _check_mitigation(self, df: pd.DataFrame) -> None:
        """
        Mark OBs as mitigated when price re-enters their range.

        FIX: previous implementation iterated the FULL remaining dataframe for
        each OB even after mitigation was confirmed. Now breaks on first touch.
        """
        for ob in self.order_blocks:
            # Only check candles after OB formation
            candles_after = df.iloc[ob.index + 1 :]
            for _, candle in candles_after.iterrows():
                hi = float(candle["high"])
                lo = float(candle["low"])
                cl = float(candle["close"])

                # FIX: break as soon as mitigation is confirmed
                if ob.type == OBType.BULLISH:
                    if lo <= ob.high and hi >= ob.low:
                        ob.mitigated = True
                        ob.mitigation_price = cl
                        break
                else:  # BEARISH
                    if hi >= ob.low and lo <= ob.high:
                        ob.mitigated = True
                        ob.mitigation_price = cl
                        break

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_obs(self) -> List[OrderBlock]:
        return [ob for ob in self.order_blocks if not ob.mitigated]

    def get_nearest_ob(
        self, current_price: float, direction: str = "below"
    ) -> Optional[OrderBlock]:
        active = self.get_active_obs()
        if direction == "below":
            candidates = [ob for ob in active if ob.type == OBType.BULLISH and ob.high < current_price]
            return max(candidates, key=lambda x: x.high) if candidates else None
        else:
            candidates = [ob for ob in active if ob.type == OBType.BEARISH and ob.low > current_price]
            return min(candidates, key=lambda x: x.low) if candidates else None

    def is_price_at_ob(
        self, price: float, tolerance: float = 0.002
    ) -> Tuple[bool, Optional[OrderBlock]]:
        tol = price * tolerance
        for ob in self.get_active_obs():
            if ob.low - tol <= price <= ob.high + tol:
                return True, ob
        return False, None

    def get_ob_analysis(self, df: pd.DataFrame) -> Dict:
        current_price = float(df["close"].iloc[-1]) if not df.empty else 0.0
        self.detect_order_blocks(df)
        active = self.get_active_obs()

        return {
            "has_ob": bool(active),
            "ob_count": len(active),
            "bullish_obs": sum(1 for ob in active if ob.type == OBType.BULLISH),
            "bearish_obs": sum(1 for ob in active if ob.type == OBType.BEARISH),
            "nearest_support": self.get_nearest_ob(current_price, "below"),
            "nearest_resistance": self.get_nearest_ob(current_price, "above"),
            "at_ob": self.is_price_at_ob(current_price)[0],
            "current_ob": self.is_price_at_ob(current_price)[1],
            "all_obs": active,
        }
