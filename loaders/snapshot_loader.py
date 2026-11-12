"""
loaders/snapshot_loader.py — load the canonical FCC knowledge graph into Neo4j.

Source of truth: data/graph/fcc_graph.json (190 nodes, 311 relationships, 10 MoCs).

The load is ADDITIVE and repeatable:
  * nodes are MERGEd on their domain key (moc_id, asset_id, wo_id, ...);
  * on an existing node, properties already in the database win — only missing ones are added;
  * relationships are MERGEd on (start, type, end);
  * nothing is ever deleted.

Usage:
    python -m loaders.snapshot_loader --dry-run     # report what would change
    python -m loaders.snapshot_loader --apply       # write to the database in .env
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

GRAPH_FILE = Path(__file__).resolve().parents[1] / "data" / "graph" / "fcc_graph.json"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    """Labels, relationship types and key names are interpolated into Cypher, so they must be plain identifiers."""
    if not _IDENT.match(name):
        raise ValueError(f"Unsafe identifier in graph file: {name!r}")
    return name


def load_graph_file(path: Path = GRAPH_FILE) -> Dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    keys = doc["keys"]
    seen = set()
    for n in doc["nodes"]:
        ident = (n["label"], n["key"])
        if n["label"] not in keys:
            raise ValueError(f"Node label {n['label']} has no key property declared under 'keys'.")
        if ident in seen:
            raise ValueError(f"Duplicate node {ident} in {path}.")
        seen.add(ident)
    for r in doc["relationships"]:
        for end in ("from", "to"):
            if tuple(r[end]) not in seen:
                raise ValueError(f"Relationship {r['type']} points at missing node {r[end]}.")
    return doc


def _nodes_by_label(doc: Dict) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = defaultdict(list)
    for n in doc["nodes"]:
        out[n["label"]].append(n)
    return out


def _rels_by_shape(doc: Dict) -> Dict[Tuple[str, str, str], List[Dict]]:
    out: Dict[Tuple[str, str, str], List[Dict]] = defaultdict(list)
    for r in doc["relationships"]:
        out[(r["from"][0], r["type"], r["to"][0])].append(r)
    return out


def plan(client, doc: Dict) -> Dict:
    """Compare the file with the database without writing."""
    keys = doc["keys"]
    nodes_new: Dict[str, int] = {}
    nodes_existing: Dict[str, int] = {}
    for label, nodes in _nodes_by_label(doc).items():
        key_prop = _ident(keys[label])
        rows = client._run(f"MATCH (n:`{_ident(label)}`) RETURN n.`{key_prop}` AS k")
        present = {r["k"] for r in rows}
        wanted = {n["key"] for n in nodes}
        nodes_new[label] = len(wanted - present)
        nodes_existing[label] = len(wanted & present)
    rels_new: Dict[str, int] = defaultdict(int)
    rels_existing: Dict[str, int] = defaultdict(int)
    for (from_label, rel_type, to_label), rels in _rels_by_shape(doc).items():
        a_key, b_key = _ident(keys[from_label]), _ident(keys[to_label])
        rows = client._run(
            f"MATCH (a:`{_ident(from_label)}`)-[:`{_ident(rel_type)}`]->(b:`{_ident(to_label)}`) "
            f"RETURN a.`{a_key}` AS a, b.`{b_key}` AS b"
        )
        present = {(r["a"], r["b"]) for r in rows}
        for r in rels:
            if (r["from"][1], r["to"][1]) in present:
                rels_existing[rel_type] += 1
            else:
                rels_new[rel_type] += 1
    return {
        "nodes_to_create": {k: v for k, v in sorted(nodes_new.items()) if v},
        "nodes_already_present": sum(nodes_existing.values()),
        "relationships_to_create": dict(sorted(rels_new.items())),
        "relationships_already_present": sum(rels_existing.values()),
        "totals": {"nodes_to_create": sum(nodes_new.values()), "relationships_to_create": sum(rels_new.values())},
    }


def apply(client, doc: Dict) -> Dict:
    """Write the file into the database (additive; existing property values are kept)."""
    keys = doc["keys"]
    for label, nodes in _nodes_by_label(doc).items():
        key_prop = _ident(keys[label])
        rows = [{"key": n["key"], "props": {**n["props"], "id": n["key"]}} for n in nodes]
        client._run(
            f"UNWIND $rows AS row "
            f"MERGE (n:`{_ident(label)}` {{`{key_prop}`: row.key}}) "
            f"WITH n, row, properties(n) AS existing "
            f"SET n += row.props "          # add everything from the file ...
            f"SET n += existing",           # ... then restore whatever the database already had
            {"rows": rows},
        )
    for (from_label, rel_type, to_label), rels in _rels_by_shape(doc).items():
        a_key, b_key = _ident(keys[from_label]), _ident(keys[to_label])
        rows = [{"a": r["from"][1], "b": r["to"][1], "props": r.get("props") or {}} for r in rels]
        client._run(
            f"UNWIND $rows AS row "
            f"MATCH (a:`{_ident(from_label)}` {{`{a_key}`: row.a}}), (b:`{_ident(to_label)}` {{`{b_key}`: row.b}}) "
            f"MERGE (a)-[r:`{_ident(rel_type)}`]->(b) "
            f"WITH r, row, properties(r) AS existing "
            f"SET r += row.props SET r += existing",
            {"rows": rows},
        )
    counts = client._run("MATCH (n) RETURN count(n) AS nodes")[0]["nodes"]
    rel_counts = client._run("MATCH ()-[r]->() RETURN count(r) AS rels")[0]["rels"]
    mocs = client._run("MATCH (m:MoC) RETURN count(m) AS c")[0]["c"]
    return {"nodes_in_database": counts, "relationships_in_database": rel_counts, "mocs": mocs}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load data/graph/fcc_graph.json into Neo4j (additive).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="report what would be created; write nothing")
    mode.add_argument("--apply", action="store_true", help="write to the database configured in .env")
    args = parser.parse_args()

    from core.neo4j_client import (
        Neo4jClient,  # imported late so --help works without a database
    )

    doc = load_graph_file()
    client = Neo4jClient()
    report = plan(client, doc)
    print(json.dumps({"file": {"nodes": len(doc["nodes"]), "relationships": len(doc["relationships"])}, "plan": report}, indent=2))
    if args.apply:
        print(json.dumps({"applied": apply(client, doc)}, indent=2))
        print(json.dumps({"remaining": plan(client, doc)["totals"]}, indent=2))


if __name__ == "__main__":
    main()
