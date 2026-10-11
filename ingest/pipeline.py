"""
Run dlt load into Snowflake BRONZE schema.

Usage (from repo root):
  python -m ingest.pipeline
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import dlt

from ingest.sources.full_graph_export import full_graph_export_source
from ingest.sources.moc_domain import moc_domain_source


def _snowflake_credentials() -> dict:
    password = os.getenv("SNOWFLAKE_PASSWORD")
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "").strip() or None
    creds = {
        "host": os.getenv("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT"),
        "username": os.getenv("SNOWFLAKE_USER", "YOUR_SNOWFLAKE_USER"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "MOC_DEV"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "MOC_WH"),
        "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    }
    if password:
        creds["password"] = password
    elif authenticator:
        creds["authenticator"] = authenticator
    else:
        creds["authenticator"] = "externalbrowser"
    return creds


def run() -> None:
    dataset = os.getenv("SNOWFLAKE_BRONZE_SCHEMA", "BRONZE")
    destination = dlt.destinations.snowflake(
        credentials=_snowflake_credentials(),
        # Keep schema name as BRONZE (do not lowercase)
        enable_dataset_name_normalization=False,
    )
    pipeline = dlt.pipeline(
        pipeline_name="moc_bronze",
        destination=destination,
        dataset_name=dataset,
    )
    load_info = pipeline.run([moc_domain_source(), full_graph_export_source()])
    print(load_info)


if __name__ == "__main__":
    run()
