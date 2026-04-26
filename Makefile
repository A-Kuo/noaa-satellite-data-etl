.DEFAULT_GOAL := help
COMPOSE  := docker compose
DBT      := cd dbt && dbt
SPARK    := docker compose exec spark-master spark-submit \
            --master spark://spark-master:7077 \
            --packages org.postgresql:postgresql:42.7.3

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}' | sort

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------
.PHONY: up down logs ps

up: ## Start all services (postgres, airflow, spark)
	$(COMPOSE) up -d

down: ## Stop and remove containers
	$(COMPOSE) down

logs: ## Tail all service logs
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
.PHONY: db-init db-shell

db-init: ## Apply SQL schema to the PostGIS warehouse
	$(COMPOSE) exec postgres psql -U postgres -d noaa_dw \
	  -f /docker-entrypoint-initdb.d/001_create_tables.sql \
	  -f /docker-entrypoint-initdb.d/002_create_indexes.sql

db-shell: ## Open a psql session to the warehouse
	$(COMPOSE) exec postgres psql -U postgres -d noaa_dw

# ---------------------------------------------------------------------------
# ETL pipeline
# ---------------------------------------------------------------------------
.PHONY: ingest

ingest: ## Run ingestion for EVENT_ID (usage: make ingest EVENT_ID=2024_hurricane_helene)
	python scripts/run_etl.py $(EVENT_ID)

# ---------------------------------------------------------------------------
# dbt
# ---------------------------------------------------------------------------
.PHONY: dbt-deps dbt-run dbt-test dbt-docs dbt-full

dbt-deps: ## Install dbt packages
	$(DBT) deps

dbt-run: ## Run all dbt models
	$(DBT) run

dbt-test: ## Run dbt schema + data tests
	$(DBT) test

dbt-docs: ## Generate and serve dbt documentation
	$(DBT) docs generate && $(DBT) docs serve

dbt-full: dbt-deps dbt-run dbt-test ## deps → run → test in one step

# ---------------------------------------------------------------------------
# Spark
# ---------------------------------------------------------------------------
.PHONY: spark-coverage spark-raster

spark-coverage: ## Run PySpark coverage aggregator (OUTPUT=/path/to/parquet)
	$(SPARK) /opt/spark/jobs/coverage_aggregator.py \
	  --output $(or $(OUTPUT),/data/coverage_stats)

spark-raster: ## Run PySpark raster metadata extractor (STAGING=/path/to/tifs)
	$(SPARK) /opt/spark/jobs/raster_metadata.py \
	  --staging-path $(or $(STAGING),/data/staging) \
	  --output /data/raster_metadata

# ---------------------------------------------------------------------------
# Airflow
# ---------------------------------------------------------------------------
.PHONY: af-unpause-all af-trigger-ingest

af-unpause-all: ## Unpause all DAGs
	$(COMPOSE) exec airflow-scheduler airflow dags unpause noaa_ingest
	$(COMPOSE) exec airflow-scheduler airflow dags unpause dbt_transform

af-trigger-ingest: ## Manually trigger the NOAA ingest DAG
	$(COMPOSE) exec airflow-scheduler \
	  airflow dags trigger noaa_ingest

# ---------------------------------------------------------------------------
# Dev
# ---------------------------------------------------------------------------
.PHONY: install lint typecheck test

install: ## Install Python package in editable mode with dev extras
	pip install -e ".[dev]"

lint: ## Run ruff linter
	ruff check src tests

typecheck: ## Run mypy
	mypy src

test: ## Run pytest
	pytest
