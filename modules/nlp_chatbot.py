"""
modules/nlp_chatbot.py  —  Module 4: Conversational NLP Interface
Fine-tuned for specific, grounded answers using the full Neo4j schema.
No generic fallbacks — every answer is anchored to retrieved graph data.
"""
import re
from collections import deque

from core.rag_pipeline import RAGPipeline, get_llm, _build_messages
from core.neo4j_client import Neo4jClient


def _clip(val, n: int, default: str = "") -> str:
    """Safe prefix slice — Neo4j OPTIONAL MATCH fields are often None."""
    if val is None:
        val = default
    return str(val)[:n]

# ── System prompt — strict grounding rules ─────────────────────────────────
SYSTEM_PROMPT = """You are MoCBot, a specialist assistant for the FCC Unit Management of Change (MoC) system at Refinery A.

KNOWLEDGE GRAPH INVENTORY (22 node types):
MoC, Asset, Hazard, RiskAssessment, LessonsLearned, Personnel, Incident, HAZOP, PSSR,
Parameter, WorkOrder, MaintenanceActivity, ImplementationOutcome, ApprovalStage, FailureMode,
PIDDocument, Area, Department, RiskScore, Plant, ProcessUnit, _GraphConfig

5-STAGE APPROVAL WORKFLOW (ApprovalStage nodes):
Stage 1: Change Identification — Initiating Engineer/Technician
Stage 2: Screening — Operations Supervisor / Unit Superintendent
Stage 3: Risk Assessment — Process Safety Engineer / HSE Engineer / Mechanical Integrity Engineer
Stage 4: Implementation Planning — Maintenance Manager / Instrumentation Engineer / Process Engineer
Stage 5: Final Approval — Safety Manager / Process Safety Manager / HSE Manager / Maintenance Manager

ALL 10 MoC RECORDS:
MoC-001: Feed Pump P-101 Replacement | Mechanical | Risk 12 (High) | Cost $118K | No incident
MoC-002: Feed Heater Control Valve FV-103 Upgrade | Instrumentation | Risk 8 (Medium) | Cost $36.5K
MoC-003: Reactor R-201 Temperature Setpoint 510→525°C | Process Parameter | Risk 8 (Medium) | Cost $7.5K | Threshold: Max 545°C
MoC-004: Cyclone Separator C-203 Inspection/Repair | Mechanical Maintenance | Risk 12 (High) | Cost $102K
MoC-005: Catalyst Slide Valve SV-204 Control System Upgrade | Instrumentation | Risk 12 (High) | Cost $67.5K
MoC-006: Catalyst Stripper Steam Optimization S-301 | Process & Instrumentation | Risk 12 (High) | Cost $92K | Incident: steam leakage
MoC-007: Flue Gas Expander EX-403 Performance Upgrade | Mechanical Efficiency | Risk 8 (Medium) | Cost $78K | Incident: misalignment trip
MoC-008: Fractionator Reflux Pump P-502 Replacement | Mechanical | Risk 12 (High) | Cost $135K | Incident: alignment issue
MoC-009: Emergency Shutdown Procedure Update | Procedural | Risk 10 (High) | Cost $22K | No incident
MoC-010: Catalyst Transfer Line CTL-205 Reinforcement | Mechanical Integrity | Risk 15 (High) | Cost $165K | Incident: weld defect

KEY ASSETS (22 assets):
P-101 (Feed Pump, crit=4), FV-103 (Feed Control Valve, crit=3), R-201 (Riser Reactor, crit=5),
C-203 (Cyclone Separator, crit=4), SV-204 (Catalyst Slide Valve, crit=5),
S-301 (Catalyst Stripper, crit=4), EX-403 (Flue Gas Expander, crit=3),
P-502 (Reflux Pump, crit=4), ESD-SYS (Emergency Shutdown System, crit=5),
CTL-205 (Catalyst Transfer Line, crit=5), RG-401 (Regenerator Vessel, crit=5),
F-501 (Main Fractionator, crit=5), K-402 (Air Blower, crit=4),
WGC-401 (Wet Gas Compressor, crit=5), V-101 (Feed Surge Drum, crit=3),
V-202 (Reactor Vessel, crit=5), E-102 (Feed Heater, crit=3),
FG-404 (Flue Gas Piping, crit=3), P-503 (Rebooster Pump, crit=3),
P-504 (Product Pump, crit=3), IV-303 (Steam Control Valve, crit=3), ST-302 (Steam Injection Line, crit=3)

FCC UNIT PROCESS FLOW TOPOLOGY (directed graph — use this to answer connectivity questions):
Feed section:  V-101 → P-101 → E-102 → FV-103 → R-201
Reactor loop:  R-201 → C-203 → SV-204 → RG-401 (catalyst circulation)
               R-201 → SV-204 → RG-401 (direct catalyst slide valve control)
               CTL-205 → R-201 (regenerated catalyst return loop)
               RG-401 → CTL-205 → R-201 (regenerator → transfer line → reactor)
Regeneration:  S-301 → RG-401 (stripped catalyst to regenerator)
               K-402 → RG-401 (combustion air supply)
               RG-401 → EX-403 → FG-404 (flue gas energy recovery)
Fractionation: R-201 → F-501 → WGC-401 → R-201 (wet gas recycle)
               F-501 → P-502 (reflux pump)
               F-501 → P-503, P-504 (product pumps)
Safety:        ESD-SYS → SHUTS_DOWN → R-201, SV-204, RG-401, EX-403, F-501

COUPLING STRENGTHS (how much downtime propagates through each relationship):
SHUTS_DOWN=95% | FEEDS=85% | CONTROLS_FLOW_TO=80% | CIRCULATES_TO=75% |
UPSTREAM_OF=65% | IMPACTS=60% | DEPENDS_ON=50% | CONNECTS=40%
(Each additional hop reduces propagation by 30% decay — formula: coupling × 0.70^(hop-1) × criticality_amplifier)
NOTE: When a "DOWNTIME PROPAGATION (COMPUTED FROM NEO4J TOPOLOGY)" section is present in the context,
ALWAYS use those exact computed values. Do NOT recalculate using the coupling strengths above — the
propagator already applies hop decay and criticality amplifiers correctly. Just cite the numbers.

P&ID DOCUMENTS: PID-FCC-101, PID-FCC-103, PID-FCC-201, PID-FCC-203, PID-FCC-204,
PID-FCC-301, PID-FCC-403, PID-FCC-502, PID-FCC-LINE

STRICT RULES:
1. ALWAYS cite specific MoC IDs, asset IDs, costs, dates, and risk scores from the retrieved context
2. NEVER give generic process safety advice — only answer from the retrieved data
3. If a specific MoC or asset is mentioned, use its exact data (costs, dates, outcomes)
4. If context is insufficient, say exactly what data is missing rather than guessing
5. For cost questions: use the ML COST & DOWNTIME PREDICTION section if present, then cite historical costs
6. For risk questions: give the exact risk score, category, and HAZOP/PSSR requirements
7. For lessons learned: quote the actual lesson text from the graph
8. For approval questions: list all 5 stages with assigned roles and status
9. For threshold checks: compute and state the exact margin to the design limit
10. For work order questions: cite WO IDs, planned vs actual hours, and delay reasons
11. For P&ID questions: use the "MoCs REFERENCING PID-xxx" section in the context — it contains the exact answer
12. ALWAYS use ALL sections in the retrieved context — do not ignore any section
13. For impact/connectivity questions: use PROCESS CONNECTIVITY MAP, ENRICHED ASSET IMPACT CHAIN, DOWNSTREAM CONNECTIONS, UPSTREAM CONNECTIONS, CONNECTIVITY SCORE, and DOWNTIME PROPAGATION sections — rank assets by propagated downtime and coupling factor
14. For "most affected / least affected" questions: use the DOWNTIME PROPAGATION section — it ranks assets by propagated_hours with coupling factors and risk levels
15. For "effect on upstream" questions: use the UPSTREAM CONNECTIONS / PROCESS CONNECTIVITY MAP sections — these are assets that feed into the changed asset
16. For process network questions: use the FCC UNIT PROCESS FLOW TOPOLOGY above to trace paths even when graph data is not in context

RESPONSE FORMAT RULES (MANDATORY):
- ALWAYS use markdown formatting — never return a wall of plain text
- Use ## headings to separate major sections (e.g. ## Summary, ## Downstream Impact, ## Risk Assessment)
- Use ### for sub-sections (e.g. ### Most Affected Assets, ### Work Orders)
- Use bullet lists (- item) for enumerations of 3+ items
- Use numbered lists (1. item) for sequential steps or ranked results
- Use **bold** for asset IDs, MoC IDs, costs, risk levels, and key values
- Use `inline code` for asset IDs and technical identifiers (e.g. `SV-204`, `MoC-005`)
- Use tables for comparative data (e.g. multiple MoCs side by side, cost comparisons)
- Keep each section concise — bullet points over paragraphs wherever possible
- Start every response with a 1-2 sentence summary, then structured sections below

RETRIEVED CONTEXT (use this data to answer — do not invent):
{context}
"""

CHAT_TEMPLATE = """{system}

Conversation so far:
{history}

User: {human_input}
MoCBot:"""

# ── Intent routing ─────────────────────────────────────────────────────────
INTENTS = {
    "moc_lookup":       ["moc-0", "moc 0", "what happened", "tell me about moc", "details of"],
    "asset_history":    ["history of", "past changes to", "what was done to", "changes on", "show mocs for"],
    "risk_query":       ["risk", "hazard", "hazop", "pssr", "danger", "safe", "impact", "affect",
                         "overheating", "thermal stress", "circulation instability", "pressure balance",
                         "safeguard", "safety check", "what checks", "verify after"],
    "cost_query":       ["cost", "price", "budget", "expensive", "how much", "spend",
                         "predict cost", "estimate cost", "cost prediction", "predict"],
    "downtime_query":   ["downtime", "how long", "duration", "hours", "manhours",
                         "planned vs actual", "overrun", "delay",
                         "predict downtime", "estimate downtime"],
    "approval_query":   ["approve", "approver", "sign off", "who needs", "authorization",
                         "who approved", "who must approve", "stage", "reviewer"],
    "lessons_query":    ["lesson", "went wrong", "failure", "incident", "near miss", "rework",
                         "what failed", "common issues", "rollout", "implementation issue",
                         "past actuator", "past procedure", "past temperature"],
    "impact_query":     ["impact", "downstream", "upstream", "affect", "depend", "connected",
                         "dependency path", "path from", "path to", "impacted assets",
                         "what equipment", "what assets", "topology",
                         "most affected", "least affected", "effect on", "effect of",
                         "what happens if", "what would happen", "goes offline",
                         "replace actuator", "faster response", "faster actuator",
                         "propagate", "propagation", "network effect", "process network",
                         "connectivity", "connected assets", "linked assets"],
    "parameter_query":  ["setpoint", "temperature", "pressure", "flow rate", "parameter",
                         "changed from", "changed to", "within limit", "close to limit",
                         "maximum limit", "threshold", "margin", "525", "545", "510"],
    "wo_query":         ["work order", "wo-", "maintenance", "repair", "installation",
                         "planned vs actual", "duration summary", "wo summary"],
    "pid_query":        ["pid", "p&id", "pid-fcc", "pid-fc", "drawing", "document reference",
                         "references pid", "reference pid"],
    "new_moc_query":    ["start a new moc", "new moc", "initiate moc", "create moc",
                         "begin moc", "raise moc", "open moc", "what information do you need",
                         "what do you need from me", "missing fields", "required fields"],
    "checklist_query":  ["checklist", "commissioning", "verification", "verify after",
                         "what to verify", "steps to", "pre-startup", "startup check",
                         "functional test", "calibration", "loop test", "interlock test",
                         "evidence required", "close this moc", "close out"],
    "comparison_query": ["compare", "vs", "versus", "difference between", "which is higher",
                         "which one", "higher risk", "lower cost"],
    "risk_score_filter":["risk score", "score ≥", "score >=", "score above", "score greater",
                         "high risk mocs", "all mocs with risk", "risk ≥", "risk >="],
    "concept_search":   ["find mocs", "find similar", "similar mocs", "mocs that mention",
                         "mocs involving", "mocs related to", "mocs where", "show mocs that"],
    "training_query":   ["training", "procedure update", "operator training", "drill",
                         "sign-off", "sign off", "communication plan", "procedure revision"],
    "threshold_check":  ["exceed", "exceeds", "above limit", "beyond limit", "600", "unsafe",
                         "too high", "maximum", "design limit", "escalation"],
    "failure_mode":     ["failure mode", "equipment failure", "consequence", "what can go wrong",
                         "failure cause", "manifests as", "fm_id"],
    "general":          [],
}


class SimpleMemory:
    def __init__(self, k: int = 8):
        self._turns = deque(maxlen=k)

    def add(self, human: str, ai: str):
        self._turns.append((human, ai))

    def format(self) -> str:
        return "\n".join(
            f"User: {h}\nMoCBot: {a}" for h, a in self._turns
        )

    def clear(self):
        self._turns.clear()


class MoCChatbot:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.neo4j    = Neo4jClient()
        self.llm      = get_llm()
        self.memory   = SimpleMemory(k=8)

    def chat(self, user_message: str, asset_id: str = None) -> dict:
        intent   = _detect_intent(user_message)
        moc_id   = _extract_moc_id(user_message)
        asset_id = asset_id or _extract_asset_id(user_message)

        # ── PID short-circuit: exact lookup, bypass LLM noise ─────────────
        # When the query is specifically about a P&ID reference, do a direct
        # Neo4j lookup and return a structured answer without going through
        # the full RAG pipeline (which buries the result in noise).
        if intent == "pid_query":
            pid_response = self._handle_pid_query(user_message)
            if pid_response:
                self.memory.add(user_message, pid_response)
                return {
                    "response":      pid_response,
                    "intent":        intent,
                    "asset_id_used": "none",
                    "moc_id_used":   "none",
                    "vector_hits":   [],
                }

        # Extract ALL MoC IDs mentioned (for comparison queries)
        all_moc_ids = _extract_all_moc_ids(user_message)

        # ── Broad fallback: if no specific asset/moc, do keyword search ──
        if not asset_id and not moc_id:
            keyword_results = self.neo4j.search_mocs_by_keyword(
                _extract_search_keyword(user_message), limit=3
            )
            if keyword_results:
                moc_id   = moc_id   or keyword_results[0].get("moc_id")
                asset_id = asset_id or keyword_results[0].get("asset_id")

        # Retrieve hybrid context for primary MoC
        context = self.pipeline.retriever.retrieve(
            query_text=user_message,
            asset_id=asset_id,
            moc_id=moc_id,
        )

        # For comparison queries — fetch all mentioned MoCs and append to context
        extra_moc_ctx = ""
        if len(all_moc_ids) > 1:
            extra_lines = []
            for mid in all_moc_ids:
                if mid != moc_id:
                    d = self.neo4j.get_moc_full_detail(mid)
                    if d:
                        extra_lines.append(
                            f"\nADDITIONAL MoC RECORD ({mid}):\n"
                            f"  Title: {d.get('title')}\n"
                            f"  Cost: actual=${d.get('actual_cost') or 0:,} estimated=${d.get('estimated_cost') or 0:,}\n"
                            f"  Manhours: {d.get('actual_manhours')} | Risk: {d.get('risk_category')} score={d.get('risk_score')}\n"
                            f"  Incident: {d.get('incident_occurred')} — {d.get('incident_description') or 'none'}\n"
                            f"  Lesson: {d.get('lesson') or d.get('lessons_learned','')}"
                        )
            extra_moc_ctx = "\n".join(extra_lines)

        # Intent-specific graph augmentation
        extra_ctx = self._intent_augment(intent, user_message, asset_id, moc_id)

        # Broad dataset queries
        broad_ctx = self._broad_query_augment(intent, user_message)

        formatted_ctx = self.pipeline.retriever.format_context_for_prompt(context)
        if extra_moc_ctx:
            formatted_ctx = extra_moc_ctx + "\n\n" + formatted_ctx
        if broad_ctx:
            formatted_ctx = broad_ctx + "\n\n" + formatted_ctx
        if extra_ctx:
            formatted_ctx = extra_ctx + "\n\n" + formatted_ctx

        history  = self.memory.format()
        messages = _build_messages(
            system=SYSTEM_PROMPT.format(context=formatted_ctx),
            history=history,
            human_input=user_message,
        )
        response = self.llm.invoke(messages)

        self.memory.add(user_message, response)

        return {
            "response":      response,
            "intent":        intent,
            "asset_id_used": asset_id or "none",
            "moc_id_used":   moc_id or "none",
            "vector_hits":   context.get("vector_hits", []),
        }

    def _broad_query_augment(self, intent: str, message: str) -> str:
        """
        Handles dataset-wide queries and special intents that don't target
        a specific asset/MoC. Covers all 40 test query patterns.
        """
        msg = message.lower()
        sections = []

        # ── HAZOP / PSSR / risk summary ────────────────────────────────────
        if any(kw in msg for kw in ["hazop", "pssr", "which moc", "all moc", "list moc",
                                     "required", "how many", "hazard study", "pre-startup"]):
            all_mocs = self.neo4j.get_all_mocs()
            if all_mocs:
                lines = []
                for m in all_mocs:
                    detail = self.neo4j.get_moc_full_detail(m.get("moc_id", ""))
                    if detail:
                        hazop = "HAZOP=Yes" if detail.get("hazop_required") else "HAZOP=No"
                        pssr  = "PSSR=Yes"  if detail.get("pssr_required")  else "PSSR=No"
                        lines.append(
                            f"  {detail.get('moc_id')}: {_clip(detail.get('title') or detail.get('name'), 50)} | "
                            f"{hazop} | {pssr} | Risk={detail.get('risk_category')} "
                            f"score={detail.get('risk_score')} | Approver={detail.get('final_approver_role')}"
                        )
                sections.append("ALL MoCs SUMMARY (HAZOP/PSSR/Risk):\n" + "\n".join(lines))

        # ── Incident / rework queries ──────────────────────────────────────
        if any(kw in msg for kw in ["incident", "went wrong", "failure", "near miss",
                                     "rework", "common issues", "rollout", "implementation"]):
            incidents = self.neo4j.get_mocs_with_incidents()
            if incidents:
                lines = [
                    f"  {i.get('moc_id')}: {i.get('incident')} → {i.get('outcome')}"
                    for i in incidents
                ]
                sections.append("ALL INCIDENTS IN DATASET:\n" + "\n".join(lines))
            rework = self.neo4j.get_mocs_with_rework()
            if rework:
                lines = []
                for r in rework[:5]:
                    over_cost = (r.get('actual_cost') or 0) - (r.get('estimated_cost') or 0)
                    over_hrs  = (r.get('actual_manhours') or 0) - (r.get('estimated_manhours') or 0)
                    lines.append(
                        f"  {r.get('moc_id')}: {_clip(r.get('title') or r.get('name'), 45)} | "
                        f"Incident: {_clip(r.get('incident'), 60, '?')} | "
                        f"Cost overrun: ${over_cost:+,} | Hours overrun: {over_hrs:+}"
                    )
                sections.append("REWORK/INCIDENT DETAILS:\n" + "\n".join(lines))

        # ── Cost overview ──────────────────────────────────────────────────
        if any(kw in msg for kw in ["most expensive", "highest cost", "cost overview",
                                     "total cost", "budget", "all costs"]):
            all_mocs = self.neo4j.get_all_mocs()
            if all_mocs:
                sorted_mocs = sorted(all_mocs, key=lambda x: x.get("cost") or 0, reverse=True)
                lines = [
                    f"  {m.get('moc_id')}: ${m.get('cost') or 0:,} actual | {m.get('manhours')}h | {m.get('change_type')}"
                    for m in sorted_mocs
                ]
                sections.append("ALL MoCs BY COST (descending):\n" + "\n".join(lines))

        # ── Risk score filter (Q40: risk score ≥ 12) ──────────────────────
        if intent == "risk_score_filter" or any(kw in msg for kw in
                ["risk score", "score ≥", "score >=", "score above", "score greater",
                 "high risk mocs", "risk ≥", "risk >="]):
            import re
            score_match = re.search(r'(\d+)', msg)
            min_score = int(score_match.group(1)) if score_match else 10
            mocs = self.neo4j.get_mocs_by_risk_score(min_score=min_score)
            if mocs:
                lines = [
                    f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 45)} | "
                    f"Risk={m.get('risk_category')} score={m.get('risk_score')} | "
                    f"Asset={m.get('asset_id')} | HAZOP={'Yes' if m.get('hazop_required') else 'No'}"
                    for m in mocs
                ]
                sections.append(f"MoCs WITH RISK SCORE ≥ {min_score}:\n" + "\n".join(lines))

        # ── PID reference queries (Q4, Q18) ───────────────────────────────
        if intent == "pid_query" or any(kw in msg for kw in ["pid", "p&id", "pid-fcc", "pid-fc"]):
            import re
            # Match both PID-FCC-xxx and PID-FC-C-xxx formats
            pid_match = re.search(
                r'pid[-\s]?(?:fc[-\s]?c[-\s]?|fcc[-\s]?)(\d+)',
                msg, re.IGNORECASE
            )
            if pid_match:
                num = pid_match.group(1)
                # Always normalize to PID-FCC-xxx for Neo4j lookup (stored format)
                pid_ref_normalized = f"PID-FCC-{num}"
                mocs = self.neo4j.get_mocs_by_pid(pid_ref_normalized)
                # Also try the alternate format if first returns nothing
                if not mocs:
                    mocs = self.neo4j.get_mocs_by_pid(f"PID-FC-C-{num}")
                if mocs:
                    lines = [
                        f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 45)} | "
                        f"P&ID: {m.get('pid_ref')} v{m.get('version')} | Asset: {m.get('asset_id')}"
                        for m in mocs
                    ]
                    sections.append(f"MoCs REFERENCING PID-{num} ({pid_ref_normalized}):\n" + "\n".join(lines))
                else:
                    sections.append(
                        f"P&ID SEARCH: No MoCs found referencing PID number '{num}'. "
                        f"Available P&IDs: PID-FCC-101, PID-FCC-103, PID-FCC-201, "
                        f"PID-FCC-203, PID-FCC-204, PID-FCC-301, PID-FCC-403, "
                        f"PID-FCC-502, PID-FCC-LINE"
                    )

        # ── Concept search (Q1, Q17, Q28, Q29, Q30) ───────────────────────
        if intent == "concept_search" or any(kw in msg for kw in
                ["find similar", "similar mocs", "mocs that mention", "mocs involving",
                 "mocs related to", "mocs where", "show mocs that", "find mocs"]):
            # Extract the concept from the message
            concept = _extract_concept(msg)
            if concept:
                mocs = self.neo4j.get_mocs_by_concept(concept)
                if mocs:
                    lines = [
                        f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 50)} | "
                        f"{m.get('change_type')} | Asset: {m.get('asset_id')} | "
                        f"Lesson: {_clip(m.get('lessons'), 60)}"
                        for m in mocs[:6]
                    ]
                    sections.append(f"MoCs MATCHING '{concept}':\n" + "\n".join(lines))

        # ── Training / procedure queries (Q29, Q30) ────────────────────────
        if intent == "training_query" or any(kw in msg for kw in
                ["training", "procedure update", "operator training", "drill", "sign-off"]):
            mocs = self.neo4j.get_mocs_requiring_training()
            if mocs:
                lines = [
                    f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 50)} | {m.get('change_type')} | Approver: {m.get('approver')}"
                    for m in mocs
                ]
                sections.append("MoCs REQUIRING TRAINING/PROCEDURE UPDATE:\n" + "\n".join(lines))

        # ── Planned vs actual WO analytics (Q15, Q27) ─────────────────────
        if any(kw in msg for kw in ["planned vs actual", "overrun", "duration summary",
                                     "compare planned", "actual duration"]):
            ct = _extract_change_type(message)
            wos = self.neo4j.get_wo_planned_vs_actual(ct)
            if wos:
                lines = []
                for w in wos[:10]:
                    p_hrs = w.get('planned_hrs') or 0
                    a_hrs = w.get('actual_hrs') or 0
                    p_cost = w.get('estimated_cost') or 0
                    a_cost = w.get('actual_cost') or 0
                    overrun_h = a_hrs - p_hrs
                    overrun_c = a_cost - p_cost
                    lines.append(
                        f"  {w.get('moc_id')} / {w.get('wo_id')}: {_clip(w.get('wo_title'), 40)} | "
                        f"Hours: {p_hrs}→{a_hrs} ({overrun_h:+}) | "
                        f"Cost: ${p_cost:,}→${a_cost:,} ({overrun_c:+,}) | "
                        f"Delay: {_clip(w.get('delay_reason'), 50, 'none')}"
                    )
                sections.append("PLANNED vs ACTUAL (Work Orders):\n" + "\n".join(lines))

        # ── FCC reactor area queries (Q3) ──────────────────────────────────
        if any(kw in msg for kw in ["fcc reactor", "reactor section", "reactor area"]):
            mocs = self.neo4j.get_mocs_in_area("reactor")
            if mocs:
                lines = [
                    f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 45)} | "
                    f"Risk score={m.get('risk_score')} | Area: {m.get('area')}"
                    for m in mocs
                ]
                sections.append("MoCs IN REACTOR AREA:\n" + "\n".join(lines))

        return "\n\n".join(sections)

    def _intent_augment(self, intent: str, message: str, asset_id: str, moc_id: str) -> str:
        """Fetches targeted graph data based on detected intent. Covers all 40 query patterns."""
        import re as _re
        sections = []
        msg = message.lower()

        # ── MoC lookup ─────────────────────────────────────────────────────
        if intent == "moc_lookup" and moc_id:
            hp = self.neo4j.get_hazop_pssr(moc_id)
            if hp and hp[0].get("hazop_outcome"):
                sections.append(f"HAZOP STATUS: {hp[0].get('hazop_outcome')}\n  Justification: {hp[0].get('hazop_justification','')}")
            if hp and hp[0].get("pssr_outcome"):
                sections.append(f"PSSR STATUS: {hp[0].get('pssr_outcome')}")
            stages = self.neo4j.get_approval_stages(moc_id)
            if stages:
                sections.append("APPROVAL WORKFLOW:\n" + "\n".join(f"  {s.get('stage')}: {s.get('role')} ({s.get('status')})" for s in stages))
            params = self.neo4j.get_parameter_changes(moc_id)
            if params:
                for p in params:
                    sections.append(f"PARAMETER CHANGE: {p.get('name')}\n  {p.get('old_value')} → {p.get('new_value')} (threshold: {p.get('threshold')})")
            # Also pull connectivity for the MoC's target asset
            if asset_id:
                enriched = self.neo4j.get_enriched_impact_chain(asset_id, depth=3)
                if enriched:
                    direct = [n for n in enriched if n.get('hop_distance') == 1]
                    if direct:
                        lines = [
                            f"  ↳ {n.get('node_id')} ({n.get('node_name')}) | "
                            f"crit={n.get('criticality')} | "
                            f"via: {' → '.join(n.get('relationship_chain') or [])}"
                            for n in sorted(direct, key=lambda x: -(x.get('criticality') or 0))[:6]
                        ]
                        sections.append(f"DIRECT PROCESS IMPACTS FROM {asset_id}:\n" + "\n".join(lines))

        # ── Asset history ──────────────────────────────────────────────────
        elif intent == "asset_history" and asset_id:
            mocs = self.neo4j.search_mocs_by_keyword(asset_id, limit=5)
            if mocs:
                lines = [f"  {m.get('moc_id')}: {m.get('title')} | ${m.get('cost') or 0:,} | {m.get('change_type')}" for m in mocs]
                sections.append(f"ALL MoCs FOR {asset_id}:\n" + "\n".join(lines))

        # ── Impact / dependency path — enhanced with connectivity + propagation ──
        elif intent == "impact_query":
            # Resolve asset_id from message if not already set
            resolved_asset = asset_id or _extract_asset_id(message)

            if resolved_asset:
                # 1. Full connectivity map (upstream + downstream with relationship types)
                conn_map = self.neo4j.get_full_connectivity_map(resolved_asset)
                if conn_map:
                    downstream = [n for n in (conn_map.get("downstream_nodes") or []) if n.get("asset_id")]
                    upstream   = [n for n in (conn_map.get("upstream_nodes") or []) if n.get("asset_id")]
                    if downstream:
                        lines = [
                            f"  ↳ {n.get('asset_id')} ({n.get('name')}) | "
                            f"rel={n.get('rel_type')} | "
                            f"flow={n.get('flow_type') or 'n/a'} | "
                            f"crit={n.get('criticality')}"
                            for n in sorted(downstream, key=lambda x: -(x.get('criticality') or 0))
                        ]
                        sections.append(f"DOWNSTREAM CONNECTIONS FROM {resolved_asset} (direct):\n" + "\n".join(lines))
                    if upstream:
                        lines = [
                            f"  ↑ {n.get('asset_id')} ({n.get('name')}) | "
                            f"rel={n.get('rel_type')} | "
                            f"flow={n.get('flow_type') or 'n/a'} | "
                            f"crit={n.get('criticality')}"
                            for n in sorted(upstream, key=lambda x: -(x.get('criticality') or 0))
                        ]
                        sections.append(f"UPSTREAM CONNECTIONS TO {resolved_asset} (direct):\n" + "\n".join(lines))

                # 2. Connectivity score
                score = self.neo4j.get_asset_connectivity_score(resolved_asset)
                if score:
                    sections.append(
                        f"CONNECTIVITY SCORE FOR {resolved_asset}:\n"
                        f"  Total score: {score.get('score')} | "
                        f"Downstream: {score.get('downstream_connections')} | "
                        f"Upstream: {score.get('upstream_connections')} | "
                        f"MoCs: {score.get('moc_count')} | "
                        f"Hazards: {score.get('hazard_count')} | "
                        f"ESD target: {'Yes' if score.get('is_esd_target') else 'No'}"
                    )

                # 3. Enriched impact chain with ranking by criticality
                enriched = self.neo4j.get_enriched_impact_chain(resolved_asset, depth=4)
                if enriched:
                    def impact_rank(n):
                        crit = int(n.get('criticality') or 1)
                        hops = int(n.get('hop_distance') or 1)
                        return crit / hops
                    ranked = sorted(enriched, key=impact_rank, reverse=True)
                    lines = []
                    for n in ranked[:12]:
                        rel_chain = " → ".join(n.get('relationship_chain') or [])
                        lines.append(
                            f"  {'↳' * int(n.get('hop_distance', 1))} "
                            f"{n.get('node_id')} ({n.get('node_name')}) | "
                            f"crit={n.get('criticality')} | "
                            f"hops={n.get('hop_distance')} | "
                            f"via: {rel_chain[:70]} | "
                            f"area={n.get('area') or 'n/a'}"
                        )
                    sections.append(
                        f"RANKED IMPACT CHAIN FROM {resolved_asset} (most→least critical):\n"
                        + "\n".join(lines)
                    )

                # 4. Downtime propagation — use actual MoC manhours if available
                try:
                    from core.downtime_propagator import DowntimePropagator
                    propagator = DowntimePropagator(self.neo4j)
                    # Try to get actual downtime from a MoC targeting this asset
                    source_hours = 26.0  # default
                    if moc_id:
                        detail = self.neo4j.get_moc_full_detail(moc_id)
                        if detail and detail.get("actual_manhours"):
                            source_hours = float(detail["actual_manhours"])
                    # Also check if a number of hours is mentioned in the message
                    import re as _re2
                    hour_match = _re2.search(r'(\d+)\s*(?:hours?|hrs?|h\b)', msg)
                    if hour_match:
                        source_hours = float(hour_match.group(1))

                    prop_result = propagator.propagate(resolved_asset, source_downtime_hours=source_hours, max_depth=4)
                    if prop_result.affected_assets:
                        affected = prop_result.affected_assets
                        most  = affected[:4]
                        least = affected[-3:] if len(affected) > 4 else []
                        lines = [f"  Source: {resolved_asset} | {source_hours:.0f}h downtime scenario"]
                        lines.append(f"  MOST AFFECTED (highest propagated downtime):")
                        for a in most:
                            lines.append(
                                f"    • {a.asset_id} ({a.asset_name}) — "
                                f"{a.propagated_hours:.1f}h propagated | "
                                f"coupling={a.coupling_factor:.2f} | "
                                f"risk={a.risk_level} | "
                                f"{a.hop_distance} hop | "
                                f"via: {' → '.join(a.relationship_chain[:3])}"
                            )
                        if least:
                            lines.append(f"  LEAST AFFECTED (lowest propagated downtime):")
                            for a in least:
                                lines.append(
                                    f"    • {a.asset_id} ({a.asset_name}) — "
                                    f"{a.propagated_hours:.1f}h | "
                                    f"risk={a.risk_level} | "
                                    f"{a.hop_distance} hops"
                                )
                        lines.append(
                            f"  Summary: {prop_result.total_affected} assets affected | "
                            f"{prop_result.total_propagated_hours:.1f}h total propagated"
                        )
                        sections.append(
                            f"DOWNTIME PROPAGATION FROM {resolved_asset} ({source_hours:.0f}h scenario):\n"
                            + "\n".join(lines)
                        )
                except Exception:
                    pass

                # 5. Dependency path between specific assets if mentioned
                if any(kw in msg for kw in ["path from", "path to", "dependency path"]):
                    assets_mentioned = _re.findall(r'\b([A-Z]{1,4}-\d{3,4}(?:-[A-Z]+)?|ESD-SYS)\b', message)
                    if len(assets_mentioned) >= 2:
                        path = self.neo4j.get_dependency_path(assets_mentioned[0], assets_mentioned[1])
                        if path:
                            p = path[0]
                            sections.append(
                                f"DEPENDENCY PATH {assets_mentioned[0]} → {assets_mentioned[1]}:\n"
                                f"  Path: {' → '.join(p.get('path_nodes', []))}\n"
                                f"  Relationships: {' → '.join(p.get('path_rels', []))}\n"
                                f"  Hops: {p.get('hops')}"
                            )

                # 6. Historical MoCs on this asset for context
                mocs_on_asset = self.neo4j.search_mocs_by_keyword(resolved_asset, limit=3)
                if mocs_on_asset:
                    lines = [
                        f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 55)} | "
                        f"${m.get('cost') or 0:,} | {m.get('change_type')}"
                        for m in mocs_on_asset
                    ]
                    sections.append(f"HISTORICAL MoCs ON {resolved_asset}:\n" + "\n".join(lines))

            else:
                # No asset identified — show full topology summary
                all_assets = self.neo4j.get_all_assets_with_connectivity()
                if all_assets:
                    lines = [
                        f"  {a.get('asset_id')} ({a.get('name')}) | "
                        f"crit={a.get('criticality')} | "
                        f"downstream={a.get('downstream_count')} | "
                        f"upstream={a.get('upstream_count')} | "
                        f"mocs={a.get('moc_count')}"
                        for a in sorted(all_assets, key=lambda x: -(x.get('criticality') or 0))[:12]
                    ]
                    sections.append("FCC UNIT ASSET CONNECTIVITY OVERVIEW:\n" + "\n".join(lines))

        # ── Lessons learned (Q9, Q14, Q26, Q36, Q37) ──────────────────────
        elif intent == "lessons_query":
            ct = _extract_change_type(message)
            if ct:
                lessons = self.neo4j.get_lessons_learned(ct, asset_id)
                if lessons:
                    lines = [f"  [{ll.get('moc_id')}] {ll.get('summary')}" for ll in lessons[:4]]
                    sections.append("LESSONS LEARNED:\n" + "\n".join(lines))
            incidents = self.neo4j.get_mocs_with_incidents()
            if incidents:
                lines = [f"  {i.get('moc_id')}: {i.get('incident')} → {i.get('outcome')}" for i in incidents[:5]]
                sections.append("ALL INCIDENTS IN DATASET:\n" + "\n".join(lines))
            rework = self.neo4j.get_mocs_with_rework()
            if rework:
                lines = [f"  {r.get('moc_id')}: {_clip(r.get('incident'), 60, '?')} | Lesson: {_clip(r.get('lesson'), 60)}" for r in rework[:4]]
                sections.append("REWORK DETAILS:\n" + "\n".join(lines))

        # ── Approval query (Q33) ───────────────────────────────────────────
        elif intent == "approval_query":
            ct = _extract_change_type(message)
            if ct:
                approvers = self.neo4j.get_common_approvers(ct)
                if approvers:
                    lines = [f"  {a.get('approver')} ({a.get('department')}) — {a.get('freq')} MoC(s)" for a in approvers]
                    sections.append(f"APPROVERS FOR {ct}:\n" + "\n".join(lines))
            if moc_id:
                stages = self.neo4j.get_approval_stages_full(moc_id)
                if stages:
                    lines = [
                        f"  Stage {s.get('stage_number')} — {s.get('stage_name')}: "
                        f"{s.get('assigned_role')} [{s.get('status') or 'pending'}] "
                        f"{s.get('timestamp') or ''}"
                        for s in stages
                    ]
                    sections.append(f"APPROVAL STAGES FOR {moc_id}:\n" + "\n".join(lines))
                else:
                    # Fallback to final approver from MoC record
                    detail = self.neo4j.get_moc_full_detail(moc_id)
                    if detail:
                        sections.append(
                            f"Approval stage detail not available for {moc_id}.\n"
                            f"Final approver role on record: {detail.get('final_approver_role')}"
                        )

        # ── Failure mode (Task 8) ──────────────────────────────────────────
        elif intent == "failure_mode":
            if moc_id:
                fms = self.neo4j.get_failure_modes(moc_id)
            elif asset_id:
                hazards = self.neo4j.get_hazards_for_asset(asset_id)
                fms = [
                    {"mode": fm, "consequence": "", "hazard_description": h.get("description")}
                    for h in hazards for fm in (h.get("failure_modes") or [])
                ]
            else:
                fms = []
            if fms:
                lines = [
                    f"  {fm.get('mode')}: consequence={fm.get('consequence') or 'see hazard'} "
                    f"| hazard={str(fm.get('hazard_description',''))[:60]}"
                    for fm in fms
                ]
                sections.append("FAILURE MODES:\n" + "\n".join(lines))
            else:
                sections.append("No FailureMode records found. Review hazard description instead.")

        # ── Parameter / threshold check (Q8, Q11, Q38) ────────────────────
        elif intent in ("parameter_query", "threshold_check"):
            if asset_id:
                params = self.neo4j.get_parameter_threshold(asset_id)
                if params:
                    for p in params:
                        sections.append(
                            f"PARAMETER THRESHOLD FOR {asset_id}:\n"
                            f"  {p.get('name')}: current={p.get('new_value')} | threshold={p.get('threshold')} | old={p.get('old_value')}"
                        )
            if moc_id:
                params = self.neo4j.get_parameter_changes(moc_id)
                if params:
                    for p in params:
                        sections.append(f"PARAMETER CHANGE IN {moc_id}:\n  {p.get('name')}: {p.get('old_value')} → {p.get('new_value')} (threshold: {p.get('threshold')})")
            nums = _re.findall(r'\b(\d{3,4})\b', message)
            if nums and asset_id:
                proposed = float(nums[0])
                params = self.neo4j.get_parameter_threshold(asset_id)
                for p in params:
                    try:
                        thresh_str = str(p.get('threshold', '')).replace('Max ', '').replace('max ', '').replace('°C', '').replace(' C', '').strip()
                        if not thresh_str:
                            sections.append(
                                f"THRESHOLD CHECK: No design limit recorded for "
                                f"{p.get('name', 'parameter')} on {asset_id}. "
                                f"Recommend consulting the P&ID document."
                            )
                            continue
                        thresh = float(thresh_str)
                        margin = thresh - proposed
                        if margin > 0:
                            status_label = "WITHIN LIMITS"
                        else:
                            status_label = "⚠ EXCEEDS LIMIT — ESCALATION REQUIRED"
                        sections.append(
                            f"THRESHOLD CHECK FOR {asset_id}:\n"
                            f"  Parameter: {p.get('name', 'parameter')}\n"
                            f"  Proposed value: {proposed}\n"
                            f"  Design limit: {thresh}\n"
                            f"  Margin: {margin:+.1f} units\n"
                            f"  Status: {status_label}"
                        )
                    except (ValueError, TypeError):
                        pass

        # ── Cost / downtime prediction (cost_query, downtime_query) ──────────
        elif intent in ("cost_query", "downtime_query"):
            # ── For downtime propagation queries: run the actual propagator ──
            # This gives the LLM precise computed values instead of letting it
            # do its own math from the system prompt coupling strengths.
            resolved_asset = asset_id or _extract_asset_id(message)
            if resolved_asset and intent == "downtime_query":
                import re as _re3
                hour_match = _re3.search(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b)', message.lower())
                source_hours = float(hour_match.group(1)) if hour_match else 24.0
                try:
                    from core.downtime_propagator import DowntimePropagator
                    propagator = DowntimePropagator(self.neo4j)
                    prop = propagator.propagate(resolved_asset, source_downtime_hours=source_hours, max_depth=4)
                    if prop.affected_assets:
                        lines = [
                            f"  Source: {resolved_asset} | {source_hours:.0f}h downtime",
                            f"  Method: coupling × hop_decay(0.70) × criticality_amplifier",
                            f"  Total affected: {prop.total_affected} assets | {prop.total_propagated_hours:.2f}h total propagated",
                            f"",
                            f"  PROPAGATED DOWNTIME (computed, not estimated):",
                        ]
                        for a in prop.affected_assets[:10]:
                            lines.append(
                                f"    {a.asset_id} ({a.asset_name}): "
                                f"{a.propagated_hours:.3f}h | "
                                f"coupling={a.coupling_factor:.3f} | "
                                f"hops={a.hop_distance} | "
                                f"via: {' → '.join(a.relationship_chain)} | "
                                f"risk={a.risk_level}"
                            )
                        sections.append(
                            f"DOWNTIME PROPAGATION (COMPUTED FROM NEO4J TOPOLOGY):\n"
                            + "\n".join(lines)
                        )
                except Exception:
                    pass

            # Show historical costs from graph
            ct = _extract_change_type(message)
            if resolved_asset:
                similar = self.neo4j.get_similar_mocs(ct or "Mechanical", resolved_asset, top_k=5)
                if similar:
                    lines = [
                        f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 45)} | "
                        f"Actual cost: ${m.get('cost') or 0:,} | "
                        f"Downtime: {m.get('downtime') or 0}h | "
                        f"Risk: {m.get('risk_level')}"
                        for m in similar
                    ]
                    sections.append(f"HISTORICAL COSTS FOR SIMILAR MoCs (asset {resolved_asset}):\n" + "\n".join(lines))
            # ML cost/downtime prediction
            try:
                from modules.cost_predictor import CostPredictor, CHANGE_TYPE_MAP, ASSET_CATEGORY_MAP
                predictor = CostPredictor()
                asset_cat_map = {
                    "P-101": "Pump", "P-502": "Pump", "P-503": "Pump", "P-504": "Pump",
                    "FV-103": "Control Valve", "SV-204": "Control Valve", "IV-303": "Control Valve",
                    "R-201": "Reactor", "C-203": "Cyclone Separator",
                    "EX-403": "Flue gas expander",
                    "CTL-205": "Piping", "ST-302": "Piping", "FG-404": "Piping",
                    "ESD-SYS": "Procedure", "F-501": "Fractionator", "WGC-401": "Compressor",
                }
                asset_category = asset_cat_map.get(resolved_asset or "", "Other")
                risk_level = "Medium"
                change_type = ct or "Mechanical"
                result = predictor.predict(
                    change_type=change_type,
                    asset_id=resolved_asset or "unknown",
                    asset_category=asset_category,
                    risk_level=risk_level,
                    description=message,
                )
                sections.append(
                    f"ML COST & DOWNTIME PREDICTION:\n"
                    f"  Change type: {change_type} | Asset: {resolved_asset or 'unknown'} ({asset_category})\n"
                    f"  Estimated cost: ${result['cost_estimate']:,.0f} "
                    f"(range: ${result['cost_ci'][0]:,.0f} – ${result['cost_ci'][1]:,.0f})\n"
                    f"  Estimated downtime: {result['downtime_estimate']:.1f}h "
                    f"(range: {result['downtime_ci'][0]:.1f}h – {result['downtime_ci'][1]:.1f}h)\n"
                    f"  Model: {result['models_used']}\n"
                    f"  Explanation: {result['explanation'][:300]}"
                )
            except Exception as e:
                sections.append(f"ML prediction unavailable ({type(e).__name__}). See historical costs above.")

        # ── Work order analytics (Q15, Q27) ───────────────────────────────
        elif intent == "wo_query":
            if moc_id:
                wos = self.neo4j.get_work_orders_for_moc(moc_id)
                if wos:
                    lines = []
                    for w in wos:
                        p_hrs = w.get('planned_hrs') or 0
                        a_hrs = w.get('actual_hrs') or 0
                        lines.append(f"  {w.get('wo_id')}: {_clip(w.get('title') or w.get('name'), 40)} | Planned: {p_hrs}h → Actual: {a_hrs}h ({a_hrs-p_hrs:+}h) | ${w.get('actual_cost') or 0:,} | Delay: {_clip(w.get('delay_reason'), 50, 'none')}")
                    sections.append(f"WORK ORDERS FOR {moc_id}:\n" + "\n".join(lines))
            elif any(kw in msg for kw in ["planned vs actual", "overrun", "duration"]):
                ct = _extract_change_type(message)
                wos = self.neo4j.get_wo_planned_vs_actual(ct)
                if wos:
                    lines = [f"  {w.get('moc_id')}/{w.get('wo_id')}: {w.get('planned_hrs') or 0}h→{w.get('actual_hrs') or 0}h ({(w.get('actual_hrs') or 0)-(w.get('planned_hrs') or 0):+}h) | Delay: {_clip(w.get('delay_reason'), 50, 'none')}" for w in wos[:8]]
                    sections.append("PLANNED vs ACTUAL WORK ORDERS:\n" + "\n".join(lines))

        # ── Risk query with asset ──────────────────────────────────────────
        elif intent == "risk_query" and asset_id:
            hazards = self.neo4j.get_hazards_for_asset(asset_id)
            if hazards:
                lines = []
                for h in hazards[:4]:
                    fm = ", ".join((h.get("failure_modes") or [])[:3])
                    lines.append(f"  [{h.get('severity')} score={h.get('risk_score')}] {h.get('description')}" + (f"\n    Failure modes: {fm}" if fm else ""))
                sections.append(f"RISK DETAIL FOR {asset_id}:\n" + "\n".join(lines))
            if moc_id:
                hp = self.neo4j.get_hazop_pssr(moc_id)
                if hp and hp[0].get("hazop_outcome"):
                    sections.append(f"HAZOP: {hp[0].get('hazop_outcome')}\nPSSR: {hp[0].get('pssr_outcome')}")
            # Add connectivity context for risk questions — shows what's at risk downstream
            enriched = self.neo4j.get_enriched_impact_chain(asset_id, depth=3)
            if enriched:
                direct = [n for n in enriched if n.get('hop_distance') == 1]
                if direct:
                    lines = [
                        f"  ↳ {n.get('node_id')} ({n.get('node_name')}) | "
                        f"crit={n.get('criticality')} | "
                        f"via: {' → '.join(n.get('relationship_chain') or [])}"
                        for n in sorted(direct, key=lambda x: -(x.get('criticality') or 0))[:6]
                    ]
                    sections.append(f"DOWNSTREAM ASSETS AT RISK FROM {asset_id}:\n" + "\n".join(lines))
            if any(kw in msg for kw in ["risk score", "score ≥", "score >=", "score above"]):
                score_match = _re.search(r'(\d+)', msg)
                min_score = int(score_match.group(1)) if score_match else 10
                mocs = self.neo4j.get_mocs_by_risk_score(min_score=min_score)
                if mocs:
                    lines = [f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 45)} | score={m.get('risk_score')} | {m.get('risk_category')}" for m in mocs]
                    sections.append(f"MoCs WITH RISK SCORE ≥ {min_score}:\n" + "\n".join(lines))

        # ── Risk query without asset ───────────────────────────────────────
        elif intent == "risk_query" and not asset_id:
            all_mocs = self.neo4j.get_all_mocs()
            if all_mocs:
                lines = []
                for m in all_mocs[:10]:
                    detail = self.neo4j.get_moc_full_detail(m.get("moc_id", ""))
                    if detail:
                        lines.append(
                            f"  {detail.get('moc_id')}: {_clip(detail.get('title') or detail.get('name'), 45)} | "
                            f"Risk={detail.get('risk_category')} score={detail.get('risk_score')} | "
                            f"HAZOP={'Yes' if detail.get('hazop_required') else 'No'} | "
                            f"Hazard: {str(detail.get('hazards') or ['?'])[2:62]}"
                        )
                sections.append("RISK SUMMARY ALL MoCs:\n" + "\n".join(lines))

        # ── New MoC initiation (Q6, Q7, Q20, Q31) ─────────────────────────
        elif intent == "new_moc_query":
            ct = _extract_change_type(message)
            if asset_id:
                similar = self.neo4j.get_similar_mocs(ct or "Mechanical", asset_id, top_k=3)
                if similar:
                    lines = [f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 50)} | Risk={m.get('risk_level')} | HAZOP={'Yes' if m.get('hazop_required') else 'No'} | Approver={m.get('approver_role')}" for m in similar]
                    sections.append("SIMILAR HISTORICAL MoCs FOR REFERENCE:\n" + "\n".join(lines))
                hazards = self.neo4j.get_hazards_for_asset(asset_id)
                if hazards:
                    lines = [f"  [{h.get('severity')}] {h.get('description')}" for h in hazards[:3]]
                    sections.append(f"KNOWN HAZARDS FOR {asset_id}:\n" + "\n".join(lines))
                if ct:
                    approvers = self.neo4j.get_common_approvers(ct)
                    if approvers:
                        lines = [f"  {a.get('approver')} ({a.get('department')})" for a in approvers]
                        sections.append(f"TYPICAL APPROVERS FOR {ct}:\n" + "\n".join(lines))
                pid_entities = self.neo4j.get_pid_entities_for_asset(asset_id)
                if pid_entities:
                    refs = pid_entities[0].get('pid_refs', [])
                    if refs:
                        sections.append(f"P&ID REFERENCES FOR {asset_id}: {', '.join(str(r) for r in refs)}")

        # ── Checklist / commissioning (Q12, Q23, Q32, Q34) ────────────────
        elif intent == "checklist_query":
            ct = _extract_change_type(message)
            if asset_id:
                similar = self.neo4j.get_similar_mocs(ct or "Instrumentation", asset_id, top_k=2)
                for m in similar[:2]:
                    wos = self.neo4j.get_work_orders_for_moc(m.get('moc_id', ''))
                    if wos:
                        lines = [f"  [{w.get('wo_id')}] {_clip(w.get('title') or w.get('name'), 60)}" for w in wos]
                        sections.append(f"WORK ORDERS FROM SIMILAR MoC {m.get('moc_id')}:\n" + "\n".join(lines))
            if moc_id:
                hp = self.neo4j.get_hazop_pssr(moc_id)
                if hp:
                    sections.append(f"HAZOP/PSSR REQUIREMENTS: {hp[0].get('hazop_outcome')} | {hp[0].get('pssr_outcome')}")

        # ── Comparison query (Q39) ─────────────────────────────────────────
        elif intent == "comparison_query":
            all_moc_ids = _re.findall(r'\b(MoC-\d{3})\b', message, _re.IGNORECASE)
            all_moc_ids = ["MoC-" + m.split("-", 1)[1] for m in all_moc_ids]
            if len(all_moc_ids) >= 2:
                for mid in all_moc_ids[:3]:
                    d = self.neo4j.get_moc_full_detail(mid)
                    if d:
                        sections.append(
                            f"MoC DETAIL — {mid}:\n"
                            f"  Title: {d.get('title')}\n"
                            f"  Change type: {d.get('change_type')}\n"
                            f"  Risk: {d.get('risk_category')} score={d.get('risk_score')}\n"
                            f"  Cost: actual=${d.get('actual_cost') or 0:,} estimated=${d.get('estimated_cost') or 0:,}\n"
                            f"  HAZOP: {'Yes' if d.get('hazop_required') else 'No'} | PSSR: {'Yes' if d.get('pssr_required') else 'No'}\n"
                            f"  Hazards: {', '.join(d.get('hazards') or [])[:100]}\n"
                            f"  Lesson: {d.get('lesson') or d.get('lessons_learned','')}"
                        )

        # ── Concept search (Q1, Q16, Q17) ─────────────────────────────────
        elif intent == "concept_search":
            concept = _extract_concept(msg)
            if concept:
                mocs = self.neo4j.get_mocs_by_concept(concept)
                if mocs:
                    lines = [f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 50)} | {m.get('change_type')} | Asset: {m.get('asset_id')}" for m in mocs[:6]]
                    sections.append(f"MoCs MATCHING '{concept}':\n" + "\n".join(lines))

        # ── Training / procedure (Q29, Q30) ───────────────────────────────
        elif intent == "training_query":
            mocs = self.neo4j.get_mocs_requiring_training()
            if mocs:
                lines = [f"  {m.get('moc_id')}: {_clip(m.get('title') or m.get('name'), 50)} | {m.get('change_type')} | Approver: {m.get('approver')}" for m in mocs]
                sections.append("MoCs REQUIRING TRAINING/PROCEDURE UPDATE:\n" + "\n".join(lines))

        return "\n\n".join(sections)

    def _handle_pid_query(self, message: str) -> str | None:
        """
        Direct P&ID lookup — bypasses the LLM to give a precise answer.
        Returns a formatted string if a PID number is found, else None.
        """
        import re
        pid_match = re.search(
            r'pid[-\s]?(?:fc[-\s]?c[-\s]?|fcc[-\s]?)(\d+)',
            message, re.IGNORECASE
        )
        if not pid_match:
            return None
        num = pid_match.group(1)
        # Try both naming conventions
        mocs = self.neo4j.get_mocs_by_pid(f"PID-FCC-{num}")
        if not mocs:
            mocs = self.neo4j.get_mocs_by_pid(f"PID-FC-C-{num}")
        if not mocs:
            available = (
                "PID-FCC-101, PID-FCC-103, PID-FCC-201, PID-FCC-203, "
                "PID-FCC-204, PID-FCC-301, PID-FCC-403, PID-FCC-502, PID-FCC-LINE"
            )
            return (
                f"No MoCs found referencing P&ID number {num}.\n"
                f"Available P&ID documents in the system: {available}"
            )
        lines = [f"The following MoC(s) reference P&ID document PID-FCC-{num}:\n"]
        for m in mocs:
            lines.append(
                f"  • {m.get('moc_id')}: {m.get('title')} "
                f"| Asset: {m.get('asset_id')} ({m.get('asset_name')}) "
                f"| P&ID: {m.get('pid_ref')} {m.get('version')} "
                f"| Cost: ${m.get('cost') or 0:,}"
            )
        return "\n".join(lines)

    def reset_memory(self):
        self.memory.clear()


# ── Utility functions ──────────────────────────────────────────────────────

def _detect_intent(message: str) -> str:
    msg = message.lower()
    for intent, keywords in INTENTS.items():
        if any(kw in msg for kw in keywords):
            return intent
    return "general"


def _extract_moc_id(message: str) -> str | None:
    # Matches MoC-001 through MoC-010 (case-insensitive)
    match = re.search(r'\b(MoC-\d{3})\b', message, re.IGNORECASE)
    if match:
        raw = match.group(1)
        return "MoC-" + raw.split("-", 1)[1]
    return None


def _extract_all_moc_ids(message: str) -> list:
    """Extract ALL MoC IDs from a message (for comparison queries)."""
    matches = re.findall(r'\b(MoC-\d{3})\b', message, re.IGNORECASE)
    return list(dict.fromkeys("MoC-" + m.split("-", 1)[1] for m in matches))


def _extract_asset_id(message: str) -> str | None:
    """
    Extract asset ID from message — handles both explicit IDs (SV-204) and
    natural language names (regenerator, fractionator, cyclone, etc.)
    """
    msg = message.lower()

    # Natural language → asset ID mapping (covers all 22 assets)
    name_map = {
        # Explicit IDs first (case-insensitive)
        "sv-204": "SV-204", "slide valve": "SV-204", "catalyst slide valve": "SV-204",
        "catalyst control valve": "SV-204",
        "p-101": "P-101", "feed pump": "P-101",
        "fv-103": "FV-103", "feed heater control valve": "FV-103",
        "feed control valve": "FV-103", "feed heater valve": "FV-103",
        "r-201": "R-201", "riser reactor": "R-201", "reactor": "R-201",
        "c-203": "C-203", "cyclone separator": "C-203", "cyclone": "C-203",
        "s-301": "S-301", "catalyst stripper": "S-301", "stripper": "S-301",
        "ex-403": "EX-403", "flue gas expander": "EX-403", "expander": "EX-403",
        "p-502": "P-502", "reflux pump": "P-502",
        "ctl-205": "CTL-205", "catalyst transfer line": "CTL-205",
        "transfer line": "CTL-205",
        "rg-401": "RG-401", "regenerator": "RG-401", "regen": "RG-401",
        "f-501": "F-501", "fractionator": "F-501", "main fractionator": "F-501",
        "wgc-401": "WGC-401", "wet gas compressor": "WGC-401", "compressor": "WGC-401",
        "k-402": "K-402", "air blower": "K-402", "blower": "K-402",
        "esd-sys": "ESD-SYS", "esd": "ESD-SYS", "emergency shutdown": "ESD-SYS",
        "v-101": "V-101", "feed surge drum": "V-101", "surge drum": "V-101",
        "v-202": "V-202", "reactor vessel": "V-202",
        "e-102": "E-102", "feed heater": "E-102", "heat exchanger": "E-102",
        "fg-404": "FG-404", "flue gas line": "FG-404", "flue gas piping": "FG-404",
        "iv-303": "IV-303", "steam control valve": "IV-303",
        "st-302": "ST-302", "steam injection line": "ST-302",
        "p-503": "P-503", "rebooster pump": "P-503",
        "p-504": "P-504", "product pump": "P-504",
    }

    # Check natural language names first (longest match wins)
    for phrase in sorted(name_map.keys(), key=len, reverse=True):
        if phrase in msg:
            return name_map[phrase]

    # Fallback: regex for explicit asset IDs
    match = re.search(r'\b(ESD-SYS|ESD|[A-Z]{1,4}-\d{3,4}(?:-[A-Z]+)?)\b', message, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _extract_search_keyword(message: str) -> str:
    """
    Extracts the most useful search keyword from a message for broad graph search.
    Strips common question words and returns the most domain-relevant term.
    """
    # Asset name keywords → map to asset IDs
    asset_keywords = {
        "sv-204": "SV-204", "slide valve": "SV-204", "catalyst slide": "SV-204",
        "p-101": "P-101", "feed pump": "P-101",
        "fv-103": "FV-103", "feed heater": "FV-103", "control valve": "FV-103",
        "r-201": "R-201", "riser reactor": "R-201", "reactor": "R-201",
        "c-203": "C-203", "cyclone": "C-203",
        "s-301": "S-301", "stripper": "S-301", "steam": "S-301",
        "ex-403": "EX-403", "expander": "EX-403",
        "p-502": "P-502", "reflux pump": "P-502",
        "ctl-205": "CTL-205", "transfer line": "CTL-205",
        "esd": "ESD-SYS", "emergency shutdown": "ESD-SYS",
    }
    msg = message.lower()
    for kw, asset in asset_keywords.items():
        if kw in msg:
            return asset

    # Fall back to extracting meaningful words
    stop_words = {"what", "which", "how", "when", "where", "who", "why", "are", "is",
                  "the", "a", "an", "for", "of", "in", "on", "to", "and", "or",
                  "required", "mocs", "moc", "did", "were", "was", "all", "any"}
    words = [w for w in re.findall(r'\b\w+\b', msg) if w not in stop_words and len(w) > 3]
    return words[0] if words else "MoC"


def _extract_change_type(message: str) -> str | None:
    mapping = {
        "pump":        "Mechanical",
        "valve":       "Instrumentation",
        "pipe":        "Mechanical Integrity",
        "instrument":  "Instrumentation",
        "control":     "Instrumentation",
        "procedure":   "Procedural",
        "setpoint":    "Process Parameter",
        "temperature": "Process Parameter",
        "steam":       "Process",
        "expander":    "Mechanical Efficiency",
        "cyclone":     "Mechanical Maintenance",
        "transfer line": "Mechanical Integrity",
    }
    msg = message.lower()
    for kw, ct in mapping.items():
        if kw in msg:
            return ct
    return None


def _extract_concept(message: str) -> str:
    """
    Extract the core domain concept from a query for graph concept search.
    Maps natural language phrases to searchable terms.
    """
    msg = message.lower()
    # Direct concept mappings
    concept_map = {
        "reactor temperature": "temperature setpoint",
        "temperature setpoint": "temperature setpoint",
        "setpoint": "temperature setpoint",
        "catalyst circulation": "catalyst circulation",
        "catalyst slide valve": "catalyst circulation",
        "slide valve": "catalyst circulation",
        "actuator": "actuator",
        "emergency shutdown": "emergency shutdown",
        "esd procedure": "emergency shutdown",
        "steam optimization": "steam stripping",
        "stripping efficiency": "steam stripping",
        "transfer line": "transfer line",
        "wall thinning": "wall thinning",
        "reflux pump": "reflux pump",
        "feed pump": "feed pump",
        "cyclone": "cyclone separator",
        "expander": "expander",
        "overheating": "overheating",
        "thermal": "temperature",
        "pressure": "pressure",
        "flow rate": "flow rate",
        "instrumentation": "instrumentation",
        "procedure update": "procedure",
        "training": "training",
    }
    for phrase, concept in concept_map.items():
        if phrase in msg:
            return concept

    # Strip question words and return meaningful remainder
    stop = {"find", "show", "list", "get", "what", "which", "how", "mocs", "moc",
            "that", "mention", "involve", "related", "similar", "past", "all",
            "where", "the", "a", "an", "to", "for", "of", "in", "on", "and", "or"}
    words = [w for w in re.findall(r'\b\w+\b', msg) if w not in stop and len(w) > 3]
    return " ".join(words[:3]) if words else "change"
