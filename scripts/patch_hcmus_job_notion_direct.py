import json
import time
from pathlib import Path

JOBS_PATH = Path(r"C:\Users\ADMIN\.openclaw\cron\jobs.json")

EXTRA = """

NOTION AUTH (IMPORTANT)
- Use the Notion REST API directly (requests to https://api.notion.com/v1).
- DO NOT use Maton gateway / api-gateway skill. Ignore MATON_API_KEY.
- Read token from NOTION_TOKEN (prefer HKCU\\Environment if needed on Windows).
- Notion-Version: 2022-06-28.
- If NOTION_TOKEN is missing/invalid or DB access fails, say that clearly in the final message.
""".strip()


def main():
    data = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    now = int(time.time() * 1000)
    changed = False

    for j in data.get("jobs", []):
        if j.get("name") != "HCMUS courses deadline check":
            continue
        payload = j.setdefault("payload", {})
        msg = payload.get("message", "")
        if "DO NOT use Maton gateway" not in msg:
            payload["message"] = msg.rstrip() + "\n\n" + EXTRA + "\n"
            j["updatedAtMs"] = now
            changed = True

    JOBS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UPDATED" if changed else "NO_CHANGE")


if __name__ == "__main__":
    main()
