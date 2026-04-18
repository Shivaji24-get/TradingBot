import os
import json
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional

logger = logging.getLogger(__name__)

class TokenManager:
    TOKEN_FILE = "token.enc"
    TOKEN_KEY_FILE = "token.key"
    
    def __init__(self, client_id: str, secret_key: str):
        self.client_id = client_id
        self.secret_key = secret_key
        self.token_dir = Path(".")
        self._fernet = self._load_or_create_key()
    
    def _load_or_create_key(self) -> Fernet:
        key_path = self.token_dir / self.TOKEN_KEY_FILE
        if key_path.exists():
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
        return Fernet(key)
    
    def save_token(self, access_token: str, refresh_token: Optional[str] = None):
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "timestamp": datetime.now().isoformat(),
            "expires_in": 86400
        }
        encrypted = self._fernet.encrypt(json.dumps(token_data).encode())
        with open(self.token_dir / self.TOKEN_FILE, "wb") as f:
            f.write(encrypted)
        logger.info("Token saved securely")
    
    def load_token(self) -> Optional[dict]:
        token_path = self.token_dir / self.TOKEN_FILE
        if not token_path.exists():
            return None
        try:
            with open(token_path, "rb") as f:
                encrypted = f.read()
            decrypted = self._fernet.decrypt(encrypted)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            return None
    
    def is_token_valid(self) -> bool:
        token_data = self.load_token()
        if not token_data:
            return False
        timestamp = datetime.fromisoformat(token_data["timestamp"])
        expiry = timestamp + timedelta(seconds=token_data.get("expires_in", 86400))
        return datetime.now() < expiry
    
    def get_access_token(self) -> Optional[str]:
        if self.is_token_valid():
            return self.load_token().get("access_token")
        return None
    
    def clear_tokens(self):
        for f in [self.TOKEN_FILE, self.TOKEN_KEY_FILE]:
            path = self.token_dir / f
            if path.exists():
                path.unlink()
        logger.info("Tokens cleared")