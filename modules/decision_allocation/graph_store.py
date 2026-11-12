"""
modules/decision_allocation/graph_store.py — knowledge-graph reads for decision allocation.

Read-only. Every function takes a client exposing `_run(query, params) -> list[dict]`
(core.neo4j_client.Neo4jClient in production, a fake in tests) and returns plain,
JSON-safe data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _plain(value: Any) -> Any:
    """Neo4j temporal and other driver types become strings so results are JSON-safe."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    return str(value)


def list_mocs(client) -> List[Dict]:
    rows = client._run(
        "MATCH (m:MoC) OPTIONAL MATCH (m)-[:TARGETS]->(a:Asset) "
        "OPTIONAL MATCH (m)-[:HAS_CHARACTERISATION]->(dc:DecisionCharacterisation) "
        "RETURN m.moc_id AS moc_id, m.title AS title, m.change_type AS change_type, a.asset_id AS asset_id, "
        "dc.allocation AS allocation, dc.allocation_label AS allocation_label, dc.signature AS signature "
        "ORDER BY moc_id"
    )
    return _plain(rows)


def get_moc_facts(client, moc_id: str) -> Optional[Dict]:
    """Everything the characteriser needs about an existing MoC, in one round trip."""
    rows = client._run(
        """
        MATCH (m:MoC {moc_id: $moc_id})
        OPTIONAL MATCH (m)-[:TARGETS]->(a:Asset)
        OPTIONAL MATCH (m)-[:LOCATED_IN]->(area:Area)
        OPTIONAL MATCH (m)-[:REFERENCES_PID]->(pid:PIDDocument)
        OPTIONAL MATCH (m)-[:CHANGES_PARAMETER]->(p:Parameter)
        OPTIONAL MATCH (m)-[:REQUIRES]->(ra:RiskAssessment)
        OPTIONAL MATCH (m)-[:GENERATES]->(wo:WorkOrder)
        OPTIONAL MATCH (m)-[:APPROVED_BY]->(per:Personnel)
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        OPTIONAL MATCH (m)-[:IMPACTS]->(imp:Asset)
        RETURN properties(m) AS moc, properties(a) AS asset,
               collect(DISTINCT area.area_id) AS areas,
               collect(DISTINCT pid.pid_ref) AS pid_refs,
               collect(DISTINCT properties(p)) AS parameters,
               collect(DISTINCT properties(ra)) AS risk_assessments,
               collect(DISTINCT wo.work_type) AS work_types,
               collect(DISTINCT per.role) AS approver_roles,
               count(DISTINCT i) AS incidents,
               collect(DISTINCT imp.asset_id) AS declared_impacts
        """,
        {"moc_id": moc_id},
    )
    return _plain(rows[0]) if rows else None


def get_asset_facts(client, asset_id: str) -> Optional[Dict]:
    rows = client._run(
        """
        MATCH (a:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (a)-[:BELONGS_TO]->(area:Area)
        OPTIONAL MATCH (esd:Asset)-[:SHUTS_DOWN]->(a)
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(a)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        RETURN properties(a) AS asset, collect(DISTINCT area.area_id) AS areas,
               count(DISTINCT esd) > 0 AS esd_target,
               collect(DISTINCT m.moc_id) AS mocs, count(DISTINCT h) AS hazards, count(DISTINCT i) AS incidents
        """,
        {"asset_id": asset_id},
    )
    return _plain(rows[0]) if rows else None


def get_reach(client, asset_id: str, max_hops: int = 4) -> Dict:
    """Distinct assets and areas reachable downstream of an asset (each asset counted once, at its nearest hop)."""
    hops = max(1, min(int(max_hops), 6))
    rows = client._run(
        f"""
        MATCH path = (a:Asset {{asset_id: $asset_id}})
              -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|FEEDS|CONNECTS|CIRCULATES_TO*1..{hops}]->(b:Asset)
        WHERE b.asset_id <> $asset_id
        WITH b, min(length(path)) AS hops
        OPTIONAL MATCH (b)-[:BELONGS_TO]->(area:Area)
        RETURN b.asset_id AS asset_id, b.equipment_type AS equipment_type, b.criticality AS criticality,
               hops, area.area_id AS area
        ORDER BY hops, criticality DESC, asset_id
        """,
        {"asset_id": asset_id},
    )
    rows = _plain(rows)
    return {
        "assets": rows,
        "asset_count": len(rows),
        "areas": sorted({r["area"] for r in rows if r.get("area")}),
        "critical_assets": [r["asset_id"] for r in rows if (r.get("criticality") or 0) >= 5],
        "direct": [r["asset_id"] for r in rows if r["hops"] == 1],
    }


def get_stored_characterisation(client, moc_id: str) -> Optional[Dict]:
    rows = client._run(
        """
        MATCH (m:MoC {moc_id: $moc_id})-[:HAS_CHARACTERISATION]->(dc:DecisionCharacterisation)
        OPTIONAL MATCH (dc)-[:SELECTS]->(c:AxisCategory)
        RETURN properties(dc) AS dc, collect(c.category_id) AS categories
        """,
        {"moc_id": moc_id},
    )
    if not rows:
        return None
    row = _plain(rows[0])
    selection = dict(c.split(".", 1) for c in row["categories"])
    return {"selection": selection, "status": row["dc"].get("status"), "source": row["dc"].get("source"),
            "model_version": row["dc"].get("model_version"), "signature": row["dc"].get("signature"),
            "allocation": row["dc"].get("allocation"), "updated_at": row["dc"].get("updated_at")}


def get_allocation_subgraph(client, moc_id: str) -> Dict:
    """Nodes and links around one MoC's decision characterisation, for graph display."""
    rows = client._run(
        """
        MATCH (m:MoC {moc_id: $moc_id})-[:HAS_CHARACTERISATION]->(dc:DecisionCharacterisation)
        OPTIONAL MATCH (dc)-[:SELECTS]->(c:AxisCategory)<-[:HAS_CATEGORY]-(ax:CharacterisationAxis)
        OPTIONAL MATCH (dc)-[:RECOMMENDS]->(mode:AllocationMode)
        OPTIONAL MATCH (dc)-[:ESCALATED_BY]->(d:Dimension)
        RETURN m.moc_id AS moc_id, m.title AS title, dc.char_id AS char_id, dc.signature AS signature,
               collect(DISTINCT {id: c.category_id, name: c.name, axis: ax.name}) AS categories,
               mode.mode_id AS mode_id, mode.name AS mode_name,
               collect(DISTINCT {id: d.dim_id, name: d.name}) AS escalated
        """,
        {"moc_id": moc_id},
    )
    if not rows:
        return {"nodes": [], "links": []}
    r = _plain(rows[0])
    nodes = [
        {"id": r["moc_id"], "label": r["moc_id"], "type": "MoC", "detail": r.get("title") or ""},
        {"id": r["char_id"], "label": f"Characterisation {r['signature']}", "type": "DecisionCharacterisation",
         "detail": f"Signature {r['signature']}"},
    ]
    links = [{"source": r["moc_id"], "target": r["char_id"], "label": "HAS_CHARACTERISATION"}]
    for c in r["categories"]:
        if c.get("id"):
            nodes.append({"id": c["id"], "label": c["name"], "type": "AxisCategory", "detail": c.get("axis") or ""})
            links.append({"source": r["char_id"], "target": c["id"], "label": "SELECTS"})
    if r.get("mode_id"):
        nodes.append({"id": r["mode_id"], "label": r["mode_name"], "type": "AllocationMode", "detail": "Recommended allocation"})
        links.append({"source": r["char_id"], "target": r["mode_id"], "label": "RECOMMENDS"})
    for d in r["escalated"]:
        if d.get("id"):
            nodes.append({"id": f"DIM-{d['id']}", "label": d["name"], "type": "Dimension", "detail": "Reaches factor III"})
            links.append({"source": r["char_id"], "target": f"DIM-{d['id']}", "label": "ESCALATED_BY"})
    return {"nodes": nodes, "links": links}
