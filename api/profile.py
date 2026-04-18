import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_profile(fyers_client) -> Dict[str, Any]:
    try:
        response = fyers_client.get_profile()
        if response.get("code") == 200:
            data = response.get("data", {})
            return {
                "name": data.get("name", "N/A"),
                "email": data.get("email", "N/A"),
                "mobile": data.get("mobile", "N/A"),
                "broker": data.get("broker", "N/A"),
                "pincode": data.get("pincode", "N/A"),
                "exchanges": data.get("exchanges", []),
                "segments": data.get("segments", []),
                "order_type": data.get("order_type", [])
            }
        logger.error(f"Profile fetch error: {response}")
        return {"error": response.get("message", "Unknown error")}
    except Exception as e:
        logger.error(f"Profile exception: {e}")
        return {"error": str(e)}