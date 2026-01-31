# tools/oauth_helper.py
import os, webbrowser, requests
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv, set_key

load_dotenv("C:\\AITrader\\.env")

API_KEY    = os.getenv("ETRADE_API_KEY")
API_SECRET = os.getenv("ETRADE_API_SECRET")
ENV        = os.getenv("ETRADE_ENV","sandbox")

REQ_TOKEN_URL = {
    "sandbox": "https://apisb.etrade.com/oauth/request_token",
    "live":    "https://api.etrade.com/oauth/request_token"
}
AUTH_URL = {
    "sandbox": "https://apisb.etrade.com/oauth/authorize",
    "live":    "https://api.etrade.com/oauth/authorize"
}
ACCESS_TOKEN_URL = {
    "sandbox": "https://apisb.etrade.com/oauth/access_token",
    "live":    "https://api.etrade.com/oauth/access_token"
}

def get_authorize_url():
    oauth = OAuth1Session(API_KEY, client_secret=API_SECRET, callback_uri="oob")
    resp = oauth.fetch_request_token(REQ_TOKEN_URL[ENV])
    set_key(".env", "ETRADE_REQUEST_TOKEN", resp["oauth_token"])
    set_key(".env", "ETRADE_REQUEST_SECRET", resp["oauth_token_secret"])
    return f"{AUTH_URL[ENV]}?key={API_KEY}&token={resp['oauth_token']}"

def exchange_pin(pin: str):
    oauth = OAuth1Session(
        API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=os.getenv("ETRADE_REQUEST_TOKEN"),
        resource_owner_secret=os.getenv("ETRADE_REQUEST_SECRET"),
        verifier=pin
    )
    tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL[ENV])
    set_key(".env", "ETRADE_ACCESS_TOKEN", tokens["oauth_token"])
    set_key(".env", "ETRADE_ACCESS_SECRET", tokens["oauth_token_secret"])
    return tokens