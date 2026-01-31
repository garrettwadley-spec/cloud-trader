import os, sys, time, webbrowser
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from requests_oauthlib import OAuth1

ENV = os.getenv("ETRADE_ENV","sandbox").lower()
BASE = "https://apisb.etrade.com" if ENV=="sandbox" else "https://api.etrade.com"
REQ_TOKEN_URL=f"{BASE}/oauth/request_token"; AUTH_URL=f"{BASE}/oauth/authorize"
ACCESS_URL=f"{BASE}/oauth/access_token"

CK=os.getenv("ETRADE_API_KEY"); CS=os.getenv("ETRADE_API_SECRET"); CB=os.getenv("ETRADE_CALLBACK_URL")

def oauth1(token=None, secret=None, cb=None):
    return OAuth1(CK, client_secret=CS, resource_owner_key=token, resource_owner_secret=secret, callback_uri=cb, signature_method="HMAC-SHA1")

def get_request_token():
    r = requests.post(REQ_TOKEN_URL, auth=oauth1(cb=CB)); r.raise_for_status(); q = parse_qs(r.text); return q["oauth_token"][0], q["oauth_token_secret"][0]

def open_auth(t):
    url = f"{AUTH_URL}?key={CK}&token={t}"; print("Authorize URL:", url); 
    try: webbrowser.open(url)
    except: pass

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query); v = q.get("oauth_verifier",[None])[0]
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK; you can close this window."); self.server.verifier = v

def capture_verifier(port=5050, timeout=300):
    server = HTTPServer(("127.0.0.1", port), Handler); server.verifier=None; end=time.time()+timeout
    while time.time()<end and not server.verifier: server.handle_request(); 
    return server.verifier

def get_access(rt, rs, verifier):
    r = requests.post(ACCESS_URL, auth=oauth1(rt, rs), data={"oauth_verifier": verifier}); r.raise_for_status(); q = parse_qs(r.text); return q["oauth_token"][0], q["oauth_token_secret"][0]

def main():
    if not CK or not CS: print("Set ETRADE_API_KEY and ETRADE_API_SECRET."); sys.exit(1)
    print(f"E*TRADE OAuth ({ENV.upper()})")
    rt, rs = get_request_token(); open_auth(rt)
    v=None
    if CB and ("127.0.0.1" in CB or "localhost" in CB):
        port = urlparse(CB).port or 80; v = capture_verifier(port=port, timeout=300)
    if not v: v = input("Paste oauth_verifier: ").strip()
    at, as_ = get_access(rt, rs, v)
    print("ETRADE_ACCESS_TOKEN=", at); print("ETRADE_ACCESS_SECRET=", as_)

if __name__ == "__main__":
    main()
