import os
import sys
import requests
import datetime as dt

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DB_ID = "31e4c265832d8011bc64e832d0cff957"
NOTION_VERSION = "2022-06-28"

if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN not set")
    sys.exit(2)

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def api(method: str, url: str, payload=None):
    r = requests.request(method, url, headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        print("NOTION_API_ERROR", r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:2000])
        sys.exit(1)
    return r.json()

# Fetch DB to get exact property keys
_db = api("GET", f"https://api.notion.com/v1/databases/{DB_ID}")
props = _db.get("properties", {})

def prop_key(name: str):
    # exact, case-insensitive, stripped
    if name in props:
        return name
    for k in props:
        if k.lower() == name.lower() or k.strip().lower() == name.lower():
            return k
    return None

p_task = prop_key("Task")
p_desc = prop_key("Description")
p_deadline = prop_key("Deadline")
p_status = prop_key("Status")
p_priority = prop_key("Priority")
p_category = prop_key("Category")

for need in (p_task, p_desc, p_deadline, p_status, p_priority, p_category):
    if not need:
        print("ERROR: missing expected property key")
        print("Found:", list(props.keys()))
        sys.exit(3)

TITLE = "MTH10131 - BTVN#3"
ASSIGN_URL = "https://courses.hcmus.edu.vn/mod/assign/view.php?id=53559"
COURSE_NAME = "Lý thuyết thống kê - 24KDL - MTH10131"

# Query page by title
q = {
    "filter": {"property": p_task, "title": {"equals": TITLE}},
    "page_size": 5,
}
res = api("POST", f"https://api.notion.com/v1/databases/{DB_ID}/query", q)
results = res.get("results", [])
if not results:
    print("ERROR: page not found for title", TITLE)
    sys.exit(4)

page_id = results[0]["id"]

# Description content (English header + original VN details)
due = dt.datetime(2026, 3, 24, 12, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=7)))
open_time = dt.datetime(2026, 3, 17, 0, 0, 0, tzinfo=dt.timezone(dt.timedelta(hours=7)))

desc_lines = [
    f"Course: {COURSE_NAME}",
    "Type: Homework (Assignment)",
    f"Moodle: {ASSIGN_URL}",
    f"Open: {open_time.isoformat()}",
    f"Due:  {due.isoformat()}",
    "",
    "Exercises (from Moodle): 2.6, 2.7, 2.10, 2.11, 2.14, 2.15, 2.16.",
    "Notes (from Moodle): 'File ảnh chụp các bài tập này xem link'.",
]

# Notion rich_text chunks <= 2000 chars each
full = "\n".join(desc_lines)
chunks = []
while full:
    chunks.append(full[:1800])
    full = full[1800:]

rich = [{"type": "text", "text": {"content": c}} for c in chunks]

payload = {
    "properties": {
        p_desc: {"rich_text": rich},
        p_priority: {"select": {"name": "Medium"}},
        p_category: {"select": {"name": "Class"}},
    }
}

upd = api("PATCH", f"https://api.notion.com/v1/pages/{page_id}", payload)
print("UPDATED:", upd.get("url"))
