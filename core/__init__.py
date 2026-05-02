"""
Core workflow modules for TradingBot.

This package contains the essential workflow orchestration components
inspired by the Career-Ops architecture:

- pipeline: Workflow orchestration
- tracker: Trading activity tracking
- metrics: Performance metrics collection
- scheduler: Job scheduling and timing
- retry: Retry mechanisms with backoff
- state_machine: Trading state management
- gemini_advisor: AI-powered signal analysis (optional)
"""

from .pipeline import TradingPipeline, PipelineStep, PipelineResult
from .tracker import TradingTracker, TradeRecord, PositionRecord, SignalRecord
from .metrics import MetricsCollector, TradingMetrics
from .scheduler import TradingScheduler, MarketSession
from .retry import RetryHandler, RetryConfig, CircuitBreaker
from .state_machine import TradingStateMachine, TradingState

try:
    from .gemini_advisor import GeminiAdvisor, SignalValidation, PositionSuggestion
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GeminiAdvisor = None
    SignalValidation = None
    PositionSuggestion = None

__all__ = [
    'TradingPipeline',
    'PipelineStep',
    'PipelineResult',
    'TradingTracker',
    'TradeRecord',
    'PositionRecord',
    'SignalRecord',
    'MetricsCollector',
    'TradingMetrics',
    'TradingScheduler',
    'MarketSession',
    'RetryHandler',
    'RetryConfig',
    'CircuitBreaker',
    'TradingStateMachine',
    'TradingState',
    'GeminiAdvisor',
    'SignalValidation',
    'PositionSuggestion',
    'GEMINI_AVAILABLE',
]
