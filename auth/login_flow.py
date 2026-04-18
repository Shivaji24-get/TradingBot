# Add these imports at the TOP of the file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import logging
import time
import webbrowser
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel

logger = logging.getLogger(__name__)

class LoginFlow:
    def __init__(self, client_id: str, secret_key: str, redirect_uri: str,
                 username: str = None, pin: str = None, mobile: str = None):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.username = username
        self.pin = pin
        self.mobile = mobile
    
    def generate_auth_code(self) -> str:
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            state="sample_state"
        )
        auth_url = session.generate_authcode()
        
        # Manual login - open browser for user
        print(f"Opening browser: {auth_url}")
        webbrowser.open(auth_url)
        
        auth_code = input("Enter auth code from redirect URL: ").strip()
        return auth_code
    
    def get_access_token(self, auth_code: str) -> dict:
        session = fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            grant_type="authorization_code"
        )
        session.set_token(auth_code)
        response = session.generate_token()
        
        if response.get("code") == 200:
            return {
                "access_token": response.get("access_token"),
                "refresh_token": response.get("refresh_token", ""),
                "expires_in": response.get("expires_in", 86400)
            }
        raise Exception(f"Failed to get access token: {response}")
    
    def authenticate(self) -> str:
        auth_code = self.generate_auth_code()
        token_response = self.get_access_token(auth_code)
        return token_response["access_token"]