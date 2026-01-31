# tools/etrade_api.py
import os
import requests
from requests_oauthlib import OAuth1

BASE_URLS = {
    "sandbox": "https://apisb.etrade.com",
    "live": "https://api.etrade.com"
}

def oauth_session():
    return OAuth1(
        os.getenv("ETRADE_API_KEY"),
        os.getenv("ETRADE_API_SECRET"),
        os.getenv("ETRADE_ACCESS_TOKEN"),
        os.getenv("ETRADE_ACCESS_SECRET"),
        signature_type='auth_header'
    )

def get_accounts():
    """Return account info or raise."""
    base = BASE_URLS[os.getenv("ETRADE_ENV","sandbox")]
    url = f"{base}/v1/accounts/list.json"
    r = requests.get(url, auth=oauth_session())
    r.raise_for_status()
    return r.json()