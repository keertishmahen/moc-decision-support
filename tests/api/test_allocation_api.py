"""
tests/api/test_allocation_api.py — HTTP contract of the decision-allocation endpoints.

Offline: file-backed graph, no Neo4j, no OpenAI.
"""
import pytest
from fastapi.testclient import TestClient

FULL = {"A1": "tactical", "A2": "sub_system", "A3": "permanent", "A4": "local",
        "A5": "collective", "A6": "by_procedure", "A7": "partially_defined", "A8": "technical"}


@pytest.fixture
def client(allocation_service):
    from api.main import app
    from api.routes import allocation
    allocation.set_service(allocation_service)
    yield TestClient(app)
    allocation.set_service(None)


def test_model_exposes_axes_weights_thresholds_and_attribution(client):
    m = client.get("/api/allocation/model").json()
    assert m["version"] == "1.14" and m["space_size"] == 2592
    assert [a["id"] for a in m["axes"]] == [f"A{i}" for i in range(1, 9)]
    assert {d["id"]: d["max"] for d in m["dimensions"]} == {"R": 3, "C": 4, "U": 2, "I": 5}
    assert m["factor_matrix"]["HIGH"]["MED"] == "III"
    assert "Atiwadkar" in m["attribution"]["author"]


def test_score_returns_the_full_explanation(client):
    r = client.post("/api/allocation/score", json={"selection": FULL})
    assert r.status_code == 200
    body = r.json()
    assert body["scores"] == {"R": 2.0, "C": 1.5, "U": 0.5, "I": 2.5}
    assert body["allocation"] == "AI_SUPPORTED" and body["allocation_label"] == "AI-supported"
    assert {"dimensions", "factors", "signature", "reasons", "flips", "levels", "escalated_by"} <= set(body)


def test_incomplete_selection_is_a_422_that_names_the_axis(client):
    partial = dict(FULL)
    del partial["A7"]
    r = client.post("/api/allocation/score", json={"selection": partial})
    assert r.status_code == 422 and "A7" in r.json()["detail"]


def test_cases_lists_ten_reproduced_reference_cases(client):
    body = client.get("/api/allocation/cases").json()
    assert body["reproduced"] == 10
    assert [c["case_id"] for c in body["cases"]][:2] == ["MOC-F01", "MOC-F02"]
    assert all(c["matches"] for c in body["cases"])


def test_moc_assessment_and_404(client):
    ok = client.get("/api/allocation/moc/MoC-002")
    assert ok.status_code == 200 and ok.json()["result"]["allocation"] == "AI_SUPPORTED"
    assert client.get("/api/allocation/moc/MoC-999").status_code == 404


def test_assess_a_proposed_change(client):
    r = client.post("/api/allocation/assess", json={"change_type": "Mechanical", "asset_id": "P-101",
                                                      "description": "Replace the failed feed pump like-for-like",
                                                      "hazop_required": False})
    assert r.status_code == 200
    body = r.json()
    assert body["selection"]["A6"] == "situational" and body["selection"]["A7"] == "deterministic"
    assert client.post("/api/allocation/assess", json={"asset_id": "NOPE"}).status_code == 404


def test_enumeration_and_moc_list(client):
    e = client.get("/api/allocation/analysis/enumeration").json()
    assert e["allocations"] == {"AI_LED": 62, "AI_SUPPORTED": 406, "HUMAN_LED": 2124}
    assert len(client.get("/api/allocation/mocs").json()["mocs"]) == 10


def test_existing_routes_are_still_registered(client):
    paths = {r.path for r in client.app.routes}
    for p in ("/api/health", "/api/healthz", "/api/forms/prefill", "/api/risk/analyse", "/api/cost/predict",
              "/api/chat", "/api/graph/context", "/api/topology", "/api/downtime/propagate", "/api/agent"):
        assert p in paths
