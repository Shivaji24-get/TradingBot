"""
Trading Pipeline – Workflow orchestration module.

FIXES:
- _handle_market_data() now fetches BOTH main_timeframe (trend) AND entry_timeframe
  (signal entry). Previously only main_timeframe was fetched, making dual-TF
  pipeline non-functional.
- Added explicit validation that PipelineConfig.symbols is not empty.
- health_check() now wraps API call in try/except so a failed API call doesn't
  crash the startup sequence.
- PipelineConfig fields have clearer defaults matching YAML structure.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    PENDING   = auto()
    RUNNING   = auto()
    COMPLETED = auto()
    FAILED    = auto()
    PARTIAL   = auto()
    CANCELLED = auto()


class PipelineStep(Enum):
    MARKET_DATA       = auto()
    SIGNAL_GENERATION = auto()
    RISK_VALIDATION   = auto()
    ORDER_PLACEMENT   = auto()
    POSITION_TRACKING = auto()
    EXIT_MONITORING   = auto()
    PNL_RECORDING     = auto()
    METRICS_UPDATE    = auto()


@dataclass
class PipelineResult:
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
    Configuration for TradingPipeline.

    Loaded from config/trading_profile.yml via cli/commands.py:start_bot_cmd().
    """
    # Execution
    max_concurrent: int = 5
    timeout_seconds: float = 30.0
    retry_attempts: int = 3

    # Features
    enable_auto_trade: bool = False
    require_confirmation: bool = True
    paper_trading: bool = True        # default SAFE

    # Signal quality
    min_signal_score: float = 75.0
    min_risk_reward: float = 1.5

    # Market
    symbols: List[str] = field(default_factory=list)
    scan_interval: int = 60           # seconds
    main_timeframe: str = "1h"        # FIX: used for trend (HTF)
    entry_timeframe: str = "5m"       # FIX: used for signal entry (LTF)


class TradingPipeline:
    """
    Orchestrates the complete trading workflow per symbol, per cycle.

    Pipeline steps (in order):
      1. MARKET_DATA       – fetch HTF + LTF candles
      2. SIGNAL_GENERATION – run strategy on fetched data
      3. RISK_VALIDATION   – check score threshold and risk limits
      4. ORDER_PLACEMENT   – place paper or live order (if enabled)
      5. POSITION_TRACKING – record position in tracker
      6. EXIT_MONITORING   – (handled externally in main loop)
      7. PNL_RECORDING     – (on close event)
      8. METRICS_UPDATE    – (batch, end of cycle)
    """

    def __init__(
        self,
        config: PipelineConfig,
        fyers_client: Any,
        tracker: Any,
        risk_manager: Any = None,
        signal_generator: Any = None,
        order_executor: Any = None,
    ) -> None:
        self.config = config
        self.fyers_client = fyers_client
        self.tracker = tracker
        self.risk_manager = risk_manager
        self.signal_generator = signal_generator
        self.order_executor = order_executor

        self._running = False
        self._results: List[PipelineResult] = []
        self._step_handlers: Dict[PipelineStep, Callable] = {}

        self._register_handlers()
        logger.info(
            "TradingPipeline initialised | paper=%s auto_trade=%s",
            config.paper_trading, config.enable_auto_trade,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        logger.info("TradingPipeline started")

    def stop(self) -> None:
        self._running = False
        logger.info("TradingPipeline stopped")

    def emergency_stop(self) -> None:
        self._running = False
        logger.warning("TradingPipeline EMERGENCY STOP")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_single(self, symbol: str) -> PipelineResult:
        """Run the full pipeline for one symbol."""
        t0 = time.time()

        try:
            # Step 1 – market data (HTF + LTF)
            r = self._step_handlers[PipelineStep.MARKET_DATA](symbol)
            if not r.success:
                return r
            market_data = r.data

            # Step 2 – signal
            r = self._step_handlers[PipelineStep.SIGNAL_GENERATION](symbol, market_data)
            if not r.success:
                return r
            signal_data = r.data

            if signal_data.get("signal") == "HOLD":
                return PipelineResult(
                    success=True, symbol=symbol,
                    step=PipelineStep.SIGNAL_GENERATION,
                    status=PipelineStatus.COMPLETED,
                    data={"message": "HOLD – no actionable signal"},
                    duration_ms=(time.time() - t0) * 1000,
                )

            # Step 3 – risk
            r = self._step_handlers[PipelineStep.RISK_VALIDATION](symbol, signal_data)
            if not r.success:
                return r

            # Step 4 – order (only if auto-trade enabled)
            if self.config.enable_auto_trade:
                r = self._step_handlers[PipelineStep.ORDER_PLACEMENT](symbol, signal_data)
                if not r.success:
                    return r
                self._step_handlers[PipelineStep.POSITION_TRACKING](symbol, r.data)

            return PipelineResult(
                success=True, symbol=symbol,
                step=PipelineStep.METRICS_UPDATE,
                status=PipelineStatus.COMPLETED,
                data={
                    "symbol": symbol,
                    "signal": signal_data.get("signal"),
                    "score": signal_data.get("score"),
                    "auto_traded": self.config.enable_auto_trade,
                },
                duration_ms=(time.time() - t0) * 1000,
            )

        except Exception as e:
            logger.exception("Pipeline error for %s", symbol)
            return PipelineResult(
                success=False, symbol=symbol,
                step=PipelineStep.MARKET_DATA,
                status=PipelineStatus.FAILED,
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    def execute_batch(self, symbols: List[str]) -> List[PipelineResult]:
        """Run the pipeline for a list of symbols sequentially."""
        if not symbols:
            logger.warning("execute_batch called with empty symbol list")
            return []

        logger.info("Batch execution: %d symbols", len(symbols))
        results: List[PipelineResult] = []

        for symbol in symbols:
            if not self._running:
                logger.info("Pipeline stopped – cancelling remaining symbols")
                break
            r = self.execute_single(symbol)
            results.append(r)
            time.sleep(0.1)   # minimal rate-limit cushion

        self._results = results
        ok = sum(1 for r in results if r.success)
        logger.info("Batch done: %d/%d successful", ok, len(results))
        return results

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, bool]:
        """
        Verify pipeline components are ready.

        FIX: API connectivity test now catches exceptions instead of letting
        them propagate and crash the startup sequence.
        """
        checks: Dict[str, bool] = {
            "pipeline_initialised": True,
            "fyers_client":         self.fyers_client is not None,
            "tracker":              self.tracker is not None,
            "config_loaded":        self.config is not None,
            "symbols_configured":   bool(self.config.symbols),
        }

        # API connectivity (non-fatal if it fails)
        if self.fyers_client:
            try:
                from api import get_funds
                funds = get_funds(self.fyers_client)
                checks["api_connectivity"] = isinstance(funds, dict) and "error" not in funds
            except Exception as e:
                logger.warning("API connectivity check failed: %s", e)
                checks["api_connectivity"] = False
        else:
            checks["api_connectivity"] = False

        return checks

    def get_results(self) -> List[PipelineResult]:
        return list(self._results)

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        self._step_handlers = {
            PipelineStep.MARKET_DATA:       self._handle_market_data,
            PipelineStep.SIGNAL_GENERATION: self._handle_signal_generation,
            PipelineStep.RISK_VALIDATION:   self._handle_risk_validation,
            PipelineStep.ORDER_PLACEMENT:   self._handle_order_placement,
            PipelineStep.POSITION_TRACKING: self._handle_position_tracking,
            PipelineStep.EXIT_MONITORING:   self._noop_step,
            PipelineStep.PNL_RECORDING:     self._noop_step,
            PipelineStep.METRICS_UPDATE:    self._noop_step,
        }

    def _handle_market_data(self, symbol: str) -> PipelineResult:
        """
        Fetch market data.

        FIX: now fetches BOTH main_timeframe (trend / HTF) and
        entry_timeframe (signal / LTF). Previously only main_timeframe
        was fetched, making the dual-TF pipeline incomplete.
        """
        try:
            from api import get_historical_data

            htf_df = get_historical_data(
                self.fyers_client, symbol,
                resolution=self.config.main_timeframe,
                count=50,
            )
            ltf_df = get_historical_data(
                self.fyers_client, symbol,
                resolution=self.config.entry_timeframe,
                count=100,
            )

            if htf_df.empty and ltf_df.empty:
                return self._failed(symbol, PipelineStep.MARKET_DATA, "No market data available")

            return PipelineResult(
                success=True, symbol=symbol,
                step=PipelineStep.MARKET_DATA,
                status=PipelineStatus.COMPLETED,
                data={"htf_df": htf_df, "ltf_df": ltf_df},
            )

        except Exception as e:
            return self._failed(symbol, PipelineStep.MARKET_DATA, f"Data fetch error: {e}")

    def _handle_signal_generation(self, symbol: str, market_data: Dict) -> PipelineResult:
        """Generate signal using available data."""
        try:
            htf_df = market_data.get("htf_df")
            ltf_df = market_data.get("ltf_df")

            # Prefer the entry (LTF) dataframe for signal if available
            df = ltf_df if (ltf_df is not None and not ltf_df.empty) else htf_df

            if self.signal_generator and df is not None:
                signal = self.signal_generator.analyze(df)
                score = getattr(self.signal_generator, "last_score", 50)
            else:
                signal, score = "HOLD", 0

            return PipelineResult(
                success=True, symbol=symbol,
                step=PipelineStep.SIGNAL_GENERATION,
                status=PipelineStatus.COMPLETED,
                data={"signal": signal, "score": score, "htf_df": htf_df, "ltf_df": ltf_df},
            )

        except Exception as e:
            return self._failed(symbol, PipelineStep.SIGNAL_GENERATION, f"Signal error: {e}")

    def _handle_risk_validation(self, symbol: str, signal_data: Dict) -> PipelineResult:
        """Validate risk parameters before allowing trade."""
        try:
            score = signal_data.get("score", 0)
            if score < self.config.min_signal_score:
                return self._failed(
                    symbol, PipelineStep.RISK_VALIDATION,
                    f"Score {score} < threshold {self.config.min_signal_score}",
                )

            if self.risk_manager:
                can, reason = self.risk_manager.can_trade()
                if not can:
                    return self._failed(symbol, PipelineStep.RISK_VALIDATION, reason)

            return PipelineResult(
                success=True, symbol=symbol,
                step=PipelineStep.RISK_VALIDATION,
                status=PipelineStatus.COMPLETED,
                data=signal_data,
            )
        except Exception as e:
            return self._failed(symbol, PipelineStep.RISK_VALIDATION, f"Risk error: {e}")

    def _handle_order_placement(self, symbol: str, signal_data: Dict) -> PipelineResult:
        """Place paper or live order."""
        try:
            signal = signal_data.get("signal")
            score  = signal_data.get("score", 50)

            if self.config.paper_trading:
                from api import get_quotes
                quote = get_quotes(self.fyers_client, symbol)
                price = quote.get("last", 0) if "error" not in quote else 0

                order_id = f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                return PipelineResult(
                    success=True, symbol=symbol,
                    step=PipelineStep.ORDER_PLACEMENT,
                    status=PipelineStatus.COMPLETED,
                    data={"order_id": order_id, "symbol": symbol,
                          "side": signal, "price": price, "qty": 1, "paper": True},
                )

            if self.order_executor:
                from api import get_funds
                funds = get_funds(self.fyers_client)
                capital = funds.get("available_cash", 100_000)
                quote = get_quotes(self.fyers_client, symbol)
                price = quote.get("last", 0)

                result = self.order_executor.execute_trade(
                    symbol=symbol, signal=signal, price=price,
                    score=score, capital=capital,
                    confirm=self.config.require_confirmation,
                )
                if result.success:
                    return PipelineResult(
                        success=True, symbol=symbol,
                        step=PipelineStep.ORDER_PLACEMENT,
                        status=PipelineStatus.COMPLETED,
                        data={"order_id": result.order_id, "symbol": symbol,
                              "side": signal, "price": price, "qty": result.qty, "paper": False},
                    )
                return self._failed(symbol, PipelineStep.ORDER_PLACEMENT, result.error or "Order failed")

            return self._failed(symbol, PipelineStep.ORDER_PLACEMENT, "No order executor configured")

        except Exception as e:
            return self._failed(symbol, PipelineStep.ORDER_PLACEMENT, f"Order error: {e}")

    def _handle_position_tracking(self, symbol: str, order_data: Dict) -> PipelineResult:
        """Record position in tracker."""
        try:
            if self.tracker and order_data.get("order_id"):
                self.tracker.add_position(
                    symbol=symbol,
                    side=order_data.get("side", "BUY"),
                    entry_price=order_data.get("price", 0),
                    qty=order_data.get("qty", 1),
                    order_id=order_data.get("order_id", ""),
                    paper=order_data.get("paper", True),
                )
        except Exception as e:
            logger.warning("Position tracking failed for %s: %s", symbol, e)

        return PipelineResult(
            success=True, symbol=symbol,
            step=PipelineStep.POSITION_TRACKING,
            status=PipelineStatus.COMPLETED,
            data=order_data,
        )

    def _noop_step(self, symbol: str = "", data: Dict = None) -> PipelineResult:
        """Placeholder for steps handled externally."""
        return PipelineResult(
            success=True, symbol=symbol,
            step=PipelineStep.METRICS_UPDATE,
            status=PipelineStatus.COMPLETED,
            data=data or {},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _failed(symbol: str, step: PipelineStep, error: str) -> PipelineResult:
        logger.debug("Pipeline step %s failed for %s: %s", step.name, symbol, error)
        return PipelineResult(
            success=False, symbol=symbol, step=step,
            status=PipelineStatus.FAILED, error=error,
        )
