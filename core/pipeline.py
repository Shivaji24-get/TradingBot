"""
Trading Pipeline - Workflow orchestration module.

Inspired by Career-Ops batch processing and pipeline patterns.
This module orchestrates the complete trading workflow from signal
generation to order execution and position tracking.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PARTIAL = auto()
    CANCELLED = auto()


class PipelineStep(Enum):
    """Trading pipeline steps."""
    MARKET_DATA = auto()
    SIGNAL_GENERATION = auto()
    RISK_VALIDATION = auto()
    ORDER_PLACEMENT = auto()
    POSITION_TRACKING = auto()
    EXIT_MONITORING = auto()
    PNL_RECORDING = auto()
    METRICS_UPDATE = auto()


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool
    symbol: str
    step: PipelineStep
    status: PipelineStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0


@dataclass
class PipelineConfig:
    """Configuration for trading pipeline."""
    # Execution settings
    max_concurrent: int = 5
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    
    # Feature toggles
    enable_auto_trade: bool = False
    require_confirmation: bool = True
    paper_trading: bool = True
    
    # Validation settings
    min_signal_score: float = 75.0
    min_risk_reward: float = 1.5
    
    # Market settings
    symbols: List[str] = field(default_factory=list)
    scan_interval: int = 60


class TradingPipeline:
    """
    Orchestrates the complete trading workflow.
    
    Inspired by Career-Ops batch processing, this pipeline:
    1. Fetches market data
    2. Generates trading signals
    3. Validates risk parameters
    4. Places orders (if enabled)
    5. Tracks positions
    6. Monitors exit conditions
    7. Records P&L
    8. Updates metrics
    
    Usage:
        pipeline = TradingPipeline(config, fyers_client, tracker)
        result = pipeline.execute_single("NSE:NIFTY50-INDEX")
        results = pipeline.execute_batch(symbols)
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        fyers_client: Any,
        tracker: Any,
        risk_manager: Any = None,
        signal_generator: Any = None,
        order_executor: Any = None
    ):
        self.config = config
        self.fyers_client = fyers_client
        self.tracker = tracker
        self.risk_manager = risk_manager
        self.signal_generator = signal_generator
        self.order_executor = order_executor
        
        self._running = False
        self._step_handlers: Dict[PipelineStep, Callable] = {}
        self._results: List[PipelineResult] = []
        
        self._register_default_handlers()
        
        logger.info("TradingPipeline initialized")
    
    def _register_default_handlers(self):
        """Register default step handlers."""
        self._step_handlers = {
            PipelineStep.MARKET_DATA: self._handle_market_data,
            PipelineStep.SIGNAL_GENERATION: self._handle_signal_generation,
            PipelineStep.RISK_VALIDATION: self._handle_risk_validation,
            PipelineStep.ORDER_PLACEMENT: self._handle_order_placement,
            PipelineStep.POSITION_TRACKING: self._handle_position_tracking,
            PipelineStep.EXIT_MONITORING: self._handle_exit_monitoring,
            PipelineStep.PNL_RECORDING: self._handle_pnl_recording,
            PipelineStep.METRICS_UPDATE: self._handle_metrics_update,
        }
    
    def execute_single(self, symbol: str) -> PipelineResult:
        """
        Execute complete pipeline for a single symbol.
        
        Args:
            symbol: Trading symbol (e.g., "NSE:NIFTY50-INDEX")
            
        Returns:
            PipelineResult with execution details
        """
        start_time = time.time()
        
        try:
            logger.debug(f"Starting pipeline for {symbol}")
            
            # Step 1: Market Data
            result = self._step_handlers[PipelineStep.MARKET_DATA](symbol)
            if not result.success:
                return result
            market_data = result.data
            
            # Step 2: Signal Generation
            result = self._step_handlers[PipelineStep.SIGNAL_GENERATION](
                symbol, market_data
            )
            if not result.success:
                return result
            signal_data = result.data
            
            # Check if signal is actionable
            if signal_data.get('signal') == 'HOLD':
                return PipelineResult(
                    success=True,
                    symbol=symbol,
                    step=PipelineStep.SIGNAL_GENERATION,
                    status=PipelineStatus.COMPLETED,
                    data={'message': 'No actionable signal'},
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Step 3: Risk Validation
            result = self._step_handlers[PipelineStep.RISK_VALIDATION](
                symbol, signal_data
            )
            if not result.success:
                return result
            
            # Step 4: Order Placement (if enabled)
            if self.config.enable_auto_trade:
                result = self._step_handlers[PipelineStep.ORDER_PLACEMENT](
                    symbol, signal_data
                )
                if not result.success:
                    return result
                order_data = result.data
                
                # Step 5: Position Tracking
                self._step_handlers[PipelineStep.POSITION_TRACKING](
                    symbol, order_data
                )
            
            # Final success result
            duration = (time.time() - start_time) * 1000
            return PipelineResult(
                success=True,
                symbol=symbol,
                step=PipelineStep.METRICS_UPDATE,
                status=PipelineStatus.COMPLETED,
                data={
                    'symbol': symbol,
                    'signal': signal_data.get('signal'),
                    'score': signal_data.get('score'),
                    'auto_traded': self.config.enable_auto_trade
                },
                duration_ms=duration
            )
            
        except Exception as e:
            logger.error(f"Pipeline failed for {symbol}: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.MARKET_DATA,
                status=PipelineStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def execute_batch(self, symbols: List[str]) -> List[PipelineResult]:
        """
        Execute pipeline for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            List of PipelineResult for each symbol
        """
        logger.info(f"Starting batch execution for {len(symbols)} symbols")
        
        results = []
        for symbol in symbols:
            if not self._running:
                logger.info("Pipeline execution cancelled")
                break
            
            result = self.execute_single(symbol)
            results.append(result)
            
            # Brief pause between symbols to avoid rate limits
            time.sleep(0.1)
        
        self._results = results
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Batch complete: {success_count}/{len(results)} successful")
        
        return results
    
    def start(self):
        """Start the pipeline for continuous execution."""
        self._running = True
        logger.info("TradingPipeline started")
    
    def stop(self):
        """Stop the pipeline."""
        self._running = False
        logger.info("TradingPipeline stopped")
    
    def get_results(self) -> List[PipelineResult]:
        """Get results from last execution."""
        return self._results
    
    # Step Handlers
    
    def _handle_market_data(self, symbol: str) -> PipelineResult:
        """Fetch market data for symbol."""
        try:
            from api import get_historical_data
            
            df = get_historical_data(
                self.fyers_client,
                symbol,
                resolution="D",
                count=50
            )
            
            if df.empty:
                return PipelineResult(
                    success=False,
                    symbol=symbol,
                    step=PipelineStep.MARKET_DATA,
                    status=PipelineStatus.FAILED,
                    error="No market data available"
                )
            
            return PipelineResult(
                success=True,
                symbol=symbol,
                step=PipelineStep.MARKET_DATA,
                status=PipelineStatus.COMPLETED,
                data={'dataframe': df}
            )
            
        except Exception as e:
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.MARKET_DATA,
                status=PipelineStatus.FAILED,
                error=f"Market data error: {str(e)}"
            )
    
    def _handle_signal_generation(
        self, symbol: str, market_data: Dict
    ) -> PipelineResult:
        """Generate trading signal."""
        try:
            if self.signal_generator:
                df = market_data.get('dataframe')
                signal = self.signal_generator.analyze(df)
                
                # Calculate score if available
                score = getattr(self.signal_generator, 'last_score', 50)
                
                return PipelineResult(
                    success=True,
                    symbol=symbol,
                    step=PipelineStep.SIGNAL_GENERATION,
                    status=PipelineStatus.COMPLETED,
                    data={
                        'signal': signal,
                        'score': score,
                        'dataframe': df
                    }
                )
            else:
                # Default: no signal generator, assume HOLD
                return PipelineResult(
                    success=True,
                    symbol=symbol,
                    step=PipelineStep.SIGNAL_GENERATION,
                    status=PipelineStatus.COMPLETED,
                    data={'signal': 'HOLD', 'score': 0}
                )
                
        except Exception as e:
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.SIGNAL_GENERATION,
                status=PipelineStatus.FAILED,
                error=f"Signal generation error: {str(e)}"
            )
    
    def _handle_risk_validation(
        self, symbol: str, signal_data: Dict
    ) -> PipelineResult:
        """Validate risk parameters."""
        try:
            if self.risk_manager:
                can_trade, reason = self.risk_manager.can_trade()
                if not can_trade:
                    return PipelineResult(
                        success=False,
                        symbol=symbol,
                        step=PipelineStep.RISK_VALIDATION,
                        status=PipelineStatus.FAILED,
                        error=f"Risk check failed: {reason}"
                    )
                
                # Check signal score threshold
                score = signal_data.get('score', 0)
                if score < self.config.min_signal_score:
                    return PipelineResult(
                        success=False,
                        symbol=symbol,
                        step=PipelineStep.RISK_VALIDATION,
                        status=PipelineStatus.FAILED,
                        error=f"Signal score {score} below threshold {self.config.min_signal_score}"
                    )
            
            return PipelineResult(
                success=True,
                symbol=symbol,
                step=PipelineStep.RISK_VALIDATION,
                status=PipelineStatus.COMPLETED,
                data=signal_data
            )
            
        except Exception as e:
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.RISK_VALIDATION,
                status=PipelineStatus.FAILED,
                error=f"Risk validation error: {str(e)}"
            )
    
    def _handle_order_placement(
        self, symbol: str, signal_data: Dict
    ) -> PipelineResult:
        """Place order (paper or live)."""
        try:
            signal = signal_data.get('signal')
            
            if self.config.paper_trading:
                # Paper trading - simulate order
                from api import get_quotes
                quote = get_quotes(self.fyers_client, symbol)
                price = quote.get('last', 0)
                
                return PipelineResult(
                    success=True,
                    symbol=symbol,
                    step=PipelineStep.ORDER_PLACEMENT,
                    status=PipelineStatus.COMPLETED,
                    data={
                        'order_id': f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        'symbol': symbol,
                        'side': signal,
                        'price': price,
                        'qty': 1,
                        'paper': True
                    }
                )
            
            elif self.order_executor:
                # Live trading with order executor
                from api import get_funds
                funds = get_funds(self.fyers_client)
                capital = funds.get('available_cash', 100000)
                
                quote = get_quotes(self.fyers_client, symbol)
                price = quote.get('last', 0)
                
                score = signal_data.get('score', 50)
                result = self.order_executor.execute_trade(
                    symbol=symbol,
                    signal=signal,
                    price=price,
                    score=score,
                    capital=capital,
                    confirm=self.config.require_confirmation
                )
                
                if result.success:
                    return PipelineResult(
                        success=True,
                        symbol=symbol,
                        step=PipelineStep.ORDER_PLACEMENT,
                        status=PipelineStatus.COMPLETED,
                        data={
                            'order_id': result.order_id,
                            'symbol': symbol,
                            'side': signal,
                            'price': price,
                            'qty': result.qty,
                            'paper': False
                        }
                    )
                else:
                    return PipelineResult(
                        success=False,
                        symbol=symbol,
                        step=PipelineStep.ORDER_PLACEMENT,
                        status=PipelineStatus.FAILED,
                        error=result.error or "Order execution failed"
                    )
            
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.ORDER_PLACEMENT,
                status=PipelineStatus.FAILED,
                error="No order executor configured"
            )
            
        except Exception as e:
            return PipelineResult(
                success=False,
                symbol=symbol,
                step=PipelineStep.ORDER_PLACEMENT,
                status=PipelineStatus.FAILED,
                error=f"Order placement error: {str(e)}"
            )
    
    def _handle_position_tracking(
        self, symbol: str, order_data: Dict
    ) -> PipelineResult:
        """Track position in tracker."""
        try:
            if self.tracker:
                self.tracker.add_position(
                    symbol=symbol,
                    side=order_data.get('side'),
                    entry_price=order_data.get('price'),
                    qty=order_data.get('qty'),
                    order_id=order_data.get('order_id'),
                    paper=order_data.get('paper', False)
                )
            
            return PipelineResult(
                success=True,
                symbol=symbol,
                step=PipelineStep.POSITION_TRACKING,
                status=PipelineStatus.COMPLETED,
                data=order_data
            )
            
        except Exception as e:
            logger.error(f"Position tracking error: {e}")
            return PipelineResult(
                success=True,  # Non-critical, continue
                symbol=symbol,
                step=PipelineStep.POSITION_TRACKING,
                status=PipelineStatus.COMPLETED,
                data=order_data
            )
    
    def _handle_exit_monitoring(
        self, symbol: str, data: Dict
    ) -> PipelineResult:
        """Monitor exit conditions."""
        # Exit monitoring is typically done separately in main loop
        return PipelineResult(
            success=True,
            symbol=symbol,
            step=PipelineStep.EXIT_MONITORING,
            status=PipelineStatus.COMPLETED,
            data=data
        )
    
    def _handle_pnl_recording(
        self, symbol: str, data: Dict
    ) -> PipelineResult:
        """Record P&L."""
        # P&L is recorded on position close
        return PipelineResult(
            success=True,
            symbol=symbol,
            step=PipelineStep.PNL_RECORDING,
            status=PipelineStatus.COMPLETED,
            data=data
        )
    
    def _handle_metrics_update(
        self, symbol: str, data: Dict
    ) -> PipelineResult:
        """Update metrics."""
        # Metrics are updated externally
        return PipelineResult(
            success=True,
            symbol=symbol,
            step=PipelineStep.METRICS_UPDATE,
            status=PipelineStatus.COMPLETED,
            data=data
        )
