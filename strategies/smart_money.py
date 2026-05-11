"""
Smart Money Concepts (SMC) Strategy
Orchestrates HTF/LTF alignment, liquidity sweeps, FVG, OB, and MSS detection.

FIXES:
- Added mtf_aligned to _empty_result() (was missing, caused AttributeError)
- Removed dead _determine_signal() method (replaced by _determine_signal_3tier)
- Added input validation throughout
- Fixed score capping logic
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .fvg_detector import FVGDetector
from .liquidity import LiquidityDetector
from .mss_detector import MSSDetector
from .order_block import OrderBlockDetector

logger = logging.getLogger(__name__)


@dataclass
class SMCResult:
    """Result of Smart Money Concept analysis."""
    symbol: str
    signal: str          # 'BUY', 'SELL', or 'NEUTRAL'
    score: int
    htf_aligned: bool
    mtf_aligned: bool    # FIX: was missing from _empty_result
    liquidity_sweep: bool
    mss_confirmed: bool
    fvg_present: bool
    ob_present: bool
    pattern: str
    details: Dict = field(default_factory=dict)


class SmartMoneyStrategy:
    """
    Smart Money Concepts Trading Strategy (3-Tier MTF).

    Tier hierarchy:
      1. HTF (e.g. 1H): Trend Bias          → 25 pts
      2. MTF (e.g. 15M): Setup Validation   → 25 pts
      3. LTF (e.g. 5M):  Entry (MSS/CHoCH)  → 20 pts
      Liquidity Sweep                        → 20 pts
      Volume Spike                           → 10 pts
      FVG bonus (contextual)                 → up to +10 pts
      OB bonus (contextual)                  → up to +5 pts

    Max raw total before capping: 115 pts → capped at 100.
    """

    WEIGHT_HTF = 25
    WEIGHT_MTF = 25
    WEIGHT_LIQUIDITY = 20
    WEIGHT_MSS = 20
    WEIGHT_VOLUME = 10
    WEIGHT_FVG_BONUS = 10
    WEIGHT_OB_BONUS = 5

    MIN_SCORE_TO_TRADE = 75

    def __init__(self) -> None:
        self.liquidity_detector = LiquidityDetector()
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.mss_detector = MSSDetector()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        ltf_df: pd.DataFrame,
        mtf_df: Optional[pd.DataFrame] = None,
        htf_df: Optional[pd.DataFrame] = None,
    ) -> SMCResult:
        """
        Perform 3-tier SMC analysis on a symbol.

        Args:
            ltf_df: Entry timeframe DataFrame (e.g. 5 m)
            mtf_df: Setup timeframe DataFrame  (e.g. 15 m); falls back to ltf_df
            htf_df: Trend timeframe DataFrame  (e.g. 1 h);  falls back to mtf_df

        Returns:
            SMCResult with signal, score, and component flags.
        """
        if ltf_df is None or ltf_df.empty:
            logger.warning("SMC analyze called with empty LTF dataframe")
            return self._empty_result()

        # Cascade fallbacks
        if mtf_df is None or mtf_df.empty:
            mtf_df = ltf_df
        if htf_df is None or htf_df.empty:
            htf_df = mtf_df

        current_price: float = float(ltf_df["close"].iloc[-1])

        # --- Component analysis ---
        htf_score, htf_aligned, htf_bias = self._analyze_htf(htf_df)
        mtf_score, mtf_aligned, mtf_data = self._analyze_mtf_setup(mtf_df, htf_bias)
        liq_score, sweep_detected, sweep_signal, liq_data = self._analyze_liquidity(mtf_df)
        mss_score, mss_confirmed, mss_data = self._analyze_mss(ltf_df)
        fvg_score, fvg_present, fvg_data = self._analyze_fvg(mtf_df, current_price)
        ob_score, ob_present, ob_data = self._analyze_ob(mtf_df, current_price)
        vol_score, vol_data = self._analyze_volume(ltf_df)

        # --- Score aggregation ---
        raw_score = (
            htf_score + mtf_score + liq_score + mss_score + vol_score
            + (fvg_score if fvg_present else 0)
            + (ob_score if ob_present else 0)
        )
        total_score = min(100, raw_score)

        # --- Signal determination ---
        signal = self._determine_signal_3tier(
            htf_bias=htf_bias,
            sweep_signal=sweep_signal,
            mss_data=mss_data,
            mtf_aligned=mtf_aligned,
            sweep_detected=sweep_detected,
            mss_confirmed=mss_confirmed,
        )

        details: Dict = {
            "htf": {"bias": htf_bias, "score": htf_score},
            "mtf": {"aligned": mtf_aligned, "score": mtf_score, "data": mtf_data},
            "liquidity": {
                "sweep": sweep_detected,
                "signal": sweep_signal,
                "score": liq_score,
            },
            "mss": {"confirmed": mss_confirmed, "score": mss_score},
            "fvg": {"present": fvg_present, "data": fvg_data},
            "ob": {"present": ob_present, "data": ob_data},
            "volume": vol_data,
            "current_price": current_price,
        }

        return SMCResult(
            symbol="",
            signal=signal,
            score=total_score,
            htf_aligned=htf_aligned,
            mtf_aligned=mtf_aligned,
            liquidity_sweep=sweep_detected,
            mss_confirmed=mss_confirmed,
            fvg_present=fvg_present,
            ob_present=ob_present,
            pattern=self._determine_pattern(fvg_present, ob_present, fvg_data, ob_data),
            details=details,
        )

    def should_trade(self, result: SMCResult) -> bool:
        """Return True only when all confluence criteria are satisfied."""
        return (
            result.score >= self.MIN_SCORE_TO_TRADE
            and result.htf_aligned
            and result.liquidity_sweep
            and result.mss_confirmed
            and result.fvg_present
            and result.signal in ("BUY", "SELL")
        )

    def get_htf_timeframe(self, ltf_timeframe: str) -> str:
        """Map a lower timeframe string to its corresponding higher timeframe."""
        mapping = {
            "1m": "5m",
            "5m": "15m",
            "15m": "1h",
            "30m": "1h",
            "1h": "4h",
            "4h": "D",
            "D": "W",
        }
        return mapping.get(ltf_timeframe, "1h")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _analyze_htf(
        self, htf_df: pd.DataFrame
    ) -> Tuple[int, bool, str]:
        """Analyse Higher Time Frame structure bias."""
        if htf_df.empty or len(htf_df) < 20:
            return 0, False, "neutral"

        mss_data = self.mss_detector.get_mss_analysis(htf_df)
        bias: str = mss_data.get("trend_bias", "neutral")
        confidence: int = mss_data.get("confidence", 0)

        if bias in ("bullish", "bearish") and confidence >= 60:
            return self.WEIGHT_HTF, True, bias
        if bias in ("bullish_weak", "bearish_weak"):
            clean_bias = bias.replace("_weak", "")
            return self.WEIGHT_HTF // 2, True, clean_bias
        return 0, False, "neutral"

    def _analyze_mtf_setup(
        self, mtf_df: pd.DataFrame, htf_bias: str
    ) -> Tuple[int, bool, Dict]:
        """Validate MTF market structure against HTF bias."""
        mss_data = self.mss_detector.get_mss_analysis(mtf_df)
        mtf_bias: str = mss_data.get("trend_bias", "neutral")

        aligned = mtf_bias == htf_bias or mtf_bias.replace("_weak", "") == htf_bias
        score = self.WEIGHT_MTF if aligned else 0
        return score, aligned, mss_data

    def _analyze_liquidity(
        self, df: pd.DataFrame
    ) -> Tuple[int, bool, Optional[str], Dict]:
        """Detect liquidity sweeps of previous day highs/lows."""
        result = self.liquidity_detector.detect_sweep(df, lookback=10)
        detected: bool = result.get("sweep_detected", False)
        signal: Optional[str] = result.get("signal")
        score = self.WEIGHT_LIQUIDITY if (detected and signal) else 0
        return score, detected, signal, result

    def _analyze_mss(
        self, df: pd.DataFrame
    ) -> Tuple[int, bool, Dict]:
        """Detect Market Structure Shift on LTF for entry confirmation."""
        mss_data = self.mss_detector.get_mss_analysis(df)
        confirmed: bool = mss_data.get("has_mss", False)
        confidence: int = mss_data.get("confidence", 0)

        if confirmed and confidence >= 60:
            return self.WEIGHT_MSS, True, mss_data
        if mss_data.get("trend_bias") in ("bullish", "bearish"):
            # Partial credit when structure is clear but no explicit CHoCH
            return self.WEIGHT_MSS // 2, True, mss_data
        return 0, False, mss_data

    def _analyze_fvg(
        self, df: pd.DataFrame, current_price: float
    ) -> Tuple[int, bool, Dict]:
        """Locate Fair Value Gaps; award bonus points when price is at one."""
        fvg_data = self.fvg_detector.get_fvg_analysis(df)
        present: bool = fvg_data.get("has_fvg", False)
        at_fvg: bool = fvg_data.get("at_fvg", False)

        if not present:
            return 0, False, fvg_data
        score = self.WEIGHT_FVG_BONUS if at_fvg else self.WEIGHT_FVG_BONUS // 2
        return score, True, fvg_data

    def _analyze_ob(
        self, df: pd.DataFrame, current_price: float
    ) -> Tuple[int, bool, Dict]:
        """Locate Order Blocks; award bonus points when price is at one."""
        ob_data = self.ob_detector.get_ob_analysis(df)
        present: bool = ob_data.get("has_ob", False)
        at_ob: bool = ob_data.get("at_ob", False)

        if not present:
            return 0, False, ob_data
        score = self.WEIGHT_OB_BONUS if at_ob else 2
        return score, True, ob_data

    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """Check for volume spike confirming the move."""
        if df.empty or "volume" not in df.columns or len(df) < 2:
            return 0, {"spike": False, "current": 0, "avg": 0, "ratio": 0}

        current_vol: float = float(df["volume"].iloc[-1])
        avg_vol: float = float(df["volume"].tail(20).mean())

        if avg_vol <= 0:
            return 0, {"spike": False, "current": current_vol, "avg": 0, "ratio": 0}

        ratio = current_vol / avg_vol
        spike = ratio >= 1.5
        score = self.WEIGHT_VOLUME if spike else 0

        return score, {
            "spike": spike,
            "current": current_vol,
            "avg": avg_vol,
            "ratio": round(ratio, 2),
        }

    def _determine_signal_3tier(
        self,
        htf_bias: str,
        sweep_signal: Optional[str],
        mss_data: Dict,
        mtf_aligned: bool,
        sweep_detected: bool,
        mss_confirmed: bool,
    ) -> str:
        """
        Consolidate all tier signals into a single trade direction.

        Requirements:
          - HTF bias must be non-neutral
          - MTF must be aligned with HTF
          - At least one of: liquidity sweep OR MSS confirmation
        """
        if not htf_bias or htf_bias == "neutral":
            return "NEUTRAL"
        if not mtf_aligned:
            return "NEUTRAL"
        if not (sweep_detected or mss_confirmed):
            return "NEUTRAL"

        mss_bias: str = mss_data.get("trend_bias", "neutral")

        if htf_bias == "bullish":
            if sweep_signal == "BUY" or mss_bias in ("bullish", "bullish_weak"):
                return "BUY"
        elif htf_bias == "bearish":
            if sweep_signal == "SELL" or mss_bias in ("bearish", "bearish_weak"):
                return "SELL"

        return "NEUTRAL"

    def _determine_pattern(
        self,
        fvg_present: bool,
        ob_present: bool,
        fvg_data: Dict,
        ob_data: Dict,
    ) -> str:
        """Build a human-readable pattern label from active confluences."""
        parts: List[str] = []
        if fvg_present:
            parts.append("FVG_ENTRY" if fvg_data.get("at_fvg") else "FVG")
        if ob_present:
            parts.append("OB_ENTRY" if ob_data.get("at_ob") else "OB")
        return "+".join(parts) if parts else "NONE"

    def _empty_result(self) -> SMCResult:
        """Return a safe default result when data is unavailable."""
        return SMCResult(
            symbol="",
            signal="NEUTRAL",
            score=0,
            htf_aligned=False,
            mtf_aligned=False,          # FIX: field was missing before
            liquidity_sweep=False,
            mss_confirmed=False,
            fvg_present=False,
            ob_present=False,
            pattern="NO_DATA",
            details={"error": "Empty or insufficient data"},
        )
