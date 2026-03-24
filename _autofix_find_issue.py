import json, re, pathlib, requests

env = pathlib.Path(r"D:\\Multi Agents\\option-b\\.env").read_text(encoding="utf-8")
m = re.search(r"^GITHUB_TOKEN=(.+)$", env, re.M)
if not m:
    raise SystemExit("GITHUB_TOKEN not found")
token = m.group(1).strip()

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json",
}
owner = "Peganyx"
repo = "test-agent"

q = f"repo:{owner}/{repo} is:issue is:open label:'auto-fix'"
r = requests.get(
    "https://api.github.com/search/issues",
    headers=headers,
    params={"q": q, "sort": "created", "order": "desc", "per_page": 20},
    timeout=30,
)
r.raise_for_status()
items = r.json()["items"]

state_path = pathlib.Path(r"C:\\Users\\ADMIN\\.openclaw\\workspace\\autofix_state.json")
processed = json.loads(state_path.read_text(encoding="utf-8-sig"))
processed_nums = {int(k) for k in processed.keys()}

started_phrase = "🤖 Auto-fix: started"

def has_started_comment(num: int) -> bool:
    rr = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{num}/comments",
        headers=headers,
        params={"per_page": 100},
        timeout=30,
    )
    rr.raise_for_status()
    return any(started_phrase in (c.get("body") or "") for c in rr.json())

candidates = []
for it in items:
    num = int(it["number"])
    if num in processed_nums:
        continue
    if has_started_comment(num):
        continue
    candidates.append(
        {
            "number": num,
            "title": it.get("title"),
            "url": it.get("html_url"),
            "created_at": it.get("created_at"),
        }
    )

print(json.dumps({"candidates": candidates}, indent=2))
