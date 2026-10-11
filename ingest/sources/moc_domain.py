"""dlt source resources built from seed_neo4j domain data (Phase 1 bootstrap)."""
from __future__ import annotations

from typing import Any, Iterator

import dlt

# Import seed dicts without connecting to Neo4j
from core.seed_neo4j import (
    AREAS,
    ASSETS,
    DEPENDENCIES,
    MOCS,
    PLANT,
    PROCESS_UNIT,
    WORK_ORDERS,
)


@dlt.resource(name="raw_plant", write_disposition="replace", primary_key="id")
def plant() -> Iterator[dict[str, Any]]:
    yield dict(PLANT)


@dlt.resource(name="raw_process_unit", write_disposition="replace", primary_key="id")
def process_unit() -> Iterator[dict[str, Any]]:
    yield dict(PROCESS_UNIT)


@dlt.resource(name="raw_area", write_disposition="replace", primary_key="id")
def areas() -> Iterator[dict[str, Any]]:
    for row in AREAS:
        yield dict(row)


@dlt.resource(name="raw_asset", write_disposition="replace", primary_key="id")
def assets() -> Iterator[dict[str, Any]]:
    for row in ASSETS:
        # Canonical key for app: asset_id (= id)
        out = dict(row)
        out["asset_id"] = out["id"]
        yield out


@dlt.resource(name="raw_dependency", write_disposition="replace")
def dependencies() -> Iterator[dict[str, Any]]:
    for upstream, downstream in DEPENDENCIES:
        yield {
            "upstream_asset_id": upstream,
            "downstream_asset_id": downstream,
        }


@dlt.resource(name="raw_moc", write_disposition="replace", primary_key="id")
def mocs() -> Iterator[dict[str, Any]]:
    for row in MOCS:
        out = dict(row)
        # Flatten work_orders list for warehouse friendliness
        wos = out.pop("work_orders", []) or []
        out["work_order_ids"] = ",".join(wos)
        out["moc_id"] = out["id"]
        yield out


@dlt.resource(name="raw_work_order", write_disposition="replace", primary_key="id")
def work_orders() -> Iterator[dict[str, Any]]:
    for row in WORK_ORDERS:
        out = dict(row)
        out["wo_id"] = out["id"]
        yield out


@dlt.resource(name="raw_hazard", write_disposition="replace", primary_key="moc_id")
def hazards() -> Iterator[dict[str, Any]]:
    for row in MOCS:
        yield {
            "moc_id": row["id"],
            "asset_id": row["asset_id"],
            "hazard_description": row.get("hazard_description", ""),
            "risk_level": row.get("risk_level"),
            "overall_risk_score": row.get("overall_risk_score"),
            "risk_people": row.get("risk_people"),
            "risk_asset": row.get("risk_asset"),
            "risk_community": row.get("risk_community"),
            "risk_env": row.get("risk_env"),
            "risk_likelihood": row.get("risk_likelihood"),
        }


@dlt.source(name="moc_domain")
def moc_domain_source():
    return [
        plant(),
        process_unit(),
        areas(),
        assets(),
        dependencies(),
        mocs(),
        work_orders(),
        hazards(),
    ]
