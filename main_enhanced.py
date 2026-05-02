#!/usr/bin/env python3
"""
Enhanced TradingBot Main Entry Point.

Uses the new modular architecture with pipeline orchestration,
structured tracking, and enhanced error handling.

Inspired by Career-Ops workflow patterns.
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent))

from utils.config import load_config, validate_config, get_profile
from utils.logger import setup_logging, log_trade, log_signal, log_risk_event
from core.pipeline import TradingPipeline, PipelineConfig
from core.tracker import TradingTracker
from core.scheduler import TradingScheduler, MarketSession, MarketStatus
from core.state_machine import TradingStateMachine, TradingState
from core.retry import retry_with_backoff, CircuitBreakerConfig
from auth import TokenManager
from api import FyersClient, get_funds, get_historical_data, get_quotes, place_order
from strategies import SignalGenerator, RiskManager


class TradingBot:
    """
    Enhanced TradingBot using pipeline architecture.
    
    This replaces the monolithic main() with a structured,
    modular approach inspired by Career-Ops workflow patterns.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.profile = get_profile(config)
        self.logger = setup_logging(
            log_file=config.get("log_file", "trading_bot.log"),
            log_level=config.get("log_level", "INFO"),
            structured=True,
            log_dir="logs"
        )
        
        # Initialize state machine
        self.state_machine = TradingStateMachine()
        
        # Initialize tracker
        self.tracker = TradingTracker(data_dir="data")
        
        # Initialize scheduler
        market_session = MarketSession(timezone=self.profile.timezone)
        self.scheduler = TradingScheduler(market_session=market_session)
        
        # Initialize pipeline
        self.pipeline = None
        
        # API client
        self.client: Optional[FyersClient] = None
        self.capital: float = 0.0
        
        # Control flags
        self.running = False
        self.shutdown_requested = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        self.state_machine.transition_to(TradingState.STOPPED)
    
    @retry_with_backoff(max_attempts=3, retryable_exceptions=(Exception,))
    def _authenticate(self) -> bool:
        """Authenticate with Fyers API."""
        self.logger.info("Authenticating with Fyers API...")
        
        try:
            tm = TokenManager(
                client_id=self.config["client_id"],
                secret_key=self.config["secret_key"]
            )
            token = tm.get_access_token()
            
            if not token:
                self.logger.error("Authentication failed. Run: python -m cli.main login")
                return False
            
            self.client = FyersClient(self.config["client_id"], token)
            self.logger.info("Authentication successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            raise
    
    def _initialize_pipeline(self) -> bool:
        """Initialize the trading pipeline."""
        self.logger.info("Initializing trading pipeline...")
        
        try:
            # Get available funds
            funds = get_funds(self.client.get_client())
            self.capital = funds.get("available_cash", 100000)
            self.logger.info(f"Available capital: INR {self.capital:,.2f}")
            
            # Create pipeline config
            pipeline_config = PipelineConfig(
                symbols=self.config.get("symbols", ["NSE:NIFTY50-INDEX"]),
                min_signal_score=self.config.get("confidence_threshold", 0.75) * 100,  # Convert to percentage
                enable_auto_trade=self.config.get("auto_trading_enabled", False),
                paper_trading=self.config.get("paper_trading", True),
                scan_interval=self.config.get("scan_interval", 60)
            )
            
            # Create pipeline with API functions
            self.pipeline = TradingPipeline(
                config=pipeline_config,
                fyers_client=self.client.get_client(),
                tracker=self.tracker
            )
            
            self.logger.info("Pipeline initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {e}")
            return False
    
    def _check_market_session(self) -> bool:
        """Check and handle market session state."""
        status = self.scheduler.get_market_status()
        is_open = status.get('is_trading_hours', False)
        
        if is_open:
            if self.state_machine.get_state() != TradingState.SCANNING:
                self.state_machine.transition_to(TradingState.SCANNING)
                time_until_close = status.get('time_until_close', 0)
                self.logger.info(f"Market session OPEN - Starting trading ({time_until_close}s remaining)")
            return True
        else:
            if self.state_machine.get_state() == TradingState.SCANNING:
                self.state_machine.transition_to(TradingState.IDLE)
                self.logger.info("Market session CLOSED - Trading paused")
            return False
    
    def _run_trading_cycle(self):
        """Execute one trading cycle."""
        try:
            for symbol in self.config.get("symbols", []):
                if self.shutdown_requested:
                    break
                
                try:
                    # Run pipeline for symbol
                    result = self.pipeline.execute_single(symbol)
                    
                    if result and result.success:
                        # Log signal from pipeline data
                        signal_data = result.data.get("signal", {})
                        if signal_data and signal_data.get("action") != "HOLD":
                            log_signal(
                                self.logger,
                                symbol=symbol,
                                signal=signal_data.get("action", "HOLD"),
                                score=signal_data.get("score", 0),
                                price=signal_data.get("price", 0)
                            )
                        
                        # Log trade if executed
                        trade_data = result.data.get("trade", {})
                        if trade_data:
                            log_trade(
                                self.logger,
                                symbol=symbol,
                                side=trade_data.get("side", "BUY"),
                                qty=trade_data.get("qty", 0),
                                price=trade_data.get("price", 0),
                                order_id=trade_data.get("order_id", "UNKNOWN")
                            )
                            
                            self.logger.trade(
                                f"Executed {trade_data.get('side', 'BUY')} {symbol} @ {trade_data.get('price', 0)}, "
                                f"qty: {trade_data.get('qty', 0)}"
                            )
                        
                        # Check exit conditions for open positions
                        self._check_exits(symbol)
                        
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
    
    def _check_exits(self, symbol: str):
        """Check and execute exit conditions for open positions."""
        positions = self.tracker.get_active_positions()
        
        for pos_symbol, position in positions.items():
            if pos_symbol == symbol:
                try:
                    market_data = get_quotes(self.client.get_client(), symbol)
                    current_price = market_data.get("last", 0)
                    
                    if current_price <= 0:
                        continue
                    
                    # Check stop loss
                    if position.side == "LONG":
                        if current_price <= position.stop_loss:
                            self._exit_position(position, current_price, "STOP_LOSS")
                        elif current_price >= position.take_profit:
                            self._exit_position(position, current_price, "TAKE_PROFIT")
                    else:  # SHORT
                        if current_price >= position.stop_loss:
                            self._exit_position(position, current_price, "STOP_LOSS")
                        elif current_price <= position.take_profit:
                            self._exit_position(position, current_price, "TAKE_PROFIT")
                            
                except Exception as e:
                    self.logger.error(f"Error checking exit for {symbol}: {e}")
    
    def _exit_position(self, position, current_price: float, reason: str):
        """Exit a position."""
        try:
            exit_side = "SELL" if position.side == "LONG" else "BUY"
            
            result = place_order(
                self.client.get_client(),
                position.symbol,
                position.quantity,
                exit_side,
                "MARKET",
                "MIS"
            )
            
            if result and "order_id" in result:
                pnl = self.tracker.close_position(position.symbol, current_price, result["order_id"])
                
                log_trade(
                    self.logger,
                    symbol=position.symbol,
                    side=exit_side,
                    qty=position.quantity,
                    price=current_price,
                    order_id=result["order_id"],
                    pnl=pnl
                )
                
                self.logger.trade(
                    f"Exited {position.symbol} @ {current_price}, P&L: ₹{pnl:.2f}, Reason: {reason}"
                )
            
        except Exception as e:
            self.logger.error(f"Error exiting position {position.symbol}: {e}")
    
    def _cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up resources...")
        
        try:
            # Close any open positions if configured
            if self.config.get("auto_close_on_exit", False):
                self.logger.info("Auto-closing open positions...")
                positions = self.tracker.get_active_positions()
                for pos_symbol, position in positions.items():
                    try:
                        market_data = get_quotes(self.client.get_client(), pos_symbol)
                        current_price = market_data.get("last", 0)
                        if current_price > 0:
                            self._exit_position(position, current_price, "SESSION_END")
                    except Exception as e:
                        self.logger.error(f"Error closing position {pos_symbol}: {e}")
            
            # Update final state
            self.state_machine.transition_to(TradingState.IDLE)
            
            self.logger.info("Cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def run(self):
        """Main trading bot loop."""
        self.logger.info("=" * 60)
        self.logger.info("TradingBot Starting - Enhanced Architecture")
        self.logger.info("=" * 60)
        
        try:
            # Validate configuration
            is_valid, errors = validate_config(self.config)
            if not is_valid:
                self.logger.error(f"Configuration errors: {', '.join(errors)}")
                return 1
            
            # State machine starts in IDLE, no need to transition
            
            # Authenticate
            if not self._authenticate():
                return 1
            
            # Initialize pipeline
            if not self._initialize_pipeline():
                return 1
            
            self.state_machine.transition_to(TradingState.IDLE)
            
            # Wait for market open
            if not self._check_market_session():
                self.logger.info("Market closed. Waiting for market open...")
                while not self.shutdown_requested and not self._check_market_session():
                    time.sleep(60)
            
            if self.shutdown_requested:
                self.logger.info("Shutdown requested before market open")
                self._cleanup()
                return 0
            
            # Main trading loop
            self.running = True
            self.logger.info("Entering main trading loop...")
            
            while self.running and not self.shutdown_requested:
                try:
                    # Check market session
                    if not self._check_market_session():
                        self.logger.info("Market closed. Waiting...")
                        while not self.shutdown_requested and not self._check_market_session():
                            time.sleep(60)
                        continue
                    
                    # Run trading cycle
                    self._run_trading_cycle()
                    
                    # Sleep between cycles
                    time.sleep(self.config.get("scan_interval", 60))
                    
                except KeyboardInterrupt:
                    self.logger.info("Interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    time.sleep(5)
            
            self._cleanup()
            self.logger.info("TradingBot stopped gracefully")
            return 0
            
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self._cleanup()
            return 1


def main():
    """Enhanced main entry point."""
    try:
        # Load configuration
        config = load_config(prefer_yaml=True)
        
        # Create and run bot
        bot = TradingBot(config)
        exit_code = bot.run()
        sys.exit(exit_code)
        
    except FileNotFoundError as e:
        print(f"Configuration error: {e}")
        print("\nTo get started:")
        print("1. Copy config/trading_profile.example.yml to config/trading_profile.yml")
        print("2. Edit with your Fyers API credentials")
        print("3. Run: python scripts/init_tracking.py")
        print("4. Run: python scripts/health_check.py")
        sys.exit(1)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
