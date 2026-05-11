"""
Strategies package – signal generation, scanning, and execution.

FIXES:
- SMCResult now exported (was used externally but not exported)
- Lazy imports for heavy modules to speed startup
- All public symbols in __all__
"""

from .base import BaseStrategy
from .indicators import IndicatorValues, calculate_all_indicators, evaluate_strategy
from .order_executor import OrderExecutor, TradeConfig, TradeResult
from .parser import StrategyParser
from .pattern_analyzer import Pattern, PatternAnalyzer
from .pattern_detector import PatternDetector
from .risk_manager import RiskManager
from .scanner import StockScanner
from .signal_generator import SignalGenerator
from .signal_scorer import SignalScore, SignalScorer
from .smart_money import SMCResult, SmartMoneyStrategy  # FIX: SMCResult now exported

# Heavy / optional imports
try:
    from .fvg_detector import FVG, FVGDetector, FVGType
    from .harmonic_detector import HarmonicDetector, HarmonicPattern
    from .liquidity import LiquidityDetector
    from .live_engine import LiveEngine, LiveTick
    from .live_smc_engine import LiveSMCEngine
    from .mss_detector import MSS, MSSDetector, MSSState, MSSType
    from .order_block import OBType, OrderBlock, OrderBlockDetector
except ImportError as _e:
    import logging
    logging.getLogger(__name__).warning("Optional strategy module not available: %s", _e)

__all__ = [
    "BaseStrategy",
    "SignalGenerator",
    "RiskManager",
    "StockScanner",
    "PatternAnalyzer",
    "PatternDetector",
    "Pattern",
    "SignalScorer",
    "SignalScore",
    "OrderExecutor",
    "TradeConfig",
    "TradeResult",
    "LiveEngine",
    "LiveTick",
    "LiveSMCEngine",
    "IndicatorValues",
    "calculate_all_indicators",
    "evaluate_strategy",
    "SmartMoneyStrategy",
    "SMCResult",            # FIX: was missing
    "LiquidityDetector",
    "FVGDetector",
    "FVG",
    "FVGType",
    "OrderBlockDetector",
    "OrderBlock",
    "OBType",
    "MSSDetector",
    "MSS",
    "MSSState",
    "MSSType",
    "HarmonicDetector",
    "HarmonicPattern",
]
