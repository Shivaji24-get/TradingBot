import logging
import pandas as pd
from typing import Dict, Any, List, Optional
import time

logger = logging.getLogger(__name__)

# Map common timeframes to Fyers resolution codes
TIMEFRAME_MAP = {
    "D": "D",      # Daily
    "1D": "D",     # Daily alias
    "5m": "5",     # 5 minutes
    "15m": "15",   # 15 minutes
    "30m": "30",   # 30 minutes
    "1h": "60",    # 1 hour
    "4h": "240",   # 4 hours
    "1m": "1",     # 1 minute
}

def get_historical_data(fyers_client, symbol: str, resolution: str = "D",
                        date_range: Optional[Dict] = None, count: int = 100) -> pd.DataFrame:
    try:
        # Map resolution to Fyers format
        fyers_resolution = TIMEFRAME_MAP.get(resolution, resolution)

        data = {
            "symbol": symbol,
            "resolution": fyers_resolution,
            "date_format": "0"
        }

        # Calculate time range based on resolution
        current_time = int(time.time())

        # Determine seconds per candle based on resolution
        if fyers_resolution == "D":
            seconds_per_candle = 86400  # Daily
        elif fyers_resolution == "1":
            seconds_per_candle = 60  # 1 minute
        elif fyers_resolution in ["5", "15", "30"]:
            seconds_per_candle = int(fyers_resolution) * 60  # Minutes
        elif fyers_resolution in ["60", "120", "240"]:
            seconds_per_candle = int(fyers_resolution) * 60  # Hours in minutes
        else:
            seconds_per_candle = 86400  # Default to daily

        # Add buffer for weekends/holidays (2x for daily, 1.5x for intraday)
        buffer_multiplier = 2 if fyers_resolution == "D" else 1.5
        total_seconds = int(count * seconds_per_candle * buffer_multiplier)

        data["range_from"] = str(current_time - total_seconds)
        data["range_to"] = str(current_time)
        
        response = fyers_client.history(data=data)
        if response.get("code") == 200:
            candles = response.get("candles", [])
            if candles:
                df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                return df
        logger.error(f"History fetch error: {response}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"History exception: {e}")
        return pd.DataFrame()

def get_quotes(fyers_client, symbol: str) -> Dict[str, Any]:
    try:
        response = fyers_client.quotes(data={"symbols": symbol})
        if response.get("code") == 200:
            response_data = response.get("d", {})

            # Handle both dict and list responses
            if isinstance(response_data, dict):
                data = response_data.get(symbol, {})
            elif isinstance(response_data, list) and len(response_data) > 0:
                data = response_data[0]
            else:
                return {"error": "No data in response"}

            return {
                "symbol": symbol,
                "last": data.get("v", {}).get("lp", 0),
                "open": data.get("v", {}).get("open", 0),
                "high": data.get("v", {}).get("high", 0),
                "low": data.get("v", {}).get("low", 0),
                "volume": data.get("v", {}).get("volume", 0),
                "change": data.get("v", {}).get("change", 0),
                "change_percent": data.get("v", {}).get("ch", 0)
            }
        logger.error(f"Quotes fetch error: {response}")
        return {"error": response.get("message", "Unknown error")}
    except Exception as e:
        logger.error(f"Quotes exception: {e}")
        return {"error": str(e)}