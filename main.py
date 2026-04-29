import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_config, setup_logging, is_market_open, export_to_csv
from auth import TokenManager
from api import FyersClient
from api import get_funds, get_historical_data, get_quotes, place_order
from strategies import SignalGenerator, RiskManager

logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validates that all required configuration keys are present.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: True if valid, raises exception if invalid
        
    Raises:
        ValueError: If required keys are missing
    """
    required_keys = [
        "client_id",
        "secret_key",
        "log_level",
        "log_file",
        "confidence_threshold",
        "market_open_time",
        "market_close_time",
        "symbols"
    ]
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Missing required config keys: {', '.join(missing_keys)}. "
            f"Please check your config.ini file."
        )
    
    return True

def main() -> None:
    """Main trading bot entry point with comprehensive error handling."""
    try:
        config = load_config()
        validate_config(config)
        setup_logging(config["log_level"], config["log_file"])
        
        logger.info("Starting Fyers Trading Bot...")
        
        tm = TokenManager(config["client_id"], config["secret_key"])
        token = tm.get_access_token()
        
        if not token:
            logger.error("Not authenticated. Run 'python -m cli.main login' first.")
            sys.exit(1)
        
        client = FyersClient(config["client_id"], token)
        signal_gen = SignalGenerator(
            min_pattern_size=5,
            confidence_threshold=config["confidence_threshold"]
        )
        risk_mgr = RiskManager(config)
        
        funds = get_funds(client.get_client())
        capital = funds.get("available_cash", 100000)
        logger.info(f"Available capital: ₹{capital}")
        
        logger.info("Waiting for market open...")
        while not is_market_open(config["market_open_time"], config["market_close_time"]):
            time.sleep(60)
        
        logger.info("Market opened. Starting trading loop...")
        
        try:
            while is_market_open(config["market_open_time"], config["market_close_time"]):
                for symbol in config.get("symbols", []):
                    try:
                        df = get_historical_data(client.get_client(), symbol, "D", count=50)
                        if df.empty:
                            continue
                        
                        signal = signal_gen.analyze(df)
                        logger.info(f"{symbol}: {signal}")
                        
                        if signal != "HOLD" and risk_mgr.can_trade():
                            try:
                                market_data = get_quotes(client.get_client(), symbol)
                                price = market_data.get("last", 0)
                                
                                if price > 0:
                                    qty = risk_mgr.calculate_position_size(capital, price)
                                    result = place_order(
                                        client.get_client(), symbol, qty, signal.lower(),
                                        "MARKET", "MIS"
                                    )
                                    
                                    if result and "order_id" in result:
                                        risk_mgr.add_position(symbol, signal, price, qty)
                                        export_to_csv([{
                                            "symbol": symbol,
                                            "side": signal,
                                            "qty": qty,
                                            "price": price,
                                            "order_id": result["order_id"],
                                            "status": "executed",
                                            "timestamp": datetime.now().isoformat()
                                        }])
                                        logger.info(f"Executed {signal} {symbol} @ {price}, qty: {qty}")
                                    else:
                                        logger.warning(f"Order placement failed for {symbol}: {result}")
                            except Exception as e:
                                logger.error(f"Error placing order for {symbol}: {e}", exc_info=True)
                        
                        # Check exit conditions for open positions
                        try:
                            for sym, pos in list(risk_mgr.positions.items()):
                                current_price = get_quotes(client.get_client(), sym).get("last", 0)
                                if current_price > 0 and risk_mgr.check_exit(pos, current_price):
                                    try:
                                        exit_result = place_order(
                                            client.get_client(), sym, pos["qty"],
                                            "SELL" if pos["side"] == "BUY" else "BUY", "MARKET", "MIS"
                                        )
                                        
                                        if exit_result and "order_id" in exit_result:
                                            pnl = risk_mgr.remove_position(sym, current_price)
                                            export_to_csv([{
                                                "symbol": sym,
                                                "side": "EXIT",
                                                "qty": pos["qty"],
                                                "exit_price": current_price,
                                                "pnl": pnl,
                                                "order_id": exit_result["order_id"],
                                                "timestamp": datetime.now().isoformat()
                                            }])
                                            logger.info(f"Exited {sym} @ {current_price}, P&L: ₹{pnl:.2f}")
                                        else:
                                            logger.warning(f"Exit order failed for {sym}: {exit_result}")
                                    except Exception as e:
                                        logger.error(f"Error exiting position for {sym}: {e}", exc_info=True)
                        except Exception as e:
                            logger.error(f"Error checking exit conditions: {e}", exc_info=True)
                    
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}", exc_info=True)
                
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in trading loop: {e}", exc_info=True)
            raise
        finally:
            logger.info("Trading session ended")
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
