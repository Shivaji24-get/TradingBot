import logging
import pandas as pd

logger = logging.getLogger(__name__)


class SignalGenerator:
    def __init__(self, min_pattern_size: int = 5, confidence_threshold: float = 0.75):
        self.min_pattern_size = min_pattern_size
        self.confidence_threshold = confidence_threshold

    def analyze(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < self.min_pattern_size * 3:
            return "HOLD"
        signals = [self._rsi_signal(df), self._ma_crossover_signal(df), self._volatility_signal(df)]
        buy = signals.count("BUY")
        sell = signals.count("SELL")
        if buy > sell and buy >= 2:
            return "BUY"
        if sell > buy and sell >= 2:
            return "SELL"
        return "HOLD"

    def _rsi_signal(self, df: pd.DataFrame) -> str:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if rsi < 30:
            return "BUY"
        if rsi > 70:
            return "SELL"
        return "HOLD"

    def _ma_crossover_signal(self, df: pd.DataFrame) -> str:
        df = df.copy()
        df["ma20"] = df["close"].rolling(20).mean()
        df["ma50"] = df["close"].rolling(50).mean()
        if len(df) < 2:
            return "HOLD"
        if df["ma20"].iloc[-1] > df["ma50"].iloc[-1] and df["ma20"].iloc[-2] <= df["ma50"].iloc[-2]:
            return "BUY"
        if df["ma20"].iloc[-1] < df["ma50"].iloc[-1] and df["ma20"].iloc[-2] >= df["ma50"].iloc[-2]:
            return "SELL"
        return "HOLD"

    def _volatility_signal(self, df: pd.DataFrame) -> str:
        recent = df["close"].pct_change().rolling(10).std().iloc[-1]
        older = df["close"].pct_change().rolling(30).std().iloc[-10:-5].mean()
        if recent > older * 1.5:
            return "BUY"
        if recent < older * 0.5:
            return "SELL"
        return "HOLD"
