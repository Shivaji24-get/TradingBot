import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, config: Dict):
        trader = config.get("trader", {})
        self.notif = trader.get("notifications", {})
        self.trader_email = trader.get("email", "")

    def send_telegram(self, message: str):
        if not self.notif.get("telegram_enabled"):
            return
        token = os.environ.get("TELEGRAM_BOT_TOKEN") or self.notif.get("telegram_bot_token", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID") or self.notif.get("telegram_chat_id", "")
        if not token or not chat_id:
            logger.warning("Telegram credentials not configured")
            return
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            logger.error("Telegram error: %s", e)

    def send_email(self, subject: str, body: str):
        if not self.notif.get("email_enabled"):
            return
        logger.info("Email notifications: configure SMTP in trading_profile.yml")

    def notify(self, message: str, subject: str = "TradingBot Alert"):
        self.send_telegram(message)
        self.send_email(subject, message)
