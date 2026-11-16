"""
modules/agents/specialists.py — the specialist agents.

Each agent runs one existing component and records, in the shared Ledger, what it found,
where the knowledge came from (SourceKind) and on which evidence. No new analysis is added:
risk is RiskEngine, review needs are SmartFormModule, cost is CostPredictor, reach is the
graph store, propagation is DowntimePropagator, allocation is the decision-allocation engine.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from core.provenance import AgentContribution, AgentStatus, Basis, Gap, SourceKind, Verification

from .base import Agent, AgentSpec, RunContext, status_from, unique

log = logging.getLogger(__name__)

YES, NO = "Yes", "No"
RATINGS = ("Low", "Medium", "High", "Critical")

# Graph equipment types -> the categories the cost model was trained on (modules/cost_predictor.py).
ASSET_CATEGORY = {
    "pump": "Pump", "control valve": "Control Valve", "reactor": "Reactor", "cyclone": "Cyclone Separator",
    "expander": "Flue gas expander", "piping": "Piping", "fractionator": "Fractionator",
    "compressor": "Compressor", "blower": "Compressor", "safety system": "Procedure",
}


def _yes_no(value: Any) -> Optional[bool]:
    v = str(value or "").strip().lower()
    return True if v in ("yes", "true", "required") else False if v in ("no", "false", "not required") else None


# ── Stage 1 ─────────────────────────────────────────────────────────────────────────────────────

class KnowledgeRetrievalAgent(Agent):
    spec = AgentSpec(
        id="retrieval", name="Knowledge Retrieval Agent",
        role="Finds past changes, hazards, incidents and lessons related to the proposed change.",
        pattern="specialist", stage=1, basis=Basis.RETRIEVAL,
        components=("core.rag_pipeline.HybridRetriever.retrieve", "core.vector_store.VectorStore.search",
                    "core.neo4j_client.Neo4jClient"),
        sources=(SourceKind.ENGINEERING_RECORD, SourceKind.KNOWLEDGE_GRAPH),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        req, L = ctx.request, ctx.ledger
        context = ctx.tools.get("rag").get_raw_context(req.description, asset_id=req.asset_id,
                                                        change_type=req.change_type, moc_id=req.moc_id)
        c = self.spec.contribution()
        hits = context.get("vector_hits") or []
        hit_ids = []
        for h in hits[:5]:
            meta = h.get("metadata") or {}
            hit_ids.append(L.cite(SourceKind.ENGINEERING_RECORD, f"MoC:{h.get('moc_id')}",
                                  f"{h.get('moc_id')} {str(meta.get('title') or '')[:60]}".strip(),
                                  f"semantic similarity {float(h.get('similarity') or 0):.2f}"))
        if hits:
            best = hits[0]
            c.findings.append(L.finding(
                self.spec.id, f"{len(hits)} similar past changes found; the closest is {best.get('moc_id')} "
                              f"(similarity {float(best.get('similarity') or 0):.2f}).",
                Basis.RETRIEVAL, hit_ids, verification=Verification.NOT_APPLICABLE))
        else:
            c.gaps.append(Gap("missing", self.spec.id, "No similar past change was found in the change records."))

        hazards = context.get("hazards") or []
        hz_ids = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Hazard:{h.get('hazard_id')}", str(h.get("hazard_id")),
                         str(h.get("description") or "")[:140]) for h in hazards if h.get("hazard_id")]
        if hazards:
            c.findings.append(L.finding(self.spec.id, f"{len(hazards)} hazard(s) recorded against changes to {req.asset_id}.",
                                        Basis.DETERMINISTIC, hz_ids, verification=Verification.VERIFIED,
                                        note="Read directly from the knowledge graph."))
        incidents = context.get("incidents") or []
        if incidents:
            inc_ids = [L.cite(SourceKind.ENGINEERING_RECORD, f"Incident:{i.get('incident_id')}", str(i.get("incident_id")),
                              str(i.get("description") or "")[:140]) for i in incidents if i.get("incident_id")]
            c.findings.append(L.finding(self.spec.id, f"{len(incidents)} past incident(s) on this asset.", Basis.DETERMINISTIC,
                                        inc_ids, verification=Verification.VERIFIED))
        lessons = context.get("lessons") or []
        if lessons:
            ll_ids = [L.cite(SourceKind.ENGINEERING_RECORD, f"Lesson:{x.get('moc_id')}", f"Lesson from {x.get('moc_id')}",
                             str(x.get("summary") or "")[:140]) for x in lessons if x.get("moc_id")]
            c.findings.append(L.finding(self.spec.id, f"{len(lessons)} lesson(s) learned from similar change types.",
                                        Basis.RETRIEVAL, ll_ids, verification=Verification.NOT_APPLICABLE))
        c.summary = f"{len(hits)} similar changes, {len(hazards)} hazards, {len(incidents)} incidents, {len(lessons)} lessons."
        return c, context


class ImpactAgent(Agent):
    spec = AgentSpec(
        id="impact", name="Impact & Dependency Agent",
        role="Traces which equipment, areas and processes the change reaches, and how downtime would propagate.",
        pattern="specialist", stage=1, basis=Basis.DETERMINISTIC,
        components=("modules.decision_allocation.graph_store.get_asset_facts",
                    "modules.decision_allocation.graph_store.get_reach",
                    "core.downtime_propagator.DowntimePropagator.propagate"),
        sources=(SourceKind.ONTOLOGY, SourceKind.KNOWLEDGE_GRAPH, SourceKind.COMPUTATIONAL_MODEL),
    )
    SOURCE_DOWNTIME_HOURS = 24.0

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        from modules.decision_allocation import graph_store

        req, L = ctx.request, ctx.ledger
        client = ctx.tools.get("neo4j")
        c = self.spec.contribution()
        facts = graph_store.get_asset_facts(client, req.asset_id)
        if not facts:
            c.status = AgentStatus.DEGRADED
            c.gaps.append(Gap("missing", self.spec.id, f"Asset {req.asset_id} is not in the knowledge graph."))
            c.summary = "Asset not found."
            return c, {"asset": None}
        asset = facts.get("asset") or {}
        reach = graph_store.get_reach(client, req.asset_id)
        asset_ev = L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Asset:{req.asset_id}", req.asset_id,
                          f"{asset.get('equipment_type')}, criticality {asset.get('criticality')}")
        area_ev = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Area:{a}", a) for a in facts.get("areas") or []]
        reached_ev = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Asset:{r['asset_id']}", r["asset_id"],
                             f"{r.get('equipment_type')}, criticality {r.get('criticality')}, {r['hops']} hop(s)")
                      for r in reach["assets"]]
        c.findings.append(L.finding(
            self.spec.id,
            f"{req.asset_id} ({asset.get('equipment_type')}, criticality {asset.get('criticality')}) reaches "
            f"{reach['asset_count']} downstream asset(s) in {len(reach['areas'])} area(s); directly: "
            f"{', '.join(reach['direct']) or 'none'}.",
            Basis.DETERMINISTIC, [asset_ev, *area_ev, *reached_ev[:12]], verification=Verification.VERIFIED,
            note="Computed by graph traversal over stored relationships."))
        if reach["critical_assets"]:
            crit_ev = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Asset:{a}", a) for a in reach["critical_assets"]]
            c.findings.append(L.finding(self.spec.id, f"Criticality-5 assets reached: {', '.join(reach['critical_assets'])}.",
                                        Basis.DETERMINISTIC, crit_ev, verification=Verification.VERIFIED))
        if facts.get("esd_target"):
            c.findings.append(L.finding(self.spec.id, f"{req.asset_id} is shut down by the Emergency Shutdown System.",
                                        Basis.DETERMINISTIC, [asset_ev], verification=Verification.VERIFIED))

        propagation: Dict[str, Any] = {}
        try:
            from core.downtime_propagator import propagation_result_to_dict
            result = ctx.tools.get("propagator").propagate(req.asset_id, self.SOURCE_DOWNTIME_HOURS)
            propagation = propagation_result_to_dict(result)
            rels = unique([r for a in propagation.get("affected_assets", []) for r in a.get("relationship_chain") or []])
            onto_ev = [L.cite(SourceKind.ONTOLOGY, f"Relationship:{r}", r, "relationship type traversed") for r in rels]
            model_ev = L.cite(SourceKind.COMPUTATIONAL_MODEL, "Model:downtime-propagation", "Downtime propagation model",
                              "coupling per relationship type, hop decay and criticality amplifier")
            c.findings.append(L.finding(
                self.spec.id,
                f"A {self.SOURCE_DOWNTIME_HOURS:g}-hour outage at {req.asset_id} propagates "
                f"{propagation.get('total_propagated_hours')} hours across {propagation.get('total_affected')} asset(s).",
                Basis.DETERMINISTIC, [model_ev, asset_ev, *onto_ev], verification=Verification.NOT_APPLICABLE))
            c.gaps.append(Gap("assumption", self.spec.id,
                              f"Propagation assumes a {self.SOURCE_DOWNTIME_HOURS:g}-hour outage at the source."))
            c.gaps.append(Gap("uncertainty", self.spec.id,
                              "Propagation coefficients are modelling assumptions, not measured plant behaviour."))
        except Exception as exc:                                   # noqa: BLE001 — propagation is optional
            log.warning("Propagation failed for %s: %s", req.asset_id, exc)
            c.status = AgentStatus.DEGRADED
            c.gaps.append(Gap("missing", self.spec.id, "Downtime propagation could not be computed."))
        c.summary = f"{reach['asset_count']} assets in {len(reach['areas'])} areas reached."
        return c, {"facts": facts, "reach": reach, "propagation": propagation}


# ── Stage 2 ─────────────────────────────────────────────────────────────────────────────────────

class RiskAgent(Agent):
    spec = AgentSpec(
        id="risk", name="Risk Assessment Agent",
        role="Identifies the main risks, their severity and mitigations, from graph evidence.",
        pattern="specialist", stage=2, basis=Basis.LLM,
        components=("modules.risk_engine.RiskEngine.analyse", "core.llm.gateway (structured output)"),
        sources=(SourceKind.KNOWLEDGE_GRAPH, SourceKind.ENGINEERING_RECORD, SourceKind.LLM_INTERPRETATION),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        req, L = ctx.request, ctx.ledger
        r = ctx.tools.get("risk_engine").analyse(req.change_type, req.asset_id, req.description)
        c = self.spec.contribution(status=status_from(r.get("llm_status"), r.get("graph_status")))
        llm_ev = L.cite(SourceKind.LLM_INTERPRETATION, "LLM:risk-analysis", "Risk analysis by the language model",
                        "structured output, schema-validated")
        hz_ev = [L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Hazard:{h.get('hazard_id')}", str(h.get("hazard_id")),
                        str(h.get("description") or "")[:140]) for h in r.get("hazards") or [] if h.get("hazard_id")]
        if r.get("llm_status") == "ok":
            c.findings.append(L.finding(self.spec.id, f"Overall risk rated {r.get('overall_rating')}.", Basis.LLM,
                                        [llm_ev, *hz_ev]))
            for risk in (r.get("risks") or [])[:5]:
                c.findings.append(L.finding(self.spec.id, f"[{risk.get('severity')}] {risk.get('description')}", Basis.LLM,
                                            [llm_ev, *hz_ev]))
            c.findings.append(L.finding(self.spec.id, f"HAZOP triggered: {r.get('hazop_triggered')}; PSSR required: "
                                                      f"{r.get('pssr_required')}.", Basis.LLM, [llm_ev]))
        else:
            c.gaps.append(Gap("missing", self.spec.id, "The AI service was unavailable: no risk rating; graph hazards only."))
        if r.get("graph_status") != "ok":
            c.gaps.append(Gap("missing", self.spec.id, "The knowledge graph was unavailable to the risk engine."))
        c.gaps.append(Gap("uncertainty", self.spec.id,
                          "Risk descriptions and ratings are a language-model interpretation of the evidence."))
        c.summary = f"Overall {r.get('overall_rating')}; {len(r.get('risks') or [])} risks; {len(r.get('mitigations') or [])} mitigations."
        return c, r


class ReviewRequirementsAgent(Agent):
    spec = AgentSpec(
        id="review", name="Review Requirements Agent",
        role="Suggests approvers, required documents and whether HAZOP and PSSR reviews are needed.",
        pattern="specialist", stage=2, basis=Basis.LLM,
        components=("modules.smart_forms.SmartFormModule.get_prefill_suggestions", "core.llm.gateway (structured output)"),
        sources=(SourceKind.KNOWLEDGE_GRAPH, SourceKind.DOCUMENT, SourceKind.ENGINEERING_RECORD,
                 SourceKind.LLM_INTERPRETATION),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        req, L = ctx.request, ctx.ledger
        s = ctx.tools.get("smart_forms").get_prefill_suggestions(req.change_type, req.asset_id, req.description)
        c = self.spec.contribution(status=status_from(s.get("llm_status"), s.get("graph_status")))
        llm_ev = L.cite(SourceKind.LLM_INTERPRETATION, "LLM:review-requirements", "Review suggestions by the language model",
                        "structured output, schema-validated")
        role_ev = [L.cite(SourceKind.ENGINEERING_RECORD, f"ApproverRole:{a.get('approver')}", str(a.get("approver")),
                          f"approved {a.get('freq')} past change(s) of this type") for a in s.get("graph_approvers") or []
                   if a.get("approver")]
        pid_refs = unique([p for row in s.get("graph_pid_entities") or [] for p in (row.get("pid_refs") or [])])
        pid_ev = [L.cite(SourceKind.DOCUMENT, f"PIDDocument:{p}", p, f"P&ID referenced by past changes to {req.asset_id}")
                  for p in pid_refs]
        basis = Basis.LLM if s.get("llm_status") == "ok" else Basis.RULE
        c.findings.append(L.finding(self.spec.id, f"HAZOP required: {s.get('hazop_required')}.", basis, [llm_ev]))
        c.findings.append(L.finding(self.spec.id, f"PSSR required: {s.get('pssr_required')}.", basis, [llm_ev]))
        if s.get("approvers"):
            c.findings.append(L.finding(self.spec.id, f"Suggested approvers: {', '.join(s['approvers'])}.", basis,
                                        [llm_ev, *role_ev]))
        if pid_ev:
            c.findings.append(L.finding(self.spec.id, f"P&IDs to review: {', '.join(pid_refs)}.", Basis.DETERMINISTIC,
                                        pid_ev, verification=Verification.VERIFIED, note="P&IDs linked in the knowledge graph."))
        else:
            c.gaps.append(Gap("missing", self.spec.id, f"No P&ID document is linked to past changes on {req.asset_id}."))
        if s.get("llm_status") != "ok":
            c.gaps.append(Gap("missing", self.spec.id, "The AI service was unavailable: suggestions come from past changes only."))
        c.summary = f"HAZOP {s.get('hazop_required')}, PSSR {s.get('pssr_required')}, {len(s.get('approvers') or [])} approver(s)."
        return c, s


# ── Stage 3 ─────────────────────────────────────────────────────────────────────────────────────

class CostAgent(Agent):
    spec = AgentSpec(
        id="cost", name="Cost & Downtime Agent",
        role="Estimates cost and downtime with ranges, and explains the estimate.",
        pattern="specialist", stage=3, basis=Basis.ML,
        components=("modules.cost_predictor.CostPredictor.predict",),
        sources=(SourceKind.ML_MODEL, SourceKind.KNOWLEDGE_GRAPH, SourceKind.LLM_INTERPRETATION),
        reads=("impact", "risk"),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        req, L = ctx.request, ctx.ledger
        c = self.spec.contribution()
        equipment = str(((ctx.result("impact") or {}).get("facts") or {}).get("asset", {}).get("equipment_type") or "")
        category = ASSET_CATEGORY.get(equipment.lower(), "Other")
        rating = (ctx.result("risk") or {}).get("overall_rating")
        if rating not in RATINGS:
            c.gaps.append(Gap("assumption", self.spec.id, "No risk rating was available; the cost model was given 'Medium'."))
            rating = "Medium"
        p = ctx.tools.get("cost_predictor").predict(req.change_type, req.asset_id, category, rating, req.description)
        c.status = status_from(p.get("llm_status"), p.get("graph_status"))
        model_ev = L.cite(SourceKind.ML_MODEL, "Model:cost-downtime", "Cost and downtime model",
                          str(p.get("models_used") or ""))
        feat_ev = L.cite(SourceKind.KNOWLEDGE_GRAPH, f"Features:{req.asset_id}", f"Graph features for {req.asset_id}",
                         f"{(p.get('features') or {}).get('n_dependencies')} dependencies, "
                         f"{(p.get('features') or {}).get('n_hazards')} hazards")
        lo, hi = (p.get("cost_ci") or [None, None])[:2]
        dlo, dhi = (p.get("downtime_ci") or [None, None])[:2]
        c.findings.append(L.finding(self.spec.id, f"Estimated cost ${p.get('cost_estimate'):,.0f} (range ${lo:,.0f} to ${hi:,.0f}).",
                                    Basis.ML, [model_ev, feat_ev], verification=Verification.NOT_APPLICABLE))
        c.findings.append(L.finding(self.spec.id, f"Estimated downtime {p.get('downtime_estimate'):.1f} h (range {dlo:.1f} to {dhi:.1f} h).",
                                    Basis.ML, [model_ev, feat_ev], verification=Verification.NOT_APPLICABLE))
        if p.get("llm_status") == "ok":
            c.findings.append(L.finding(self.spec.id, "Explanation of the estimate written by the language model.", Basis.LLM,
                                        [L.cite(SourceKind.LLM_INTERPRETATION, "LLM:cost-explanation", "Cost explanation")]))
        c.gaps.append(Gap("uncertainty", self.spec.id, "Cost and downtime figures are illustrative until benchmarked: "
                                                        "the model is fitted to ten historical changes."))
        c.gaps.append(Gap("uncertainty", self.spec.id, "The ranges are fixed percentages (cost 25 %, downtime 30 %), "
                                                        "not statistical confidence intervals."))
        c.gaps.append(Gap("assumption", self.spec.id, f"Asset category '{category}' and risk level '{rating}' were used as model inputs."))
        c.summary = f"${p.get('cost_estimate'):,.0f}, {p.get('downtime_estimate'):.1f} h downtime."
        return c, {**p, "asset_category": category, "risk_level_used": rating}


class AllocationAgent(Agent):
    spec = AgentSpec(
        id="allocation", name="Decision Allocation Agent",
        role="Recommends whether the decision should be AI-led, AI-supported or human-led.",
        pattern="specialist", stage=3, basis=Basis.DETERMINISTIC,
        components=("modules.decision_allocation.service.DecisionAllocationService.assess_change",
                    "core.allocation.engine.score"),
        sources=(SourceKind.COMPUTATIONAL_MODEL, SourceKind.KNOWLEDGE_GRAPH, SourceKind.ASSUMPTION),
        reads=("risk", "review"),
    )

    def run(self, ctx: RunContext) -> Tuple[AgentContribution, Any]:
        from modules.decision_allocation.provenance import record_allocation

        req = ctx.request
        risk, review = ctx.result("risk") or {}, ctx.result("review") or {}
        c = self.spec.contribution()
        # The HAZOP/PSSR need is an INPUT to the model. Use it only when both AI agents agree;
        # otherwise pass "unknown", which the characteriser treats cautiously.
        hazop = _agreed(review.get("hazop_required"), risk.get("hazop_triggered"))
        pssr = _agreed(review.get("pssr_required"), risk.get("pssr_required"))
        service = ctx.tools.get("allocation")
        if req.moc_id:
            # An existing MoC: use its recorded / reference characterisation (graph facts, not AI suggestions).
            assessment = service.assess_moc(req.moc_id)
            c.gaps.append(Gap("assumption", self.spec.id, f"The characterisation of {req.moc_id} on record was used; "
                                                          "the AI agents' HAZOP/PSSR suggestions were not needed as inputs."))
            record_allocation(assessment, ctx.ledger, c)
            return c, assessment
        assessment = service.assess_change(req.change_type, req.asset_id, req.description,
                                           hazop_required=hazop, pssr_required=pssr)
        if hazop is None:
            c.gaps.append(Gap("uncertainty", self.spec.id, "The Risk and Review agents did not agree on whether a HAZOP is "
                                                           "needed (or did not answer), so the model treated it as unknown."))
        else:
            c.gaps.append(Gap("assumption", self.spec.id, f"HAZOP {'required' if hazop else 'not required'} was taken from "
                                                          "the Risk and Review agents (language-model suggestions that agree)."))
        record_allocation(assessment, ctx.ledger, c)
        return c, assessment


def _agreed(a: Any, b: Any) -> Optional[bool]:
    x, y = _yes_no(a), _yes_no(b)
    return x if (x is not None and x == y) else None
