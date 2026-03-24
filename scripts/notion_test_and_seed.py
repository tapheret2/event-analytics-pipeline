import os
import sys
import json
import datetime as dt
import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DB_ID = "31e4c265832d8011bc64e832d0cff957"
NOTION_VERSION = "2022-06-28"

if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN is not set")
    sys.exit(2)

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def api(method: str, path: str, payload=None):
    url = f"https://api.notion.com/v1{path}"
    r = requests.request(method, url, headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        print("NOTION_API_ERROR", r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:2000])
        sys.exit(1)
    return r.json()

# 1) Fetch DB schema
_db = api("GET", f"/databases/{DB_ID}")
print("OK: connected to Notion DB")
print("DB title:", "".join([t.get("plain_text", "") for t in _db.get("title", [])]) or "(no title)")
props = _db.get("properties", {})

# helpers to find property names

def find_prop(expected: str):
    # try exact then case-insensitive, also tolerate leading/trailing whitespace in Notion property names
    if expected in props:
        return expected
    for k in props.keys():
        if k.lower() == expected.lower():
            return k
    for k in props.keys():
        if k.strip().lower() == expected.lower():
            return k
    return None

p_task = find_prop("Task")
p_desc = find_prop("Description")
p_deadline = find_prop("Deadline")
p_status = find_prop("Status")
p_priority = find_prop("Priority")
p_category = find_prop("Category")

missing = [n for n, v in [("Task", p_task), ("Deadline", p_deadline), ("Status", p_status), ("Category", p_category)] if v is None]
if missing:
    print("ERROR: Missing expected properties:", missing)
    print("Found properties:", list(props.keys()))
    sys.exit(3)

# pick a default non-done status
status_options = props[p_status].get("status", {}).get("options", [])
def_status = None
for opt in status_options:
    if opt.get("name", "").lower() not in ("done", "completed"):
        def_status = opt.get("name")
        break
if not def_status and status_options:
    def_status = status_options[0].get("name")

# Ensure Category value exists (select)
cat_options = props[p_category].get("select", {}).get("options", [])
cat_names = {o.get("name") for o in cat_options}
cat_value = "Class"

# 2) Upsert check: find existing task with same title
course = "MTH10131"
title = f"{course} - BTVN#3"

query = {
    "filter": {
        "property": p_task,
        "title": {"equals": title},
    },
    "page_size": 5,
}
res = api("POST", f"/databases/{DB_ID}/query", query)
exists = (res.get("results") or [])

# deadline in Asia/Bangkok
deadline = dt.datetime(2026, 3, 24, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=7)))

page_props = {
    p_task: {"title": [{"text": {"content": title}}]},
    p_deadline: {"date": {"start": deadline.isoformat()}},
}

# set Status if possible
if def_status:
    page_props[p_status] = {"status": {"name": def_status}}

# set Category (select) — Notion often auto-creates if absent; we try anyway
page_props[p_category] = {"select": {"name": cat_value}}

if not exists:
    payload = {
        "parent": {"database_id": DB_ID},
        "properties": page_props,
    }
    created = api("POST", "/pages", payload)
    url = created.get("url")
    print("CREATED:", url)
else:
    page_id = exists[0].get("id")
    upd = api("PATCH", f"/pages/{page_id}", {"properties": page_props})
    print("UPDATED:", upd.get("url"))

# 3) Digest: due next 7 days (not done) for Category=Class
now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
end = now + dt.timedelta(days=7)

# Build filter for date between now and end
f = {
    "and": [
        {"property": p_category, "select": {"equals": cat_value}},
        {"property": p_deadline, "date": {"on_or_after": now.date().isoformat()}},
        {"property": p_deadline, "date": {"on_or_before": end.date().isoformat()}},
    ]
}
# If status has a Done option, filter it out
if status_options:
    done_names = [o.get("name") for o in status_options if o.get("name", "").lower() in ("done", "completed")]
    if done_names:
        f["and"].append({"property": p_status, "status": {"does_not_equal": done_names[0]}})

digest = api("POST", f"/databases/{DB_ID}/query", {"filter": f, "page_size": 20})
items = []
for pg in digest.get("results", []):
    pr = pg.get("properties", {})
    # title
    t = pr.get(p_task, {}).get("title", [])
    title_txt = "".join([x.get("plain_text", "") for x in t])
    d = pr.get(p_deadline, {}).get("date", {})
    due = (d or {}).get("start")
    st = pr.get(p_status, {}).get("status", {}).get("name") if p_status in pr else None
    items.append({"title": title_txt, "due": due, "status": st, "url": pg.get("url")})

print("DIGEST_COUNT:", len(items))
print(json.dumps(items, ensure_ascii=False, indent=2))
