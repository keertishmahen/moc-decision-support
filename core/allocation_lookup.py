"""
core/allocation_lookup.py — the decision allocation of an MoC, for MoCBot and the agent.

Reads the characterisation stored in the knowledge graph (falling back to the reference
file), then lets the deterministic engine in core.allocation compute the allocation.
The chat models only REPORT this result; they never decide it.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.allocation.engine import score
from core.allocation.reference_cases import reference_case_for_moc
from core.allocation.types import DIMENSION_IDS

log = logging.getLogger(__name__)


def _stored_selection(client: Any, moc_id: str) -> Optional[Dict[str, Any]]:
    rows = client._run(
        "MATCH (m:MoC {moc_id: $moc_id})-[:HAS_CHARACTERISATION]->(dc:DecisionCharacterisation) "
        "OPTIONAL MATCH (dc)-[:SELECTS]->(c:AxisCategory) "
        "RETURN dc.status AS status, collect(c.category_id) AS categories",
        {"moc_id": moc_id},
    )
    if not rows or len(rows[0]["categories"]) != 8:
        return None
    return {"selection": dict(c.split(".", 1) for c in rows[0]["categories"]), "status": rows[0]["status"]}


def allocation_summary(client: Any, moc_id: str) -> Dict[str, Any]:
    """Compact, JSON-safe allocation result for one MoC, or an {"error": ...} dict."""
    moc_id = (moc_id or "").strip()
    stored = None
    try:
        stored = _stored_selection(client, moc_id)
    except Exception as exc:                                        # noqa: BLE001 — fall back to the reference file
        log.warning("Could not read stored characterisation for %s: %s", moc_id, exc)
    if stored is None:
        reference = reference_case_for_moc(moc_id)
        if reference is None:
            return {"error": f"No decision characterisation is recorded for {moc_id}."}
        stored = {"selection": dict(reference.selection), "status": reference.status}

    result = score(stored["selection"], with_flips=False)
    return {
        "moc_id": moc_id,
        "allocation": result.allocation.label,
        "signature_risk_complexity_uncertainty": result.signature,
        "scores": {result.dimensions[d].name: result.dimensions[d].score for d in DIMENSION_IDS},
        "levels": {result.dimensions[d].name: result.dimensions[d].level.value for d in DIMENSION_IDS},
        "escalated_by": [result.dimensions[d].name for d in result.escalated_by],
        "reasons": list(result.reasons),
        "characterisation_status": stored["status"],
        "model_version": result.model_version,
        "note": "Computed by a fixed scoring model (not an AI judgement). The characterisation is "
                "a reconstruction pending expert confirmation.",
    }


def allocation_summary_text(client: Any, moc_id: str) -> str:
    """The same result as a context block for a chat prompt."""
    s = allocation_summary(client, moc_id)
    if "error" in s:
        return f"DECISION ALLOCATION ({moc_id}): {s['error']}"
    scores = ", ".join(f"{k} {v:g} ({s['levels'][k]})" for k, v in s["scores"].items())
    return (
        f"DECISION ALLOCATION ({s['moc_id']}) — deterministic model v{s['model_version']}:\n"
        f"  Recommended allocation: {s['allocation']}\n"
        f"  Signature Risk/Complexity/Uncertainty: {s['signature_risk_complexity_uncertainty']}\n"
        f"  Scores: {scores}\n"
        f"  Why: {s['reasons'][-1]}\n"
        f"  Status: {s['characterisation_status']}. Report this result as given; do not re-derive it."
    )
