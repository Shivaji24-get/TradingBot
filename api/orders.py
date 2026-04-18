import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def place_order(fyers_client, symbol: str, qty: int, side: str, 
                order_type: str = "MARKET", product_type: str = "MIS",
                price: Optional[float] = None, stop_loss: Optional[float] = None,
                take_profit: Optional[float] = None) -> Dict[str, Any]:
    try:
        order_data = {
            "symbol": symbol,
            "qty": qty,
            "type": order_type,
            "side": side,
            "productType": product_type
        }
        if price and order_type == "LIMIT":
            order_data["limitPrice"] = price
        if stop_loss:
            order_data["stopLoss"] = stop_loss
        if take_profit:
            order_data["takeProfit"] = take_profit
        
        response = fyers_client.place_order(data=order_data)
        if response.get("code") == 200:
            return {
                "order_id": response.get("id", ""),
                "status": "success",
                "message": "Order placed successfully"
            }
        logger.error(f"Order placement error: {response}")
        return {"error": response.get("message", "Failed to place order")}
    except Exception as e:
        logger.error(f"Order placement exception: {e}")
        return {"error": str(e)}

def modify_order(fyers_client, order_id: str, qty: Optional[int] = None,
                 price: Optional[float] = None) -> Dict[str, Any]:
    try:
        order_data = {"id": order_id}
        if qty:
            order_data["qty"] = qty
        if price:
            order_data["limitPrice"] = price
        
        response = fyers_client.update_order(data=order_data)
        if response.get("code") == 200:
            return {"status": "success", "message": "Order modified"}
        return {"error": response.get("message", "Failed to modify")}
    except Exception as e:
        logger.error(f"Order modify exception: {e}")
        return {"error": str(e)}

def cancel_order(fyers_client, order_id: str) -> Dict[str, Any]:
    try:
        response = fyers_client.cancel_order(data={"id": order_id})
        if response.get("code") == 200:
            return {"status": "success", "message": "Order cancelled"}
        return {"error": response.get("message", "Failed to cancel")}
    except Exception as e:
        logger.error(f"Order cancel exception: {e}")
        return {"error": str(e)}

def get_order_status(fyers_client, order_id: str) -> Dict[str, Any]:
    try:
        response = fyers_client.orderbook()
        if response.get("code") == 200:
            orders = response.get("data", {})
            for order in orders:
                if str(order.get("id")) == str(order_id):
                    return {
                        "order_id": order.get("id"),
                        "status": order.get("status", ""),
                        "symbol": order.get("symbol", ""),
                        "qty": order.get("qty", 0),
                        "filled_qty": order.get("filledQty", 0),
                        "side": order.get("side", ""),
                        "type": order.get("type", ""),
                        "price": order.get("limitPrice", 0),
                        "avg_price": order.get("avgPrice", 0)
                    }
        return {"error": "Order not found"}
    except Exception as e:
        logger.error(f"Order status exception: {e}")
        return {"error": str(e)}

def get_orderbook(fyers_client) -> list:
    try:
        response = fyers_client.orderbook()
        if response.get("code") == 200:
            return response.get("data", [])
        return []
    except Exception as e:
        logger.error(f"Orderbook exception: {e}")
        return []