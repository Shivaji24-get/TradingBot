import logging
from fyers_apiv3 import fyersModel
from typing import Optional

logger = logging.getLogger(__name__)

class FyersClient:
    def __init__(self, client_id: str, access_token: str, secret_key: str = ""):
        self.client_id = client_id
        self.access_token = access_token
        self.secret_key = secret_key
        self.fyers = None
        self._initialize()
    
    def _initialize(self):
        self.fyers = fyersModel.FyersModel(
            client_id=self.client_id,
            is_async=False,
            token=self.access_token,
            log_path=""
        )
        logger.info("Fyers client initialized")
    
    def refresh_token(self, new_token: str):
        self.access_token = new_token
        self._initialize()
    
    def get_client(self):
        return self.fyers
    
    def test_connection(self) -> bool:
        try:
            response = self.fyers.get_profile()
            return response.get("code") == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False