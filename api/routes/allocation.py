"""
api/routes/allocation.py — Human–AI decision-allocation endpoints.

Read-only by design: the API has no authentication, so nothing here writes to the
knowledge graph. Reference characterisations are loaded with loaders/allocation_loader.py.
"""
from __future__ import annotations

import threading
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.allocation import SelectionError
from modules.decision_allocation import DecisionAllocationService, NotFound

router = APIRouter(prefix="/api/allocation", tags=["decision-allocation"])

_service: Optional[DecisionAllocationService] = None
_service_lock = threading.Lock()


def get_service() -> DecisionAllocationService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = DecisionAllocationService()
    return _service


def set_service(service: Optional[DecisionAllocationService]) -> None:
    """Test hook: inject a service built on a fake graph client."""
    global _service
    _service = service


class ScoreRequest(BaseModel):
    selection: Dict[str, str] = Field(..., description="Axis id (A1..A8) to category id")


class AssessRequest(BaseModel):
    change_type: str = Field("", max_length=120)
    asset_id: Optional[str] = Field(None, max_length=40)
    description: str = Field("", max_length=4000)
    hazop_required: Optional[bool] = None
    pssr_required: Optional[bool] = None
    shutdown_required: Optional[bool] = None


@router.get("/model")
def allocation_model():
    """Axes, categories, weights, thresholds, factor matrix, rule and attribution."""
    return get_service().model()


@router.post("/score")
def allocation_score(req: ScoreRequest):
    """Score a full eight-axis characterisation. Deterministic; no database or LLM involved."""
    try:
        return get_service().score(req.selection)
    except SelectionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/cases")
def allocation_cases():
    """The ten FCC reference cases: published thesis output next to the engine's output."""
    return get_service().reference_cases()


@router.get("/mocs")
def allocation_mocs():
    """MoC records available for assessment, with their stored allocation where one exists."""
    return get_service().list_mocs()


@router.get("/moc/{moc_id}")
def allocation_for_moc(moc_id: str):
    """Impact assessment, suggested and reference characterisation, and the recommended allocation for an MoC."""
    try:
        return get_service().assess_moc(moc_id)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/moc/{moc_id}/graph")
def allocation_graph_for_moc(moc_id: str):
    """Knowledge-graph neighbourhood of an MoC's decision characterisation."""
    return get_service().graph(moc_id)


@router.post("/assess")
def allocation_assess(req: AssessRequest):
    """Suggest a characterisation for a proposed change and score it. The caller confirms or overrides."""
    try:
        return get_service().assess_change(req.change_type, req.asset_id, req.description,
                                           req.hazop_required, req.pssr_required, req.shutdown_required)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/analysis/enumeration")
def allocation_enumeration():
    """Allocation shares and signatures over the whole characterisation space."""
    return get_service().enumeration()
