import logging
import time
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

TIMEFRAME_MAP = {
    "D": "D", "1D": "D",
    "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "4h": "240", "1m": "1",
}


def get_historical_data(fyers_client, symbol: str, resolution: str = "D",
                        date_range: Optional[Dict] = None, count: int = 100) -> pd.DataFrame:
    try:
        fyers_resolution = TIMEFRAME_MAP.get(resolution, resolution)
        current_time = int(time.time())

        seconds_map = {"D": 86400, "1": 60, "5": 300, "15": 900,
                       "30": 1800, "60": 3600, "120": 7200, "240": 14400}
        spc = seconds_map.get(fyers_resolution, 86400)
        buf = 2 if fyers_resolution == "D" else 1.5
        total = int(count * spc * buf)

        data = {
            "symbol": symbol,
            "resolution": fyers_resolution,
            "date_format": "0",
            "range_from": str(current_time - total),
            "range_to": str(current_time),
        }

        response = fyers_client.history(data=data)
        if response.get("code") == 200:
            candles = response.get("candles", [])
            if candles:
                df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                return df
        logger.error("History fetch error for %s: %s", symbol, response)
        return pd.DataFrame()
    except Exception as e:
        logger.error("History exception for %s: %s", symbol, e)
        return pd.DataFrame()


def get_quotes(fyers_client, symbol: str) -> Dict[str, Any]:
    try:
        response = fyers_client.quotes(data={"symbols": symbol})
        if response.get("code") == 200:
            d = response.get("d", {})
            data = d.get(symbol, {}) if isinstance(d, dict) else (d[0] if d else {})
            v = data.get("v", {})
            return {
                "symbol": symbol,
                "last": v.get("lp", 0),
                "open": v.get("open", 0),
                "high": v.get("high", 0),
                "low": v.get("low", 0),
                "volume": v.get("volume", 0),
                "change": v.get("change", 0),
                "change_percent": v.get("ch", 0),
            }
        logger.error("Quotes error for %s: %s", symbol, response)
        return {"error": response.get("message", "Unknown error")}
    except Exception as e:
        logger.error("Quotes exception for %s: %s", symbol, e)
        return {"error": str(e)}
