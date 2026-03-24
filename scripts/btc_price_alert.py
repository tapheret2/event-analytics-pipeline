import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

STATE_PATH = Path(__file__).parent / "btc_price_alert_state.json"
API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
USER_TARGET = "telegram:1914302791"
CHANNEL = "telegram"
HOUR_MSG_FMT = "🕐 BTC hourly update: ${price:,.2f} USD (as of {timestamp})"
MILESTONE_MSG_FMT = "📈 BTC hit ${milestone:,} (current {price:,.2f}) at {timestamp}"
ERROR_MSG_FMT = "⚠️ BTC alert error: {error}"


def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"last_milestone": None, "last_hour": ""}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state))


def send_message(text):
    subprocess.run(
        [
            "openclaw",
            "message",
            "send",
            "--channel",
            CHANNEL,
            "--to",
            USER_TARGET,
            "--message",
            text,
        ],
        check=True,
    )


def fetch_price():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    price = data.get("bitcoin", {}).get("usd")
    if price is None:
        raise ValueError("API did not return USD price")
    return float(price)


def round_milestone(price):
    milestone = math.floor(price / 1000) * 1000
    if milestone <= 0:
        milestone = 0
    return milestone


def format_timestamp(now):
    return now.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    state = load_state()
    while True:
        now = datetime.now(timezone.utc)
        local_ts = format_timestamp(now)
        try:
            price = fetch_price()
        except Exception as exc:
            try:
                send_message(ERROR_MSG_FMT.format(error=exc))
            except Exception:
                pass
            time.sleep(60)
            continue

        # Hourly alert
        hour_tag = now.strftime("%Y-%m-%dT%H")
        if hour_tag != state.get("last_hour") and now.minute == 0:
            msg = HOUR_MSG_FMT.format(price=price, timestamp=local_ts)
            try:
                send_message(msg)
                state["last_hour"] = hour_tag
            except Exception as exc:
                pass

        # Milestone alert (every 1000 USD)
        milestone = round_milestone(price)
        last_milestone = state.get("last_milestone")
        if milestone and milestone != last_milestone and abs(price - milestone) <= 20:
            msg = MILESTONE_MSG_FMT.format(milestone=milestone, price=price, timestamp=local_ts)
            try:
                send_message(msg)
                state["last_milestone"] = milestone
            except Exception as exc:
                pass

        save_state(state)
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
