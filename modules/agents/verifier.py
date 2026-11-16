"""
modules/agents/verifier.py — the Verification agent (critic).

Checks the claims of the language-model agents against the knowledge graph and against each
other, with fixed rules. It marks findings verified or in conflict, adds the gaps it finds,
and sets the human checkpoints. It never changes another agent's answer.

What it checks (stated in the UI as its limits too):
  * asset identifiers named by the Risk agent exist in the graph, and are within the computed reach;
  * P&ID tags suggested by the Review agent exist as P&ID documents or assets in the graph;
  * the Risk and Review agents agree on HAZOP and PSSR, and agree with similar past changes;
  * the overall risk rating is within the range of ratings of similar past changes;
  * which agents ran degraded or failed.
It does not judge the meaning of free text.
"""
from __future__ import annotations

import re
from typing import Any, List, Set, Tuple

from core.provenance import (
    AgentContribution,
    AgentStatus,
    Basis,
    CheckpointKind,
    Gap,
    SourceKind,
    Verification,
)

from .base import Agent, AgentSpec, RunContext
from .specialists import RATINGS, _yes_no

_ASSET_ID = re.compile(r"\b[A-Z]{1,4}-[A-Z0-9]{2,4}\b")


class VerificationAgent(Agent):
    spec = AgentSpec(
        id="verifier", name="Verification Agent",
        role="Checks the language-model agents' claims against the knowledge graph and each other; sets human checkpoints.",
        pattern="verifier", stage=4, basis=Basis.RULE,
        components=("modules.agents.verifier (fixed rules)", "core.neo4j_client.Neo4jClient"),
        sources=(SourceKind.KNOWLEDGE_GRAPH, SourceKind.ENGINEERING_RECORD, SourceKind.DOCUMENT),
        reads=("retrieval", "impact", "risk", "review", "cost", "allocation"),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        L = ctx.ledger
        c = self.spec.contribution()
        known_assets, known_pids = self._catalogue(ctx)
        checks: List[str] = []

        # 1. Assets named by the Risk agent.
        risk = ctx.result("risk") or {}
        impact = ctx.result("impact") or {}
        reach_ids: Set[str] = {a["asset_id"] for a in ((impact.get("reach") or {}).get("assets") or [])}
        named = {*(risk.get("directly_affected") or []), *(risk.get("indirectly_affected") or [])}
        for r in risk.get("risks") or []:
            named.update(_ASSET_ID.findall(str(r.get("description") or "")))
        named.discard(ctx.request.asset_id)
        if named and known_assets:
            unknown = sorted(a for a in named if a not in known_assets)
            outside = sorted(a for a in named if a in known_assets and reach_ids and a not in reach_ids)
            inside = sorted(a for a in named if a in reach_ids)
            ev = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Asset:{a}", a) for a in inside]
            if unknown:
                c.findings.append(L.finding(self.spec.id, f"Assets named by the Risk agent that are not in the knowledge graph: "
                                                          f"{', '.join(unknown)}.", Basis.RULE,
                                            verification=Verification.CONFLICT, note="Possible fabricated identifier."))
                self._mark(ctx, "risk", lambda f: any(u in f.statement for u in unknown), Verification.CONFLICT,
                           "Names an asset that is not in the knowledge graph.")
                L.checkpoint(CheckpointKind.VERIFICATION, f"Check the risk analysis: it names {', '.join(unknown)}, "
                                                          "which do not exist in the knowledge graph.",
                             "A language model may produce identifiers that do not exist.", "Process safety engineer",
                             self.spec.id)
            if outside:
                c.gaps.append(Gap("uncertainty", self.spec.id, f"The Risk agent names {', '.join(outside)}, which exist but are "
                                                               "outside the computed downstream reach."))
            if inside:
                c.findings.append(L.finding(self.spec.id, f"Assets named by the Risk agent and confirmed in the computed reach: "
                                                          f"{', '.join(inside)}.", Basis.RULE, ev,
                                            verification=Verification.VERIFIED))
            checks.append("asset identifiers")

        # 2. P&ID tags suggested by the Review agent.
        review = ctx.result("review") or {}
        tags = [str(t).strip() for t in review.get("pid_tags") or [] if str(t).strip()]
        if tags and (known_pids or known_assets):
            bad = [t for t in tags if t not in known_pids and t not in known_assets]
            if bad:
                c.findings.append(L.finding(self.spec.id, f"Suggested P&ID tags not found in the knowledge graph: {', '.join(bad)}.",
                                            Basis.RULE, verification=Verification.CONFLICT))
                L.checkpoint(CheckpointKind.VERIFICATION, f"Confirm the P&ID references: {', '.join(bad)} were not found.",
                             "Suggested references must exist before they are relied on.", "Engineer assessing the change",
                             self.spec.id)
            checks.append("P&ID references")

        # 3. HAZOP / PSSR agreement between the two AI agents and with past changes.
        similar = (ctx.result("retrieval") or {}).get("similar_mocs") or []
        for label, review_key, risk_key, hist_key in (("HAZOP", "hazop_required", "hazop_triggered", "hazop_required"),
                                                      ("PSSR", "pssr_required", "pssr_required", "pssr_required")):
            a, b = _yes_no(review.get(review_key)), _yes_no(risk.get(risk_key))
            hist = [h for h in (_yes_no(m.get(hist_key)) for m in similar) if h is not None]
            majority = None if not hist else sum(hist) * 2 >= len(hist)
            sim_ev = [L.cite(SourceKind.ENGINEERING_RECORD, f"MoC:{m.get('moc_id')}", str(m.get("moc_id")),
                             f"{label} {'required' if _yes_no(m.get(hist_key)) else 'not required'}")
                      for m in similar if m.get("moc_id") and _yes_no(m.get(hist_key)) is not None]
            if a is None or b is None:
                c.gaps.append(Gap("missing", self.spec.id, f"{label}: at least one agent gave no answer."))
                continue
            if a != b:
                c.findings.append(L.finding(self.spec.id, f"{label}: the Review and Risk agents disagree.", Basis.RULE, sim_ev,
                                            verification=Verification.CONFLICT))
                for agent in ("review", "risk"):
                    self._mark(ctx, agent, lambda f, lb=label: lb in f.statement, Verification.CONFLICT,
                               f"The two AI agents disagree on {label}.")
                L.checkpoint(CheckpointKind.VERIFICATION, f"Decide whether a {label} is required.",
                             "The AI agents disagree.", "Process Safety Manager", self.spec.id)
            elif majority is not None and a != majority:
                c.findings.append(L.finding(self.spec.id, f"{label}: both agents say {'required' if a else 'not required'}, "
                                                          "unlike most similar past changes.", Basis.RULE, sim_ev,
                                            verification=Verification.CONFLICT))
                for agent in ("review", "risk"):
                    self._mark(ctx, agent, lambda f, lb=label: lb in f.statement, Verification.CONFLICT,
                               f"Differs from most similar past changes on {label}.")
                L.checkpoint(CheckpointKind.VERIFICATION, f"Confirm the {label} decision.",
                             "The AI suggestion differs from similar past changes.", "Process Safety Manager", self.spec.id)
            else:
                note = "Both AI agents agree" + (" and so do similar past changes." if majority is not None else ".")
                c.findings.append(L.finding(self.spec.id, f"{label} {'required' if a else 'not required'}: {note}",
                                            Basis.RULE, sim_ev, verification=Verification.VERIFIED))
                for agent in ("review", "risk"):
                    self._mark(ctx, agent, lambda f, lb=label: lb in f.statement, Verification.VERIFIED, note)
            if a:
                L.checkpoint(CheckpointKind.APPROVAL, f"Hold the {label} before implementation.",
                             f"{label} is required for this change.", "Process Safety Manager", self.spec.id)
        checks.append("HAZOP/PSSR agreement")

        # 4. Risk rating against similar past changes.
        rating = risk.get("overall_rating")
        past = [m.get("risk_level") for m in similar if m.get("risk_level") in RATINGS]
        if rating in RATINGS and past:
            lo, hi = min(past, key=RATINGS.index), max(past, key=RATINGS.index)
            ok = RATINGS.index(lo) <= RATINGS.index(rating) <= RATINGS.index(hi)
            ev = [L.cite(SourceKind.ENGINEERING_RECORD, f"MoC:{m.get('moc_id')}", str(m.get("moc_id")),
                         f"risk {m.get('risk_level')}") for m in similar if m.get("risk_level") in RATINGS]
            c.findings.append(L.finding(self.spec.id, f"Risk rating {rating} {'is within' if ok else 'is outside'} the range of "
                                                      f"similar past changes ({lo} to {hi}).", Basis.RULE, ev,
                                        verification=Verification.VERIFIED if ok else Verification.UNVERIFIED))
            self._mark(ctx, "risk", lambda f: f.statement.startswith("Overall risk rated"),
                       Verification.VERIFIED if ok else Verification.UNVERIFIED,
                       f"{'Within' if ok else 'Outside'} the range of similar past changes ({lo} to {hi}).")
            checks.append("risk rating")

        # 5. Agents that did not run fully.
        for contrib in ctx.contributions.values():
            if contrib.status in (AgentStatus.DEGRADED, AgentStatus.FAILED):
                c.gaps.append(Gap("missing", self.spec.id, f"{contrib.name} {contrib.status.value}: its part of the assessment "
                                                           "is incomplete."))

        # 6. Who decides, from the allocation.
        alloc = ((ctx.result("allocation") or {}).get("result") or {}).get("allocation")
        if alloc == "HUMAN_LED":
            L.checkpoint(CheckpointKind.APPROVAL, "Assign a named engineer to lead this decision.",
                         "The decision-allocation model recommends human-led control.", "Engineering manager", self.spec.id)
        elif alloc == "AI_SUPPORTED":
            L.checkpoint(CheckpointKind.VERIFICATION, "Review the AI-prepared assessment before deciding.",
                         "The decision-allocation model recommends AI-supported control: AI prepares, a person decides.",
                         "Engineer assessing the change", self.spec.id)
        elif alloc == "AI_LED":
            L.checkpoint(CheckpointKind.VERIFICATION, "Oversee the AI-led decision and confirm it.",
                         "AI-led still requires human oversight.", "Engineer assessing the change", self.spec.id)

        c.gaps.append(Gap("uncertainty", self.spec.id, "The verification rules check identifiers, review flags and ratings; "
                                                       "they do not judge the meaning of free text."))
        n_conf = sum(1 for f in c.findings if f.verification is Verification.CONFLICT)
        c.summary = f"Checked {', '.join(checks) or 'nothing (inputs missing)'}; {n_conf} conflict(s)."
        return c, {"checks": checks, "conflicts": n_conf}

    # ── helpers ─────────────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _mark(ctx: RunContext, agent: str, match, status: Verification, note: str) -> None:
        contrib = ctx.contributions.get(agent)
        if not contrib:
            return
        for f in contrib.findings:
            if f.basis in (Basis.LLM, Basis.RULE) and match(f):
                # never downgrade a conflict found earlier
                if f.verification is not Verification.CONFLICT:
                    f.verification, f.note = status, note

    @staticmethod
    def _catalogue(ctx: RunContext) -> Tuple[Set[str], Set[str]]:
        try:
            client = ctx.tools.get("neo4j")
            assets = {r["id"] for r in client.get_all_assets() if r.get("id")}
            pids = {r["pid"] for r in client._run("MATCH (p:PIDDocument) RETURN p.pid_ref AS pid") if r.get("pid")}
            return assets, pids
        except Exception:                                            # noqa: BLE001 — verification degrades, never fails
            return set(), set()

