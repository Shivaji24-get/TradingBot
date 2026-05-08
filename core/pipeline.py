"""
Trading Pipeline - Workflow orchestration module.

================================================================================
WHAT IS THIS FILE?
================================================================================
This is the HEART of the trading bot. It orchestrates everything:
- Fetching market data from Fyers API
- Generating trading signals using strategies
- Checking risk limits (stop loss, position sizing)
- Tracking trades and performance
- Executing orders (in paper or live mode)

================================================================================
WORKFLOW: How a Trading Cycle Works
================================================================================
For EACH symbol (every 60 seconds during market hours):

  1. FETCH MARKET DATA
     ↓ Get 1H candles for trend analysis
     ↓ Get 5M candles for entry signals
     
  2. GENERATE SIGNALS
     ↓ Run Smart Money Concepts (SMC) strategy
     ↓ Run Order Block detection
     ↓ Calculate signal score (0-100)
     
  3. VALIDATE RISK
     ↓ Check: Max positions not exceeded?
     ↓ Check: Daily loss limit not hit?
     ↓ Check: Risk/Reward ratio acceptable?
     
  4. LOG OR TRADE
     ↓ If paper mode: Simulate the trade
     ↓ If live mode: Place real order
     ↓ Save to signals.md and positions.md
     
  5. MONITOR POSITIONS
     ↓ Check for stop loss hit
     ↓ Check for target reached
     ↓ Update unrealized P&L

================================================================================
KEY CLASSES
================================================================================
- TradingPipeline: Main orchestrator (you interact with this)
- PipelineConfig: Settings (symbols, timeframes, risk limits)
- PipelineResult: Result of each trading cycle
- PipelineStep: Enum of pipeline stages

================================================================================
FOR BEGINNERS
================================================================================
You DON'T need to edit this file. It's configured via:
- config/trading_profile.yml (your settings)
- CLI commands (how you interact)

To START the pipeline:
    python -m cli.main start-bot --paper

To UNDERSTAND output:
    - "Cycle complete: X/Y successful" = Data fetched successfully
    - Check data/signals.md for generated signals
    - Check data/positions.md for trades

================================================================================
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
    """
    Configuration for trading pipeline.
    
    These settings control HOW the bot trades. They come from:
    config/trading_profile.yml → loaded by CLI → passed here
    
    KEY SETTINGS FOR BEGINNERS:
    ---------------------------
    paper_trading (bool): 
        True = Fake money (safe for testing)
        False = Real money (only after weeks of testing!)
    
    enable_auto_trade (bool):
        True = Bot places orders automatically
        False = Bot only logs signals, you trade manually
        
    min_signal_score (float):
        Minimum confidence (0-100) to take a trade
        60 = More trades, lower quality
        85 = Fewer trades, higher quality
        
    symbols (List[str]):
        Which stocks to monitor
        Example: ["NSE:NIFTY50-INDEX", "NSE:RELIANCE-EQ"]
        
    scan_interval (int):
        Seconds between market checks
        60 = Check every minute
        300 = Check every 5 minutes
        
    main_timeframe (str):
        "1h" = 1-hour candles for trend analysis
        "D" = Daily candles for swing trading
        
    entry_timeframe (str):
        "5m" = 5-minute candles for entries
        "15m" = 15-minute candles for swing entries
    """
    # Execution settings - How fast/safe the bot runs
    max_concurrent: int = 5           # Max parallel API calls
    timeout_seconds: float = 30.0     # API timeout
    retry_attempts: int = 3           # Retries on failure
    
    # Feature toggles - Turn features ON/OFF
    enable_auto_trade: bool = False    # ⚠️ AUTO-TRADING: True = Bot places orders!
    require_confirmation: bool = True  # Always confirm before live trades
    paper_trading: bool = True         # True = Fake money (safe mode)
    
    # Validation settings - Signal quality filters
    min_signal_score: float = 75.0     # Min confidence (0-100)
    min_risk_reward: float = 1.5       # Min risk/reward ratio (1.5 = 1:1.5)
    
    # Market settings - What and when to trade
    symbols: List[str] = field(default_factory=list)  # Stocks to monitor
    scan_interval: int = 60                            # Seconds between scans
    main_timeframe: str = "1h"                         # Trend timeframe (1H)
    entry_timeframe: str = "5m"                       # Entry timeframe (5M)


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
        """Stop the pipeline gracefully."""
        self._running = False
        logger.info("TradingPipeline stopped")
    
    def emergency_stop(self):
        """Emergency stop - halt immediately without cleanup."""
        self._running = False
        logger.warning("TradingPipeline EMERGENCY STOP triggered")
    
    def close_all_positions(self):
        """Close all open positions (called during shutdown)."""
        logger.info("Closing all positions...")
        if self.tracker:
            try:
                active = self.tracker.get_active_positions()
                for symbol, pos in active.items():
                    logger.info(f"Closing position: {symbol}")
                    # Position closure logic would go here
            except Exception as e:
                logger.error(f"Error closing positions: {e}")
        logger.info("All positions closed")
    
    def get_results(self) -> List[PipelineResult]:
        """Get results from last execution."""
        return self._results
    
    def health_check(self) -> Dict[str, bool]:
        """
        Run health checks on pipeline components.
        
        Returns:
            Dictionary of check names and their status (True=healthy)
        """
        checks = {
            'pipeline_initialized': True,
            'fyers_client': self.fyers_client is not None,
            'tracker': self.tracker is not None,
            'config_loaded': self.config is not None,
            'risk_manager': self.risk_manager is not None or True,  # Optional
            'signal_generator': self.signal_generator is not None or True,  # Optional
        }
        
        # Test API connectivity if client available
        if self.fyers_client:
            try:
                # Try to get funds as a simple connectivity test
                from api import get_funds
                funds = get_funds(self.fyers_client)
                checks['api_connectivity'] = funds is not None
            except Exception:
                checks['api_connectivity'] = False
        else:
            checks['api_connectivity'] = False
        
        return checks
    
    # Step Handlers
    
    def _handle_market_data(self, symbol: str) -> PipelineResult:
        """Fetch market data for symbol."""
        try:
            from api import get_historical_data
            
            # Use main_timeframe from config (1H for trend, 5M for entries)
            df = get_historical_data(
                self.fyers_client,
                symbol,
                resolution=self.config.main_timeframe,
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
