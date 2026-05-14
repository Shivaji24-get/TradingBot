import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_holdings(fyers_client) -> List[Dict[str, Any]]:
    try:
        response = fyers_client.holdings()
        if response.get("code") == 200:
            return [
                {
                    "symbol": h.get("symbol", ""),
                    "qty": h.get("qty", 0),
                    "avg_price": h.get("avg_price", 0),
                    "ltp": h.get("ltp", 0),
                    "close": h.get("close", 0),
                    "pnl": h.get("pnl", 0),
                    "pnl_percent": h.get("pnl_percent", 0),
                }
                for h in response.get("data", {})
            ]
        return [{"error": response.get("message", "Unknown error")}]
    except Exception as e:
        return [{"error": str(e)}]
