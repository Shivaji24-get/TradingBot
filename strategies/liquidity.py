"""
Liquidity Sweep Detection Module
Detects sweeps of Previous Day High (PDH) and Previous Day Low (PDL)
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


class LiquidityDetector:
    """
    Detects liquidity sweeps for Smart Money Concept trading.
    
    A liquidity sweep occurs when:
    - Price briefly breaks above PDH (Previous Day High) then reverses down → SELL setup
    - Price briefly breaks below PDL (Previous Day Low) then reverses up → BUY setup
    """
    
    def __init__(self):
        self.pdh = None
        self.pdl = None
        self.sweep_detected = False
        self.sweep_type = None  # 'high' or 'low'
        
    def calculate_pdh_pdl(self, df: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate Previous Day High and Previous Day Low.
        
        Args:
            df: DataFrame with at least 2 days of data
            
        Returns:
            Tuple of (PDH, PDL)
        """
        if df.empty or len(df) < 2:
            return 0.0, 0.0
            
        # Get date information from timestamps
        df = df.copy()
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        # Group by date and get high/low for each day
        daily_data = df.groupby('date').agg({
            'high': 'max',
            'low': 'min'
        }).reset_index()
        
        if len(daily_data) < 2:
            # Not enough days, use overall high/low
            return df['high'].max(), df['low'].min()
        
        # Get previous day (not current day)
        prev_day = daily_data.iloc[-2]
        
        self.pdh = prev_day['high']
        self.pdl = prev_day['low']
        
        return self.pdh, self.pdl
    
    def detect_sweep(self, df: pd.DataFrame, lookback: int = 5) -> Dict:
        """
        Detect if price has swept liquidity (PDH or PDL).
        
        Args:
            df: DataFrame with price data
            lookback: Number of recent candles to check for sweep
            
        Returns:
            Dictionary with sweep detection results
        """
        if df.empty or len(df) < 10:
            return {
                'sweep_detected': False,
                'sweep_type': None,
                'pdh': 0,
                'pdl': 0,
                'signal': None
            }
        
        # Calculate PDH and PDL
        pdh, pdl = self.calculate_pdh_pdl(df)
        
        if pdh == 0 or pdl == 0:
            return {
                'sweep_detected': False,
                'sweep_type': None,
                'pdh': pdh,
                'pdl': pdl,
                'signal': None
            }
        
        # Get recent candles
        recent_df = df.tail(lookback).copy()
        
        # Check for PDH sweep (price goes above PDH then reverses)
        # Criteria:
        # 1. Price breaks above PDH
        # 2. Then closes back below PDH (rejection)
        high_sweep = False
        low_sweep = False
        
        # Check if any candle wick went above PDH
        above_pdh = recent_df['high'] > pdh
        
        if above_pdh.any():
            # Get the candle that swept
            sweep_idx = recent_df[above_pdh].index[0]
            sweep_candle = recent_df.loc[sweep_idx]
            
            # Check if it closed below PDH (rejection)
            if sweep_candle['close'] < pdh:
                high_sweep = True
        
        # Check for PDL sweep (price goes below PDL then reverses)
        # Criteria:
        # 1. Price breaks below PDL
        # 2. Then closes back above PDL (rejection)
        below_pdl = recent_df['low'] < pdl
        
        if below_pdl.any():
            # Get the candle that swept
            sweep_idx = recent_df[below_pdl].index[0]
            sweep_candle = recent_df.loc[sweep_idx]
            
            # Check if it closed above PDL (rejection)
            if sweep_candle['close'] > pdl:
                low_sweep = True
        
        # Determine signal based on sweep
        signal = None
        sweep_type = None
        
        if high_sweep:
            sweep_type = 'high'
            signal = 'SELL'  # Swept highs, look for sells
        elif low_sweep:
            sweep_type = 'low'
            signal = 'BUY'   # Swept lows, look for buys
        
        return {
            'sweep_detected': high_sweep or low_sweep,
            'sweep_type': sweep_type,
            'pdh': pdh,
            'pdl': pdl,
            'signal': signal,
            'high_sweep': high_sweep,
            'low_sweep': low_sweep,
            'sweep_distance': self._calculate_sweep_distance(recent_df, sweep_type, pdh, pdl) if (high_sweep or low_sweep) else 0
        }
    
    def _calculate_sweep_distance(self, df: pd.DataFrame, sweep_type: str, 
                                   pdh: float, pdl: float) -> float:
        """Calculate how far price swept beyond the level."""
        if sweep_type == 'high':
            max_high = df['high'].max()
            return ((max_high - pdh) / pdh) * 100 if pdh > 0 else 0
        elif sweep_type == 'low':
            min_low = df['low'].min()
            return ((pdl - min_low) / pdl) * 100 if pdl > 0 else 0
        return 0
    
    def get_liquidity_levels(self, df: pd.DataFrame, num_levels: int = 3) -> Dict:
        """
        Get multiple liquidity levels (swing highs/lows) beyond just PDH/PDL.
        
        Args:
            df: DataFrame with price data
            num_levels: Number of recent swing highs/lows to identify
            
        Returns:
            Dictionary with liquidity levels
        """
        if df.empty or len(df) < 20:
            return {'swing_highs': [], 'swing_lows': []}
        
        # Find swing highs (local maxima)
        highs = df['high'].values
        swing_highs = []
        
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append({
                    'price': highs[i],
                    'index': i,
                    'timestamp': df.iloc[i]['timestamp']
                })
        
        # Find swing lows (local minima)
        lows = df['low'].values
        swing_lows = []
        
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append({
                    'price': lows[i],
                    'index': i,
                    'timestamp': df.iloc[i]['timestamp']
                })
        
        # Get recent N levels
        recent_highs = sorted(swing_highs, key=lambda x: x['index'], reverse=True)[:num_levels]
        recent_lows = sorted(swing_lows, key=lambda x: x['index'], reverse=True)[:num_levels]
        
        return {
            'swing_highs': recent_highs,
            'swing_lows': recent_lows,
            'pdh': self.pdh,
            'pdl': self.pdl
        }
