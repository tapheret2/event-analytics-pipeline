from __future__ import annotations

import os
import sys
import json
import datetime as dt
from typing import Any, Optional

import requests

NOTION_VERSION = "2022-06-28"


def notion_headers() -> dict[str, str]:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise SystemExit("Missing NOTION_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def api(method: str, path: str, payload: Any | None = None) -> Any:
    url = f"https://api.notion.com/v1{path}"
    r = requests.request(method, url, headers=notion_headers(), json=payload, timeout=30)
    if r.status_code >= 400:
        raise SystemExit(f"Notion API error {r.status_code}: {r.text[:400]}")
    return r.json()


def list_child_databases(page_id: str, limit_pages: int = 10) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    start: Optional[str] = None
    for _ in range(limit_pages):
        qs = f"?page_size=100" + (f"&start_cursor={start}" if start else "")
        data = api("GET", f"/blocks/{page_id}/children{qs}")
        for b in data.get("results", []):
            if b.get("type") == "child_database":
                out.append({"id": b.get("id"), "title": (b.get("child_database") or {}).get("title", "")})
        start = data.get("next_cursor")
        if not start:
            break
    return out


def search_database(query: str) -> list[dict[str, str]]:
    payload = {
        "query": query,
        "filter": {"value": "database", "property": "object"},
        "page_size": 10,
    }
    data = api("POST", "/search", payload)
    out = []
    for d in data.get("results", []):
        title = "".join(t.get("plain_text", "") for t in d.get("title", []))
        out.append({"id": d.get("id"), "title": title})
    return out


def pick_date_prop(db: dict) -> str:
    props = db.get("properties", {})
    for k, v in props.items():
        if v.get("type") == "date":
            return k
    raise SystemExit("No date property found in timetable database")


def pick_title_prop(db: dict) -> str:
    props = db.get("properties", {})
    for k, v in props.items():
        if v.get("type") == "title":
            return k
    raise SystemExit("No title property found")


def get_plain_title(page: dict, title_prop: str) -> str:
    t = ((page.get("properties", {}) or {}).get(title_prop, {}) or {}).get("title", [])
    return "".join(x.get("plain_text", "") for x in t).strip()


def get_date(page: dict, date_prop: str) -> dict | None:
    return ((page.get("properties", {}) or {}).get(date_prop, {}) or {}).get("date")


def query_for_day(db_id: str, date_prop: str, day: dt.date) -> list[dict]:
    # Notion date filter uses ISO date strings.
    payload = {
        "filter": {
            "property": date_prop,
            "date": {"equals": day.isoformat()},
        },
        "sorts": [{"property": date_prop, "direction": "ascending"}],
        "page_size": 50,
    }
    data = api("POST", f"/databases/{db_id}/query", payload)
    return data.get("results", [])


def fmt_item(page: dict, title_prop: str, date_prop: str) -> str:
    title = get_plain_title(page, title_prop)
    d = get_date(page, date_prop) or {}
    start = d.get("start")
    end = d.get("end")
    if start and end:
        return f"{start} → {end} — {title}"
    if start:
        return f"{start} — {title}"
    return title or "(untitled)"


def main():
    page_id = sys.argv[1] if len(sys.argv) > 1 else "1934c265832d80e1b249ff9d768f2479"

    child_dbs = list_child_databases(page_id)
    db_id = child_dbs[0]["id"] if child_dbs else None

    if not db_id:
        # fallback: search by common VN name
        cands = search_database("Thời khoá biểu")
        if cands:
            db_id = cands[0]["id"]

    if not db_id:
        raise SystemExit("Could not find timetable database")

    db = api("GET", f"/databases/{db_id}")
    date_prop = pick_date_prop(db)
    title_prop = pick_title_prop(db)

    tz = dt.timezone(dt.timedelta(hours=7))
    now = dt.datetime.now(tz)

    # Provide both 'today' and 'tomorrow' because user messages can arrive after midnight.
    days = [now.date(), (now + dt.timedelta(days=1)).date()]

    out = {
        "db_id": db_id,
        "db_title": "".join(t.get("plain_text", "") for t in db.get("title", [])),
        "date_prop": date_prop,
        "title_prop": title_prop,
        "days": {},
    }

    for day in days:
        items = query_for_day(db_id, date_prop, day)
        out["days"][day.isoformat()] = [fmt_item(p, title_prop, date_prop) for p in items]

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
