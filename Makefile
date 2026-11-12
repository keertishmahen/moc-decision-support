.PHONY: help check test lint docs frontend-check api web graph-plan graph-load-canonical allocation-load \
        snowflake-bootstrap dlt-bronze dbt-build pipeline graph-load

# Code written since v3.0 is held to the stricter lint level.
STRICT_PATHS = core/allocation core/llm core/allocation_lookup.py modules/decision_allocation api/routes api/errors.py \
               loaders/snapshot_loader.py loaders/allocation_loader.py scripts/generate_docs.py \
               tests/allocation tests/api tests/llm tests/modules tests/structure tests/file_graph.py

help:
	@echo "Everyday:"
	@echo "  check                 lint + tests + docs check + frontend type-check (what CI runs)"
	@echo "  test                  offline test suite (no database, no OpenAI)"
	@echo "  lint                  ruff: base rules everywhere, strict rules on new code"
	@echo "  docs                  regenerate docs/generated/ (graph schema needs the live graph)"
	@echo "  api / web             run the backend on :8000 / the frontend on :5173"
	@echo "Knowledge graph:"
	@echo "  graph-plan            dry-run: what loading data/graph/fcc_graph.json would change"
	@echo "  graph-load-canonical  load data/graph/fcc_graph.json (additive)"
	@echo "  allocation-load       project the decision-allocation model into the graph"
	@echo "Legacy Snowflake pipeline:"
	@echo "  snowflake-bootstrap, dlt-bronze, dbt-build, graph-load, pipeline"

check: lint test frontend-check
	python scripts/generate_docs.py --check

test:
	python -m pytest tests

lint:
	python -m ruff check api core modules loaders tests scripts/generate_docs.py
	python -m ruff check $(STRICT_PATHS) --select E,F,W,B,I

docs:
	python scripts/generate_docs.py --api --graph

frontend-check:
	cd frontend && npm run build

api:
	uvicorn api.main:app --reload --port 8000

web:
	cd frontend && npm run dev

graph-plan:
	python -m loaders.snapshot_loader --dry-run
	python -m loaders.allocation_loader --dry-run

graph-load-canonical:
	python -m loaders.snapshot_loader --apply

allocation-load:
	python -m loaders.allocation_loader --apply

# ── Legacy Snowflake -> dbt -> Neo4j pipeline (not needed to run the application) ──────────────
snowflake-bootstrap:
	python scripts/bootstrap_snowflake.py

dlt-bronze:
	python -m ingest.pipeline

dbt-build:
	cd dbt_moc && dbt build --profiles-dir .

graph-load:
	python -m loaders.graph_loader

pipeline: snowflake-bootstrap dlt-bronze dbt-build graph-load
