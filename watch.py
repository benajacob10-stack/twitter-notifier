#!/usr/bin/env python3
"""Watch one X user for a keyword; ping Telegram on each match."""
import os, json, time, requests
from requests.exceptions import ChunkedEncodingError, ConnectionError

BEARER = os.environ["X_BEARER_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

USERNAME = "FabrizioRomano"   # handle to watch, no @
KEYWORD  = "Everton"      # keyword (use quotes in the rule for exact phrases)
HASHTAG  = "#EFC"

RULE = f'from:{USERNAME}' # ("{KEYWORD}" OR {HASHTAG})'
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
    msg = f"🔔 @{USERNAME} matched:\n{t['text']}\n{url}"
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

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
    while True:
        try:
            stream()
        except (ChunkedEncodingError, ConnectionError) as e:
            print("Reconnecting:", e)
            time.sleep(5)
