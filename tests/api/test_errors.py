"""
tests/api/test_errors.py — failures become honest status codes and never leak exception text.

Offline.
"""
import datetime

import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from api.errors import GRAPH_DOWN, LLM_BAD, LLM_DOWN, json_safe, to_http_error
from core.allocation import SelectionError
from core.llm import LLMInvalidOutput, LLMUnavailable


def test_graph_outage_is_503():
    e = to_http_error(ServiceUnavailable("Unable to retrieve routing information for neo4j+s://secret-host"))
    assert (e.status_code, e.detail) == (503, GRAPH_DOWN)


def test_ai_outage_is_502():
    assert (to_http_error(LLMUnavailable("x")).status_code, to_http_error(LLMUnavailable("x")).detail) == (502, LLM_DOWN)
    assert to_http_error(LLMInvalidOutput("x")).detail == LLM_BAD


def test_bad_characterisation_is_422_with_the_fix_it_message():
    e = to_http_error(SelectionError("Invalid characterisation: A3 is not set."))
    assert e.status_code == 422 and "A3" in e.detail


def test_unknown_errors_are_500_with_a_reference_and_no_internals():
    e = to_http_error(RuntimeError("password=hunter2 at /app/core/x.py line 3"))
    assert e.status_code == 500
    assert "hunter2" not in e.detail and "reference" in e.detail


def test_json_safe_converts_driver_values():
    out = json_safe({"when": datetime.date(2025, 1, 15), "ids": {"a"}, "nested": [{"t": datetime.datetime(2025, 1, 1, 9)}]})
    assert out == {"when": "2025-01-15", "ids": ["a"], "nested": [{"t": "2025-01-01T09:00:00"}]}


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_route_failure_does_not_leak_exception_text(client, monkeypatch):
    import api.main as main

    def broken():
        raise RuntimeError("internal detail: neo4j+s://secret-host password=hunter2")

    monkeypatch.setattr(main, "get_risk_engine", broken)
    r = client.post("/api/risk/analyse", json={"change_type": "Mechanical", "asset_id": "P-101", "description": "x"})
    assert r.status_code == 500
    assert "hunter2" not in r.text and "secret-host" not in r.text


def test_ai_failure_in_a_route_is_502(client, monkeypatch):
    import api.main as main

    class Bot:
        def chat(self, *a, **k):
            raise LLMUnavailable("AI service call failed (APITimeoutError).")

    monkeypatch.setattr(main, "get_chatbot", lambda: Bot())
    r = client.post("/api/chat", json={"message": "hello", "session_id": "s1"})
    assert r.status_code == 502 and r.json()["detail"] == LLM_DOWN


def test_graph_failure_in_a_route_is_503(client, monkeypatch):
    import api.main as main

    def down():
        raise ServiceUnavailable("routing information unavailable")

    monkeypatch.setattr(main, "get_cost_predictor", down)
    r = client.post("/api/cost/predict", json={"change_type": "Mechanical", "asset_id": "P-101",
                                               "asset_category": "Pump", "risk_level": "High", "description": "x"})
    assert r.status_code == 503 and r.json()["detail"] == GRAPH_DOWN


def test_agent_iterations_are_bounded(client):
    r = client.post("/api/agent", json={"query": "x", "max_iterations": 50})
    assert r.status_code == 422


def test_chat_passes_the_session_id(client, monkeypatch):
    import api.main as main
    seen = {}

    class Bot:
        def chat(self, message, asset_id=None, session_id=None):
            seen["session_id"] = session_id
            return {"response": "ok", "intent": "general", "asset_id_used": "none", "moc_id_used": "none", "vector_hits": []}

        def reset_memory(self, session_id=None):
            seen["reset"] = session_id

    monkeypatch.setattr(main, "get_chatbot", lambda: Bot())
    assert client.post("/api/chat", json={"message": "hi", "session_id": "abc"}).status_code == 200
    assert client.post("/api/chat/reset", json={"session_id": "abc"}).status_code == 200
    assert client.post("/api/chat/reset").status_code == 200           # body stays optional
    assert seen == {"session_id": "abc", "reset": None}
