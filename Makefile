.PHONY: snowflake-bootstrap dlt-bronze dbt-build pipeline graph-load help

help:
	@echo "Targets:"
	@echo "  snowflake-bootstrap  Create MOC_WH + MOC_DEV + BRONZE/SILVER/GOLD"
	@echo "  dlt-bronze           Load seed data into Snowflake BRONZE"
	@echo "  dbt-build            Run dbt build (SILVER + GOLD marts)"
	@echo "  graph-load           Load GOLD graph marts into Neo4j"
	@echo "  pipeline             bootstrap → dlt → dbt → graph-load"

snowflake-bootstrap:
	python scripts/bootstrap_snowflake.py

dlt-bronze:
	python -m ingest.pipeline

dbt-build:
	cd dbt_moc && dbt build --profiles-dir .

graph-load:
	python -m loaders.graph_loader

pipeline: snowflake-bootstrap dlt-bronze dbt-build graph-load
