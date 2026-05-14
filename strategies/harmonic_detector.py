import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .mss_detector import SwingPoint, MSSDetector


@dataclass
class HarmonicPattern:
    name: str
    direction: str
    points: Dict[str, SwingPoint]
    ratios: Dict[str, float]
    confidence: float
    timestamp: pd.Timestamp


class HarmonicDetector:
    TOLERANCE = 0.15
    PATTERNS = {
        "Gartley":   {"AB_XA": 0.618, "BC_AB": (0.382, 0.886), "CD_BC": (1.272, 1.618), "AD_XA": 0.786},
        "Butterfly":  {"AB_XA": 0.786, "BC_AB": (0.382, 0.886), "CD_BC": (1.618, 2.618), "AD_XA": (1.27, 1.618)},
        "Bat":        {"AB_XA": (0.382, 0.50), "BC_AB": (0.382, 0.886), "CD_BC": (1.618, 2.618), "AD_XA": 0.886},
        "Crab":       {"AB_XA": (0.382, 0.618), "BC_AB": (0.382, 0.886), "CD_BC": (2.24, 3.618), "AD_XA": 1.618},
    }

    def __init__(self, swing_lookback: int = 5):
        self.mss_detector = MSSDetector(swing_lookback=swing_lookback)

    def detect_patterns(self, df: pd.DataFrame) -> List[HarmonicPattern]:
        if df.empty or len(df) < 50:
            return []
        highs, lows = self.mss_detector.find_swings(df)
        all_swings = sorted(highs + lows, key=lambda x: x.index)
        if len(all_swings) < 5:
            return []
        patterns = []
        recent = all_swings[-12:]
        for i in range(len(recent) - 4):
            pts = recent[i:i + 5]
            if (pts[0].type == "low" and pts[1].type == "high" and pts[2].type == "low"
                    and pts[3].type == "high" and pts[4].type == "low"):
                p = self._validate_pattern(pts, "bullish")
                if p:
                    patterns.append(p)
            elif (pts[0].type == "high" and pts[1].type == "low" and pts[2].type == "high"
                  and pts[3].type == "low" and pts[4].type == "high"):
                p = self._validate_pattern(pts, "bearish")
                if p:
                    patterns.append(p)
        return patterns

    def _validate_pattern(self, pts: List[SwingPoint], direction: str) -> Optional[HarmonicPattern]:
        X, A, B, C, D = pts
        XA = abs(A.price - X.price)
        AB = abs(B.price - A.price)
        BC = abs(C.price - B.price)
        CD = abs(D.price - C.price)
        if XA == 0 or AB == 0 or BC == 0:
            return None
        ratios = {"AB_XA": AB / XA, "BC_AB": BC / AB, "CD_BC": CD / BC,
                  "AD_XA": abs(D.price - X.price) / XA}
        best, max_conf = None, 0
        for name, defs in self.PATTERNS.items():
            conf = self._confidence(ratios, defs)
            if conf > 0.7 and conf > max_conf:
                max_conf, best = conf, name
        if best:
            return HarmonicPattern(best, direction, {"X": X, "A": A, "B": B, "C": C, "D": D},
                                   ratios, max_conf, D.timestamp)
        return None

    def _confidence(self, ratios: Dict, defs: Dict) -> float:
        scores = []
        for key, target in defs.items():
            val = ratios[key]
            if isinstance(target, tuple):
                scores.append(1.0 if target[0] <= val <= target[1]
                               else max(0, 1 - min(abs(val - target[0]), abs(val - target[1])) / (target[0] * self.TOLERANCE)))
            else:
                scores.append(max(0, 1 - abs(val - target) / (target * self.TOLERANCE)) if target else 0)
        return sum(scores) / len(scores) if scores else 0

    def get_harmonic_analysis(self, df: pd.DataFrame) -> Dict:
        patterns = self.detect_patterns(df)
        if not patterns:
            return {"has_pattern": False, "patterns": [], "confidence": 0}
        patterns.sort(key=lambda x: x.points["D"].index, reverse=True)
        latest = patterns[0]
        return {"has_pattern": True, "pattern_count": len(patterns),
                "latest_pattern": latest.name, "direction": latest.direction,
                "confidence": latest.confidence, "all_patterns": patterns}
