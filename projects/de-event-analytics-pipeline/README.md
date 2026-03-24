# DE Event Analytics Pipeline (Postgres + Docker)

A **CV-ready Data Engineering project**: ingest raw e-commerce events into Postgres, transform into analytics marts, and run data quality checks.

## What this project demonstrates
- **ELT workflow**: raw → staging → marts
- **Postgres** schema design (dimensions + facts)
- **Data quality checks**: nulls, duplicates, referential integrity, freshness
- **Reproducible local environment** with Docker Compose

## Architecture (high level)
- `docker-compose.yml`: Postgres
- `src/ingest/`: load CSV → `raw.events`
- `src/transform/`: build marts (SQL)
- `src/quality/`: run checks (SQL)

## Quickstart
### 0) Requirements
- Docker Desktop
- Python 3.10+

### 1) Start Postgres
```bash
make up
```

### 2) Create tables + load sample data
```bash
make ingest
```

### 3) Build marts
```bash
make transform
```

### 4) Run quality checks
```bash
make quality
```

## Output tables
- `stg.users`
- `stg.events`
- `marts.fact_purchases`
- `marts.daily_kpis`

## Notes
This repo is structured to support **daily commits** (small, meaningful increments). See `docs/weekly-plan.md`.
