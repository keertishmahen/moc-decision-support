"""
modules/decision_allocation/characteriser.py — suggest the eight axis values from platform data.

Principle: the platform SUGGESTS a characterisation with its evidence; a person confirms
or overrides it; the deterministic engine in core.allocation then allocates.

The rules below are transparent heuristics over facts already in the knowledge graph.
They were fitted to the ten FCC reference cases, so their agreement with those cases is
a consistency check, not a validation. Characterisation is judgement-dependent (thesis
Section 8.2: four practitioners disagreed on five of eight axes for one case), which is
why every suggestion carries a confidence and can be overridden.

No I/O here: `ChangeFacts` in, suggestions out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SOURCE_RULE = "graph-rule"
SOURCE_DEFAULT = "default"
SOURCE_TEXT = "description"

PLANT_WIDE_AREAS = {"AREA-ALL"}
_NUMBER = re.compile(r"^\s*-?\d+(\.\d+)?\s*([^\s\d].*)?$")
_REACTIVE_ACTION = re.compile(r"\b(replace|replacement|repair)\w*", re.I)
_REACTIVE_TEXT = re.compile(r"\b(replace|repair|fail|leak|breakdown|emergency|damag)\w*", re.I)
_LIKE_FOR_LIKE = re.compile(r"like[- ]for[- ]like|replacement[- ]in[- ]kind", re.I)
_TEMPORARY = re.compile(r"\b(temporar|bypass|trial|interim|short[- ]term)\w*", re.I)
_OPEN_ENDED = re.compile(r"until further notice|open[- ]ended|no end date|indefinite", re.I)


@dataclass
class ChangeFacts:
    """What the platform knows about a change. None means 'not known'."""
    kind: str = "proposed"                       # "moc" (existing record) or "proposed"
    moc_id: Optional[str] = None
    title: str = ""
    change_type: str = ""
    action_type: str = ""
    description: str = ""
    asset_id: Optional[str] = None
    equipment_type: str = ""
    criticality: Optional[int] = None            # MoC criticality rating, else the asset's
    areas: List[str] = field(default_factory=list)
    hazop_required: Optional[bool] = None
    pssr_required: Optional[bool] = None
    shutdown_required: Optional[bool] = None
    like_for_like_text: str = ""                 # HAZOP reason / justification text
    parameter_old: Optional[str] = None
    parameter_new: Optional[str] = None
    parameter_threshold: Optional[str] = None
    pid_refs: List[str] = field(default_factory=list)
    esd_target: bool = False
    reach_assets: Optional[int] = None
    reach_areas: List[str] = field(default_factory=list)

    @property
    def plant_wide(self) -> bool:
        return bool(PLANT_WIDE_AREAS & set(self.areas)) or self.equipment_type.lower() == "safety system"

    @property
    def numeric_parameter(self) -> bool:
        return bool(self.parameter_old and self.parameter_new
                    and _NUMBER.match(str(self.parameter_old)) and _NUMBER.match(str(self.parameter_new)))

    @property
    def like_for_like(self) -> bool:
        return bool(_LIKE_FOR_LIKE.search(self.like_for_like_text or "") or _LIKE_FOR_LIKE.search(self.description or ""))

    @property
    def reactive(self) -> bool:
        """Triggered by a failure or defect rather than planned."""
        if self.action_type:
            return bool(_REACTIVE_ACTION.search(self.action_type))
        return bool(_REACTIVE_TEXT.search(self.description or ""))

    @property
    def procedural(self) -> bool:
        return "procedur" in (self.change_type or "").lower()

    @property
    def control_or_parameter_change(self) -> bool:
        t = (self.change_type or "").lower()
        return "instrument" in t or "process" in t or "parameter" in t


@dataclass
class Suggestion:
    axis_id: str
    value: str
    source: str
    confidence: str            # "high" | "medium" | "low"
    evidence: str
    needs_confirmation: bool = True

    def to_dict(self) -> Dict:
        return {"axis_id": self.axis_id, "value": self.value, "source": self.source,
                "confidence": self.confidence, "evidence": self.evidence,
                "needs_confirmation": self.needs_confirmation}


def _yes_no(flag: Optional[bool]) -> str:
    return "not recorded" if flag is None else ("required" if flag else "not required")


def _nature(f: ChangeFacts) -> Suggestion:
    if f.plant_wide:
        return Suggestion("A1", "strategic", SOURCE_RULE, "medium",
                          "The change applies plant-wide (all areas / safety system), so it reaches plant objectives.")
    if f.criticality == 5 and f.control_or_parameter_change:
        return Suggestion("A1", "strategic", SOURCE_RULE, "medium",
                          f"Criticality 5 and a {f.change_type or 'control/parameter'} change: potential for high-consequence failure.")
    if f.hazop_required is False and f.reactive:
        return Suggestion("A1", "operational", SOURCE_RULE, "medium",
                          "Replacement or repair with no HAZOP required: routine, bounded, close to replacement-in-kind.")
    confidence = "medium" if f.hazop_required is not None else "low"
    return Suggestion("A1", "tactical", SOURCE_RULE, confidence,
                      "A modification beyond routine replacement that does not reach plant-wide objectives.")


def _system_level(f: ChangeFacts) -> Suggestion:
    if f.plant_wide:
        return Suggestion("A2", "system", SOURCE_RULE, "high", "Located in all areas / acts on the safety system.")
    if f.criticality == 5:
        return Suggestion("A2", "system", SOURCE_RULE, "medium",
                          f"Target {f.asset_id or 'asset'} has criticality 5: a change here acts on the interacting system.")
    reach = (f" It reaches {f.reach_assets} downstream assets in {len(f.reach_areas)} area(s)."
             if f.reach_assets is not None else "")
    if f.hazop_required is True:
        return Suggestion("A2", "sub_system", SOURCE_RULE, "medium",
                          "HAZOP required and criticality below 5: the change affects a composite of equipment, not the whole unit." + reach)
    if f.hazop_required is False:
        return Suggestion("A2", "unit", SOURCE_RULE, "medium",
                          "No HAZOP required: the change is confined to one piece of equipment." + reach)
    value = "sub_system" if (f.criticality or 0) >= 4 else "unit"
    return Suggestion("A2", value, SOURCE_RULE, "low",
                      f"HAZOP need not recorded; inferred from criticality {f.criticality}." + reach)


def _duration(f: ChangeFacts) -> Suggestion:
    text = f"{f.title} {f.description}"
    if _TEMPORARY.search(text):
        if _OPEN_ENDED.search(text):
            return Suggestion("A3", "undefined_duration", SOURCE_TEXT, "low",
                              "The description reads as temporary with no end date.")
        return Suggestion("A3", "temporary", SOURCE_TEXT, "low", "The description reads as a temporary change.")
    return Suggestion("A3", "permanent", SOURCE_DEFAULT, "low",
                      "The knowledge graph has no duration field; assumed permanent. Confirm, or mark as temporary.")


def _scope(f: ChangeFacts, system_level: str) -> Suggestion:
    if f.plant_wide or len(f.areas) > 1:
        return Suggestion("A4", "general", SOURCE_RULE, "high",
                          f"Located in more than one area ({', '.join(f.areas) or 'plant-wide'}).")
    if system_level == "system":
        return Suggestion("A4", "general", SOURCE_RULE, "medium",
                          "A system-level change propagates across the unit's network.")
    if f.numeric_parameter and f.hazop_required:
        return Suggestion("A4", "general", SOURCE_RULE, "medium",
                          f"An operating parameter moves ({f.parameter_old} → {f.parameter_new}) and a HAZOP is required: "
                          "the effect is not confined to the component.")
    return Suggestion("A4", "local", SOURCE_RULE, "medium" if f.hazop_required is not None else "low",
                      "Confined to one area with no operating-parameter change that needs a HAZOP.")


def _acceptance(f: ChangeFacts) -> Suggestion:
    if f.hazop_required is True:
        return Suggestion("A5", "collective", SOURCE_RULE, "high",
                          "A HAZOP is required: acceptance involves a multidisciplinary team.")
    if f.hazop_required is False:
        return Suggestion("A5", "individual", SOURCE_RULE, "medium",
                          "No HAZOP required: a single approving authority can accept the change.")
    return Suggestion("A5", "collective", SOURCE_DEFAULT, "low",
                      "HAZOP need not recorded; assumed collective (the cautious choice). Confirm.")


def _occurrence(f: ChangeFacts) -> Suggestion:
    if f.procedural:
        return Suggestion("A6", "situational", SOURCE_RULE, "medium",
                          "A procedural change responds to a specific situation rather than following a codified path.")
    if f.reactive:
        basis = f"action type '{f.action_type}'" if f.action_type else "the description"
        return Suggestion("A6", "situational", SOURCE_RULE, "medium" if f.action_type else "low",
                          f"Replacement/repair driven by a failure or defect ({basis}): a non-routine event.")
    basis = f"action type '{f.action_type}'" if f.action_type else "the description"
    return Suggestion("A6", "by_procedure", SOURCE_RULE, "medium" if f.action_type else "low",
                      f"A planned upgrade, optimisation or set-point change ({basis}) follows the standard procedure.")


def _information(f: ChangeFacts) -> Suggestion:
    if f.kind == "moc" and not f.pid_refs and not f.numeric_parameter:
        return Suggestion("A7", "undefined", SOURCE_RULE, "medium",
                          "No P&ID reference and no quantified parameter: outcomes cannot be estimated from the record.")
    if f.hazop_required is False and (f.like_for_like or f.numeric_parameter):
        why = "like-for-like replacement" if f.like_for_like else f"a quantified parameter change ({f.parameter_old} → {f.parameter_new})"
        return Suggestion("A7", "deterministic", SOURCE_RULE, "medium",
                          f"No HAZOP required and {why}: the outcome is well defined.")
    return Suggestion("A7", "partially_defined", SOURCE_RULE, "medium" if f.kind == "moc" else "low",
                      "Information is incomplete: effects are described but not fully quantified.")


def _impact_type(f: ChangeFacts) -> Suggestion:
    t = (f.change_type or "").lower()
    if f.procedural:
        return Suggestion("A8", "organisational", SOURCE_RULE, "medium",
                          "A procedure update principally affects how people and teams work.")
    if "efficien" in t or "energy" in t:
        return Suggestion("A8", "economic", SOURCE_RULE, "medium",
                          f"'{f.change_type}': the objective principally affected is efficiency / cost.")
    return Suggestion("A8", "technical", SOURCE_RULE, "medium" if t else "low",
                      "An equipment, instrumentation or process change principally affects technical performance and design.")


def suggest(facts: ChangeFacts) -> Dict[str, Suggestion]:
    """One suggestion per axis, keyed by axis id."""
    system = _system_level(facts)
    out = [_nature(facts), system, _duration(facts), _scope(facts, system.value), _acceptance(facts),
           _occurrence(facts), _information(facts), _impact_type(facts)]
    return {s.axis_id: s for s in out}


def facts_from_moc(record: Dict, reach: Optional[Dict] = None) -> ChangeFacts:
    """Build ChangeFacts from graph_store.get_moc_facts() output."""
    moc = record.get("moc") or {}
    asset = record.get("asset") or {}
    params = [p for p in (record.get("parameters") or []) if p]
    param = params[0] if params else {}
    criticality = moc.get("criticality_rating")
    if criticality is None:
        criticality = asset.get("criticality")
    return ChangeFacts(
        kind="moc", moc_id=moc.get("moc_id"), title=moc.get("title") or "",
        change_type=moc.get("change_type") or "", action_type=moc.get("action_type") or "",
        description=moc.get("description") or "", asset_id=asset.get("asset_id"),
        equipment_type=asset.get("equipment_type") or "",
        criticality=int(criticality) if criticality is not None else None,
        areas=sorted(a for a in (record.get("areas") or []) if a),
        hazop_required=moc.get("hazop_required"), pssr_required=moc.get("pssr_required"),
        shutdown_required=moc.get("shutdown_required"),
        like_for_like_text=" ".join(str(moc.get(k) or "") for k in ("hazop_reason", "hazop_justification")),
        parameter_old=str(param.get("old_value") if param.get("old_value") is not None else moc.get("old_value") or "") or None,
        parameter_new=str(param.get("new_value") if param.get("new_value") is not None else moc.get("new_value") or "") or None,
        parameter_threshold=str(param.get("threshold") or moc.get("threshold_limit") or "") or None,
        pid_refs=sorted(p for p in (record.get("pid_refs") or []) if p),
        reach_assets=(reach or {}).get("asset_count"), reach_areas=(reach or {}).get("areas") or [],
    )


def facts_from_proposal(change_type: str, asset_id: Optional[str], description: str, asset_record: Optional[Dict],
                        reach: Optional[Dict], hazop_required: Optional[bool] = None,
                        pssr_required: Optional[bool] = None, shutdown_required: Optional[bool] = None) -> ChangeFacts:
    """Build ChangeFacts for a change that is not yet a record in the graph."""
    asset = (asset_record or {}).get("asset") or {}
    criticality = asset.get("criticality")
    return ChangeFacts(
        kind="proposed", change_type=change_type or "", description=description or "", asset_id=asset_id,
        equipment_type=asset.get("equipment_type") or "",
        criticality=int(criticality) if criticality is not None else None,
        areas=sorted(a for a in ((asset_record or {}).get("areas") or []) if a),
        hazop_required=hazop_required, pssr_required=pssr_required, shutdown_required=shutdown_required,
        esd_target=bool((asset_record or {}).get("esd_target")),
        reach_assets=(reach or {}).get("asset_count"), reach_areas=(reach or {}).get("areas") or [],
    )
