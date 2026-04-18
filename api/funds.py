import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_funds(fyers_client) -> Dict[str, Any]:
    try:
        response = fyers_client.funds()
        if response.get("code") == 200:
            data = response.get("data", {})
            return {
                "available_cash": data.get("available_cash", 0),
                "available_margin": data.get("available_margin", 0),
                "utilized_margin": data.get("utilized_margin", 0),
                "total_cash": data.get("total_cash", 0),
                "currency": data.get("currency", "INR")
            }
        logger.error(f"Funds fetch error: {response}")
        return {"error": response.get("message", "Unknown error")}
    except Exception as e:
        logger.error(f"Funds exception: {e}")
        return {"error": str(e)}