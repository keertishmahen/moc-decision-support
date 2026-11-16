"""
api/routes/case.py — multi-agent change assessment ("Change Case").

POST /api/case/assess runs the agent line-up on one proposed change and returns a case
record that answers: what happens, who should decide, and why the recommendation can be
trusted (provenance). Read-only: nothing is written to the knowledge graph.
"""
from __future__ import annotations

import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.errors import json_safe, to_http_error
from modules.agents import ChangeRequest, Supervisor, Toolbox, registry

router = APIRouter(prefix="/api/case", tags=["change-case"])

_supervisor: Optional[Supervisor] = None
_lock = threading.Lock()


def _tools() -> Toolbox:
    """The agents use the application's shared component instances (imported lazily: no extra clients)."""
    def main():
        import api.main as m
        return m

    def neo4j():
        from core.neo4j_client import Neo4jClient
        return Neo4jClient()

    def propagator():
        from core.downtime_propagator import DowntimePropagator
        return DowntimePropagator(neo4j())

    def allocation():
        from api.routes.allocation import get_service
        return get_service()

    return Toolbox(
        rag=lambda: main().get_risk_engine().pipeline,
        risk_engine=lambda: main().get_risk_engine(),
        smart_forms=lambda: main().get_smart_forms(),
        cost_predictor=lambda: main().get_cost_predictor(),
        allocation=allocation,
        neo4j=neo4j,
        propagator=propagator,
    )


def get_supervisor() -> Supervisor:
    global _supervisor
    if _supervisor is None:
        with _lock:
            if _supervisor is None:
                from core.allocation import default_model
                from core.config import OPENAI_MODEL
                _supervisor = Supervisor(_tools(), model_info={
                    "language_model": OPENAI_MODEL,
                    "allocation_model_version": default_model().version,
                })
    return _supervisor


def set_supervisor(supervisor: Optional[Supervisor]) -> None:
    """Test hook."""
    global _supervisor
    _supervisor = supervisor


class CaseRequest(BaseModel):
    change_type: str = Field(..., min_length=2, max_length=120)
    asset_id: str = Field(..., min_length=2, max_length=40)
    description: str = Field(..., min_length=5, max_length=4000)
    moc_id: Optional[str] = Field(None, max_length=20)


@router.get("/agents")
def case_agents():
    """The agent line-up, the multi-agent patterns used, and the provenance source kinds."""
    return registry()


@router.post("/assess")
def case_assess(req: CaseRequest):
    """Run every agent on one proposed change and return the case record with its provenance."""
    try:
        record = get_supervisor().assess(ChangeRequest(
            change_type=req.change_type.strip(), asset_id=req.asset_id.strip(),
            description=req.description.strip(), moc_id=(req.moc_id or "").strip() or None))
        return json_safe(record)
    except HTTPException:
        raise
    except Exception as e:                                       # noqa: BLE001 — mapped to a clean status
        raise to_http_error(e) from e
