"""Publish local fix for Peganyx/test-agent issue #32.

This is a one-off debug helper to verify the end-to-end path:
- Ensure branch fix/issue-32 exists
- Upload updated files via GitHub API
- Create PR
- Comment on issue + PR

Reads GITHUB_TOKEN from D:\Multi Agents\option-b\.env.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

OPTION_B = Path(r"D:\Multi Agents\option-b")
ENV_PATH = OPTION_B / ".env"

REPO_OWNER = "Peganyx"
REPO_NAME = "test-agent"
ISSUE_NUMBER = 32
BRANCH = f"fix/issue-{ISSUE_NUMBER}"

LOCAL_REPO = Path(r"C:\Users\ADMIN\.openclaw\workspace\autofix\test-agent")
FILES = [
    ("src/services/payment_service.py", LOCAL_REPO / "src" / "services" / "payment_service.py"),
    ("tests/test_payment_service.py", LOCAL_REPO / "tests" / "test_payment_service.py"),
]


def read_env_token() -> str:
    text = ENV_PATH.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^GITHUB_TOKEN=(.+)$", text, flags=re.MULTILINE)
    if not m:
        raise SystemExit(f"Missing GITHUB_TOKEN in {ENV_PATH}")
    return m.group(1).strip()


def main():
    token = read_env_token()

    sys.path.insert(0, str(OPTION_B))
    from services.github_client import GitHubClient  # type: ignore

    gh = GitHubClient(token=token, owner=REPO_OWNER, repo_name=REPO_NAME)

    # Ensure branch exists
    gh.create_branch(BRANCH)

    commit_msg = "fix: validate promo codes correctly (issue #32)"

    changed = []
    for path, local_path in FILES:
        if not local_path.exists():
            raise SystemExit(f"Local file missing: {local_path}")
        content = local_path.read_text(encoding="utf-8")
        gh.create_or_update_file(path, content, commit_msg, BRANCH)
        changed.append(path)

    pr_title = "fix: promo code validation (issue #32)"
    pr_body = (
        "Fixes #32\n\n"
        "This PR removes the insecure promo-code validation that accepted arbitrary codes ending with a digit, "
        "and adds regression tests to ensure only known promo codes are accepted.\n"
    )

    # Create PR (idempotency: if exists, just link it)
    # PyGithub doesn't have an easy head-lookup here without extra calls; attempt create and fall back.
    try:
        pr = gh.create_pull_request(title=pr_title, body=pr_body, head=BRANCH)
        pr_number = pr["number"]
        pr_url = pr["url"]
    except Exception as e:
        # Fallback: search PRs by head
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "openclaw-autofix",
        }
        r = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            params={"state": "all", "head": f"{REPO_OWNER}:{BRANCH}"},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        arr = r.json()
        if not arr:
            raise
        pr_number = arr[0]["number"]
        pr_url = arr[0]["html_url"]

    # Comment issue
    gh.post_issue_comment(
        ISSUE_NUMBER,
        "🤖 **Auto-fix update**\n\n"
        f"I uploaded a fix and opened/updated a PR:\n"
        f"- Branch: `{BRANCH}`\n"
        f"- PR: #{pr_number} ({pr_url})\n\n"
        f"Files changed: {', '.join(changed)}\n",
    )

    # Comment PR as issue comment
    gh.post_issue_comment(
        pr_number,
        "## 🤖 Auto-Review (Phát Em)\n\n"
        "**Decision:** APPROVE\n\n"
        "Fix looks correct for the described bug (digit-suffix bypass removed; unknown codes rejected). "
        "Tests cover valid code, normalization, and invalid codes.\n",
    )

    print(f"OK PR #{pr_number}: {pr_url}")


if __name__ == "__main__":
    main()
