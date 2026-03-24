import json
import time
import uuid
import datetime as dt
from pathlib import Path

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")

NAME = "Notion timetable check (tomorrow)"
NOTION_PAGE_ID = "1934c265832d80e1b249ff9d768f2479"

TZ = dt.timezone(dt.timedelta(hours=7))  # Asia/Bangkok


def next_run_22_local_ms(now: dt.datetime) -> int:
    today_22 = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if now < today_22:
        nxt = today_22
    else:
        nxt = (now + dt.timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
    return int(nxt.timestamp() * 1000)


def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    jobs = data.setdefault("jobs", [])

    # If exists, just update schedule + message.
    now_ms = int(time.time() * 1000)
    now_local = dt.datetime.now(TZ)
    nxt_ms = next_run_22_local_ms(now_local)

    msg = (
        "NOTION_TIMETABLE_TICK\n"
        "Goal: At 22:00 Asia/Bangkok, check Phát's Notion timetable page and message what classes tomorrow.\n\n"
        f"Notion page: https://www.notion.so/{NOTION_PAGE_ID}\n\n"
        "Instructions:\n"
        "1) Use Notion API (NOTION_TOKEN, Notion-Version 2022-06-28).\n"
        "2) Inspect the page blocks to locate the timetable database/view. If it's a database, query items for tomorrow (local Asia/Bangkok date).\n"
        "3) Build a digest in Vietnamese: list each class with time range, course name/code, location/room, and any notes.\n"
        "4) If you cannot find structured schedule, at least summarize any text that indicates tomorrow's classes.\n"
        "5) If there is no class tomorrow, reply exactly: 'Mai không có môn nào.'\n"
    )

    for j in jobs:
        if j.get("name") == NAME:
            j["enabled"] = True
            j["updatedAtMs"] = now_ms
            j["schedule"] = {"kind": "cron", "expr": "0 22 * * *", "tz": "Asia/Bangkok"}
            j.setdefault("payload", {})
            j["payload"].update({"kind": "agentTurn", "message": msg, "thinking": "low", "timeoutSeconds": 180})
            j["delivery"] = {"mode": "announce", "channel": "telegram", "to": "telegram:1914302791", "bestEffort": True}
            j.setdefault("state", {})
            j["state"]["nextRunAtMs"] = nxt_ms
            JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("UPDATED", j.get("id"), nxt_ms)
            return

    job = {
        "id": str(uuid.uuid4()),
        "name": NAME,
        "enabled": True,
        "createdAtMs": now_ms,
        "updatedAtMs": now_ms,
        "schedule": {"kind": "cron", "expr": "0 22 * * *", "tz": "Asia/Bangkok"},
        "sessionTarget": "isolated",
        "wakeMode": "now",
        "payload": {"kind": "agentTurn", "message": msg, "thinking": "low", "timeoutSeconds": 180},
        "delivery": {"mode": "announce", "channel": "telegram", "to": "telegram:1914302791", "bestEffort": True},
        "state": {"nextRunAtMs": nxt_ms, "consecutiveErrors": 0},
    }

    jobs.append(job)
    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ADDED", job["id"], nxt_ms)


if __name__ == "__main__":
    main()
