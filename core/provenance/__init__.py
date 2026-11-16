"""
core.provenance — who produced what, from which source, on which evidence, and what is uncertain.

Pure domain vocabulary for the trust layer (standard library only; enforced by
tests/structure/test_architecture.py). Agents in modules/agents write to a Ledger; the
supervisor turns it into the case record shown under "Why this recommendation?".
"""
from .ledger import Ledger, evidence_id, summarise
from .types import (
    AgentContribution,
    AgentStatus,
    Basis,
    CheckpointKind,
    Evidence,
    Finding,
    Gap,
    HumanCheckpoint,
    SourceKind,
    Verification,
    source_kinds,
    to_jsonable,
)

__all__ = [
    "AgentContribution", "AgentStatus", "Basis", "CheckpointKind", "Evidence", "Finding", "Gap", "HumanCheckpoint",
    "Ledger", "SourceKind", "Verification", "evidence_id", "source_kinds", "summarise", "to_jsonable",
]
