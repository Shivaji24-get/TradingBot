"""
Order Block (OB) Detection Module
Detects bullish and bearish order blocks
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class OBType(Enum):
    BULLISH = "bullish"  # Before bearish move (buy zone)
    BEARISH = "bearish"  # Before bullish move (sell zone)


@dataclass
class OrderBlock:
    """Represents an Order Block"""
    type: OBType
    index: int
    open: float
    high: float
    low: float
    close: float
    timestamp: pd.Timestamp
    mitigated: bool = False
    mitigation_price: Optional[float] = None
    
    @property
    def body_top(self) -> float:
        return max(self.open, self.close)
    
    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)
    
    @property
    def is_bullish_candle(self) -> bool:
        return self.close > self.open


class OrderBlockDetector:
    """
    Detects Order Blocks - the last opposite candle before a strong move.
    
    Bullish OB: Last bearish candle before a strong bullish move (impulse)
    Bearish OB: Last bullish candle before a strong bearish move (impulse)
    """
    
    def __init__(self, impulse_threshold: float = 1.5):
        """
        Initialize OB detector.
        
        Args:
            impulse_threshold: Minimum body size ratio to consider as impulse (vs avg)
        """
        self.impulse_threshold = impulse_threshold
        self.order_blocks: List[OrderBlock] = []
        
    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 100) -> List[OrderBlock]:
        """
        Detect order blocks in the data.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Number of candles to analyze
            
        Returns:
            List of OrderBlock objects
        """
        if df.empty or len(df) < 10:
            return []
        
        self.order_blocks = []
        
        # Work with recent data
        df_check = df.tail(lookback).copy().reset_index(drop=True)
        
        # Calculate average candle body size
        df_check['body_size'] = abs(df_check['close'] - df_check['open'])
        avg_body = df_check['body_size'].mean()
        
        # Detect impulses and preceding order blocks
        for i in range(2, len(df_check) - 1):
            prev_candle = df_check.iloc[i - 1]
            curr_candle = df_check.iloc[i]
            
            # Check for bullish impulse (strong bullish candle)
            if self._is_bullish_impulse(curr_candle, avg_body):
                # Look for bearish candle before the impulse (Bullish OB)
                if prev_candle['close'] < prev_candle['open']:  # Bearish candle
                    ob = OrderBlock(
                        type=OBType.BULLISH,
                        index=i - 1,
                        open=prev_candle['open'],
                        high=prev_candle['high'],
                        low=prev_candle['low'],
                        close=prev_candle['close'],
                        timestamp=prev_candle['timestamp']
                    )
                    self.order_blocks.append(ob)
            
            # Check for bearish impulse (strong bearish candle)
            elif self._is_bearish_impulse(curr_candle, avg_body):
                # Look for bullish candle before the impulse (Bearish OB)
                if prev_candle['close'] > prev_candle['open']:  # Bullish candle
                    ob = OrderBlock(
                        type=OBType.BEARISH,
                        index=i - 1,
                        open=prev_candle['open'],
                        high=prev_candle['high'],
                        low=prev_candle['low'],
                        close=prev_candle['close'],
                        timestamp=prev_candle['timestamp']
                    )
                    self.order_blocks.append(ob)
        
        # Check mitigation status
        self._check_mitigation(df_check)
        
        return self.order_blocks
    
    def _is_bullish_impulse(self, candle: pd.Series, avg_body: float) -> bool:
        """Check if candle is a bullish impulse."""
        body = candle['close'] - candle['open']
        return body > 0 and body > avg_body * self.impulse_threshold
    
    def _is_bearish_impulse(self, candle: pd.Series, avg_body: float) -> bool:
        """Check if candle is a bearish impulse."""
        body = candle['open'] - candle['close']
        return body > 0 and body > avg_body * self.impulse_threshold
    
    def _check_mitigation(self, df: pd.DataFrame):
        """Check if order blocks have been mitigated (price returned to them)."""
        for ob in self.order_blocks:
            # Check candles after OB formation
            candles_after = df.iloc[ob.index + 1:]
            
            for idx, candle in candles_after.iterrows():
                # Bullish OB mitigated when price comes back into its range
                if ob.type == OBType.BULLISH:
                    # Mitigated if price enters the OB range
                    if candle['low'] <= ob.high and candle['high'] >= ob.low:
                        ob.mitigated = True
                        ob.mitigation_price = candle['close']
                        break
                
                # Bearish OB mitigated when price comes back into its range
                elif ob.type == OBType.BEARISH:
                    if candle['high'] >= ob.low and candle['low'] <= ob.high:
                        ob.mitigated = True
                        ob.mitigation_price = candle['close']
                        break
    
    def get_active_obs(self) -> List[OrderBlock]:
        """Get unmitigated (active) order blocks."""
        return [ob for ob in self.order_blocks if not ob.mitigated]
    
    def get_nearest_ob(self, current_price: float, direction: str = 'below') -> Optional[OrderBlock]:
        """
        Get nearest active order block to current price.
        
        Args:
            current_price: Current market price
            direction: 'below' for bullish OBs (support), 'above' for bearish OBs (resistance)
            
        Returns:
            Nearest OrderBlock or None
        """
        active = self.get_active_obs()
        
        if direction == 'below':
            # Find bullish OBs below current price
            support_obs = [ob for ob in active 
                         if ob.type == OBType.BULLISH and ob.high < current_price]
            if support_obs:
                # Return the one closest to current price (highest high)
                return max(support_obs, key=lambda x: x.high)
        
        elif direction == 'above':
            # Find bearish OBs above current price
            resistance_obs = [ob for ob in active 
                              if ob.type == OBType.BEARISH and ob.low > current_price]
            if resistance_obs:
                # Return the one closest to current price (lowest low)
                return min(resistance_obs, key=lambda x: x.low)
        
        return None
    
    def is_price_at_ob(self, price: float, tolerance: float = 0.002) -> Tuple[bool, Optional[OrderBlock]]:
        """
        Check if price is currently at or near an active order block.
        
        Args:
            price: Current price
            tolerance: Tolerance percentage
            
        Returns:
            Tuple of (is_at_ob, ob_object)
        """
        active = self.get_active_obs()
        
        for ob in active:
            tol_amount = price * tolerance
            
            # Check if price is near the OB
            if ob.type == OBType.BULLISH:
                # For bullish OB, price should be near the high (premium) or low (discount)
                if abs(price - ob.high) <= tol_amount or abs(price - ob.low) <= tol_amount:
                    return True, ob
                if ob.low <= price <= ob.high:
                    return True, ob
            
            elif ob.type == OBType.BEARISH:
                # For bearish OB, price should be near the low (premium) or high (discount)
                if abs(price - ob.low) <= tol_amount or abs(price - ob.high) <= tol_amount:
                    return True, ob
                if ob.low <= price <= ob.high:
                    return True, ob
        
        return False, None
    
    def get_ob_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Get comprehensive Order Block analysis.
        
        Returns:
            Dictionary with OB analysis
        """
        current_price = df['close'].iloc[-1] if not df.empty else 0
        
        # Detect order blocks
        self.detect_order_blocks(df)
        
        active = self.get_active_obs()
        bullish_active = [ob for ob in active if ob.type == OBType.BULLISH]
        bearish_active = [ob for ob in active if ob.type == OBType.BEARISH]
        
        # Find nearest OBs
        nearest_support = self.get_nearest_ob(current_price, 'below')
        nearest_resistance = self.get_nearest_ob(current_price, 'above')
        
        # Check if price is at an OB
        at_ob, current_ob = self.is_price_at_ob(current_price)
        
        return {
            'has_ob': len(active) > 0,
            'ob_count': len(active),
            'bullish_obs': len(bullish_active),
            'bearish_obs': len(bearish_active),
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'at_ob': at_ob,
            'current_ob': current_ob,
            'all_obs': active
        }
