"""
modules.decision_allocation — connects the MoC knowledge graph to the allocation engine.

    graph_store     read-only Cypher
    characteriser   axis suggestions with evidence (pure rules)
    service         orchestration used by the API
"""
from .service import DecisionAllocationService, NotFound

__all__ = ["DecisionAllocationService", "NotFound"]
