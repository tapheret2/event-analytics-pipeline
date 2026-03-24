.PHONY: up down logs ingest transform quality psql

PY=python

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

ingest:
	$(PY) -m pip install -q -r requirements.txt
	$(PY) src/ingest/setup_and_load.py

transform:
	$(PY) -m pip install -q -r requirements.txt
	$(PY) src/transform/run_sql.py src/transform/build_marts.sql

quality:
	$(PY) -m pip install -q -r requirements.txt
	$(PY) src/quality/run_checks.py

psql:
	docker exec -it de_event_postgres psql -U de -d analytics
