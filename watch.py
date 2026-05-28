#!/usr/bin/env python3
"""Watch one X user for a keyword; ping Telegram on each match."""
import os, json, time, requests
from requests.exceptions import ChunkedEncodingError, ConnectionError

BEARER = os.environ["X_BEARER_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

USERNAME = "FabrizioRomano"   # handle to watch, no @
KEYWORD  = "Everton"      # keyword (use quotes in the rule for exact phrases)
KEYWORD2 = "here we go" 
KEYWORD3 = "premier league"
HASHTAG  = "#EFC"

RULE = f'from:{USERNAME} ("{KEYWORD}" OR "{KEYWORD2}" OR "{KEYWORD3}" OR {HASHTAG})'
STREAM = "https://api.twitter.com/2/tweets/search/stream"
RULES  = STREAM + "/rules"
H = {"Authorization": f"Bearer {BEARER}"}

def set_rules():
    existing = requests.get(RULES, headers=H).json().get("data", [])
    if existing:
        requests.post(RULES, headers=H,
                      json={"delete": {"ids": [r["id"] for r in existing]}})
    r = requests.post(RULES, headers=H,
                      json={"add": [{"value": RULE, "tag": "watch"}]})
    r.raise_for_status()
    print("Rule installed:", r.json())

def notify(tweet):
    t = tweet["data"]
    url = f"https://x.com/{USERNAME}/status/{t['id']}"
    msg = f"{t['text']}\n\n{url}"
    requests.post(DISCORD_WEBHOOK_URL, json={
        "content": msg,
        "flags": 4,
    })

def stream():
    params = {"tweet.fields": "created_at,author_id"}
    with requests.get(STREAM, headers=H, params=params,
                      stream=True, timeout=90) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                notify(json.loads(line))
            except json.JSONDecodeError:
                pass

if __name__ == "__main__":
    set_rules()
    backoff = 5
    while True:
        try:
            stream()
            backoff = 5   # reset after a clean run
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            if code == 429:
                print(f"429 rate limited — backing off {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 600)   # exponential, cap 10 min
            else:
                print(f"HTTP {code}: {e.response.text}")
                time.sleep(60)
        except (ChunkedEncodingError, ConnectionError, requests.exceptions.Timeout) as e:
            print("Reconnecting:", e)
            time.sleep(backoff)
        except KeyboardInterrupt:
            print("Shutting down cleanly")
            break
