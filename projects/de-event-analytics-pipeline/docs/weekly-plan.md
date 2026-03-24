# Weekly plan (daily commits)

Goal: 1 week = 1 CV-ready project, with daily meaningful commits.

## Day 1 — Scaffold
- Repo structure, Docker Compose, README
- Define tables + sample dataset

## Day 2 — Ingest
- Create `raw.events` table
- Load sample CSV

## Day 3 — Transform
- Build `stg.*` tables
- Build `marts.daily_kpis`

## Day 4 — Quality
- Add checks: null/dup/FK/freshness
- Fail-fast quality runner

## Day 5 — Orchestration
- Add `Makefile` targets
- Add simple schedule notes (cron) + logging

## Day 6 — Polish
- Architecture diagram + screenshots
- CV bullets in README

## Day 7 — Buffer
- Fix issues, improve robustness
