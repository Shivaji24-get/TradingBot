import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_config, setup_logging, is_market_open, export_to_csv
from auth import TokenManager
from api import FyersClient
from api import get_funds, get_historical_data, get_quotes, place_order
from strategies import SignalGenerator, RiskManager

logger = logging.getLogger(__name__)

def main():
    config = load_config()
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
                        market_data = get_quotes(client.get_client(), symbol)
                        price = market_data.get("last", 0)
                        
                        if price > 0:
                            qty = risk_mgr.calculate_position_size(capital, price)
                            result = place_order(
                                client.get_client(), symbol, qty, signal.lower(),
                                "MARKET", "MIS"
                            )
                            
                            if "order_id" in result:
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
                    
                    for sym, pos in list(risk_mgr.positions.items()):
                        current_price = get_quotes(client.get_client(), sym).get("last", 0)
                        if current_price > 0 and risk_mgr.check_exit(pos, current_price):
                            exit_result = place_order(
                                client.get_client(), sym, pos["qty"],
                                "SELL" if pos["side"] == "BUY" else "BUY", "MARKET", "MIS"
                            )
                            pnl = risk_mgr.remove_position(sym, current_price)
                            export_to_csv([{
                                "symbol": sym,
                                "side": "EXIT",
                                "qty": pos["qty"],
                                "exit_price": current_price,
                                "pnl": pnl,
                                "timestamp": datetime.now().isoformat()
                            }])
                            logger.info(f"Exited {sym} @ {current_price}, P&L: ₹{pnl:.2f}")
                
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
            
            time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    
    logger.info("Trading session ended")

if __name__ == "__main__":
    main()