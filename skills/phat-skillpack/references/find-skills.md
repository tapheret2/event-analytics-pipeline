# find-skills (Skills CLI) — notes

Use to discover/install skills from the ecosystem.

## Typical flow

1) Clarify need (domain + task keywords).
2) Search:

- `npx skills find <query>`

3) Present 1–5 options with:
- what it does
- install command
- link

4) Install when user confirms:

- `npx skills add <owner/repo@skill> -g -y`

## Search tips
- Use specific queries (e.g., `react performance`, `pr review`, `changelog`).
- Try synonyms (deploy/deployment/ci-cd).

Source: https://clawhub.ai/JimLiuxinghai/find-skills
