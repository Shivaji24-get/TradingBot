import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api import FyersClient
from auth import TokenManager
from utils import load_config
from strategies import StockScanner
import pandas as pd
from pprint import pprint

def debug_smc(symbol="NSE:RELIANCE-EQ"):
    config = load_config()
    tm = TokenManager(config["client_id"], config["secret_key"])
    token = tm.get_access_token()
    
    if not token:
        print("Not logged in")
        return
        
    client = FyersClient(config["client_id"], token)
    scanner = StockScanner(enable_smc=True)
    
    from api import get_historical_data
    
    print(f"Fetching LTF (5m) for {symbol}...")
    ltf_df = get_historical_data(client.get_client(), symbol, "5", count=200)
    print(f"Got {len(ltf_df)} candles")
    
    print(f"Fetching HTF (15m) for {symbol}...")
    htf_df = get_historical_data(client.get_client(), symbol, "15", count=200)
    print(f"Got {len(htf_df)} candles")
    
    if ltf_df.empty:
        print("LTF data is empty")
        return
        
    print("\n--- MSS HTF Analysis ---")
    mss_analysis = scanner.smc_strategy.mss_detector.get_mss_analysis(htf_df)
    pprint(mss_analysis)

    result = scanner.scan_symbol_smc(symbol, ltf_df, htf_df)
    
    print("\n--- SMC Analysis Result ---")
    print(f"Symbol: {result['symbol']}")
    print(f"Signal: {result['signal']}")
    print(f"Score: {result['score']}%")
    print(f"HTF Aligned: {result['htf_aligned']}")
    print(f"FVG Present: {result['fvg_present']}")
    
    print("\n--- Details ---")
    pprint(result['details'])

if __name__ == "__main__":
    debug_smc()
