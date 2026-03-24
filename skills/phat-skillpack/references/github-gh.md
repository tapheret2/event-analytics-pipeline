# GitHub via gh CLI — notes

Rule: always specify `--repo owner/repo` when not inside the git repo.

## PRs / CI
- Checks: `gh pr checks <pr-number> --repo owner/repo`
- Runs list: `gh run list --repo owner/repo --limit 10`
- Run view: `gh run view <run-id> --repo owner/repo`
- Failed logs: `gh run view <run-id> --repo owner/repo --log-failed`

## gh api (advanced)
- `gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'`

## JSON output
- `gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'`

Source: https://clawhub.ai/steipete/github
