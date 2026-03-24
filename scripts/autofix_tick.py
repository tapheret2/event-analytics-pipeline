"""autofix_tick.py

A small helper used by the cron agent-turn to keep the cron message short and
avoid quoting issues.

What it does:
- Reads GITHUB_TOKEN from env or from D:\Multi Agents\option-b\.env
- Finds the next OPEN issue with label 'auto-fix' that is not yet started
  (no comment contains '🤖 Auto-fix: started')
- Writes selection to workspace/autofix/current_issue.json
- Posts the 'started' comment

It does NOT generate code fixes (the OpenClaw agent is the brain).

Usage:
  python scripts/autofix_tick.py --repo Peganyx/test-agent

Output:
  Prints JSON with repo, issue_number, title, url.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import requests

OPTION_B_ENV = Path(r"D:\Multi Agents\option-b\.env")
STATE_DIR = Path(r"C:\Users\ADMIN\.openclaw\workspace\autofix")
STATE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_ISSUE_PATH = STATE_DIR / "current_issue.json"


def read_token() -> str:
    if os.getenv("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()
    if OPTION_B_ENV.exists():
        txt = OPTION_B_ENV.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^GITHUB_TOKEN=(.+)$", txt, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    raise SystemExit("Missing GITHUB_TOKEN (env or option-b .env)")


def gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "openclaw-autofix",
    }


def find_next_issue(token: str, repo: str) -> dict | None:
    owner, name = repo.split("/", 1)
    # List issues with label auto-fix (includes PRs; filter pull_request field)
    url = f"https://api.github.com/repos/{owner}/{name}/issues"
    r = requests.get(
        url,
        params={"state": "open", "labels": "auto-fix", "per_page": 30, "sort": "created", "direction": "asc"},
        headers=gh_headers(token),
        timeout=30,
    )
    r.raise_for_status()
    issues = r.json()

    for it in issues:
        if it.get("pull_request"):
            continue
        number = it["number"]

        # Check comments for started marker
        cr = requests.get(
            f"https://api.github.com/repos/{owner}/{name}/issues/{number}/comments",
            params={"per_page": 100},
            headers=gh_headers(token),
            timeout=30,
        )
        cr.raise_for_status()
        comments = cr.json()
        if any("🤖 Auto-fix: started" in (c.get("body") or "") for c in comments):
            continue

        return {
            "repo": repo,
            "issue_number": number,
            "title": it.get("title") or "",
            "url": it.get("html_url") or "",
        }

    return None


def comment_started(token: str, repo: str, issue_number: int) -> None:
    owner, name = repo.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{name}/issues/{issue_number}/comments"
    body = {
        "body": f"🤖 Auto-fix: started\n\nBranch will be `fix/issue-{issue_number}`. I will open a PR when ready."  # keep short
    }
    r = requests.post(url, headers=gh_headers(token), json=body, timeout=30)
    r.raise_for_status()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    args = ap.parse_args()

    token = read_token()
    issue = find_next_issue(token, args.repo)

    if not issue:
        print(json.dumps({"status": "no_work"}))
        return

    # Persist and comment started
    CURRENT_ISSUE_PATH.write_text(json.dumps(issue, ensure_ascii=False, indent=2), encoding="utf-8")
    comment_started(token, issue["repo"], int(issue["issue_number"]))

    issue["status"] = "started"
    print(json.dumps(issue, ensure_ascii=False))


if __name__ == "__main__":
    main()
