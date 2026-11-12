"""
core/allocation/engine.py — deterministic Human–AI decision-allocation engine.

Pipeline (thesis chapters 5 and 6):
    eight categorical selections
      -> weighted sum per dimension (Risk, Complexity, Uncertainty, Impact)
      -> level LOW/MED/HIGH per dimension (thresholds are fractions of the column maximum)
      -> factor I/II/III for R, C and U, each read against the shared Impact level
      -> signature "R/C/U" -> allocation (AI-led, AI-supported, Human-led)

The same selection always yields the same result. No I/O, no LLM, standard library only.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Tuple

from .model import AllocationModel, default_model
from .types import (
    DIMENSION_IDS,
    FACTOR_DIMENSION_IDS,
    IMPACT,
    Allocation,
    AllocationResult,
    Contribution,
    DimensionResult,
    Factor,
    FactorResult,
    Flip,
    Level,
)


class SelectionError(ValueError):
    """The characterisation is incomplete or names an unknown axis/category."""


def validate_selection(model: AllocationModel, selection: Mapping[str, str]) -> Dict[str, str]:
    """Return a normalised {axis_id: category_id}; raise SelectionError with a fix-it message."""
    problems: List[str] = []
    known = {a.id for a in model.axes}
    for key in selection:
        if key not in known:
            problems.append(f"unknown axis '{key}' (valid: {', '.join(sorted(known))})")
    out: Dict[str, str] = {}
    for axis in model.axes:
        value = selection.get(axis.id)
        valid = [c.id for c in axis.categories]
        if value is None or value == "":
            problems.append(f"{axis.id} ({axis.name}) is not set (choose one of: {', '.join(valid)})")
        elif value not in valid:
            problems.append(f"{axis.id} ({axis.name}) has unknown category '{value}' (valid: {', '.join(valid)})")
        else:
            out[axis.id] = value
    if problems:
        raise SelectionError("Invalid characterisation: " + "; ".join(problems) + ".")
    return out


def level_for(score: float, low_boundary: float, high_boundary: float) -> Level:
    """Below the lower boundary is LOW; at or above it but below the upper is MED; else HIGH."""
    if score < low_boundary:
        return Level.LOW
    if score < high_boundary:
        return Level.MED
    return Level.HIGH


def allocation_for(factors: Mapping[str, Factor]) -> Allocation:
    """Rule 'any-III-human__all-I-ai__else-supported' (thesis Section 6.3)."""
    values = [factors[d] for d in FACTOR_DIMENSION_IDS]
    if any(f is Factor.III for f in values):
        return Allocation.HUMAN_LED
    if all(f is Factor.I for f in values):
        return Allocation.AI_LED
    return Allocation.AI_SUPPORTED


def _raw_scores(model: AllocationModel, selection: Mapping[str, str]) -> Dict[str, float]:
    return {
        dim: sum(axis.category(selection[axis.id]).weight(dim) for axis in model.axes)
        for dim in DIMENSION_IDS
    }


def classify(model: AllocationModel, selection: Mapping[str, str]) -> Tuple[Dict[str, float], Dict[str, Level], Dict[str, Factor], Allocation]:
    """Fast path used by enumeration: scores, levels, factors and allocation, no explanation."""
    scores = _raw_scores(model, selection)
    levels = {d: level_for(scores[d], *model.boundaries(d)) for d in DIMENSION_IDS}
    factors = {d: model.factor_matrix[levels[d]][levels[IMPACT]] for d in FACTOR_DIMENSION_IDS}
    return scores, levels, factors, allocation_for(factors)


def signature_of(factors: Mapping[str, Factor]) -> str:
    return "/".join(factors[d].value for d in FACTOR_DIMENSION_IDS)


def _join(names: List[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _reasons(model: AllocationModel, dims: Mapping[str, DimensionResult],
             factors: Mapping[str, FactorResult], allocation: Allocation) -> Tuple[str, ...]:
    impact = dims[IMPACT]
    out: List[str] = []
    for d in FACTOR_DIMENSION_IDS:
        f, r = factors[d], dims[d]
        drivers = ", ".join(f"{c.category_name} ({c.axis_name}, +{c.weight:g})" for c in r.contributions) or "no contributing category"
        out.append(
            f"{r.name}: score {r.score:g} of {r.maximum:g} is {r.level.value}; read against {impact.level.value} "
            f"Impact this gives factor {f.factor.value}. Driven by: {drivers}."
        )
    i_drivers = ", ".join(f"{c.category_name} ({c.axis_name}, +{c.weight:g})" for c in impact.contributions) or "no contributing category"
    out.append(f"Impact: score {impact.score:g} of {impact.maximum:g} is {impact.level.value}. Driven by: {i_drivers}.")

    top = [factors[d].dimension_name for d in FACTOR_DIMENSION_IDS if factors[d].factor is Factor.III]
    mid = [factors[d].dimension_name for d in FACTOR_DIMENSION_IDS if factors[d].factor is Factor.II]
    if allocation is Allocation.HUMAN_LED:
        alone = " alone" if len(top) == 1 else ""
        out.append(f"Human-led because {_join(top)}{alone} reach{'es' if len(top) == 1 else ''} factor III; "
                   "one dimension at the top factor is enough to escalate.")
    elif allocation is Allocation.AI_LED:
        out.append("AI-led is permissible because Risk, Complexity and Uncertainty are all at factor I.")
    else:
        out.append(f"AI-supported because no dimension reaches factor III, while {_join(mid)} "
                   f"{'is' if len(mid) == 1 else 'are'} at factor II.")
    return tuple(out)


def _flips(model: AllocationModel, selection: Mapping[str, str], allocation: Allocation) -> Tuple[Flip, ...]:
    """Single-axis changes that would move the allocation: what the result is sensitive to."""
    out: List[Flip] = []
    for axis in model.axes:
        for cat in axis.categories:
            if cat.id == selection[axis.id]:
                continue
            alt = dict(selection)
            alt[axis.id] = cat.id
            new_alloc = classify(model, alt)[3]
            if new_alloc is not allocation:
                out.append(Flip(axis_id=axis.id, axis_name=axis.name, from_category=selection[axis.id],
                                to_category=cat.id, to_category_name=cat.name, allocation=new_alloc))
    return tuple(out)


def score(selection: Mapping[str, str], model: Optional[AllocationModel] = None,
          with_flips: bool = True) -> AllocationResult:
    """Score a full eight-axis characterisation and explain the recommended allocation."""
    model = model or default_model()
    sel = validate_selection(model, selection)
    scores, levels, factor_values, allocation = classify(model, sel)

    dims: Dict[str, DimensionResult] = {}
    for d in model.dimensions:
        lo, hi = model.boundaries(d.id)
        maximum = model.column_max(d.id)
        contributions = tuple(
            Contribution(axis_id=a.id, axis_name=a.name, category_id=sel[a.id],
                         category_name=a.category(sel[a.id]).name, weight=a.category(sel[a.id]).weight(d.id))
            for a in model.axes if a.category(sel[a.id]).weight(d.id) > 0
        )
        s = scores[d.id]
        dims[d.id] = DimensionResult(
            id=d.id, name=d.name, score=s, maximum=maximum, normalised=s / maximum, level=levels[d.id],
            low_boundary=lo, high_boundary=hi, margin=min(abs(s - lo), abs(s - hi)), contributions=contributions,
        )

    factors = {
        d: FactorResult(dimension_id=d, dimension_name=model.dimension(d).name, level=levels[d],
                        impact_level=levels[IMPACT], factor=factor_values[d])
        for d in FACTOR_DIMENSION_IDS
    }
    return AllocationResult(
        model_version=model.version,
        selection=sel,
        dimensions=dims,
        factors=factors,
        signature=signature_of(factor_values),
        allocation=allocation,
        escalated_by=tuple(d for d in FACTOR_DIMENSION_IDS if factor_values[d] is Factor.III),
        reasons=_reasons(model, dims, factors, allocation),
        flips=_flips(model, sel, allocation) if with_flips else tuple(),
    )
