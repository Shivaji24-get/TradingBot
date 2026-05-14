import pandas as pd
from typing import Dict, Optional, Tuple


class LiquidityDetector:
    def __init__(self):
        self.pdh = None
        self.pdl = None

    def calculate_pdh_pdl(self, df: pd.DataFrame) -> Tuple[float, float]:
        if df.empty or len(df) < 2:
            return 0.0, 0.0
        d = df.copy()
        d["date"] = pd.to_datetime(d["timestamp"]).dt.date
        daily = d.groupby("date").agg({"high": "max", "low": "min"}).reset_index()
        if len(daily) < 2:
            return float(df["high"].max()), float(df["low"].min())
        prev = daily.iloc[-2]
        self.pdh = float(prev["high"])
        self.pdl = float(prev["low"])
        return self.pdh, self.pdl

    def detect_sweep(self, df: pd.DataFrame, lookback: int = 5) -> Dict:
        empty = {"sweep_detected": False, "sweep_type": None, "pdh": 0, "pdl": 0, "signal": None}
        if df.empty or len(df) < 10:
            return empty
        pdh, pdl = self.calculate_pdh_pdl(df)
        if pdh == 0 or pdl == 0:
            return {**empty, "pdh": pdh, "pdl": pdl}
        recent = df.tail(lookback).copy()
        high_sweep = False
        low_sweep = False
        above = recent["high"] > pdh
        if above.any():
            c = recent[above].iloc[0]
            if float(c["close"]) < pdh:
                high_sweep = True
        below = recent["low"] < pdl
        if below.any():
            c = recent[below].iloc[0]
            if float(c["close"]) > pdl:
                low_sweep = True
        signal = "SELL" if high_sweep else ("BUY" if low_sweep else None)
        sweep_type = "high" if high_sweep else ("low" if low_sweep else None)
        return {"sweep_detected": high_sweep or low_sweep, "sweep_type": sweep_type,
                "pdh": pdh, "pdl": pdl, "signal": signal,
                "high_sweep": high_sweep, "low_sweep": low_sweep, "sweep_distance": 0}
