"""
modules/agents/base.py — what an agent is, and what it is given when it runs.

An agent wraps EXISTING platform code (risk engine, form prefill, cost model, graph queries,
decision-allocation engine). It adds no new analysis; it records what that code produced,
from which sources, on which evidence, and with which gaps, in the shared Ledger.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.provenance import AgentContribution, AgentStatus, Basis, Ledger, SourceKind


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    role: str
    pattern: str                      # "specialist" | "verifier"
    stage: int
    basis: Basis
    components: Tuple[str, ...]       # existing code this agent runs
    sources: Tuple[SourceKind, ...]   # where its knowledge comes from
    needs: Tuple[str, ...] = ()       # agent ids it cannot run without (skipped if they fail)
    reads: Tuple[str, ...] = ()       # agent ids whose results it uses if present (states an assumption if not)

    def contribution(self, **kwargs) -> AgentContribution:
        return AgentContribution(agent=self.id, name=self.name, role=self.role, pattern=self.pattern,
                                 stage=self.stage, basis=self.basis, components=list(self.components),
                                 sources=list(self.sources), **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "role": self.role, "pattern": self.pattern, "stage": self.stage,
                "basis": self.basis.value, "components": list(self.components),
                "sources": [s.value for s in self.sources], "needs": list(self.needs),
                "reads": list(self.reads)}


@dataclass(frozen=True)
class ChangeRequest:
    change_type: str
    asset_id: str
    description: str
    moc_id: Optional[str] = None     # set when the case is an existing MoC used as an example


class Toolbox:
    """Lazy access to the existing platform components. Tests pass fakes; the API passes the
    application's shared instances so the agents add no extra clients or memory."""

    def __init__(self, **factories: Callable[[], Any]):
        self._factories = factories
        self._cache: Dict[str, Any] = {}

    def get(self, name: str) -> Any:
        if name not in self._cache:
            if name not in self._factories:
                raise KeyError(f"Toolbox has no component '{name}'")
            self._cache[name] = self._factories[name]()
        return self._cache[name]


@dataclass
class RunContext:
    request: ChangeRequest
    ledger: Ledger
    tools: Toolbox
    results: Dict[str, Any] = field(default_factory=dict)          # blackboard: agent id -> result
    contributions: Dict[str, AgentContribution] = field(default_factory=dict)

    def result(self, agent_id: str) -> Any:
        return self.results.get(agent_id)

    def succeeded(self, agent_id: str) -> bool:
        c = self.contributions.get(agent_id)
        return bool(c and c.status in (AgentStatus.OK, AgentStatus.DEGRADED) and agent_id in self.results)


class Agent:
    spec: AgentSpec

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        """Return this agent's contribution and its raw result (stored on the blackboard)."""
        raise NotImplementedError


def status_from(*flags: Optional[str]) -> AgentStatus:
    """Map existing llm_status / graph_status values to an agent status."""
    return AgentStatus.DEGRADED if any(f not in (None, "ok") for f in flags) else AgentStatus.OK


def unique(items: List[str]) -> List[str]:
    return list(dict.fromkeys(i for i in items if i))
