"""
tests/file_graph.py — an offline stand-in for the knowledge graph, backed by data/graph/fcc_graph.json.

It answers the same questions as modules/decision_allocation/graph_store.py, so the service
and API can be tested without Neo4j.
"""
import json
from collections import defaultdict, deque
from pathlib import Path

GRAPH_FILE = Path(__file__).resolve().parents[1] / "data" / "graph" / "fcc_graph.json"
FLOW = {"UPSTREAM_OF", "DEPENDS_ON", "IMPACTS", "CONTROLS_FLOW_TO", "FEEDS", "CONNECTS", "CIRCULATES_TO"}


class FileGraph:
    def __init__(self):
        doc = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
        self.nodes = {(n["label"], n["key"]): n["props"] for n in doc["nodes"]}
        self.out = defaultdict(list)       # (label, key) -> [(type, (label, key))]
        self.inc = defaultdict(list)
        for r in doc["relationships"]:
            a, b = tuple(r["from"]), tuple(r["to"])
            self.out[a].append((r["type"], b))
            self.inc[b].append((r["type"], a))

    def _targets(self, node, rel_type, label=None):
        return [b for t, b in self.out[node] if t == rel_type and (label is None or b[0] == label)]

    def _sources(self, node, rel_type, label=None):
        return [a for t, a in self.inc[node] if t == rel_type and (label is None or a[0] == label)]

    def list_mocs(self, _client=None):
        rows = []
        for (label, key), props in sorted(self.nodes.items()):
            if label == "MoC":
                asset = self._targets((label, key), "TARGETS", "Asset")
                rows.append({"moc_id": key, "title": props.get("title"), "change_type": props.get("change_type"),
                             "asset_id": asset[0][1] if asset else None, "allocation": None,
                             "allocation_label": None, "signature": None})
        return rows

    def get_moc_facts(self, _client, moc_id):
        node = ("MoC", moc_id)
        if node not in self.nodes:
            return None
        asset = self._targets(node, "TARGETS", "Asset")
        return {
            "moc": dict(self.nodes[node]),
            "asset": dict(self.nodes[asset[0]]) if asset else None,
            "areas": [b[1] for b in self._targets(node, "LOCATED_IN")],
            "pid_refs": [b[1] for b in self._targets(node, "REFERENCES_PID")],
            "parameters": [dict(self.nodes[b]) for b in self._targets(node, "CHANGES_PARAMETER")],
            "risk_assessments": [dict(self.nodes[b]) for b in self._targets(node, "REQUIRES")],
            "work_types": sorted({self.nodes[b].get("work_type") for b in self._targets(node, "GENERATES")}),
            "approver_roles": [self.nodes[b].get("role") for b in self._targets(node, "APPROVED_BY")],
            "incidents": len(self._sources(node, "RELATED_TO", "Incident")),
            "declared_impacts": [b[1] for b in self._targets(node, "IMPACTS")],
        }

    def get_asset_facts(self, _client, asset_id):
        node = ("Asset", asset_id)
        if node not in self.nodes:
            return None
        mocs = self._sources(node, "TARGETS", "MoC")
        return {
            "asset": dict(self.nodes[node]),
            "areas": [b[1] for b in self._targets(node, "BELONGS_TO")],
            "esd_target": bool(self._sources(node, "SHUTS_DOWN")),
            "mocs": sorted(m[1] for m in mocs),
            "hazards": sum(len(self._targets(m, "IDENTIFIES")) for m in mocs),
            "incidents": sum(len(self._sources(m, "RELATED_TO", "Incident")) for m in mocs),
        }

    def get_reach(self, _client, asset_id, max_hops=4):
        start = ("Asset", asset_id)
        hops = {start: 0}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if hops[node] >= max_hops:
                continue
            for rel_type, b in self.out[node]:
                if rel_type in FLOW and b[0] == "Asset" and b not in hops:
                    hops[b] = hops[node] + 1
                    queue.append(b)
        rows = []
        for node, h in hops.items():
            if node == start:
                continue
            props = self.nodes[node]
            area = self._targets(node, "BELONGS_TO")
            rows.append({"asset_id": node[1], "equipment_type": props.get("equipment_type"),
                         "criticality": props.get("criticality"), "hops": h, "area": area[0][1] if area else None})
        rows.sort(key=lambda r: (r["hops"], -(r["criticality"] or 0), r["asset_id"]))
        return {"assets": rows, "asset_count": len(rows),
                "areas": sorted({r["area"] for r in rows if r["area"]}),
                "critical_assets": [r["asset_id"] for r in rows if (r["criticality"] or 0) >= 5],
                "direct": [r["asset_id"] for r in rows if r["hops"] == 1]}

    def get_stored_characterisation(self, _client, moc_id):
        return None

    def get_allocation_subgraph(self, _client, moc_id):
        return {"nodes": [], "links": []}
