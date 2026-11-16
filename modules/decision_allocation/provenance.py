"""
modules/decision_allocation/provenance.py — "Why this recommendation?" for a decision allocation.

Records, for an allocation result: which component produced it (the deterministic model),
where each of the eight inputs came from (knowledge-graph rule, reference case, user, or an
assumption), which inputs drove each score, what is uncertain, and where a person must act.
Used by the Decision Allocation agent and by the /api/allocation endpoints.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional

from core.provenance import (
    AgentContribution,
    Basis,
    CheckpointKind,
    Gap,
    Ledger,
    SourceKind,
    Verification,
    summarise,
)

AGENT_ID = "allocation"
APPROVER = "Accountable approver (set by the organisation)"

# Where an axis value came from -> the provenance source kind.
_AXIS_SOURCE = {
    "graph-rule": SourceKind.KNOWLEDGE_GRAPH,
    "default": SourceKind.ASSUMPTION,
    "description": SourceKind.USER_INPUT,
    "reference": SourceKind.ENGINEERING_RECORD,
    "user": SourceKind.USER_INPUT,
}

_MEANING = {
    "AI_LED": "AI may take the decision under human oversight",
    "AI_SUPPORTED": "AI prepares the assessment and a person decides",
    "HUMAN_LED": "a person leads the decision; AI assists",
}


def _axis_origin(axis: Mapping) -> str:
    if axis.get("reference") and axis.get("selected") == (axis.get("reference") or {}).get("value"):
        return "reference"
    suggested = axis.get("suggested") or {}
    if suggested and axis.get("selected") == suggested.get("value"):
        return suggested.get("source") or "graph-rule"
    return "user"


def record_allocation(assessment: Mapping, ledger: Ledger, c: AgentContribution,
                      subject_case: Optional[str] = None) -> None:
    """Write the allocation's findings, evidence, gaps and checkpoints into the ledger and contribution."""
    result = assessment["result"]
    axes: List[Mapping] = assessment.get("axes") or [
        {"axis_id": d_axis, "axis": d_axis, "selected": v, "selected_name": v} for d_axis, v in result["selection"].items()
    ]
    subject = assessment.get("subject") or {}
    case_id = subject_case or subject.get("case_id")

    model_ev = ledger.cite(SourceKind.COMPUTATIONAL_MODEL, f"Model:decision-allocation-v{result['model_version']}",
                           f"Decision-allocation model v{result['model_version']}",
                           "P. P. Atiwadkar, MSc thesis, Cranfield University (2026): weights, thresholds, factor matrix, rule")

    # Inputs: one evidence item and one finding per axis, with its origin.
    axis_ev: Dict[str, str] = {}
    low_conf: List[str] = []
    for a in axes:
        origin = _axis_origin(a)
        suggested = a.get("suggested") or {}
        source = _AXIS_SOURCE.get(origin, SourceKind.USER_INPUT)
        if origin == "reference" and case_id:
            ref = f"ReferenceCase:{case_id}:{a['axis_id']}"
            detail = f"reference characterisation for {case_id} ({(a.get('reference') or {}).get('status') or 'reference'})"
        else:
            ref = f"Characterisation:{a['axis_id']}"
            detail = suggested.get("evidence") or ("entered or changed by the user" if origin == "user" else "")
        axis_ev[a["axis_id"]] = ledger.cite(source, ref, f"{a['axis_id']} {a.get('axis')}: {a.get('selected_name')}", detail)
        confidence = suggested.get("confidence") if origin not in ("reference", "user") else None
        if confidence == "low":
            low_conf.append(f"{a['axis_id']} {a.get('axis')}")
        c.findings.append(ledger.finding(
            AGENT_ID, f"{a['axis_id']} {a.get('axis')} = {a.get('selected_name')}.",
            Basis.RULE if origin == "graph-rule" else Basis.DETERMINISTIC if origin == "reference" else
            Basis.RULE if origin == "default" else Basis.DETERMINISTIC,
            [axis_ev[a["axis_id"]]], confidence=confidence, verification=Verification.NOT_APPLICABLE,
            note={"graph-rule": "Suggested by a transparent rule over knowledge-graph facts.",
                  "default": "No data: a default was assumed.",
                  "description": "Read from the change description.",
                  "reference": "Taken from the reference characterisation.",
                  "user": "Set by the person assessing the change."}.get(origin, "")))
        if origin == "default":
            c.gaps.append(Gap("assumption", AGENT_ID, f"{a['axis_id']} {a.get('axis')}: {suggested.get('evidence') or 'assumed'}"))

    # Scores: which inputs drove each dimension.
    for d in result["dimensions"]:
        drivers = [axis_ev[x["axis_id"]] for x in d["contributions"] if x["axis_id"] in axis_ev]
        c.findings.append(ledger.finding(
            AGENT_ID, f"{d['name']} {d['score']:g} of {d['max']:g} is {d['level']} (margin {d['margin']:.2f} to the nearest boundary).",
            Basis.DETERMINISTIC, [model_ev, *drivers], verification=Verification.NOT_APPLICABLE,
            note="Reproducible: the same inputs always give the same score."))

    # The recommendation itself.
    alloc = result["allocation"]
    c.findings.append(ledger.finding(
        AGENT_ID, f"Recommended allocation: {result['allocation_label']} (signature {result['signature']}). {result['reasons'][-1]}",
        Basis.DETERMINISTIC, [model_ev, *axis_ev.values()], verification=Verification.NOT_APPLICABLE,
        note="Computed by the fixed model; no language model takes part in the scoring."))

    # Uncertainty and sensitivity, from signals the engine already produces.
    c.gaps.append(Gap("uncertainty", AGENT_ID, "The model's weights and thresholds are not yet empirically calibrated."))
    if (assessment.get("characterisation_status") or "").startswith("reconstructed"):
        c.gaps.append(Gap("uncertainty", AGENT_ID, "The reference characterisation is reconstructed from published scores "
                                                   "and awaits confirmation by the model's author."))
    flips = result.get("flips") or []
    if flips:
        axes_flip = sorted({f"{f['axis_id']} {f['axis']}" for f in flips})
        c.gaps.append(Gap("uncertainty", AGENT_ID, f"Changing any one of these inputs alone would change the recommendation: "
                                                   f"{', '.join(axes_flip)}."))
    if assessment.get("graph_status") == "unavailable":
        c.gaps.append(Gap("missing", AGENT_ID, "The knowledge graph was unavailable: inputs could not be suggested from it."))

    # Where people must act.
    if low_conf:
        ledger.checkpoint(CheckpointKind.VERIFICATION, f"Confirm the low-confidence inputs: {', '.join(low_conf)}.",
                          "These values were suggested with little supporting data.", "Engineer assessing the change", AGENT_ID)
    ledger.checkpoint(
        CheckpointKind.APPROVAL, "Approve or reject the change.",
        f"The recommendation is that {_MEANING.get(alloc, 'the decision is allocated as shown')}. "
        "A decision allocation is not decision authority: the organisation's delegated approver decides.",
        APPROVER, AGENT_ID)
    c.summary = f"{result['allocation_label']}, signature {result['signature']}."


def allocation_provenance(assessment: Mapping) -> Dict:
    """Stand-alone 'Why this recommendation?' payload for an allocation (one contributing component)."""
    ledger = Ledger()
    c = AgentContribution(
        agent=AGENT_ID, name="Decision Allocation model", pattern="specialist", stage=1, basis=Basis.DETERMINISTIC,
        role="Recommends whether the decision should be AI-led, AI-supported or human-led.",
        components=["core.allocation.engine.score", "modules.decision_allocation.characteriser.suggest"],
        sources=[SourceKind.COMPUTATIONAL_MODEL, SourceKind.KNOWLEDGE_GRAPH, SourceKind.ASSUMPTION],
    )
    record_allocation(assessment, ledger, c)
    return summarise([c], ledger)
