"""
modules/agents/registry.py — the declared agents and the order the Supervisor runs them in.

This list is the single source for the agent line-up: the Supervisor runs it, the API serves
it (GET /api/case/agents), and docs/generated/agents.md is generated from it.
"""
from __future__ import annotations

from typing import Dict, List

from core.provenance import Basis, SourceKind

from .base import Agent, AgentSpec
from .specialists import (
    AllocationAgent,
    CostAgent,
    ImpactAgent,
    KnowledgeRetrievalAgent,
    ReviewRequirementsAgent,
    RiskAgent,
)
from .verifier import VerificationAgent

SUPERVISOR = AgentSpec(
    id="supervisor", name="Supervisor",
    role="Plans the assessment, runs the agents stage by stage (in parallel within a stage), isolates failures "
         "and assembles the case record. Its routing is fixed code, not a model decision.",
    pattern="supervisor", stage=0, basis=Basis.DETERMINISTIC,
    components=("modules.agents.supervisor.Supervisor",),
    sources=(SourceKind.USER_INPUT,),
)


def build_agents() -> List[Agent]:
    return [KnowledgeRetrievalAgent(), ImpactAgent(), RiskAgent(), ReviewRequirementsAgent(), CostAgent(),
            AllocationAgent(), VerificationAgent()]


def stages(agents: List[Agent]) -> List[List[Agent]]:
    by_stage: Dict[int, List[Agent]] = {}
    for a in agents:
        by_stage.setdefault(a.spec.stage, []).append(a)
    return [by_stage[k] for k in sorted(by_stage)]


def registry() -> Dict:
    agents = build_agents()
    return {
        "patterns": [
            {"id": "supervisor", "name": "Supervisor (hierarchical)",
             "use": "A deterministic supervisor plans the run and assembles the result."},
            {"id": "parallel", "name": "Parallel fan-out", "use": "Agents in the same stage run at the same time."},
            {"id": "sequential", "name": "Sequential stages with shared state",
             "use": "Later stages read earlier results from a shared case record (blackboard)."},
            {"id": "verifier", "name": "Independent verifier (critic)",
             "use": "A rule-based agent checks the language-model agents against the knowledge graph."},
            {"id": "human", "name": "Human in the loop",
             "use": "Every case ends with human checkpoints; allocation is advice, not decision authority."},
        ],
        "supervisor": SUPERVISOR.to_dict(),
        "agents": [a.spec.to_dict() for a in agents],
        "stages": [[a.spec.id for a in s] for s in stages(agents)],
        "source_kinds": [{"id": k.value, "label": k.label} for k in SourceKind],
    }
