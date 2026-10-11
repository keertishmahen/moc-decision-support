"""
modules/smart_forms.py  —  Module 1: Smart Guided Forms with Auto-Prefill
"""
from core.rag_pipeline import RAGPipeline
from core.neo4j_client import Neo4jClient
from neo4j.exceptions import ServiceUnavailable, Neo4jError

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

Respond in this EXACT format (one value per line):
RECOMMENDED_APPROVERS: <comma-separated roles from graph-verified approvers>
REQUIRED_DOCUMENTS: <comma-separated document types>
SUGGESTED_RISK_LEVEL: <Low | Medium | High | Critical>
HAZOP_REQUIRED: <Yes | No>
PSSR_REQUIRED: <Yes | No>
AFFECTED_SCOPE: <brief description of affected systems>
PID_TAGS_TO_REVIEW: <comma-separated P&ID references>
JUSTIFICATION: <2-3 sentences citing specific MoC IDs and risk scores from the context>
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

        raw = self.pipeline.run(
            query=description,
            prompt_template=FORM_PREFILL_PROMPT,
            asset_id=asset_id,
            change_type=change_type,
            extra_vars={"approver_hint": approver_hint or "Process Safety Manager, Safety Manager, Maintenance Manager"}
        )
        suggestions = _parse_form_response(raw)
        suggestions["graph_approvers"]    = graph_approvers
        suggestions["graph_pid_entities"] = graph_pid
        suggestions["graph_status"]       = graph_status
        # If LLM returned no approvers, fall back to graph data
        if not suggestions["approvers"] and graph_approvers:
            suggestions["approvers"] = [a.get("approver","") for a in graph_approvers[:3]]
        return suggestions

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


def _parse_form_response(raw: str) -> dict:
    result = {
        "approvers": [], "documents": [], "risk_level": "Unknown",
        "hazop_required": "Unknown", "pssr_required": "Unknown",
        "scope": "", "pid_tags": [], "justification": "",
    }
    key_map = {
        "RECOMMENDED_APPROVERS": "approvers",
        "REQUIRED_DOCUMENTS":    "documents",
        "SUGGESTED_RISK_LEVEL":  "risk_level",
        "HAZOP_REQUIRED":        "hazop_required",
        "PSSR_REQUIRED":         "pssr_required",
        "AFFECTED_SCOPE":        "scope",
        "PID_TAGS_TO_REVIEW":    "pid_tags",
        "JUSTIFICATION":         "justification",
    }
    for line in raw.strip().splitlines():
        for key, field in key_map.items():
            if line.startswith(key + ":"):
                value = line.split(":", 1)[1].strip()
                if field in ("approvers", "documents", "pid_tags"):
                    result[field] = [v.strip() for v in value.split(",") if v.strip()]
                else:
                    result[field] = value
    return result
