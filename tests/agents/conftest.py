"""Shared fakes for the agent tests: AI/ML components faked, graph reads from the file-backed graph."""
import pytest
from fakes import FakeCost, FakeForms, FakeNeo4j, FakePropagator, FakeRag, FakeRisk

from modules.agents import Supervisor, Toolbox


@pytest.fixture
def make_supervisor(allocation_service):
    def make(**overrides):
        parts = {"rag": FakeRag(), "risk_engine": FakeRisk(), "smart_forms": FakeForms(), "cost_predictor": FakeCost(),
                 "allocation": allocation_service, "neo4j": FakeNeo4j(), "propagator": FakePropagator()}
        parts.update(overrides)
        return Supervisor(Toolbox(**{k: (lambda v=v: v) for k, v in parts.items()}))
    return make
