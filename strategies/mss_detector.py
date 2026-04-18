"""
Market Structure Shift (MSS) Detection Module
Detects breaks of structure (BOS) and change of character (CHoCH)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MSSState(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MSSType(Enum):
    BOS = "break_of_structure"  # Continuation
    CHOCH = "change_of_character"  # Reversal


@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    type: str  # 'high' or 'low'
    price: float
    index: int
    timestamp: pd.Timestamp


@dataclass
class MSS:
    """Represents a Market Structure Shift"""
    type: MSSType
    direction: str  # 'bullish' or 'bearish'
    index: int
    price: float
    timestamp: pd.Timestamp
    break_level: float  # The swing point that was broken
    

class MSSDetector:
    """
    Detects Market Structure Shifts:
    - Break of Structure (BOS): Break of previous swing in trend direction
    - Change of Character (CHoCH): Break of previous swing against trend (reversal)
    """
    
    def __init__(self, swing_lookback: int = 5, displacement_threshold: float = 1.0):
        """
        Initialize MSS detector.
        
        Args:
            swing_lookback: Candles to look back for swing detection
            displacement_threshold: Minimum body size for displacement candle
        """
        self.swing_lookback = swing_lookback
        self.displacement_threshold = displacement_threshold
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.mss_events: List[MSS] = []
        self.current_structure: MSSState = MSSState.NEUTRAL
        
    def find_swings(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """
        Find swing highs and lows in the data.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Tuple of (swing_highs, swing_lows)
        """
        if df.empty or len(df) < self.swing_lookback * 2 + 1:
            return [], []
        
        self.swing_highs = []
        self.swing_lows = []
        
        highs = df['high'].values
        lows = df['low'].values
        
        lookback = self.swing_lookback
        
        # Find swing highs
        for i in range(lookback, len(highs) - lookback):
            # Check if current high is highest in lookback window
            is_swing_high = True
            current_high = highs[i]
            
            for j in range(1, lookback + 1):
                if highs[i - j] >= current_high or highs[i + j] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                self.swing_highs.append(SwingPoint(
                    type='high',
                    price=current_high,
                    index=i,
                    timestamp=df.iloc[i]['timestamp']
                ))
        
        # Find swing lows
        for i in range(lookback, len(lows) - lookback):
            # Check if current low is lowest in lookback window
            is_swing_low = True
            current_low = lows[i]
            
            for j in range(1, lookback + 1):
                if lows[i - j] <= current_low or lows[i + j] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                self.swing_lows.append(SwingPoint(
                    type='low',
                    price=current_low,
                    index=i,
                    timestamp=df.iloc[i]['timestamp']
                ))
        
        return self.swing_highs, self.swing_lows
    
    def detect_mss(self, df: pd.DataFrame) -> List[MSS]:
        """
        Detect Market Structure Shifts.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            List of MSS events
        """
        if df.empty or len(df) < 20:
            return []
        
        self.mss_events = []
        
        # Find swings first
        self.find_swings(df)
        
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return []
        
        # Get recent swings
        recent_highs = sorted(self.swing_highs, key=lambda x: x.index, reverse=True)[:3]
        recent_lows = sorted(self.swing_lows, key=lambda x: x.index, reverse=True)[:3]
        
        # Determine initial structure based on swing sequence
        if recent_highs and recent_lows:
            last_high = recent_highs[0]
            last_low = recent_lows[0]
            
            # If last high came after last low, potential bearish structure
            # If last low came after last high, potential bullish structure
            if last_high.index > last_low.index:
                self.current_structure = MSSState.BEARISH
            else:
                self.current_structure = MSSState.BULLISH
        
        # Check for structure breaks in recent candles
        df_check = df.copy().reset_index(drop=True)
        
        for i in range(len(df_check) - 5, len(df_check)):
            if i < 5:
                continue
                
            current_candle = df_check.iloc[i]
            prev_candles = df_check.iloc[i-5:i]
            
            # Check for bullish CHoCH (price breaks above previous lower high)
            # This happens in a downtrend when price breaks structure
            if self.current_structure == MSSState.BEARISH:
                # Find the most recent significant lower high
                for swing_high in recent_highs:
                    if swing_high.index < i:  # Swing occurred before current candle
                        # Check if current candle breaks above this high with displacement
                        if (current_candle['close'] > swing_high.price and 
                            current_candle['open'] < swing_high.price):
                            
                            # Check for displacement (strong body)
                            body_size = abs(current_candle['close'] - current_candle['open'])
                            avg_body = prev_candles['close'].diff().abs().mean()
                            
                            if body_size > avg_body * self.displacement_threshold:
                                mss = MSS(
                                    type=MSSType.CHOCH,
                                    direction='bullish',
                                    index=i,
                                    price=current_candle['close'],
                                    timestamp=current_candle['timestamp'],
                                    break_level=swing_high.price
                                )
                                self.mss_events.append(mss)
                                self.current_structure = MSSState.BULLISH
                                break
            
            # Check for bearish CHoCH (price breaks below previous higher low)
            elif self.current_structure == MSSState.BULLISH:
                # Find the most recent significant higher low
                for swing_low in recent_lows:
                    if swing_low.index < i:  # Swing occurred before current candle
                        # Check if current candle breaks below this low with displacement
                        if (current_candle['close'] < swing_low.price and 
                            current_candle['open'] > swing_low.price):
                            
                            # Check for displacement (strong body)
                            body_size = abs(current_candle['close'] - current_candle['open'])
                            avg_body = prev_candles['close'].diff().abs().mean()
                            
                            if body_size > avg_body * self.displacement_threshold:
                                mss = MSS(
                                    type=MSSType.CHOCH,
                                    direction='bearish',
                                    index=i,
                                    price=current_candle['close'],
                                    timestamp=current_candle['timestamp'],
                                    break_level=swing_low.price
                                )
                                self.mss_events.append(mss)
                                self.current_structure = MSSState.BEARISH
                                break
        
        return self.mss_events
    
    def detect_structure_break(self, df: pd.DataFrame) -> Optional[MSS]:
        """
        Detect if most recent price action shows a structure break.
        
        Returns:
            Latest MSS event or None
        """
        self.detect_mss(df)
        
        if self.mss_events:
            # Return the most recent event
            return max(self.mss_events, key=lambda x: x.index)
        
        return None
    
    def get_trend_bias(self, df: pd.DataFrame) -> Dict:
        """
        Get trend bias based on market structure.
        
        Returns:
            Dictionary with trend analysis
        """
        self.detect_mss(df)
        
        # Count higher highs and higher lows for bullish trend
        # Count lower highs and lower lows for bearish trend
        
        if len(self.swing_highs) < 2 or len(self.swing_lows) < 2:
            return {
                'bias': 'neutral',
                'structure': self.current_structure.value,
                'confidence': 0,
                'higher_highs': False,
                'higher_lows': False,
                'lower_highs': False,
                'lower_lows': False
            }
        
        # Check for higher highs
        highs_sorted = sorted(self.swing_highs, key=lambda x: x.index)
        higher_highs = highs_sorted[-1].price > highs_sorted[-2].price if len(highs_sorted) >= 2 else False
        
        # Check for higher lows
        lows_sorted = sorted(self.swing_lows, key=lambda x: x.index)
        higher_lows = lows_sorted[-1].price > lows_sorted[-2].price if len(lows_sorted) >= 2 else False
        
        # Check for lower highs
        lower_highs = highs_sorted[-1].price < highs_sorted[-2].price if len(highs_sorted) >= 2 else False
        
        # Check for lower lows
        lower_lows = lows_sorted[-1].price < lows_sorted[-2].price if len(lows_sorted) >= 2 else False
        
        # Determine bias
        bias = 'neutral'
        confidence = 0
        
        if higher_highs and higher_lows:
            bias = 'bullish'
            confidence = 80
        elif lower_highs and lower_lows:
            bias = 'bearish'
            confidence = 80
        elif higher_highs or higher_lows:
            bias = 'bullish_weak'
            confidence = 50
        elif lower_highs or lower_lows:
            bias = 'bearish_weak'
            confidence = 50
        
        # Boost confidence if MSS confirmed
        if self.mss_events:
            latest_mss = max(self.mss_events, key=lambda x: x.index)
            if latest_mss.type == MSSType.CHOCH:
                confidence = min(95, confidence + 15)
        
        return {
            'bias': bias,
            'structure': self.current_structure.value,
            'confidence': confidence,
            'higher_highs': higher_highs,
            'higher_lows': higher_lows,
            'lower_highs': lower_highs,
            'lower_lows': lower_lows,
            'recent_mss': self.mss_events[-1] if self.mss_events else None
        }
    
    def get_mss_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Get comprehensive MSS analysis.
        
        Returns:
            Dictionary with MSS analysis
        """
        trend_bias = self.get_trend_bias(df)
        
        # Check for recent MSS
        recent_mss = trend_bias.get('recent_mss')
        
        return {
            'has_mss': recent_mss is not None,
            'mss_type': recent_mss.type.value if recent_mss else None,
            'mss_direction': recent_mss.direction if recent_mss else None,
            'trend_bias': trend_bias['bias'],
            'structure': trend_bias['structure'],
            'confidence': trend_bias['confidence'],
            'higher_highs': trend_bias['higher_highs'],
            'higher_lows': trend_bias['higher_lows'],
            'lower_highs': trend_bias['lower_highs'],
            'lower_lows': trend_bias['lower_lows'],
            'swing_highs_count': len(self.swing_highs),
            'swing_lows_count': len(self.swing_lows)
        }
