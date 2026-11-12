"""
core/allocation/analysis.py — structural analysis of the allocation model (thesis chapter 7).

The characterisation space is finite (2,592 points for the baseline model), so the
model's whole behaviour can be enumerated instead of sampled.

Pure: standard library only. Every function is deterministic (Monte Carlo takes a seed).
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import replace
from itertools import product
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from .engine import allocation_for, classify, level_for, signature_of
from .model import AllocationModel, default_model
from .types import DIMENSION_IDS, FACTOR_DIMENSION_IDS, IMPACT, Allocation, Axis, Category, Level


def iter_space(model: AllocationModel) -> Iterator[Dict[str, str]]:
    """Every characterisation point, as {axis_id: category_id}."""
    ids = [a.id for a in model.axes]
    for combo in product(*[[c.id for c in a.categories] for a in model.axes]):
        yield dict(zip(ids, combo))


def enumerate_space(model: Optional[AllocationModel] = None) -> Dict:
    """Allocation shares, signatures reached, and the high-U / low-R / low-C region."""
    model = model or default_model()
    allocations: Counter = Counter()
    signatures: Counter = Counter()
    high_u_low_rc = 0
    total = 0
    for sel in iter_space(model):
        _, levels, factors, alloc = classify(model, sel)
        total += 1
        allocations[alloc.value] += 1
        signatures[signature_of(factors)] += 1
        if levels["U"] is Level.HIGH and levels["R"] is Level.LOW and levels["C"] is Level.LOW:
            high_u_low_rc += 1
    all_signatures = ["/".join(p) for p in product(("I", "II", "III"), repeat=3)]
    return {
        "model_version": model.version,
        "total": total,
        "allocations": {a.value: allocations.get(a.value, 0) for a in Allocation},
        "shares": {a.value: round(allocations.get(a.value, 0) / total, 4) for a in Allocation},
        "signatures_reached": len(signatures),
        "signatures_possible": len(all_signatures),
        "signatures_unreached": [s for s in all_signatures if s not in signatures],
        "signature_counts": dict(signatures.most_common()),
        "high_uncertainty_low_risk_low_complexity_points": high_u_low_rc,
    }


def single_axis_swing(model: Optional[AllocationModel] = None) -> List[Dict]:
    """Score span each axis induces on each dimension (0 = structural zero)."""
    model = model or default_model()
    out = []
    for a in model.axes:
        spans = {d: max(c.weight(d) for c in a.categories) - min(c.weight(d) for c in a.categories)
                 for d in DIMENSION_IDS}
        out.append({"axis_id": a.id, "axis": a.name, "span": spans,
                    "feeds": [d for d in DIMENSION_IDS if spans[d] > 0]})
    return out


def _scaled_model(model: AllocationModel, factors: Mapping[Tuple[str, str], float]) -> AllocationModel:
    """Copy of the model with each (axis, dimension) link multiplied by a factor."""
    axes: List[Axis] = []
    for a in model.axes:
        cats = []
        for c in a.categories:
            weights = {d: c.weight(d) * factors.get((a.id, d), 1.0) for d in DIMENSION_IDS if c.weight(d) > 0}
            cats.append(Category(id=c.id, name=c.name, weights=weights))
        axes.append(Axis(id=a.id, name=a.name, hint=a.hint, categories=tuple(cats)))
    return replace(model, axes=tuple(axes))


def _classify_fixed_boundaries(perturbed: AllocationModel, baseline: AllocationModel,
                               selection: Mapping[str, str]) -> Allocation:
    """Score with perturbed weights but level against the BASELINE boundaries.

    Re-deriving the boundaries from the perturbed weights would move numerator and
    denominator together and report stability that is an artefact (thesis Section 3.3).
    """
    scores = {d: sum(a.category(selection[a.id]).weight(d) for a in perturbed.axes) for d in DIMENSION_IDS}
    levels = {d: level_for(scores[d], *baseline.boundaries(d)) for d in DIMENSION_IDS}
    factors = {d: baseline.factor_matrix[levels[d]][levels[IMPACT]] for d in FACTOR_DIMENSION_IDS}
    return allocation_for(factors)


def links(model: AllocationModel) -> List[Tuple[str, str]]:
    """(axis_id, dimension_id) pairs with at least one non-zero weight."""
    return [(a.id, d) for a in model.axes for d in DIMENSION_IDS if a.max_weight(d) > 0]


def weight_perturbation(model: Optional[AllocationModel] = None, pct: float = 0.20) -> List[Dict]:
    """One-at-a-time: scale one axis->dimension link by (1 - pct) and (1 + pct), count allocation flips.

    `flip_share_mean` (the mean of the down and up shares) is the figure the thesis reports in Fig. 12.
    """
    model = model or default_model()
    points = list(iter_space(model))
    baseline = [classify(model, s)[3] for s in points]
    out = []
    for axis_id, dim in links(model):
        flipped_down = flipped_up = either = 0
        down = _scaled_model(model, {(axis_id, dim): 1 - pct})
        up = _scaled_model(model, {(axis_id, dim): 1 + pct})
        for sel, base in zip(points, baseline):
            d = _classify_fixed_boundaries(down, model, sel) is not base
            u = _classify_fixed_boundaries(up, model, sel) is not base
            flipped_down += d
            flipped_up += u
            either += (d or u)
        n = len(points)
        out.append({
            "axis_id": axis_id, "axis": model.axis(axis_id).name, "dimension": dim,
            "flip_share_down": round(flipped_down / n, 4), "flip_share_up": round(flipped_up / n, 4),
            "flip_share_either": round(either / n, 4),
            "flip_share_mean": round((flipped_down + flipped_up) / (2 * n), 4),
        })
    out.sort(key=lambda r: r["flip_share_mean"], reverse=True)
    return out


def threshold_sweep(model: Optional[AllocationModel] = None,
                    lows: Sequence[float] = (0.15, 0.25, 0.33, 0.45, 0.55),
                    highs: Sequence[float] = (0.45, 0.55, 0.67, 0.75, 0.85)) -> Dict:
    """Share going human-led when all four dimensions use the same (low, high) boundary pair.

    A score exactly on a boundary belongs to the higher level (Section 6.1). With high = 0.75 the
    Complexity and Uncertainty boundaries land exactly on attainable scores (3.0 and 1.5); the thesis
    Fig. 13 column for 0.75 is reproduced only if the boundary sits marginally above 0.75.
    """
    model = model or default_model()
    points = list(iter_space(model))
    rows = []
    for lo in lows:
        row = []
        for hi in highs:
            if lo >= hi:
                row.append(None)
                continue
            swept = replace(model, dimensions=tuple(replace(d, low=lo, high=hi) for d in model.dimensions))
            human = sum(1 for s in points if classify(swept, s)[3] is Allocation.HUMAN_LED)
            row.append(round(100 * human / len(points)))
        rows.append({"low": lo, "human_led_pct": row})
    return {"highs": list(highs), "rows": rows}


def monte_carlo_stability(selection: Mapping[str, str], model: Optional[AllocationModel] = None,
                          draws: int = 1000, spread: float = 0.25, seed: int = 0) -> Dict:
    """Perturb every non-zero link by U(1 - spread, 1 + spread) and report how often the allocation holds."""
    model = model or default_model()
    rng = random.Random(seed)
    base = classify(model, selection)[3]
    all_links = links(model)
    counts: Counter = Counter()
    for _ in range(draws):
        factors = {link: rng.uniform(1 - spread, 1 + spread) for link in all_links}
        counts[_classify_fixed_boundaries(_scaled_model(model, factors), model, selection).value] += 1
    return {
        "baseline_allocation": base.value, "draws": draws, "spread": spread, "seed": seed,
        "stability": round(counts.get(base.value, 0) / draws, 4),
        "allocations": {a.value: counts.get(a.value, 0) for a in Allocation},
    }


def matching_selections(target_scores: Mapping[str, float], model: Optional[AllocationModel] = None) -> Iterable[Dict[str, str]]:
    """All characterisations whose four raw scores equal the target (used to reconstruct published cases)."""
    model = model or default_model()
    for sel in iter_space(model):
        scores = classify(model, sel)[0]
        if all(abs(scores[d] - float(target_scores[d])) < 1e-9 for d in DIMENSION_IDS):
            yield sel
