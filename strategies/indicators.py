import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class IndicatorValues:
    rsi: float
    sma_20: float
    sma_50: float
    volume: float
    price: float


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def calculate_sma(prices: pd.Series, period: int) -> float:
    sma = prices.rolling(window=period).mean()
    return float(sma.iloc[-1]) if not sma.empty else float(prices.iloc[-1])


def calculate_all_indicators(df: pd.DataFrame) -> IndicatorValues:
    if df.empty or len(df) < 14:
        last_price = float(df["close"].iloc[-1]) if not df.empty else 0.0
        return IndicatorValues(
            rsi=50.0, sma_20=last_price, sma_50=last_price,
            volume=float(df["volume"].iloc[-1]) if not df.empty and "volume" in df.columns else 0.0,
            price=last_price,
        )
    return IndicatorValues(
        rsi=calculate_rsi(df["close"]),
        sma_20=calculate_sma(df["close"], 20),
        sma_50=calculate_sma(df["close"], 50),
        volume=float(df["volume"].iloc[-1]) if "volume" in df.columns else 0.0,
        price=float(df["close"].iloc[-1]),
    )


def evaluate_strategy(indicators: IndicatorValues, entry_conditions: Dict[str, Any],
                      exit_conditions: Dict[str, Any]) -> str:
    """Evaluate entry/exit conditions against indicators."""
    signal = "HOLD"
    if entry_conditions:
        entry_met = True
        for key, value in entry_conditions.items():
            if key == "rsi_less_than" and indicators.rsi >= value:
                entry_met = False
                break
            elif key == "volume_greater_than" and indicators.volume <= value:
                entry_met = False
                break
        if entry_met:
            signal = "BUY"
    if signal == "HOLD" and exit_conditions:
        exit_met = True
        for key, value in exit_conditions.items():
            if key == "rsi_greater_than" and indicators.rsi <= value:
                exit_met = False
                break
        if exit_met:
            signal = "SELL"
    return signal
