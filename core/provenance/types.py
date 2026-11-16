"""
core/provenance/types.py — the trust and provenance vocabulary.

Every part of a change assessment answers four questions (the Symmetra trust brief):
  1. which agent or computational component produced it, and in what role   -> AgentContribution
  2. where its knowledge came from                                            -> SourceKind, Evidence
  3. what evidence supports it                                                -> Finding.evidence
  4. what is uncertain, assumed or missing, and where a person must act       -> Finding / Gap / HumanCheckpoint

There is deliberately no trust score. The record shows the signals the platform already
has (source, basis, verification status, existing confidence) and leaves judgement to people.

Pure data: standard library only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceKind(str, Enum):
    """Where a piece of knowledge originates."""
    ONTOLOGY = "ontology"                      # schema: node types and relationship types
    KNOWLEDGE_GRAPH = "knowledge_graph"        # facts stored on nodes and relationships in Neo4j
    ENGINEERING_RECORD = "engineering_record"  # historical MoC records, work orders, lessons (incl. vector search)
    DOCUMENT = "document"                      # engineering documents, e.g. P&ID references
    COMPUTATIONAL_MODEL = "computational_model"  # deterministic model (decision allocation, propagation)
    ML_MODEL = "ml_model"                      # trained statistical model (cost and downtime)
    LLM_INTERPRETATION = "llm_interpretation"  # text produced by a language model from the evidence
    USER_INPUT = "user_input"                  # entered by the person assessing the change
    ASSUMPTION = "assumption"                  # a default used because data is missing

    @property
    def label(self) -> str:
        return {
            "ontology": "Ontology", "knowledge_graph": "Knowledge graph",
            "engineering_record": "Engineering records", "document": "Engineering documents",
            "computational_model": "Computational model", "ml_model": "ML model",
            "llm_interpretation": "LLM interpretation", "user_input": "User input", "assumption": "Assumption",
        }[self.value]


class Basis(str, Enum):
    """How a finding was produced. Only DETERMINISTIC and RULE are reproducible exactly."""
    DETERMINISTIC = "deterministic"   # fixed computation over stored data
    RULE = "rule"                     # transparent heuristic rule over stored data
    ML = "ml"                         # statistical model output
    LLM = "llm"                       # language-model interpretation
    RETRIEVAL = "retrieval"           # what was found by search, as found


class Verification(str, Enum):
    VERIFIED = "verified"         # checked against the knowledge graph and consistent
    UNVERIFIED = "unverified"     # not independently checked
    CONFLICT = "conflict"         # checked and inconsistent with another source: a person must resolve it
    NOT_APPLICABLE = "not_applicable"


class AgentStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"   # ran, but a dependency (graph or AI service) was unavailable
    FAILED = "failed"
    SKIPPED = "skipped"     # an input it needs was not produced


class CheckpointKind(str, Enum):
    VERIFICATION = "verification"   # a person should check a fact or a suggestion
    APPROVAL = "approval"           # a person with delegated authority must decide


@dataclass(frozen=True)
class Evidence:
    id: str                       # stable within a case, e.g. "kg:Asset:R-201"
    source: SourceKind
    reference: str                # what it points at, e.g. "Asset:R-201", "MoC:MoC-003", "PIDDocument:PID-FCC-201"
    label: str                    # short human-readable name
    detail: str = ""


@dataclass
class Finding:
    id: str
    statement: str
    agent: str
    basis: Basis
    evidence: List[str] = field(default_factory=list)      # Evidence ids
    confidence: Optional[str] = None                        # an EXISTING signal, e.g. "low" from the characteriser
    verification: Verification = Verification.UNVERIFIED
    note: str = ""                                          # why it is verified / in conflict


@dataclass(frozen=True)
class Gap:
    """Something uncertain, assumed or missing."""
    kind: str        # "assumption" | "uncertainty" | "missing"
    agent: str
    text: str


@dataclass(frozen=True)
class HumanCheckpoint:
    id: str
    kind: CheckpointKind
    what: str
    why: str
    role: str                # who should act, e.g. "Process Safety Manager"
    raised_by: str           # agent id


@dataclass
class AgentContribution:
    agent: str
    name: str
    role: str
    pattern: str                         # "supervisor" | "specialist" | "verifier"
    stage: int
    basis: Basis
    components: List[str]                # the existing code this agent ran
    sources: List[SourceKind]
    status: AgentStatus = AgentStatus.OK
    duration_ms: int = 0
    summary: str = ""
    findings: List[Finding] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)
    error: str = ""


def to_jsonable(value: Any) -> Any:
    """Dataclasses and enums to plain JSON values."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def source_kinds() -> List[Dict[str, str]]:
    return [{"id": k.value, "label": k.label} for k in SourceKind]
