"""
Fair Value Gap (FVG) Detection Module.

FIXES:
- _check_filled_status() previously continued iterating ALL candles after a gap
  was filled. Now breaks on first fill (eliminates O(n²) worst case).
- Added guard for empty/short DataFrames.
- All float conversions made explicit to avoid pandas Series comparison warnings.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class FVGType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class FVG:
    """Represents a single Fair Value Gap."""

    type: FVGType
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    timestamp: pd.Timestamp
    filled: bool = False
    fill_timestamp: Optional[pd.Timestamp] = None

    @property
    def height(self) -> float:
        return self.top - self.bottom

    @property
    def mid_point(self) -> float:
        return (self.top + self.bottom) / 2


class FVGDetector:
    """
    Detects Fair Value Gaps — 3-candle imbalance patterns.

    Bullish FVG: candle[i].high < candle[i+2].low  (gap upward)
    Bearish FVG: candle[i].low  > candle[i+2].high (gap downward)
    """

    def __init__(self, min_gap_pips: float = 0.0) -> None:
        self.min_gap_pips = min_gap_pips
        self.fvgs: List[FVG] = []

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_fvg(self, df: pd.DataFrame, lookback: int = 50) -> List[FVG]:
        """Detect all FVGs in the most recent *lookback* candles."""
        self.fvgs = []

        if df.empty or len(df) < 3:
            return self.fvgs

        work = df.tail(lookback).copy().reset_index(drop=True)

        for i in range(len(work) - 2):
            c1 = work.iloc[i]
            c3 = work.iloc[i + 2]

            c1_high = float(c1["high"])
            c1_low  = float(c1["low"])
            c1_close = float(c1["close"])
            c3_low  = float(c3["low"])
            c3_high = float(c3["high"])

            # Bullish FVG: c1.high < c3.low
            if c1_high < c3_low:
                gap = c3_low - c1_high
                if c1_close > 0 and (gap / c1_close) * 100 >= self.min_gap_pips:
                    self.fvgs.append(
                        FVG(
                            type=FVGType.BULLISH,
                            start_idx=i,
                            end_idx=i + 2,
                            top=c3_low,
                            bottom=c1_high,
                            timestamp=c3["timestamp"],
                        )
                    )

            # Bearish FVG: c1.low > c3.high
            elif c1_low > c3_high:
                gap = c1_low - c3_high
                if c1_close > 0 and (gap / c1_close) * 100 >= self.min_gap_pips:
                    self.fvgs.append(
                        FVG(
                            type=FVGType.BEARISH,
                            start_idx=i,
                            end_idx=i + 2,
                            top=c1_low,
                            bottom=c3_high,
                            timestamp=c3["timestamp"],
                        )
                    )

        self._check_filled_status(work)
        return self.fvgs

    def _check_filled_status(self, df: pd.DataFrame) -> None:
        """
        Mark FVGs as filled when price re-enters the gap.

        FIX: now breaks on first fill instead of iterating all remaining candles.
        """
        for fvg in self.fvgs:
            candles_after = df.iloc[fvg.end_idx + 1 :]
            for _, candle in candles_after.iterrows():
                hi = float(candle["high"])
                lo = float(candle["low"])
                cl = float(candle["close"])

                entered_gap = lo <= fvg.top and hi >= fvg.bottom
                if not entered_gap:
                    continue

                if fvg.type == FVGType.BULLISH:
                    # Price came back down into bullish FVG
                    if fvg.bottom <= cl <= fvg.top:
                        fvg.filled = True
                        fvg.fill_timestamp = candle["timestamp"]
                        break  # FIX: was missing
                else:
                    # Price came back up into bearish FVG
                    if fvg.bottom <= cl <= fvg.top:
                        fvg.filled = True
                        fvg.fill_timestamp = candle["timestamp"]
                        break  # FIX: was missing

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_active_fvgs(self) -> List[FVG]:
        return [f for f in self.fvgs if not f.filled]

    def get_nearest_fvg(
        self, current_price: float, direction: str = "below"
    ) -> Optional[FVG]:
        active = self.get_active_fvgs()
        if direction == "below":
            candidates = [f for f in active if f.type == FVGType.BULLISH and f.top < current_price]
            return max(candidates, key=lambda x: x.top) if candidates else None
        else:
            candidates = [f for f in active if f.type == FVGType.BEARISH and f.bottom > current_price]
            return min(candidates, key=lambda x: x.bottom) if candidates else None

    def is_price_at_fvg(
        self, price: float, tolerance: float = 0.001
    ) -> Tuple[bool, Optional[FVG]]:
        tol = price * tolerance
        for fvg in self.get_active_fvgs():
            if fvg.bottom - tol <= price <= fvg.top + tol:
                return True, fvg
        return False, None

    def get_fvg_analysis(self, df: pd.DataFrame) -> Dict:
        current_price = float(df["close"].iloc[-1]) if not df.empty else 0.0
        self.detect_fvg(df)
        active = self.get_active_fvgs()
        at_fvg, current_fvg = self.is_price_at_fvg(current_price)

        return {
            "has_fvg": bool(active),
            "fvg_count": len(active),
            "bullish_fvgs": sum(1 for f in active if f.type == FVGType.BULLISH),
            "bearish_fvgs": sum(1 for f in active if f.type == FVGType.BEARISH),
            "nearest_support": self.get_nearest_fvg(current_price, "below"),
            "nearest_resistance": self.get_nearest_fvg(current_price, "above"),
            "at_fvg": at_fvg,
            "current_fvg": current_fvg,
            "all_fvgs": active,
        }
