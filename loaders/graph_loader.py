"""
loaders/graph_loader.py — Load GOLD.mart_graph_nodes / mart_graph_edges into Neo4j.

Replaces ad-hoc core/seed_neo4j.py for pipeline runs.
Usage: python -m loaders.graph_loader
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from neo4j import GraphDatabase

from core.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from core.neo4j_client import _create_driver, _create_driver_ssc, _session_kwargs
from core.snowflake_client import fetch_all


def _props(properties_json) -> dict:
    if properties_json is None:
        return {}
    if isinstance(properties_json, dict):
        return properties_json
    try:
        return json.loads(properties_json)
    except (TypeError, json.JSONDecodeError):
        return {}


def _neo4j_driver():
    try:
        driver = _create_driver()
        driver.verify_connectivity()
        return driver
    except Exception:
        return _create_driver_ssc()


def load(clear: bool = False) -> None:
    database = os.getenv("SNOWFLAKE_DATABASE", "MOC_DEV")
    gold = os.getenv("SNOWFLAKE_GOLD_SCHEMA", "GOLD")
    nodes = fetch_all(f'select node_id, node_label, properties_json from "{database}"."{gold}".mart_graph_nodes')
    edges = fetch_all(
        f'select src_id, src_label, rel_type, dst_id, dst_label, properties_json '
        f'from "{database}"."{gold}".mart_graph_edges'
    )

    driver = _neo4j_driver()
    try:
        with driver.session(**_session_kwargs()) as session:
            if clear:
                session.run("MATCH (n) DETACH DELETE n")

            for row in nodes:
                label = row["NODE_LABEL"] if "NODE_LABEL" in row else row["node_label"]
                node_id = row.get("NODE_ID", row.get("node_id"))
                props = _props(row.get("PROPERTIES_JSON", row.get("properties_json")))
                props = {k: v for k, v in props.items() if v is not None and not isinstance(v, (dict, list))}
                props.setdefault("id", node_id)
                if label == "Asset" and "asset_id" not in props:
                    props["asset_id"] = node_id
                if label == "MoC" and "moc_id" not in props:
                    props["moc_id"] = node_id
                if label == "MoC" and "actual_manhours" in props and "actual_downtime" not in props:
                    props["actual_downtime"] = props["actual_manhours"]
                cypher = f"MERGE (n:`{label}` {{id: $id}}) SET n += $props"
                session.run(cypher, id=str(node_id), props=props)

            for row in edges:
                src_id = row.get("SRC_ID", row.get("src_id"))
                src_label = row.get("SRC_LABEL", row.get("src_label"))
                rel_type = row.get("REL_TYPE", row.get("rel_type"))
                dst_id = row.get("DST_ID", row.get("dst_id"))
                dst_label = row.get("DST_LABEL", row.get("dst_label"))
                eprops = _props(row.get("PROPERTIES_JSON", row.get("properties_json")))
                eprops = {k: v for k, v in eprops.items() if v is not None and not isinstance(v, (dict, list))}
                cypher = (
                    f"MATCH (a:`{src_label}` {{id: $src}}), (b:`{dst_label}` {{id: $dst}}) "
                    f"MERGE (a)-[r:`{rel_type}`]->(b) SET r += $props"
                )
                session.run(cypher, src=src_id, dst=dst_id, props=eprops)

        print(f"Loaded {len(nodes)} nodes and {len(edges)} edges into Neo4j.")
    finally:
        driver.close()


if __name__ == "__main__":
    load(clear=os.getenv("GRAPH_LOADER_CLEAR", "1") == "1")
