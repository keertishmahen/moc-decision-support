"""
core/allocation/types.py — value types for the Human–AI decision-allocation model.

Pure data: no I/O, standard library only (enforced by tests/structure).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Mapping, Tuple

# Dimension ids. R, C and U are each read against I (the shared Impact axis).
RISK, COMPLEXITY, UNCERTAINTY, IMPACT = "R", "C", "U", "I"
DIMENSION_IDS: Tuple[str, ...] = (RISK, COMPLEXITY, UNCERTAINTY, IMPACT)
FACTOR_DIMENSION_IDS: Tuple[str, ...] = (RISK, COMPLEXITY, UNCERTAINTY)


class Level(str, Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class Factor(str, Enum):
    I = "I"      # noqa: E741 — roman numeral, as in the thesis
    II = "II"
    III = "III"


class Allocation(str, Enum):
    AI_LED = "AI_LED"
    AI_SUPPORTED = "AI_SUPPORTED"
    HUMAN_LED = "HUMAN_LED"

    @property
    def label(self) -> str:
        return {"AI_LED": "AI-led", "AI_SUPPORTED": "AI-supported", "HUMAN_LED": "Human-led"}[self.value]


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    weights: Mapping[str, float]          # dimension id -> weight; absent means 0

    def weight(self, dim: str) -> float:
        return float(self.weights.get(dim, 0.0))


@dataclass(frozen=True)
class Axis:
    id: str
    name: str
    hint: str
    categories: Tuple[Category, ...]

    def category(self, category_id: str) -> Category:
        for c in self.categories:
            if c.id == category_id:
                return c
        raise KeyError(category_id)

    def max_weight(self, dim: str) -> float:
        return max(c.weight(dim) for c in self.categories)


@dataclass(frozen=True)
class Dimension:
    id: str
    name: str
    low: float           # LOW|MED boundary, as a fraction of the column maximum
    high: float          # MED|HIGH boundary, as a fraction of the column maximum
    definition: str = ""


@dataclass(frozen=True)
class Contribution:
    axis_id: str
    axis_name: str
    category_id: str
    category_name: str
    weight: float


@dataclass(frozen=True)
class DimensionResult:
    id: str
    name: str
    score: float
    maximum: float
    normalised: float
    level: Level
    low_boundary: float      # raw-score value of the LOW|MED boundary
    high_boundary: float     # raw-score value of the MED|HIGH boundary
    margin: float            # distance from the score to the nearest boundary
    contributions: Tuple[Contribution, ...]


@dataclass(frozen=True)
class FactorResult:
    dimension_id: str
    dimension_name: str
    level: Level
    impact_level: Level
    factor: Factor


@dataclass(frozen=True)
class Flip:
    """A single-axis change that would alter the recommended allocation."""
    axis_id: str
    axis_name: str
    from_category: str
    to_category: str
    to_category_name: str
    allocation: Allocation


@dataclass(frozen=True)
class AllocationResult:
    model_version: str
    selection: Mapping[str, str]
    dimensions: Mapping[str, DimensionResult]
    factors: Mapping[str, FactorResult]
    signature: str
    allocation: Allocation
    escalated_by: Tuple[str, ...]          # dimension ids at factor III
    reasons: Tuple[str, ...]
    flips: Tuple[Flip, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict:
        def dim(d: DimensionResult) -> Dict:
            return {
                "id": d.id, "name": d.name, "score": d.score, "max": d.maximum,
                "normalised": round(d.normalised, 4), "level": d.level.value,
                "low_boundary": round(d.low_boundary, 3), "high_boundary": round(d.high_boundary, 3),
                "margin": round(d.margin, 3),
                "contributions": [
                    {"axis_id": c.axis_id, "axis": c.axis_name, "category_id": c.category_id,
                     "category": c.category_name, "weight": c.weight}
                    for c in d.contributions
                ],
            }

        factors: List[Dict] = [
            {"dimension_id": f.dimension_id, "dimension": f.dimension_name, "level": f.level.value,
             "impact_level": f.impact_level.value, "factor": f.factor.value}
            for f in (self.factors[k] for k in FACTOR_DIMENSION_IDS)
        ]
        return {
            "model_version": self.model_version,
            "selection": dict(self.selection),
            "scores": {k: self.dimensions[k].score for k in DIMENSION_IDS},
            "levels": {k: self.dimensions[k].level.value for k in DIMENSION_IDS},
            "dimensions": [dim(self.dimensions[k]) for k in DIMENSION_IDS],
            "factors": factors,
            "signature": self.signature,
            "allocation": self.allocation.value,
            "allocation_label": self.allocation.label,
            "escalated_by": list(self.escalated_by),
            "reasons": list(self.reasons),
            "flips": [
                {"axis_id": f.axis_id, "axis": f.axis_name, "from": f.from_category, "to": f.to_category,
                 "to_name": f.to_category_name, "allocation": f.allocation.value,
                 "allocation_label": f.allocation.label}
                for f in self.flips
            ],
        }
