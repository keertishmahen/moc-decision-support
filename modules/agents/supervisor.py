"""
modules/agents/supervisor.py — runs the agents and assembles the case record.

    stage 1  Knowledge Retrieval  |  Impact & Dependency          (in parallel)
    stage 2  Risk Assessment      |  Review Requirements          (in parallel)
    stage 3  Cost & Downtime      |  Decision Allocation          (in parallel; need stage 2)
    stage 4  Verification                                           (reads everything)

A failing agent is recorded as failed and the case continues; agents that need its result
are skipped with a stated reason. The case record answers three questions: what happens,
who decides, and why the recommendation can (or cannot yet) be trusted.
"""
from __future__ import annotations

import datetime
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from core.provenance import AgentStatus, Gap, Ledger, SourceKind, summarise, to_jsonable

from .base import Agent, ChangeRequest, RunContext, Toolbox
from .registry import SUPERVISOR, build_agents, stages

log = logging.getLogger(__name__)

# Progress events: run_started, stage_started, agent_started, agent_finished, agent_skipped, run_finished.
Listener = Callable[[Dict[str, Any]], None]


class Supervisor:
    def __init__(self, tools: Toolbox, agents: Optional[List[Agent]] = None, model_info: Optional[Dict] = None):
        self.tools = tools
        self.agents = agents if agents is not None else build_agents()
        self.model_info = model_info or {}

    def assess(self, request: ChangeRequest, on_event: Optional[Listener] = None) -> Dict[str, Any]:
        """Run every agent and return the case record. `on_event`, if given, receives progress
        events as plain dicts (see `Listener` and docs/design-docs/multi-agent-trust.md); it is
        called from worker threads and a failing listener never affects the case."""
        run_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        ledger = Ledger()
        ctx = RunContext(request=request, ledger=ledger, tools=self.tools)
        ledger.cite(SourceKind.USER_INPUT, "Input:change", f"{request.change_type} change to {request.asset_id}",
                    request.description[:300])

        def emit(event: Dict[str, Any]) -> None:
            if on_event is None:
                return
            try:
                on_event(event)
            except Exception:                                      # noqa: BLE001 — a listener never sinks the case
                log.debug("case progress listener failed", exc_info=True)

        plan = stages(self.agents)
        emit({"type": "run_started", "run_id": run_id, "stages": [[a.spec.id for a in s] for s in plan]})
        timeline: List[Dict[str, Any]] = []
        for stage_agents in plan:
            emit({"type": "stage_started", "stage": stage_agents[0].spec.stage,
                  "agents": [a.spec.id for a in stage_agents]})
            runnable, skipped = [], []
            for agent in stage_agents:
                missing = [n for n in agent.spec.needs if not ctx.succeeded(n)]
                (skipped if missing else runnable).append((agent, missing))
            for agent, missing in skipped:
                ctx.contributions[agent.spec.id] = agent.spec.contribution(
                    status=AgentStatus.SKIPPED, summary=f"Skipped: needs {', '.join(missing)}.",
                    gaps=[Gap("missing", agent.spec.id, f"Not run because {', '.join(missing)} did not complete.")])
                emit({"type": "agent_skipped", "agent": agent.spec.id, "name": agent.spec.name,
                      "reason": f"needs {', '.join(missing)}"})
            with ThreadPoolExecutor(max_workers=max(1, len(runnable))) as pool:
                futures = [(agent, pool.submit(self._run_one, agent, ctx, emit)) for agent, _ in runnable]
                for agent, fut in futures:
                    contribution, result = fut.result()
                    ctx.contributions[agent.spec.id] = contribution
                    if result is not None:
                        ctx.results[agent.spec.id] = result
            timeline.append({"stage": stage_agents[0].spec.stage, "agents": [a.spec.id for a in stage_agents]})

        total_ms = int((time.perf_counter() - started) * 1000)
        ordered = [ctx.contributions[a.spec.id] for a in self.agents if a.spec.id in ctx.contributions]
        supervisor = SUPERVISOR.contribution(
            duration_ms=total_ms,
            summary=f"Ran {len(ordered)} agents in {len(plan)} stages; "
                    f"{sum(1 for c in ordered if c.status is AgentStatus.OK)} ok, "
                    f"{sum(1 for c in ordered if c.status is AgentStatus.DEGRADED)} degraded, "
                    f"{sum(1 for c in ordered if c.status in (AgentStatus.FAILED, AgentStatus.SKIPPED))} failed or skipped.")
        contributions = [supervisor, *ordered]
        why = summarise(contributions, ledger)
        log.info("case run %s: %s in %d ms", run_id, supervisor.summary, total_ms)
        emit({"type": "run_finished", "duration_ms": total_ms, "counts": why["counts"],
              "checkpoints": len(why["checkpoints"])})

        return {
            "run_id": run_id,
            "request": {"change_type": request.change_type, "asset_id": request.asset_id,
                        "description": request.description, "moc_id": request.moc_id},
            "what_happens": self._what_happens(ctx),
            "who_decides": ctx.result("allocation"),
            "why_trust": why,
            "trace": {
                "run_id": run_id,
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "duration_ms": total_ms,
                "stages": timeline,
                "agents": [{"agent": c.agent, "status": c.status.value, "duration_ms": c.duration_ms} for c in contributions],
                **self.model_info,
            },
        }

    # ── helpers ─────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _run_one(agent: Agent, ctx: RunContext, emit: Listener):
        t0 = time.perf_counter()
        emit({"type": "agent_started", "agent": agent.spec.id, "name": agent.spec.name, "stage": agent.spec.stage})
        try:
            contribution, result = agent.run(ctx)
        except Exception as exc:                                   # noqa: BLE001 — one agent never sinks the case
            log.warning("agent %s failed: %s: %s", agent.spec.id, type(exc).__name__, str(exc)[:300])
            contribution = agent.spec.contribution(
                status=AgentStatus.FAILED, summary="Failed.",
                error=f"{type(exc).__name__}",
                gaps=[Gap("missing", agent.spec.id, f"{agent.spec.name} could not complete; its part is missing.")])
            result = None
        contribution.duration_ms = int((time.perf_counter() - t0) * 1000)
        emit({"type": "agent_finished", "agent": agent.spec.id, "name": agent.spec.name,
              "status": contribution.status.value, "duration_ms": contribution.duration_ms,
              "summary": contribution.summary})
        return contribution, result

    @staticmethod
    def _what_happens(ctx: RunContext) -> Dict[str, Any]:
        impact = ctx.result("impact") or {}
        risk = ctx.result("risk") or {}
        review = ctx.result("review") or {}
        cost = ctx.result("cost") or {}
        retrieval = ctx.result("retrieval") or {}
        facts = impact.get("facts") or {}
        return to_jsonable({
            "asset": facts.get("asset"),
            "areas": facts.get("areas"),
            "esd_target": facts.get("esd_target"),
            "reach": impact.get("reach"),
            "propagation": {k: (impact.get("propagation") or {}).get(k)
                            for k in ("source_downtime", "total_affected", "total_propagated_hours", "summary")},
            "risk": {k: risk.get(k) for k in ("overall_rating", "risks", "mitigations", "hazop_triggered", "pssr_required",
                                              "reasoning", "directly_affected", "indirectly_affected", "llm_status")},
            "review": {k: review.get(k) for k in ("approvers", "documents", "hazop_required", "pssr_required", "pid_tags",
                                                  "risk_level", "llm_status")},
            "cost": {k: cost.get(k) for k in ("cost_estimate", "cost_ci", "downtime_estimate", "downtime_ci",
                                              "explanation", "asset_category", "risk_level_used", "llm_status")},
            "similar_changes": [{"moc_id": h.get("moc_id"), "similarity": h.get("similarity"),
                                 "title": (h.get("metadata") or {}).get("title")}
                                for h in (retrieval.get("vector_hits") or [])[:5]],
        })

