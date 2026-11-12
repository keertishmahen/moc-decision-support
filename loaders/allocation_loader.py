"""
loaders/allocation_loader.py — project the decision-allocation model into the knowledge graph.

Source of truth: core/allocation/config/*.json. This loader writes a PROJECTION of it:

    (:AllocationModel)-[:DEFINES_AXIS]->(:CharacterisationAxis)-[:HAS_CATEGORY]->(:AxisCategory)
    (:AxisCategory)-[:CONTRIBUTES_TO {weight}]->(:Dimension)<-[:SCORES]-(:AllocationModel)
    (:MoC)-[:HAS_CHARACTERISATION]->(:DecisionCharacterisation)
    (:DecisionCharacterisation)-[:SELECTS]->(:AxisCategory)            x8
    (:DecisionCharacterisation)-[:RECOMMENDS]->(:AllocationMode)
    (:DecisionCharacterisation)-[:ESCALATED_BY]->(:Dimension)          dimensions at factor III
    (:DecisionCharacterisation)-[:EVALUATED_WITH]->(:AllocationModel)

Repeatable. It only touches nodes and relationships of the allocation layer; the
relationships it owns are rebuilt on each run so a changed model or characterisation
never leaves stale edges behind. MoC, Asset and the other domain nodes are not modified.

Usage:
    python -m loaders.allocation_loader --dry-run
    python -m loaders.allocation_loader --apply
"""
from __future__ import annotations

import argparse
import datetime
import json
from typing import Dict, List

from core.allocation.engine import score
from core.allocation.model import AllocationModel, default_model
from core.allocation.reference_cases import reference_cases
from core.allocation.types import DIMENSION_IDS, FACTOR_DIMENSION_IDS, Allocation

SOURCE = "thesis-table-2-reconstruction"


def category_node_id(axis_id: str, category_id: str) -> str:
    return f"{axis_id}.{category_id}"


def characterisation_id(moc_id: str) -> str:
    return f"DC-{moc_id}"


def build_projection(model: AllocationModel = None, today: str = None) -> Dict:
    """Everything the loader will write, as plain data (also used by tests and --dry-run)."""
    model = model or default_model()
    today = today or datetime.date.today().isoformat()
    axes = [{"axis_id": a.id, "name": a.name, "hint": a.hint, "order": i + 1} for i, a in enumerate(model.axes)]
    categories, contributions = [], []
    for a in model.axes:
        for i, c in enumerate(a.categories):
            node_id = category_node_id(a.id, c.id)
            categories.append({"category_id": node_id, "axis_id": a.id, "code": c.id, "name": c.name, "order": i + 1})
            for d in DIMENSION_IDS:
                if c.weight(d) > 0:
                    contributions.append({"category_id": node_id, "dim_id": d, "weight": c.weight(d)})
    dimensions = []
    for d in model.dimensions:
        lo, hi = model.boundaries(d.id)
        dimensions.append({"dim_id": d.id, "name": d.name, "definition": d.definition, "max": model.column_max(d.id),
                           "low": d.low, "high": d.high, "low_boundary": round(lo, 3), "high_boundary": round(hi, 3)})
    modes = [{"mode_id": a.value, "name": a.label} for a in Allocation]

    characterisations: List[Dict] = []
    for case in reference_cases():
        r = score(case.selection, model, with_flips=False)
        props = {
            "char_id": characterisation_id(case.moc_id), "name": f"{case.moc_id}: {r.allocation.label}",
            "moc_id": case.moc_id, "case_id": case.case_id, "status": case.status, "source": SOURCE,
            "model_version": model.version, "signature": r.signature,
            "allocation": r.allocation.value, "allocation_label": r.allocation.label, "updated_at": today,
        }
        for d in DIMENSION_IDS:
            name = model.dimension(d).name.lower()
            props[f"{name}_score"] = r.dimensions[d].score
            props[f"{name}_level"] = r.dimensions[d].level.value
        for d in FACTOR_DIMENSION_IDS:
            props[f"{model.dimension(d).name.lower()}_factor"] = r.factors[d].factor.value
        characterisations.append({
            "props": props, "moc_id": case.moc_id,
            "selects": [category_node_id(axis_id, cat) for axis_id, cat in r.selection.items()],
            "escalated_by": list(r.escalated_by), "mode_id": r.allocation.value,
        })
    return {
        "model": {"model_id": model.model_id, "name": f"Decision allocation model v{model.version}",
                  "version": model.version, "title": model.title,
                  "author": model.attribution.get("author", ""), "work": model.attribution.get("work", ""),
                  "rule_id": model.rule_id, "rule_text": model.rule_text, "space_size": model.space_size,
                  "updated_at": today},
        "axes": axes, "categories": categories, "contributions": contributions,
        "dimensions": dimensions, "modes": modes, "characterisations": characterisations,
    }


def summary(p: Dict) -> Dict:
    return {
        "nodes": {"AllocationModel": 1, "CharacterisationAxis": len(p["axes"]), "AxisCategory": len(p["categories"]),
                  "Dimension": len(p["dimensions"]), "AllocationMode": len(p["modes"]),
                  "DecisionCharacterisation": len(p["characterisations"])},
        "relationships": {
            "DEFINES_AXIS": len(p["axes"]), "SCORES": len(p["dimensions"]), "HAS_CATEGORY": len(p["categories"]),
            "CONTRIBUTES_TO": len(p["contributions"]), "HAS_CHARACTERISATION": len(p["characterisations"]),
            "SELECTS": sum(len(c["selects"]) for c in p["characterisations"]),
            "RECOMMENDS": len(p["characterisations"]), "EVALUATED_WITH": len(p["characterisations"]),
            "ESCALATED_BY": sum(len(c["escalated_by"]) for c in p["characterisations"]),
        },
    }


def apply(client, p: Dict) -> Dict:
    run = client._run
    run("MERGE (m:AllocationModel {model_id: $m.model_id}) SET m += $m", {"m": p["model"]})
    run("UNWIND $rows AS row MERGE (d:Dimension {dim_id: row.dim_id}) SET d += row", {"rows": p["dimensions"]})
    run("UNWIND $rows AS row MERGE (a:AllocationMode {mode_id: row.mode_id}) SET a += row", {"rows": p["modes"]})
    run("UNWIND $rows AS row MERGE (a:CharacterisationAxis {axis_id: row.axis_id}) SET a += row", {"rows": p["axes"]})
    run("UNWIND $rows AS row MERGE (c:AxisCategory {category_id: row.category_id}) SET c += row", {"rows": p["categories"]})

    model_id = p["model"]["model_id"]
    run("MATCH (m:AllocationModel {model_id: $id}), (a:CharacterisationAxis) MERGE (m)-[:DEFINES_AXIS]->(a)", {"id": model_id})
    run("MATCH (m:AllocationModel {model_id: $id}), (d:Dimension) MERGE (m)-[:SCORES]->(d)", {"id": model_id})
    run("UNWIND $rows AS row MATCH (a:CharacterisationAxis {axis_id: row.axis_id}), (c:AxisCategory {category_id: row.category_id}) "
        "MERGE (a)-[:HAS_CATEGORY]->(c)", {"rows": p["categories"]})

    # Weights: rebuilt so a weight changed to zero does not linger.
    run("MATCH (:AxisCategory)-[r:CONTRIBUTES_TO]->(:Dimension) DELETE r")
    run("UNWIND $rows AS row MATCH (c:AxisCategory {category_id: row.category_id}), (d:Dimension {dim_id: row.dim_id}) "
        "MERGE (c)-[r:CONTRIBUTES_TO]->(d) SET r.weight = row.weight", {"rows": p["contributions"]})

    missing = []
    for c in p["characterisations"]:
        found = run("MATCH (m:MoC {moc_id: $moc_id}) RETURN count(m) AS c", {"moc_id": c["moc_id"]})[0]["c"]
        if not found:
            missing.append(c["moc_id"])
            continue
        run("MERGE (dc:DecisionCharacterisation {char_id: $props.char_id}) SET dc += $props "
            "WITH dc MATCH (m:MoC {moc_id: $moc_id}) MERGE (m)-[:HAS_CHARACTERISATION]->(dc)",
            {"props": c["props"], "moc_id": c["moc_id"]})
        run("MATCH (dc:DecisionCharacterisation {char_id: $id})-[r:SELECTS|RECOMMENDS|ESCALATED_BY|EVALUATED_WITH]->() DELETE r",
            {"id": c["props"]["char_id"]})
        run("MATCH (dc:DecisionCharacterisation {char_id: $id}) UNWIND $cats AS cat "
            "MATCH (c:AxisCategory {category_id: cat}) MERGE (dc)-[:SELECTS]->(c)",
            {"id": c["props"]["char_id"], "cats": c["selects"]})
        run("MATCH (dc:DecisionCharacterisation {char_id: $id}), (a:AllocationMode {mode_id: $mode}) MERGE (dc)-[:RECOMMENDS]->(a)",
            {"id": c["props"]["char_id"], "mode": c["mode_id"]})
        run("MATCH (dc:DecisionCharacterisation {char_id: $id}), (m:AllocationModel {model_id: $model}) MERGE (dc)-[:EVALUATED_WITH]->(m)",
            {"id": c["props"]["char_id"], "model": model_id})
        if c["escalated_by"]:
            run("MATCH (dc:DecisionCharacterisation {char_id: $id}) UNWIND $dims AS dim "
                "MATCH (d:Dimension {dim_id: dim}) MERGE (dc)-[:ESCALATED_BY]->(d)",
                {"id": c["props"]["char_id"], "dims": c["escalated_by"]})
    return {"mocs_missing_from_graph": missing, "verification": verify(client)}


def verify(client) -> Dict:
    """Check the projection in the database against a fresh engine run."""
    rows = client._run(
        "MATCH (m:MoC)-[:HAS_CHARACTERISATION]->(dc:DecisionCharacterisation) "
        "OPTIONAL MATCH (dc)-[:SELECTS]->(c:AxisCategory) "
        "WITH m, dc, collect(c.category_id) AS cats "
        "OPTIONAL MATCH (dc)-[:RECOMMENDS]->(mode:AllocationMode) "
        "RETURN m.moc_id AS moc_id, dc.signature AS signature, dc.allocation AS allocation, cats, mode.mode_id AS mode "
        "ORDER BY moc_id"
    )
    problems = []
    for r in rows:
        selection = dict(c.split(".", 1) for c in r["cats"])
        if len(selection) != 8:
            problems.append(f"{r['moc_id']}: selects {len(selection)} categories, expected 8")
            continue
        fresh = score(selection, with_flips=False)
        if fresh.signature != r["signature"] or fresh.allocation.value != r["allocation"] or r["mode"] != r["allocation"]:
            problems.append(f"{r['moc_id']}: stored {r['signature']}/{r['allocation']} differs from engine "
                            f"{fresh.signature}/{fresh.allocation.value}")
    weights = client._run("MATCH (:AxisCategory)-[r:CONTRIBUTES_TO]->(:Dimension) RETURN count(r) AS c")[0]["c"]
    return {"characterisations": len(rows), "contributes_to_edges": weights, "problems": problems}


def main() -> None:
    parser = argparse.ArgumentParser(description="Project the decision-allocation model into Neo4j.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    projection = build_projection()
    print(json.dumps({"will_write": summary(projection)}, indent=2))
    if args.apply:
        from core.neo4j_client import Neo4jClient
        print(json.dumps({"applied": apply(Neo4jClient(), projection)}, indent=2))


if __name__ == "__main__":
    main()
