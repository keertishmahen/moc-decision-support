"""Load Bloom/Neo4j CSV exports into raw_graph_nodes / raw_graph_edges."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator

import dlt

_ROOT = Path(__file__).resolve().parents[2]
NODE_CSV = _ROOT / "node-export.csv"
REL_CSV = _ROOT / "relationship-export.csv"

_ID_KEYS = (
    "moc_id",
    "asset_id",
    "wo_id",
    "hazard_id",
    "risk_id",
    "ll_id",
    "person_id",
    "incident_id",
    "hazop_id",
    "pssr_id",
    "param_id",
    "fm_id",
    "pid_ref",
    "area_id",
    "dept_id",
    "plant_id",
    "unit_id",
    "stage_id",
    "outcome_id",
    "score_id",
    "activity_id",
    "ma_id",
    "rs_id",
    "id",
)

_SKIP_COLS = {"~id", "~labels", "~start_node_id", "~end_node_id", "~relationship_type"}


def _coerce(value: str) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _business_id(label: str, props: dict[str, Any]) -> str:
    for key in _ID_KEYS:
        val = props.get(key)
        if val not in (None, ""):
            return str(val)
    name = props.get("name")
    if name:
        return str(name)
    return f"{label}:unknown"


def _node_props(row: dict[str, str]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for key, raw in row.items():
        if not key or key in _SKIP_COLS or key.startswith("_"):
            continue
        val = _coerce(raw)
        if val is None:
            continue
        props[key] = val
    return props


def parse_csv_exports(
    node_path: Path | None = None,
    rel_path: Path | None = None,
) -> tuple[list[dict], list[dict]]:
    element_to_node: dict[str, tuple[str, str]] = {}
    node_rows: list[dict] = []

    with (node_path or NODE_CSV).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            element_id = (row.get("~id") or "").strip()
            label = (row.get("~labels") or "").split(":")[0].strip()
            if not element_id or not label:
                continue
            props = _node_props(row)
            nid = _business_id(label, props)
            props.setdefault("id", nid)
            props["element_id"] = element_id
            if label == "MoC":
                props.setdefault("moc_id", nid)
                props.setdefault("name", props.get("title") or nid)
            elif label == "Asset":
                props.setdefault("asset_id", nid)
            elif label == "WorkOrder":
                props.setdefault("wo_id", nid)
                props.setdefault("name", props.get("title") or nid)
                if "planned_duration" not in props and props.get("planned_hrs") is not None:
                    props["planned_duration"] = props["planned_hrs"]
                if "actual_duration" not in props and props.get("actual_hrs") is not None:
                    props["actual_duration"] = props["actual_hrs"]
            elif label == "Hazard":
                props.setdefault("hazard_id", nid)
                props.setdefault("description", props.get("name") or nid)
            elif label == "LessonsLearned":
                props.setdefault("ll_id", nid)
            elif label == "Plant":
                props.setdefault("plant_id", nid)
            element_to_node[element_id] = (nid, label)
            node_rows.append(
                {
                    "node_id": nid,
                    "node_label": label,
                    "properties_json": json.dumps(props, ensure_ascii=False),
                }
            )

    edge_rows: list[dict] = []
    with (rel_path or REL_CSV).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            start_el = (row.get("~start_node_id") or "").strip()
            end_el = (row.get("~end_node_id") or "").strip()
            rel_type = (row.get("~relationship_type") or "").strip()
            if not start_el or not end_el or not rel_type:
                continue
            if start_el not in element_to_node or end_el not in element_to_node:
                continue
            src_id, src_label = element_to_node[start_el]
            dst_id, dst_label = element_to_node[end_el]
            eprops: dict[str, Any] = {}
            for key in ("flow_type", "description"):
                val = _coerce(row.get(key, ""))
                if val is not None:
                    eprops[key] = val
            edge_rows.append(
                {
                    "src_id": src_id,
                    "src_label": src_label,
                    "rel_type": rel_type,
                    "dst_id": dst_id,
                    "dst_label": dst_label,
                    "properties_json": json.dumps(eprops, ensure_ascii=False),
                }
            )

    return node_rows, edge_rows


@dlt.resource(name="raw_graph_nodes", write_disposition="replace")
def graph_nodes() -> Iterator[dict[str, Any]]:
    nodes, _ = parse_csv_exports()
    yield from nodes


@dlt.resource(name="raw_graph_edges", write_disposition="replace")
def graph_edges() -> Iterator[dict[str, Any]]:
    _, edges = parse_csv_exports()
    yield from edges


@dlt.source(name="full_graph_export")
def full_graph_export_source():
    return [graph_nodes(), graph_edges()]
