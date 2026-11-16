"""
tests/agents/test_case_api.py — HTTP contract of /api/case and the provenance on /api/allocation. Offline.
"""
import pytest
from fastapi.testclient import TestClient

from core.provenance import Ledger, SourceKind


@pytest.fixture
def client(make_supervisor, allocation_service):
    from api.main import app
    from api.routes import allocation, case
    allocation.set_service(allocation_service)
    case.set_supervisor(make_supervisor())
    yield TestClient(app)
    case.set_supervisor(None)
    allocation.set_service(None)


def test_agents_endpoint_lists_patterns_agents_and_sources(client):
    body = client.get("/api/case/agents").json()
    assert [p["id"] for p in body["patterns"]] == ["supervisor", "parallel", "sequential", "verifier", "human"]
    assert len(body["agents"]) == 7
    assert {s["id"] for s in body["source_kinds"]} >= {"ontology", "knowledge_graph", "llm_interpretation"}


def test_assess_returns_a_case_record(client):
    r = client.post("/api/case/assess", json={"change_type": "Instrumentation", "asset_id": "FV-103",
                                              "description": "Upgrade the valve positioner on FV-103", "moc_id": "MoC-002"})
    assert r.status_code == 200
    body = r.json()
    assert {"run_id", "what_happens", "who_decides", "why_trust", "trace"} <= set(body)
    assert body["who_decides"]["result"]["allocation"] == "AI_SUPPORTED"


def test_assess_rejects_incomplete_input(client):
    assert client.post("/api/case/assess", json={"change_type": "Mechanical", "asset_id": "P-101", "description": "x"}).status_code == 422


def test_allocation_responses_carry_provenance(client):
    moc = client.get("/api/allocation/moc/MoC-002").json()["provenance"]
    assert moc["checkpoints"][-1]["what"] == "Approve or reject the change."
    assert "computational_model" in moc["evidence_by_source"]
    sel = client.get("/api/allocation/moc/MoC-002").json()["selection"]
    scored = client.post("/api/allocation/score", json={"selection": {**sel, "A3": "temporary"}}).json()
    assert "user_input" in scored["provenance"]["evidence_by_source"]


def test_ledger_deduplicates_evidence_and_orders_checkpoints():
    from core.provenance import CheckpointKind
    led = Ledger()
    a = led.cite(SourceKind.KNOWLEDGE_GRAPH, "Asset:R-201", "R-201")
    b = led.cite(SourceKind.KNOWLEDGE_GRAPH, "Asset:R-201", "R-201 again")
    assert a == b and len(led.evidence()) == 1
    led.checkpoint(CheckpointKind.APPROVAL, "approve", "w", "r", "x")
    led.checkpoint(CheckpointKind.VERIFICATION, "verify", "w", "r", "x")
    led.checkpoint(CheckpointKind.VERIFICATION, "verify", "w", "r", "x")
    assert [c.what for c in led.checkpoints()] == ["verify", "approve"]
