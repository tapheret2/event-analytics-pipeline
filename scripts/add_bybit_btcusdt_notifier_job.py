import json
import time
import uuid
from pathlib import Path

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")
STATE_PATH = r"C:/Users/ADMIN/.openclaw/workspace/projects/bybit-demo-bot/notify_state_btcusdt.json"

NAME = "Bybit BTCUSDT v3 trade notify"


def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    jobs = data.setdefault("jobs", [])

    if any(j.get("name") == NAME for j in jobs):
        print("EXISTS")
        return

    now_ms = int(time.time() * 1000)

    msg = (
        "TRADE_NOTIFY_TICK (Bybit DEMO)\n"
        "Goal: Notify Phát on Telegram when the BTCUSDT position is opened or closed.\n\n"
        "Steps:\n"
        f"1) Read previous snapshot from {STATE_PATH} (if missing, treat as flat).\n"
        "2) Using Bybit DEMO API (pybit unified_trading), query current position for category=linear symbol=BTCUSDT (size, side, avgPrice).\n"
        "   - Read API creds from BYBIT_API_KEY/BYBIT_API_SECRET and BYBIT_DEMO=true (from HKCU\\Environment if needed).\n"
        "3) Determine transition: flat->pos = OPEN; pos->flat = CLOSE; side change = CLOSE+OPEN.\n"
        "4) If OPEN/CLOSE happened: send a Telegram message with time (Asia/Bangkok), side, size, avgPrice, and mention it's DEMO.\n"
        f"5) Write new snapshot back to {STATE_PATH}.\n"
        "6) If no change, output exactly NO_REPLY (do not send any message)."
    )

    job = {
        "id": str(uuid.uuid4()),
        "name": NAME,
        "enabled": True,
        "createdAtMs": now_ms,
        "updatedAtMs": now_ms,
        "schedule": {"kind": "every", "everyMs": 60_000, "anchorMs": now_ms + 10_000},
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {"kind": "agentTurn", "message": msg, "thinking": "low", "timeoutSeconds": 90},
        "delivery": {
            "mode": "announce",
            "channel": "telegram",
            "to": "telegram:1914302791",
            "bestEffort": True,
        },
        "state": {"nextRunAtMs": now_ms + 10_000, "consecutiveErrors": 0},
    }

    jobs.append(job)
    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ADDED", job["id"])


if __name__ == "__main__":
    main()
