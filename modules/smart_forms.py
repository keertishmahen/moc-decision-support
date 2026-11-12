"""
modules/smart_forms.py  —  Module 1: Smart Guided Forms with Auto-Prefill
"""
import logging

from core.llm import LLMError
from core.rag_pipeline import RAGPipeline
from core.neo4j_client import Neo4jClient
from neo4j.exceptions import ServiceUnavailable, Neo4jError

log = logging.getLogger(__name__)

_STRINGS = {"type": "array", "items": {"type": "string"}}
_YES_NO = {"type": "string", "enum": ["Yes", "No"]}
FORM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["approvers", "documents", "risk_level", "hazop_required", "pssr_required",
                 "scope", "pid_tags", "justification"],
    "properties": {
        "approvers": _STRINGS,
        "documents": _STRINGS,
        "risk_level": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]},
        "hazop_required": _YES_NO,
        "pssr_required": _YES_NO,
        "scope": {"type": "string"},
        "pid_tags": _STRINGS,
        "justification": {"type": "string"},
    },
}

FORM_PREFILL_PROMPT = """
You are an expert MoC (Management of Change) engineer in a process plant.
A user is filling in a new MoC initiation form. Based on the historical context below,
suggest values for the empty fields. Be specific and concise — cite actual data from the context.

CURRENT FORM (partial):
- Change Type: {change_type}
- Asset ID: {asset_id}
- Description: {query}

GRAPH-VERIFIED APPROVERS FOR THIS CHANGE TYPE: {approver_hint}

RETRIEVED CONTEXT FROM KNOWLEDGE BASE:
{context}

RULES:
- Use the GRAPH-VERIFIED APPROVERS above for the RECOMMENDED_APPROVERS field
- Base HAZOP_REQUIRED and PSSR_REQUIRED on the historical MoCs in the context
- Base SUGGESTED_RISK_LEVEL on the risk scores in the context
- Be specific — reference actual asset IDs and P&ID references from the context

Reply as JSON with these fields:
- approvers: roles from the graph-verified approvers
- documents: required document types
- risk_level: Low, Medium, High or Critical
- hazop_required: Yes or No
- pssr_required: Yes or No
- scope: brief description of affected systems
- pid_tags: P&ID references to review
- justification: 2-3 sentences citing specific MoC IDs and risk scores from the context
"""


class SmartFormModule:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.neo4j    = Neo4jClient()

    def get_prefill_suggestions(self, change_type: str, asset_id: str, description: str) -> dict:
        # Pre-fetch graph approvers to inject into prompt
        try:
            graph_approvers = self.neo4j.get_common_approvers(change_type)
            graph_pid       = self.neo4j.get_pid_entities_for_asset(asset_id)
            approver_hint   = ", ".join(a.get("approver","") for a in graph_approvers[:3]) if graph_approvers else ""
            graph_status    = "ok"
        except (ServiceUnavailable, Neo4jError, OSError):
            graph_approvers = []
            graph_pid       = []
            approver_hint   = ""
            graph_status    = "unavailable"

        try:
            suggestions = self.pipeline.run_json(
                query=description,
                prompt_template=FORM_PREFILL_PROMPT,
                schema=FORM_SCHEMA,
                name="moc_form_prefill",
                asset_id=asset_id,
                change_type=change_type,
                extra_vars={"approver_hint": approver_hint or "Process Safety Manager, Safety Manager, Maintenance Manager"}
            )
            suggestions["llm_status"] = "ok"
        except LLMError as exc:
            # The AI service failed: answer from the knowledge graph alone rather than failing the request.
            log.warning("Form prefill degraded to graph evidence: %s", exc)
            suggestions = self._graph_only_suggestions(change_type, asset_id, graph_pid)
            suggestions["llm_status"] = "unavailable"
        suggestions["graph_approvers"]    = graph_approvers
        suggestions["graph_pid_entities"] = graph_pid
        suggestions["graph_status"]       = graph_status
        # If LLM returned no approvers, fall back to graph data
        if not suggestions["approvers"] and graph_approvers:
            suggestions["approvers"] = [a.get("approver","") for a in graph_approvers[:3]]
        return suggestions

    def _graph_only_suggestions(self, change_type: str, asset_id: str, graph_pid: list) -> dict:
        """Suggestions derived from historical MoCs in the graph, used when the AI service is unavailable."""
        try:
            similar = self.neo4j.get_similar_mocs(change_type, asset_id, 5)
        except (ServiceUnavailable, Neo4jError, OSError):
            similar = []
        order = ["Low", "Medium", "High", "Critical"]
        levels = [m.get("risk_level") for m in similar if m.get("risk_level") in order]

        def majority(key):
            flags = [bool(m.get(key)) for m in similar if m.get(key) is not None]
            return "Unknown" if not flags else ("Yes" if sum(flags) * 2 >= len(flags) else "No")

        ids = ", ".join(m.get("moc_id", "") for m in similar[:3])
        return {
            "approvers": [], "documents": [],
            "risk_level": max(levels, key=order.index) if levels else "Unknown",
            "hazop_required": majority("hazop_required"), "pssr_required": majority("pssr_required"),
            "scope": "", "pid_tags": [str(p.get("pid_ref") or p.get("pid") or "") for p in (graph_pid or []) if p][:5],
            "justification": ("AI suggestions are unavailable right now. These values come from historical MoCs "
                              f"in the knowledge graph ({ids or 'none found'}); review them before use."),
        }

    def get_similar_mocs_summary(self, change_type: str, asset_id: str,
                                  description: str, top_k: int = 5) -> list:
        vector_hits = self.pipeline.retriever.vector_store.search(description, top_k=top_k)
        try:
            graph_hits = self.neo4j.get_similar_mocs(change_type, asset_id, top_k)
        except (ServiceUnavailable, Neo4jError, OSError):
            graph_hits = []
        merged = {h["moc_id"]: h for h in graph_hits}
        for h in vector_hits:
            if h["moc_id"] not in merged:
                merged[h["moc_id"]] = h
            else:
                merged[h["moc_id"]]["similarity"] = h.get("similarity", 0)
        return sorted(merged.values(), key=lambda x: x.get("similarity", 0), reverse=True)[:top_k]
