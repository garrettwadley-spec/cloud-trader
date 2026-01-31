import os, json, sys, time, webbrowser
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from requests_oauthlib import OAuth1

ENV=os.getenv("ETRADE_ENV","sandbox").lower()
BASE="https://apisb.etrade.com" if ENV=="sandbox" else "https://api.etrade.com"
REQ_TOKEN=f"{BASE}/oauth/request_token"; AUTH=f"{BASE}/oauth/authorize"
ACCESS=f"{BASE}/oauth/access_token"; ACCOUNTS=f"{BASE}/v1/accounts/list"
CK=os.getenv("ETRADE_API_KEY"); CS=os.getenv("ETRADE_API_SECRET"); CB=os.getenv("ETRADE_CALLBACK_URL")

def oauth1(t=None,s=None,cb=None):
    return OAuth1(CK, client_secret=CS, resource_owner_key=t, resource_owner_secret=s, callback_uri=cb, signature_method="HMAC-SHA1")

def get_req():
    r=requests.post(REQ_TOKEN, auth=oauth1(cb=CB)); r.raise_for_status(); q=parse_qs(r.text); return q["oauth_token"][0], q["oauth_token_secret"][0]
def open_auth(t):
    url=f"{AUTH}?key={CK}&token={t}"; print("Authorize URL:", url); 
    try: webbrowser.open(url)
    except: pass
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q=parse_qs(urlparse(self.path).query); v=q.get("oauth_verifier",[None])[0]
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK"); self.server.verifier=v
def capture(port=5050, timeout=300):
    from http.server import HTTPServer; import time
    s=HTTPServer(("127.0.0.1",port),H); s.verifier=None; end=time.time()+timeout
    while time.time()<end and not s.verifier: s.handle_request()
    return s.verifier
def get_access(rt,rs,v):
    r=requests.post(ACCESS, auth=oauth1(rt,rs), data={"oauth_verifier":v}); r.raise_for_status(); q=parse_qs(r.text); return q["oauth_token"][0], q["oauth_token_secret"][0]
def fetch_accounts(at,as_):
    r=requests.get(ACCOUNTS, auth=oauth1(at,as_)); r.raise_for_status(); return r.json()

def main():
    if not CK or not CS: print("Set ETRADE_API_KEY and ETRADE_API_SECRET."); sys.exit(1)
    rt, rs = get_req(); open_auth(rt)
    v=None
    if CB and ("127.0.0.1" in CB or "localhost" in CB):
        port = urlparse(CB).port or 80; v = capture(port=port, timeout=300)
    if not v: v = input("Paste oauth_verifier: ").strip()
    at, as_ = get_access(rt, rs, v)
    data = fetch_accounts(at, as_)
    try:
        accounts = data["AccountListResponse"]["Accounts"]["Account"]
    except Exception:
        print("Unexpected response:", json.dumps(data, indent=2)); sys.exit(1)
    out=[{k: acc.get(k) for k in ("accountId","accountIdKey","accountDesc","institutionType","accountMode")} for acc in accounts]
    print("\n=== Accounts ===")
    for a in out: print(a)
    os.makedirs("config", exist_ok=True)
    with open("config/accounts.json","w",encoding="utf-8") as f: json.dump(out, f, indent=2)
    print("\nSaved: config/accounts.json")
    if out:
        print("\nUse accountIdKey below in .env:")
        print("ETRADE_ACCOUNT_ID="+out[0]["accountIdKey"])
    print("\nAlso set in .env:")
    print("ETRADE_ACCESS_TOKEN="+at)
    print("ETRADE_ACCESS_SECRET="+as_)

if __name__=="__main__":
    main()
