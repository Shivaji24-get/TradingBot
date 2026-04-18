"""
Smart Money Concepts (SMC) Strategy
Orchestrates HTF/LTF alignment, liquidity sweeps, FVG, OB, and MSS detection
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .liquidity import LiquidityDetector
from .fvg_detector import FVGDetector, FVGType
from .order_block import OrderBlockDetector, OBType
from .mss_detector import MSSDetector, MSSState


@dataclass
class SMCResult:
    """Result of Smart Money Concept analysis"""
    symbol: str
    signal: str  # 'BUY', 'SELL', or 'NEUTRAL'
    score: int
    htf_aligned: bool
    liquidity_sweep: bool
    mss_confirmed: bool
    fvg_present: bool
    ob_present: bool
    pattern: str
    details: Dict


class SmartMoneyStrategy:
    """
    Smart Money Concepts Trading Strategy
    
    Entry Rules (ALL must be met):
    1. HTF Bias aligned (Higher Time Frame trend)
    2. Liquidity Sweep detected (PDH/PDL sweep)
    3. Market Structure Shift (MSS/CHoCH) confirmed
    4. Fair Value Gap (FVG) present
    5. Optional: Order Block (OB) present
    
    Scoring System:
    - HTF Alignment: 30%
    - Liquidity Sweep: 20%
    - MSS: 20%
    - FVG: 20%
    - Volume Spike: 10%
    
    Only trade if score >= 75%
    """
    
    # Scoring weights
    WEIGHT_HTF = 30
    WEIGHT_LIQUIDITY = 20
    WEIGHT_MSS = 20
    WEIGHT_FVG = 20
    WEIGHT_VOLUME = 10
    
    # Minimum score threshold
    MIN_SCORE = 75
    
    def __init__(self):
        """Initialize SMC strategy components"""
        self.liquidity_detector = LiquidityDetector()
        self.fvg_detector = FVGDetector()
        self.ob_detector = OrderBlockDetector()
        self.mss_detector = MSSDetector()
        
    def analyze(self, ltf_df: pd.DataFrame, htf_df: Optional[pd.DataFrame] = None) -> SMCResult:
        """
        Perform full SMC analysis on a symbol.
        
        Args:
            ltf_df: Lower Time Frame DataFrame (e.g., 5m)
            htf_df: Higher Time Frame DataFrame (e.g., 15m or 1h). If None, uses LTF only.
            
        Returns:
            SMCResult with signal and score
        """
        if ltf_df.empty:
            return self._empty_result()
        
        # Get current price
        current_price = ltf_df['close'].iloc[-1]
        
        # Step 1: HTF Bias Analysis (30% weight)
        htf_score, htf_aligned, htf_bias = self._analyze_htf(htf_df if htf_df is not None else ltf_df)
        
        # If no clear HTF trend, reject immediately
        if not htf_aligned:
            return SMCResult(
                symbol='',
                signal='NEUTRAL',
                score=0,
                htf_aligned=False,
                liquidity_sweep=False,
                mss_confirmed=False,
                fvg_present=False,
                ob_present=False,
                pattern='NO_TREND',
                details={'rejection_reason': 'No clear HTF trend'}
            )
        
        # Step 2: Liquidity Sweep Detection (20% weight)
        liquidity_score, sweep_detected, sweep_signal, liquidity_data = self._analyze_liquidity(ltf_df)
        
        # Step 3: Market Structure Shift (20% weight)
        mss_score, mss_confirmed, mss_data = self._analyze_mss(ltf_df)
        
        # Step 4: FVG Detection (20% weight)
        fvg_score, fvg_present, fvg_data = self._analyze_fvg(ltf_df, current_price)
        
        # Step 5: Order Block Detection (bonus, not required)
        ob_score, ob_present, ob_data = self._analyze_ob(ltf_df, current_price)
        
        # Step 6: Volume Analysis (10% weight)
        volume_score, volume_data = self._analyze_volume(ltf_df)
        
        # Calculate total score
        total_score = min(100, htf_score + liquidity_score + mss_score + fvg_score + volume_score + ob_score)
        
        # Determine signal based on confluence
        signal = self._determine_signal(
            htf_bias, sweep_signal, mss_data, fvg_data, sweep_detected, mss_confirmed, fvg_present
        )
        
        # Determine pattern
        pattern = self._determine_pattern(fvg_present, ob_present, fvg_data, ob_data)
        
        # Build details
        details = {
            'htf': {
                'aligned': htf_aligned,
                'bias': htf_bias,
                'score': htf_score
            },
            'liquidity': {
                'sweep_detected': sweep_detected,
                'sweep_signal': sweep_signal,
                'pdh': liquidity_data.get('pdh'),
                'pdl': liquidity_data.get('pdl'),
                'score': liquidity_score
            },
            'mss': {
                'confirmed': mss_confirmed,
                'bias': mss_data.get('trend_bias'),
                'structure': mss_data.get('structure'),
                'score': mss_score
            },
            'fvg': {
                'present': fvg_present,
                'at_fvg': fvg_data.get('at_fvg'),
                'type': 'bullish' if fvg_data.get('nearest_support') else 'bearish' if fvg_data.get('nearest_resistance') else None,
                'score': fvg_score
            },
            'ob': {
                'present': ob_present,
                'at_ob': ob_data.get('at_ob'),
                'type': 'bullish' if ob_data.get('nearest_support') else 'bearish' if ob_data.get('nearest_resistance') else None
            },
            'volume': {
                'spike': volume_data.get('spike'),
                'current': volume_data.get('current'),
                'avg': volume_data.get('avg'),
                'score': volume_score
            },
            'current_price': current_price
        }
        
        return SMCResult(
            symbol='',
            signal=signal,
            score=total_score,
            htf_aligned=htf_aligned,
            liquidity_sweep=sweep_detected,
            mss_confirmed=mss_confirmed,
            fvg_present=fvg_present,
            ob_present=ob_present,
            pattern=pattern,
            details=details
        )
    
    def _analyze_htf(self, htf_df: pd.DataFrame) -> Tuple[int, bool, str]:
        """
        Analyze Higher Time Frame bias.
        
        Returns:
            Tuple of (score, aligned, bias)
        """
        if htf_df.empty or len(htf_df) < 20:
            return 0, False, 'neutral'
        
        # Use MSS detector for HTF structure
        mss_data = self.mss_detector.get_mss_analysis(htf_df)
        
        bias = mss_data.get('trend_bias', 'neutral')
        confidence = mss_data.get('confidence', 0)
        
        # Check for clear trend
        if bias in ['bullish', 'bearish'] and confidence >= 60:
            score = self.WEIGHT_HTF
            aligned = True
        elif bias in ['bullish_weak', 'bearish_weak']:
            score = self.WEIGHT_HTF // 2
            aligned = True
            bias = bias.replace('_weak', '')
        else:
            score = 0
            aligned = False
        
        return score, aligned, bias
    
    def _analyze_liquidity(self, df: pd.DataFrame) -> Tuple[int, bool, Optional[str], Dict]:
        """
        Analyze liquidity sweeps.
        
        Returns:
            Tuple of (score, detected, signal, data)
        """
        result = self.liquidity_detector.detect_sweep(df, lookback=10)
        
        detected = result.get('sweep_detected', False)
        signal = result.get('signal')
        
        if detected and signal:
            score = self.WEIGHT_LIQUIDITY
        else:
            score = 0
        
        return score, detected, signal, result
    
    def _analyze_mss(self, df: pd.DataFrame) -> Tuple[int, bool, Dict]:
        """
        Analyze Market Structure Shift.
        
        Returns:
            Tuple of (score, confirmed, data)
        """
        mss_data = self.mss_detector.get_mss_analysis(df)
        
        confirmed = mss_data.get('has_mss', False)
        confidence = mss_data.get('confidence', 0)
        
        if confirmed and confidence >= 60:
            score = self.WEIGHT_MSS
        elif mss_data.get('trend_bias') in ['bullish', 'bearish']:
            score = self.WEIGHT_MSS // 2
            confirmed = True  # Partial credit for structure
        else:
            score = 0
        
        return score, confirmed, mss_data
    
    def _analyze_fvg(self, df: pd.DataFrame, current_price: float) -> Tuple[int, bool, Dict]:
        """
        Analyze Fair Value Gaps.
        
        Returns:
            Tuple of (score, present, data)
        """
        fvg_data = self.fvg_detector.get_fvg_analysis(df)
        
        present = fvg_data.get('has_fvg', False)
        at_fvg = fvg_data.get('at_fvg', False)
        
        if present:
            if at_fvg:
                # Price is currently at FVG - optimal entry
                score = self.WEIGHT_FVG
            else:
                # FVG exists but price not there yet
                score = self.WEIGHT_FVG // 2
        else:
            score = 0
        
        return score, present, fvg_data
    
    def _analyze_ob(self, df: pd.DataFrame, current_price: float) -> Tuple[int, bool, Dict]:
        """
        Analyze Order Blocks (bonus points).
        
        Returns:
            Tuple of (score, present, data)
        """
        ob_data = self.ob_detector.get_ob_analysis(df)
        
        present = ob_data.get('has_ob', False)
        at_ob = ob_data.get('at_ob', False)
        
        # OB is bonus - adds up to 5 points
        if present and at_ob:
            score = 5
        elif present:
            score = 2
        else:
            score = 0
        
        return score, present, ob_data
    
    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        Analyze volume for spike confirmation.
        
        Returns:
            Tuple of (score, data)
        """
        if df.empty or 'volume' not in df.columns:
            return 0, {'spike': False, 'current': 0, 'avg': 0}
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()
        
        spike = current_volume > avg_volume * 1.5 if avg_volume > 0 else False
        
        if spike:
            score = self.WEIGHT_VOLUME
        else:
            score = 0
        
        return score, {
            'spike': spike,
            'current': current_volume,
            'avg': avg_volume,
            'ratio': current_volume / avg_volume if avg_volume > 0 else 0
        }
    
    def _determine_signal(self, htf_bias: str, sweep_signal: Optional[str], 
                          mss_data: Dict, fvg_data: Dict,
                          sweep_detected: bool, mss_confirmed: bool, 
                          fvg_present: bool) -> str:
        """
        Determine final trading signal based on all confluences.
        
        Signal requires:
        - HTF bias clear
        - Liquidity sweep (with matching signal direction)
        - MSS confirmation
        - FVG present
        """
        if not sweep_detected or not mss_confirmed or not fvg_present:
            return 'NEUTRAL'
        
        # Check signal alignment
        if sweep_signal == 'BUY' and htf_bias == 'bullish':
            return 'BUY'
        elif sweep_signal == 'SELL' and htf_bias == 'bearish':
            return 'SELL'
        
        # Check MSS bias alignment
        mss_bias = mss_data.get('trend_bias', 'neutral')
        if sweep_signal == 'BUY' and mss_bias in ['bullish', 'bullish_weak']:
            return 'BUY'
        elif sweep_signal == 'SELL' and mss_bias in ['bearish', 'bearish_weak']:
            return 'SELL'
        
        return 'NEUTRAL'
    
    def _determine_pattern(self, fvg_present: bool, ob_present: bool, 
                          fvg_data: Dict, ob_data: Dict) -> str:
        """Determine the primary pattern detected."""
        patterns = []
        
        if fvg_present:
            if fvg_data.get('at_fvg'):
                patterns.append('FVG_ENTRY')
            else:
                patterns.append('FVG')
        
        if ob_present:
            if ob_data.get('at_ob'):
                patterns.append('OB_ENTRY')
            else:
                patterns.append('OB')
        
        if not patterns:
            return 'NONE'
        
        return '+'.join(patterns)
    
    def _empty_result(self) -> SMCResult:
        """Return empty result for invalid data."""
        return SMCResult(
            symbol='',
            signal='NEUTRAL',
            score=0,
            htf_aligned=False,
            liquidity_sweep=False,
            mss_confirmed=False,
            fvg_present=False,
            ob_present=False,
            pattern='NO_DATA',
            details={'error': 'Empty data provided'}
        )
    
    def should_trade(self, result: SMCResult) -> bool:
        """
        Determine if trade should be taken based on SMC result.
        
        Args:
            result: SMCResult from analysis
            
        Returns:
            True if all criteria met for trading
        """
        return (
            result.score >= self.MIN_SCORE and
            result.htf_aligned and
            result.liquidity_sweep and
            result.mss_confirmed and
            result.fvg_present and
            result.signal in ['BUY', 'SELL']
        )
    
    def get_htf_timeframe(self, ltf_timeframe: str) -> str:
        """
        Get appropriate HTF based on LTF.
        
        Args:
            ltf_timeframe: Lower timeframe (e.g., '5m', '15m')
            
        Returns:
            Higher timeframe string
        """
        mapping = {
            '1m': '5m',
            '5m': '15m',
            '15m': '1h',
            '30m': '1h',
            '1h': '4h',
            '4h': 'D',
            'D': 'W'
        }
        return mapping.get(ltf_timeframe, '1h')
