"""
Fair Value Gap (FVG) Detection Module
Detects 3-candle imbalance patterns (FVG)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FVGType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass
class FVG:
    """Represents a Fair Value Gap"""
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
    Detects Fair Value Gaps (FVG) - 3-candle imbalance patterns.
    
    Bullish FVG: Candle 1 high < Candle 3 low (gap up)
    Bearish FVG: Candle 1 low > Candle 3 high (gap down)
    """
    
    def __init__(self, min_gap_pips: float = 0.0):
        """
        Initialize FVG detector.
        
        Args:
            min_gap_pips: Minimum gap size to consider (as percentage)
        """
        self.min_gap_pips = min_gap_pips
        self.fvgs: List[FVG] = []
        
    def detect_fvg(self, df: pd.DataFrame, lookback: int = 50) -> List[FVG]:
        """
        Detect all FVGs in the data.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Number of candles to analyze
            
        Returns:
            List of FVG objects
        """
        if df.empty or len(df) < 3:
            return []
        
        self.fvgs = []
        
        # Work with recent data
        df_check = df.tail(lookback).copy().reset_index(drop=True)
        
        # Detect FVGs (need at least 3 candles)
        for i in range(len(df_check) - 2):
            candle1 = df_check.iloc[i]
            candle2 = df_check.iloc[i + 1]
            candle3 = df_check.iloc[i + 2]
            
            # Bullish FVG: Candle 1 high < Candle 3 low
            if candle1['high'] < candle3['low']:
                gap_size = candle3['low'] - candle1['high']
                gap_percent = (gap_size / candle1['close']) * 100
                
                if gap_percent >= self.min_gap_pips:
                    fvg = FVG(
                        type=FVGType.BULLISH,
                        start_idx=i,
                        end_idx=i + 2,
                        top=candle3['low'],
                        bottom=candle1['high'],
                        timestamp=candle3['timestamp']
                    )
                    self.fvgs.append(fvg)
            
            # Bearish FVG: Candle 1 low > Candle 3 high
            elif candle1['low'] > candle3['high']:
                gap_size = candle1['low'] - candle3['high']
                gap_percent = (gap_size / candle1['close']) * 100
                
                if gap_percent >= self.min_gap_pips:
                    fvg = FVG(
                        type=FVGType.BEARISH,
                        start_idx=i,
                        end_idx=i + 2,
                        top=candle1['low'],
                        bottom=candle3['high'],
                        timestamp=candle3['timestamp']
                    )
                    self.fvgs.append(fvg)
        
        # Check which FVGs have been filled
        self._check_filled_status(df_check)
        
        return self.fvgs
    
    def _check_filled_status(self, df: pd.DataFrame):
        """Check if FVGs have been filled by subsequent price action."""
        for fvg in self.fvgs:
            # Check candles after FVG formation
            candles_after = df.iloc[fvg.end_idx + 1:]
            
            for idx, candle in candles_after.iterrows():
                # Bullish FVG filled when price returns to gap
                if fvg.type == FVGType.BULLISH:
                    if candle['low'] <= fvg.top and candle['high'] >= fvg.bottom:
                        # Price entered the gap
                        if candle['close'] <= fvg.top and candle['close'] >= fvg.bottom:
                            fvg.filled = True
                            fvg.fill_timestamp = candle['timestamp']
                            break
                
                # Bearish FVG filled when price returns to gap
                elif fvg.type == FVGType.BEARISH:
                    if candle['high'] >= fvg.bottom and candle['low'] <= fvg.top:
                        # Price entered the gap
                        if candle['close'] <= fvg.top and candle['close'] >= fvg.bottom:
                            fvg.filled = True
                            fvg.fill_timestamp = candle['timestamp']
                            break
    
    def get_active_fvgs(self) -> List[FVG]:
        """Get unfilled (active) FVGs."""
        return [fvg for fvg in self.fvgs if not fvg.filled]
    
    def get_nearest_fvg(self, current_price: float, direction: str = 'below') -> Optional[FVG]:
        """
        Get the nearest active FVG to current price.
        
        Args:
            current_price: Current market price
            direction: 'below' for support FVGs, 'above' for resistance FVGs
            
        Returns:
            Nearest FVG or None
        """
        active = self.get_active_fvgs()
        
        if direction == 'below':
            # Find bullish FVGs below current price (support)
            support_fvgs = [fvg for fvg in active 
                          if fvg.type == FVGType.BULLISH and fvg.top < current_price]
            if support_fvgs:
                return max(support_fvgs, key=lambda x: x.top)
        
        elif direction == 'above':
            # Find bearish FVGs above current price (resistance)
            resistance_fvgs = [fvg for fvg in active 
                               if fvg.type == FVGType.BEARISH and fvg.bottom > current_price]
            if resistance_fvgs:
                return min(resistance_fvgs, key=lambda x: x.bottom)
        
        return None
    
    def is_price_at_fvg(self, price: float, tolerance: float = 0.001) -> Tuple[bool, Optional[FVG]]:
        """
        Check if price is currently at or near an active FVG.
        
        Args:
            price: Current price
            tolerance: Tolerance percentage
            
        Returns:
            Tuple of (is_at_fvg, fvg_object)
        """
        active = self.get_active_fvgs()
        
        for fvg in active:
            # Calculate tolerance in price terms
            tol_amount = price * tolerance
            
            # Check if price is near the FVG
            if abs(price - fvg.top) <= tol_amount or abs(price - fvg.bottom) <= tol_amount:
                return True, fvg
            
            # Check if price is inside the FVG
            if fvg.bottom <= price <= fvg.top:
                return True, fvg
        
        return False, None
    
    def get_fvg_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Get comprehensive FVG analysis for the current market condition.
        
        Returns:
            Dictionary with FVG analysis
        """
        current_price = df['close'].iloc[-1] if not df.empty else 0
        
        # Detect FVGs
        self.detect_fvg(df)
        
        active = self.get_active_fvgs()
        bullish_active = [fvg for fvg in active if fvg.type == FVGType.BULLISH]
        bearish_active = [fvg for fvg in active if fvg.type == FVGType.BEARISH]
        
        # Find nearest FVGs
        nearest_support = self.get_nearest_fvg(current_price, 'below')
        nearest_resistance = self.get_nearest_fvg(current_price, 'above')
        
        # Check if price is at an FVG
        at_fvg, current_fvg = self.is_price_at_fvg(current_price)
        
        return {
            'has_fvg': len(active) > 0,
            'fvg_count': len(active),
            'bullish_fvgs': len(bullish_active),
            'bearish_fvgs': len(bearish_active),
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'at_fvg': at_fvg,
            'current_fvg': current_fvg,
            'all_fvgs': active
        }
