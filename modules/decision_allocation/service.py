"""
modules/decision_allocation/service.py — from a change to a recommended Human–AI allocation.

    change (existing MoC or proposal)
      -> impact assessment from the knowledge graph      (graph_store)
      -> suggested eight-axis characterisation + evidence (characteriser)
      -> a person confirms or overrides                   (API client)
      -> deterministic scoring and explanation            (core.allocation.engine)

The engine never depends on the graph: if Neo4j is unavailable, scoring and the ten
reference cases still work and the response says `graph_status: "unavailable"`.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Mapping, Optional

from core.allocation import analysis
from core.allocation.engine import score
from core.allocation.model import AllocationModel, default_model
from core.allocation.reference_cases import (
    compare_all,
    reference_case_for_moc,
    source_note,
)

from . import graph_store
from .characteriser import (
    ChangeFacts,
    Suggestion,
    facts_from_moc,
    facts_from_proposal,
    suggest,
)

log = logging.getLogger(__name__)


class NotFound(LookupError):
    """The requested MoC or asset does not exist."""


class DecisionAllocationService:
    def __init__(self, client_factory: Optional[Callable[[], object]] = None,
                 model: Optional[AllocationModel] = None):
        self._client_factory = client_factory
        self._model = model or default_model()
        self._enumeration: Optional[Dict] = None

    # ── graph access ────────────────────────────────────────────────────────────────────────────
    def _client(self):
        if self._client_factory is None:
            from core.neo4j_client import (
                Neo4jClient,  # imported late: scoring needs no database
            )
            self._client_factory = Neo4jClient
        return self._client_factory()

    def _try_graph(self, fn: Callable, *args):
        """Run a graph read; return (value, 'ok') or (None, 'unavailable') without raising."""
        try:
            return fn(self._client(), *args), "ok"
        except Exception as exc:                                # noqa: BLE001 — degrade, never fail scoring
            log.warning("Knowledge graph unavailable for %s: %s", getattr(fn, "__name__", fn), exc)
            return None, "unavailable"

    # ── model and engine ────────────────────────────────────────────────────────────────────────
    def model(self) -> Dict:
        return self._model.to_dict()

    def score(self, selection: Mapping[str, str]) -> Dict:
        return score(selection, self._model).to_dict()

    def enumeration(self) -> Dict:
        if self._enumeration is None:
            self._enumeration = analysis.enumerate_space(self._model)
        return self._enumeration

    def reference_cases(self) -> Dict:
        rows = compare_all(self._model)
        for row in rows:
            row["rule_agreement"] = None
        records = {}
        graph_status = "ok"
        for row in rows:
            record, status = self._try_graph(graph_store.get_moc_facts, row["moc_id"])
            if status != "ok":
                graph_status = status
                break
            records[row["moc_id"]] = record
        if graph_status == "ok":
            for row in rows:
                record = records.get(row["moc_id"])
                if not record:
                    continue
                suggestions = suggest(facts_from_moc(record))
                differing = [a for a, s in suggestions.items() if s.value != row["selection"][a]]
                row["rule_agreement"] = {"agreeing_axes": 8 - len(differing), "differing_axes": differing}
        matched = sum(1 for r in rows if r["matches"])
        return {**source_note(), "cases": rows, "reproduced": matched, "total": len(rows),
                "graph_status": graph_status, "model_version": self._model.version}

    # ── assessments ─────────────────────────────────────────────────────────────────────────────
    def list_mocs(self) -> Dict:
        rows, status = self._try_graph(graph_store.list_mocs)
        return {"mocs": rows or [], "graph_status": status}

    def assess_moc(self, moc_id: str) -> Dict:
        moc_id = (moc_id or "").strip()
        reference = reference_case_for_moc(moc_id)
        record, status = self._try_graph(graph_store.get_moc_facts, moc_id)
        if status == "ok" and record is None and reference is None:
            raise NotFound(f"MoC {moc_id} not found.")
        if status != "ok" and reference is None:
            raise NotFound(f"MoC {moc_id} is not a reference case and the knowledge graph is unavailable.")

        suggestions: Dict[str, Suggestion] = {}
        impact = None
        facts: Optional[ChangeFacts] = None
        stored = None
        if record:
            asset_id = (record.get("asset") or {}).get("asset_id")
            reach, _ = self._try_graph(graph_store.get_reach, asset_id) if asset_id else (None, status)
            asset_record, _ = self._try_graph(graph_store.get_asset_facts, asset_id) if asset_id else (None, status)
            facts = facts_from_moc(record, reach)
            suggestions = suggest(facts)
            impact = _impact_assessment(facts, record, asset_record, reach)
            stored, _ = self._try_graph(graph_store.get_stored_characterisation, moc_id)

        # Which characterisation is in force: the one stored in the graph, else the reference file, else the suggestion.
        if stored:
            confirmed, confirmed_status, confirmed_source = stored["selection"], stored.get("status"), "knowledge-graph"
        elif reference:
            confirmed, confirmed_status, confirmed_source = dict(reference.selection), reference.status, "reference-file"
        else:
            confirmed, confirmed_status, confirmed_source = None, None, None
        selection = confirmed or {a: s.value for a, s in suggestions.items()}

        title = (record or {}).get("moc", {}).get("title") if record else (reference.title if reference else "")
        return {
            "subject": {"kind": "moc", "moc_id": moc_id, "title": title or (reference.title if reference else ""),
                        "case_id": reference.case_id if reference else None,
                        "asset_id": facts.asset_id if facts else None,
                        "change_type": facts.change_type if facts else None,
                        "description": facts.description if facts else None},
            "impact_assessment": impact,
            "axes": self._axes(suggestions, confirmed, confirmed_status, confirmed_source, selection),
            "selection": selection,
            "characterisation_status": confirmed_status or "suggested",
            "result": self.score(selection),
            "graph_status": status,
        }

    def assess_change(self, change_type: str, asset_id: Optional[str], description: str,
                      hazop_required: Optional[bool] = None, pssr_required: Optional[bool] = None,
                      shutdown_required: Optional[bool] = None) -> Dict:
        asset_id = (asset_id or "").strip() or None
        asset_record, status = (self._try_graph(graph_store.get_asset_facts, asset_id) if asset_id else (None, "ok"))
        if asset_id and status == "ok" and asset_record is None:
            raise NotFound(f"Asset {asset_id} not found.")
        reach, _ = self._try_graph(graph_store.get_reach, asset_id) if (asset_id and status == "ok") else (None, status)
        facts = facts_from_proposal(change_type, asset_id, description, asset_record, reach,
                                    hazop_required, pssr_required, shutdown_required)
        suggestions = suggest(facts)
        selection = {a: s.value for a, s in suggestions.items()}
        return {
            "subject": {"kind": "proposed", "moc_id": None, "title": "Proposed change", "case_id": None,
                        "asset_id": asset_id, "change_type": change_type, "description": description},
            "impact_assessment": _impact_assessment(facts, None, asset_record, reach),
            "axes": self._axes(suggestions, None, None, None, selection),
            "selection": selection,
            "characterisation_status": "suggested",
            "result": self.score(selection),
            "graph_status": status,
        }

    def graph(self, moc_id: str) -> Dict:
        data, status = self._try_graph(graph_store.get_allocation_subgraph, moc_id)
        return {**(data or {"nodes": [], "links": []}), "graph_status": status}

    # ── helpers ─────────────────────────────────────────────────────────────────────────────────
    def _axes(self, suggestions: Dict[str, Suggestion], confirmed: Optional[Mapping[str, str]],
              confirmed_status: Optional[str], confirmed_source: Optional[str],
              selection: Mapping[str, str]) -> List[Dict]:
        out = []
        for axis in self._model.axes:
            s = suggestions.get(axis.id)
            suggested = None
            if s:
                suggested = {**s.to_dict(), "name": axis.category(s.value).name}
            reference = None
            if confirmed:
                value = confirmed[axis.id]
                reference = {"value": value, "name": axis.category(value).name,
                             "status": confirmed_status, "source": confirmed_source}
            out.append({
                "axis_id": axis.id, "axis": axis.name, "hint": axis.hint,
                "selected": selection[axis.id], "selected_name": axis.category(selection[axis.id]).name,
                "suggested": suggested, "reference": reference,
                "agrees": (suggested["value"] == reference["value"]) if (suggested and reference) else None,
            })
        return out


def _impact_assessment(facts: ChangeFacts, record: Optional[Dict], asset_record: Optional[Dict],
                       reach: Optional[Dict]) -> Dict:
    """The dependency and safety picture the characterisation is drawn from."""
    assessments = [r for r in ((record or {}).get("risk_assessments") or []) if r]
    ra = assessments[0] if assessments else {}
    return {
        "asset": {"asset_id": facts.asset_id, "equipment_type": facts.equipment_type or None,
                  "criticality": facts.criticality, "areas": facts.areas,
                  "esd_target": bool((asset_record or {}).get("esd_target"))},
        "reach": {
            "available": reach is not None,
            "assets_affected": (reach or {}).get("asset_count"),
            "areas_reached": (reach or {}).get("areas") or [],
            "critical_assets": (reach or {}).get("critical_assets") or [],
            "direct": (reach or {}).get("direct") or [],
            "assets": ((reach or {}).get("assets") or [])[:12],
        },
        "safety": {"hazop_required": facts.hazop_required, "pssr_required": facts.pssr_required,
                   "shutdown_required": facts.shutdown_required},
        "risk_assessment": ({"category": ra.get("risk_category"), "overall_score": ra.get("overall_score"),
                             "likelihood": ra.get("likelihood")} if ra else None),
        "parameter": ({"old": facts.parameter_old, "new": facts.parameter_new, "threshold": facts.parameter_threshold}
                      if (facts.parameter_old or facts.parameter_new) else None),
        "documents": {"pid_refs": facts.pid_refs},
        "history": {"mocs_on_asset": (asset_record or {}).get("mocs") or [],
                    "incidents_on_asset": (asset_record or {}).get("incidents"),
                    "incidents_on_moc": (record or {}).get("incidents") if record else None,
                    "work_types": (record or {}).get("work_types") if record else None},
    }
