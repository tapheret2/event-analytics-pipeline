---
name: phat-skillpack
description: Meta-skillbook for everyday agent ops: discover/install skills (skills CLI), security vet skills before installing, summarize URLs/files/YouTube via summarize CLI, automate websites via agent-browser, use Google services via gog (Gmail/Calendar/Drive/Sheets/Docs), and use GitHub via gh CLI. Use when the user asks to find a skill, vet a skill, summarize content, browse/automate a site, work with Google Workspace, or operate GitHub PRs/actions/issues.
---

# Phát Skillpack (cheatsheets)

Keep this skill lean: use the reference pages below as your “how to run it” memory.

## References (read as needed)

- Skill discovery/install: `references/find-skills.md`
- Skill security vetting: `references/skill-vetter.md`
- Summarize CLI (URLs/files/YouTube): `references/summarize.md`
- Browser automation (agent-browser CLI): `references/agent-browser.md`
- Google Workspace via gog CLI: `references/gog.md`
- GitHub via gh CLI: `references/github-gh.md`
- Self-improvement logging loop: `references/self-improving-agent.md`

## Default operating rules

1. **Vetting first**: before installing/running any unknown skill or script, follow `references/skill-vetter.md`.
2. **Prefer structured output**: when available, use `--json` + `--jq` for stable parsing.
3. **Ask before sensitive actions**: sending email, creating calendar events, changing repos, or anything that could leak data.
4. **After navigation, re-snapshot** (browser automation): refs change after navigation.
5. **Log learnings** when something breaks or the user corrects you: see `references/self-improving-agent.md`.
