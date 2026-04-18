import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self, min_pattern_size: int = 5, confidence_threshold: float = 0.75):
        self.min_pattern_size = min_pattern_size
        self.confidence_threshold = confidence_threshold
    
    def analyze(self, df: pd.DataFrame) -> str:
        if df.empty or len(df) < self.min_pattern_size * 3:
            return "HOLD"
        
        signals = []
        signals.append(self._rsi_signal(df))
        signals.append(self._ma_crossover_signal(df))
        signals.append(self._volatility_signal(df))
        
        buy_signals = signals.count("BUY")
        sell_signals = signals.count("SELL")
        
        if buy_signals > sell_signals and buy_signals >= 2:
            return "BUY"
        elif sell_signals > buy_signals and sell_signals >= 2:
            return "SELL"
        return "HOLD"
    
    def _rsi_signal(self, df: pd.DataFrame) -> str:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi.iloc[-1] < 30:
            return "BUY"
        elif rsi.iloc[-1] > 70:
            return "SELL"
        return "HOLD"
    
    def _ma_crossover_signal(self, df: pd.DataFrame) -> str:
        df = df.copy()
        df["ma20"] = df["close"].rolling(window=20).mean()
        df["ma50"] = df["close"].rolling(window=50).mean()
        
        if len(df) < 2:
            return "HOLD"
        
        if df["ma20"].iloc[-1] > df["ma50"].iloc[-1] and df["ma20"].iloc[-2] <= df["ma50"].iloc[-2]:
            return "BUY"
        elif df["ma20"].iloc[-1] < df["ma50"].iloc[-1] and df["ma20"].iloc[-2] >= df["ma50"].iloc[-2]:
            return "SELL"
        return "HOLD"
    
    def _volatility_signal(self, df: pd.DataFrame) -> str:
        recent_vol = df["close"].pct_change().rolling(window=10).std().iloc[-1]
        older_vol = df["close"].pct_change().rolling(window=30).std().iloc[-10:-5].mean()
        
        if recent_vol > older_vol * 1.5:
            return "BUY"
        elif recent_vol < older_vol * 0.5:
            return "SELL"
        return "HOLD"