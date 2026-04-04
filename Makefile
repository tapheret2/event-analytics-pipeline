# =============================================================================
# Event Analytics Pipeline - Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

.PHONY: help up down restart logs generate test lint clean format dbt-run dbt-test

# Default target
help: ## Show this help message
	@echo "Event Analytics Pipeline - Available Commands:"
	@echo "================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Docker ---
up: ## Start all services
	docker compose up -d --build
	@echo "✅ Services started!"
	@echo "   Airflow:   http://localhost:8080"
	@echo "   Streamlit: http://localhost:8501"
	@echo "   Postgres:  localhost:5432"

down: ## Stop all services
	docker compose down
	@echo "✅ Services stopped!"

restart: down up ## Restart all services

logs: ## View service logs (use: make logs service=airflow)
	docker compose logs -f $(service)

ps: ## Show running services
	docker compose ps

# --- Data ---
generate: ## Generate sample event data
	python scripts/generate_events.py --days 30 --users 1000
	@echo "✅ Sample data generated!"

# --- dbt ---
dbt-run: ## Run dbt models
	cd dbt && dbt run --profiles-dir .
	@echo "✅ dbt models built!"

dbt-test: ## Run dbt tests
	cd dbt && dbt test --profiles-dir .

dbt-docs: ## Generate and serve dbt docs
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

# --- Testing ---
test: ## Run all tests
	pytest tests/ -v --tb=short
	@echo "✅ All tests passed!"

# --- Code Quality ---
lint: ## Run linters
	ruff check scripts/ dags/ tests/ streamlit_app/
	@echo "✅ Linting passed!"

format: ## Format code
	black scripts/ dags/ tests/ streamlit_app/
	ruff check --fix scripts/ dags/ tests/ streamlit_app/
	@echo "✅ Code formatted!"

# --- Cleanup ---
clean: ## Remove all containers, volumes, and generated data
	docker compose down -v --remove-orphans
	rm -rf data/bronze/* data/silver/* data/gold/*
	rm -rf dbt/target/ dbt/dbt_packages/ dbt/logs/
	rm -rf logs/ __pycache__/ .pytest_cache/
	@echo "✅ Cleaned up!"

# --- Setup ---
setup: ## Initial project setup
	cp -n .env.example .env 2>/dev/null || true
	pip install -r requirements.txt
	pre-commit install
	mkdir -p data/bronze data/silver data/gold docs/images
	@echo "✅ Project setup complete!"
