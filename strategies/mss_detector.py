import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MSSState(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MSSType(Enum):
    BOS = "break_of_structure"
    CHOCH = "change_of_character"


@dataclass
class SwingPoint:
    type: str
    price: float
    index: int
    timestamp: pd.Timestamp


@dataclass
class MSS:
    type: MSSType
    direction: str
    index: int
    price: float
    timestamp: pd.Timestamp
    break_level: float


class MSSDetector:
    def __init__(self, swing_lookback: int = 5, displacement_threshold: float = 1.0):
        self.swing_lookback = swing_lookback
        self.displacement_threshold = displacement_threshold
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.mss_events: List[MSS] = []
        self.current_structure: MSSState = MSSState.NEUTRAL

    def find_swings(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        self.swing_highs = []
        self.swing_lows = []
        if df.empty or len(df) < self.swing_lookback * 2 + 1:
            return [], []
        highs = df["high"].values
        lows = df["low"].values
        lb = self.swing_lookback
        for i in range(lb, len(highs) - lb):
            if all(highs[i] > highs[i - j] and highs[i] > highs[i + j] for j in range(1, lb + 1)):
                self.swing_highs.append(SwingPoint("high", highs[i], i, df.iloc[i]["timestamp"]))
        for i in range(lb, len(lows) - lb):
            if all(lows[i] < lows[i - j] and lows[i] < lows[i + j] for j in range(1, lb + 1)):
                self.swing_lows.append(SwingPoint("low", lows[i], i, df.iloc[i]["timestamp"]))
        return self.swing_highs, self.swing_lows

    def detect_mss(self, df: pd.DataFrame) -> List[MSS]:
        self.mss_events = []
        if df.empty or len(df) < 20:
            return []
        self.find_swings(df)
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return []
        recent_highs = sorted(self.swing_highs, key=lambda x: x.index, reverse=True)[:3]
        recent_lows = sorted(self.swing_lows, key=lambda x: x.index, reverse=True)[:3]
        last_high = recent_highs[0]
        last_low = recent_lows[0]
        self.current_structure = MSSState.BEARISH if last_high.index > last_low.index else MSSState.BULLISH
        df_check = df.copy().reset_index(drop=True)
        for i in range(max(5, len(df_check) - 10), len(df_check)):
            curr = df_check.iloc[i]
            prev5 = df_check.iloc[i - 5:i]
            body = abs(float(curr["close"]) - float(curr["open"]))
            avg_body = prev5["close"].diff().abs().mean()
            if self.current_structure == MSSState.BEARISH:
                for sh in recent_highs:
                    if sh.index < i and float(curr["close"]) > sh.price and float(curr["open"]) < sh.price:
                        if avg_body > 0 and body > avg_body * self.displacement_threshold:
                            self.mss_events.append(MSS(MSSType.CHOCH, "bullish", i,
                                                       float(curr["close"]), curr["timestamp"], sh.price))
                            self.current_structure = MSSState.BULLISH
                            break
            elif self.current_structure == MSSState.BULLISH:
                for sl in recent_lows:
                    if sl.index < i and float(curr["close"]) < sl.price and float(curr["open"]) > sl.price:
                        if avg_body > 0 and body > avg_body * self.displacement_threshold:
                            self.mss_events.append(MSS(MSSType.CHOCH, "bearish", i,
                                                       float(curr["close"]), curr["timestamp"], sl.price))
                            self.current_structure = MSSState.BEARISH
                            break
        return self.mss_events

    def get_trend_bias(self, df: pd.DataFrame) -> Dict:
        self.detect_mss(df)
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return {"bias": "neutral", "structure": self.current_structure.value, "confidence": 0,
                    "higher_highs": False, "higher_lows": False, "lower_highs": False, "lower_lows": False}
        hs = sorted(self.swing_highs, key=lambda x: x.index)
        ls = sorted(self.swing_lows, key=lambda x: x.index)
        hh = hs[-1].price > hs[-2].price if len(hs) >= 2 else False
        hl = ls[-1].price > ls[-2].price if len(ls) >= 2 else False
        lh = hs[-1].price < hs[-2].price if len(hs) >= 2 else False
        ll = ls[-1].price < ls[-2].price if len(ls) >= 2 else False
        if hh and hl:
            bias, conf = "bullish", 80
        elif lh and ll:
            bias, conf = "bearish", 80
        elif hh or hl:
            bias, conf = "bullish_weak", 50
        elif lh or ll:
            bias, conf = "bearish_weak", 50
        else:
            bias, conf = "neutral", 0
        if self.mss_events:
            conf = min(95, conf + 15)
        return {"bias": bias, "structure": self.current_structure.value, "confidence": conf,
                "higher_highs": hh, "higher_lows": hl, "lower_highs": lh, "lower_lows": ll,
                "recent_mss": self.mss_events[-1] if self.mss_events else None}

    def get_mss_analysis(self, df: pd.DataFrame) -> Dict:
        tb = self.get_trend_bias(df)
        mss = tb.get("recent_mss")
        return {"has_mss": mss is not None, "mss_type": mss.type.value if mss else None,
                "mss_direction": mss.direction if mss else None, "trend_bias": tb["bias"],
                "structure": tb["structure"], "confidence": tb["confidence"],
                "higher_highs": tb["higher_highs"], "higher_lows": tb["higher_lows"],
                "lower_highs": tb["lower_highs"], "lower_lows": tb["lower_lows"],
                "swing_highs_count": len(self.swing_highs), "swing_lows_count": len(self.swing_lows)}
