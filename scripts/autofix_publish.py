"""autofix_publish.py

Publish local workspace changes to GitHub via API, then open/update PR and comment.

This helper is meant to be called by an agent/cron run after it has created local file edits.

Inputs:
  --repo Peganyx/test-agent
  --issue 32
  --branch fix/issue-32
  --base main
  --commit-message "fix: ..."
  --pr-title "fix: ... (#32)"
  --pr-body-file path/to/pr_body.md
  --files "src/a.py=...\n" (repeatable) or --file-map-json

Auth:
  - Reads GITHUB_TOKEN from env, or from option-b .env at D:\Multi Agents\option-b\.env

Notes:
  - Idempotent: if PR already exists for head branch, it reuses it.
  - Does NOT use git; uses GitHub contents API via PyGithub (GitHubClient).
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

OPTION_B_ENV = Path(r"D:\Multi Agents\option-b\.env")


def read_token() -> str:
    if os.getenv("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()
    if OPTION_B_ENV.exists():
        text = OPTION_B_ENV.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^GITHUB_TOKEN=(.+)$", text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    raise SystemExit("Missing GITHUB_TOKEN (env or option-b .env)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--issue", type=int, required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--base", default="main")
    ap.add_argument("--commit-message", required=True)
    ap.add_argument("--pr-title", required=True)
    ap.add_argument("--pr-body-file", required=True)
    ap.add_argument(
        "--file-map-json",
        required=True,
        help="JSON dict {repoPath: localPath} for files to upload. If value starts with @, reads JSON from that file.",
    )
    args = ap.parse_args()

    token = read_token()
    owner, name = args.repo.split("/", 1)

    # Import GitHubClient from option-b
    import sys

    sys.path.insert(0, str(Path(r"D:\Multi Agents\option-b")))
    from services.github_client import GitHubClient  # type: ignore

    gh = GitHubClient(token=token, owner=owner, repo_name=name)

    gh.create_branch(args.branch, base=args.base)

    fm = args.file_map_json
    if fm.startswith("@"):
        fm = Path(fm[1:]).read_text(encoding="utf-8")
    file_map = json.loads(fm)
    changed = []
    for repo_path, local_path in file_map.items():
        lp = Path(local_path)
        if not lp.exists():
            raise SystemExit(f"Missing local file: {lp}")
        content = lp.read_text(encoding="utf-8")
        gh.create_or_update_file(repo_path, content, args.commit_message, args.branch)
        changed.append(repo_path)

    pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")

    pr_number = None
    pr_url = None
    try:
        pr = gh.create_pull_request(title=args.pr_title, body=pr_body, head=args.branch, base=args.base)
        pr_number = pr["number"]
        pr_url = pr["url"]
    except Exception:
        # Reuse existing PR via REST
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "openclaw-autofix",
        }
        r = requests.get(
            f"https://api.github.com/repos/{owner}/{name}/pulls",
            params={"state": "all", "head": f"{owner}:{args.branch}"},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        arr = r.json()
        if not arr:
            raise
        pr_number = arr[0]["number"]
        pr_url = arr[0]["html_url"]

    # Comment issue with PR link
    gh.post_issue_comment(
        args.issue,
        "🤖 **Auto-fix update**\n\n"
        f"Branch: `{args.branch}`\n"
        f"PR: #{pr_number} ({pr_url})\n\n"
        f"Files changed: {', '.join(changed)}",
    )

    print(json.dumps({"pr_number": pr_number, "pr_url": pr_url, "changed": changed}))


if __name__ == "__main__":
    main()
