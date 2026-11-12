"""
core/allocation/model.py — load and validate the decision-allocation model configuration.

The JSON file under config/ is the single source of truth for axes, weights,
thresholds, the factor matrix and the allocation rule. The Neo4j graph holds a
projection of it (see loaders/allocation_loader.py); nothing else restates the numbers.

Pure: standard library only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

from .types import DIMENSION_IDS, Axis, Category, Dimension, Factor, Level

CONFIG_DIR = Path(__file__).parent / "config"
DEFAULT_MODEL_FILE = CONFIG_DIR / "parth_v1_14.json"

SUPPORTED_RULE = "any-III-human__all-I-ai__else-supported"


class ModelConfigError(ValueError):
    """The model configuration file is malformed. The message says what to fix."""


@dataclass(frozen=True)
class AllocationModel:
    model_id: str
    version: str
    title: str
    attribution: Mapping[str, str]
    dimensions: Tuple[Dimension, ...]
    axes: Tuple[Axis, ...]
    factor_matrix: Mapping[Level, Mapping[Level, Factor]]     # [dimension level][impact level]
    rule_id: str
    rule_text: str

    def axis(self, axis_id: str) -> Axis:
        for a in self.axes:
            if a.id == axis_id:
                return a
        raise KeyError(axis_id)

    def dimension(self, dim_id: str) -> Dimension:
        for d in self.dimensions:
            if d.id == dim_id:
                return d
        raise KeyError(dim_id)

    def column_max(self, dim_id: str) -> float:
        """Highest attainable raw score: each axis contributes at most its largest weight."""
        return sum(a.max_weight(dim_id) for a in self.axes)

    def boundaries(self, dim_id: str) -> Tuple[float, float]:
        """(LOW|MED, MED|HIGH) boundaries as raw-score values."""
        d, m = self.dimension(dim_id), self.column_max(dim_id)
        return d.low * m, d.high * m

    @property
    def space_size(self) -> int:
        n = 1
        for a in self.axes:
            n *= len(a.categories)
        return n

    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "title": self.title,
            "attribution": dict(self.attribution),
            "space_size": self.space_size,
            "dimensions": [
                {"id": d.id, "name": d.name, "definition": d.definition, "max": self.column_max(d.id),
                 "low": d.low, "high": d.high,
                 "low_boundary": round(self.boundaries(d.id)[0], 3),
                 "high_boundary": round(self.boundaries(d.id)[1], 3)}
                for d in self.dimensions
            ],
            "axes": [
                {"id": a.id, "name": a.name, "hint": a.hint,
                 "categories": [
                     {"id": c.id, "name": c.name, "weights": {k: c.weight(k) for k in DIMENSION_IDS}}
                     for c in a.categories
                 ]}
                for a in self.axes
            ],
            "factor_matrix": {
                row.value: {col.value: f.value for col, f in cols.items()}
                for row, cols in self.factor_matrix.items()
            },
            "allocation_rule": {"id": self.rule_id, "text": self.rule_text},
        }


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ModelConfigError(message)


def parse_model(raw: Mapping) -> AllocationModel:
    """Build a validated AllocationModel from a decoded JSON object."""
    for key in ("model_id", "version", "dimensions", "axes", "factor_matrix", "allocation_rule"):
        _require(key in raw, f"Model config is missing '{key}'. See core/allocation/config/parth_v1_14.json.")

    dims = []
    for d in raw["dimensions"]:
        _require(0 < d["low"] < d["high"] < 1,
                 f"Dimension {d.get('id')}: thresholds must satisfy 0 < low < high < 1 "
                 f"(got low={d.get('low')}, high={d.get('high')}).")
        dims.append(Dimension(id=d["id"], name=d["name"], low=float(d["low"]), high=float(d["high"]),
                              definition=d.get("definition", "")))
    _require(tuple(d.id for d in dims) == DIMENSION_IDS,
             f"Dimensions must be exactly {DIMENSION_IDS} in that order.")

    axes = []
    seen_axes = set()
    for a in raw["axes"]:
        _require(a["id"] not in seen_axes, f"Duplicate axis id {a['id']}.")
        seen_axes.add(a["id"])
        cats, seen = [], set()
        for c in a["categories"]:
            _require(c["id"] not in seen, f"Axis {a['id']}: duplicate category id {c['id']}.")
            seen.add(c["id"])
            weights = c.get("weights", {})
            for dim_id, w in weights.items():
                _require(dim_id in DIMENSION_IDS, f"Axis {a['id']}/{c['id']}: unknown dimension '{dim_id}'.")
                _require(isinstance(w, (int, float)) and w >= 0,
                         f"Axis {a['id']}/{c['id']}: weight for {dim_id} must be a number >= 0.")
            cats.append(Category(id=c["id"], name=c["name"], weights=dict(weights)))
        _require(len(cats) >= 2, f"Axis {a['id']} needs at least two categories.")
        axes.append(Axis(id=a["id"], name=a["name"], hint=a.get("hint", ""), categories=tuple(cats)))

    matrix: Dict[Level, Dict[Level, Factor]] = {}
    for row in Level:
        _require(row.value in raw["factor_matrix"], f"factor_matrix is missing row {row.value}.")
        matrix[row] = {}
        for col in Level:
            cell = raw["factor_matrix"][row.value].get(col.value)
            _require(cell in {f.value for f in Factor},
                     f"factor_matrix[{row.value}][{col.value}] must be I, II or III (got {cell!r}).")
            matrix[row][col] = Factor(cell)

    rule = raw["allocation_rule"]
    _require(rule.get("id") == SUPPORTED_RULE,
             f"Unsupported allocation rule '{rule.get('id')}'. The engine implements '{SUPPORTED_RULE}'; "
             "add the new rule to core/allocation/engine.py before referencing it in the config.")

    model = AllocationModel(
        model_id=raw["model_id"], version=str(raw["version"]), title=raw.get("title", ""),
        attribution=dict(raw.get("attribution", {})), dimensions=tuple(dims), axes=tuple(axes),
        factor_matrix=matrix, rule_id=rule["id"], rule_text=rule.get("text", ""),
    )
    for d in model.dimensions:
        _require(model.column_max(d.id) > 0, f"No axis contributes to dimension {d.id}.")
    return model


def load_model(path: Optional[Path] = None) -> AllocationModel:
    p = Path(path) if path else DEFAULT_MODEL_FILE
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ModelConfigError(f"Model config not found at {p}.") from e
    except json.JSONDecodeError as e:
        raise ModelConfigError(f"Model config at {p} is not valid JSON: {e}.") from e
    return parse_model(raw)


@lru_cache(maxsize=1)
def default_model() -> AllocationModel:
    return load_model()
