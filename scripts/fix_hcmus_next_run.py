import json
from pathlib import Path
import datetime as dt

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")

TZ = dt.timezone(dt.timedelta(hours=7))  # Asia/Bangkok

def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))

    now = dt.datetime.now(TZ)
    today_18 = now.replace(hour=18, minute=0, second=0, microsecond=0)
    tomorrow_6 = (now + dt.timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)

    next_run = today_18 if now < today_18 else tomorrow_6
    next_ms = int(next_run.timestamp() * 1000)

    updated = False
    for j in data.get("jobs", []):
        if j.get("name") == "HCMUS courses deadline check":
            j.setdefault("state", {})["nextRunAtMs"] = next_ms
            updated = True

    if not updated:
        raise SystemExit("NOT_FOUND")

    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UPDATED_NEXT_RUN_AT_MS", next_run.isoformat(), next_ms)


if __name__ == "__main__":
    main()
