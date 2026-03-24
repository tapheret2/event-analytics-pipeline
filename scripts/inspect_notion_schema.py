import os, requests
DB_ID = "31e4c265832d8011bc64e832d0cff957"
headers = {
    "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
r = requests.get(f"https://api.notion.com/v1/databases/{DB_ID}", headers=headers, timeout=30)
print("status", r.status_code)
r.raise_for_status()
d = r.json()
props = d["properties"]
print("properties:", list(props.keys()))
prio_opts = props.get("Priority", {}).get("select", {}).get("options", [])
print("priority options:", [o.get("name") for o in prio_opts])
status_opts = props.get("Status", {}).get("status", {}).get("options", [])
print("status options:", [o.get("name") for o in status_opts])
cat_key = next((k for k in props.keys() if k.strip() == "Category"), None)
print("category key:", repr(cat_key))
cat_opts = props.get(cat_key, {}).get("select", {}).get("options", []) if cat_key else []
print("category options:", [o.get("name") for o in cat_opts])
