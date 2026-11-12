"""
core/allocation/reference_cases.py — the ten FCC reference cases from the thesis (Table 2).

Each case pairs a (reconstructed) eight-axis characterisation with the output the
thesis publishes for it, so the engine can be checked against the original instrument.

Pure: standard library only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from .engine import score
from .model import CONFIG_DIR, AllocationModel, default_model
from .types import DIMENSION_IDS

REFERENCE_CASES_FILE = CONFIG_DIR / "reference_cases.json"


@dataclass(frozen=True)
class ReferenceCase:
    case_id: str
    moc_id: str
    title: str
    selection: Mapping[str, str]
    expected: Mapping
    status: str
    alternatives: str


@lru_cache(maxsize=1)
def _raw() -> Dict:
    return json.loads(Path(REFERENCE_CASES_FILE).read_text(encoding="utf-8"))


def source_note() -> Dict[str, str]:
    raw = _raw()
    return {"source": raw["source"], "reconstruction_note": raw["reconstruction_note"]}


def reference_cases() -> List[ReferenceCase]:
    return [
        ReferenceCase(case_id=c["case_id"], moc_id=c["moc_id"], title=c["title"], selection=c["selection"],
                      expected=c["expected"], status=c["status"], alternatives=c.get("alternatives", ""))
        for c in _raw()["cases"]
    ]


def reference_case_for_moc(moc_id: str) -> Optional[ReferenceCase]:
    wanted = moc_id.strip().upper()
    for c in reference_cases():
        if c.moc_id.upper() == wanted:
            return c
    return None


def compare(case: ReferenceCase, model: Optional[AllocationModel] = None) -> Dict:
    """Run the engine on a reference case and compare with the published output."""
    model = model or default_model()
    result = score(case.selection, model, with_flips=False)
    computed = {
        "scores": {d: result.dimensions[d].score for d in DIMENSION_IDS},
        "levels": {d: result.dimensions[d].level.value for d in DIMENSION_IDS},
        "signature": result.signature,
        "allocation": result.allocation.value,
    }
    expected = {
        "scores": {d: float(case.expected["scores"][d]) for d in DIMENSION_IDS},
        "levels": dict(case.expected["levels"]),
        "signature": case.expected["signature"],
        "allocation": case.expected["allocation"],
    }
    differences = [k for k in ("scores", "levels", "signature", "allocation") if computed[k] != expected[k]]
    return {
        "case_id": case.case_id, "moc_id": case.moc_id, "title": case.title,
        "selection": dict(case.selection), "status": case.status, "alternatives": case.alternatives,
        "expected": expected, "computed": computed,
        "allocation_label": result.allocation.label,
        "matches": not differences, "differences": differences,
    }


def compare_all(model: Optional[AllocationModel] = None) -> List[Dict]:
    return [compare(c, model) for c in reference_cases()]
