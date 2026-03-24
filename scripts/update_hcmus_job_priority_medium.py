import json
import time
from pathlib import Path

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")

def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    now = int(time.time() * 1000)
    updated = False
    for j in data.get("jobs", []):
        if j.get("name") != "HCMUS courses deadline check":
            continue
        msg = j.get("payload", {}).get("message", "")
        if "Priority (select) [optional]" in msg:
            msg = msg.replace(
                "Priority (select) [optional]",
                "Priority (select) — set default to Medium for Class tasks",
            )
        if "Set Category = Class." in msg and "Set Priority = Medium." not in msg:
            msg = msg.replace(
                "Set Category = Class.",
                "Set Category = Class.\n- Set Priority = Medium.",
            )
        j.setdefault("payload", {})["message"] = msg
        j["updatedAtMs"] = now
        updated = True

    if not updated:
        raise SystemExit("NOT_FOUND")

    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UPDATED")


if __name__ == "__main__":
    main()
