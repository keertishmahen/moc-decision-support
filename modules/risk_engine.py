"""
modules/risk_engine.py  —  Module 2: Risk & Impact via Dependency Graph Reasoning
"""
import logging

from core.llm import LLMError
from core.rag_pipeline import RAGPipeline
from core.neo4j_client import Neo4jClient
from core.config import GRAPH_DEPTH
from neo4j.exceptions import ServiceUnavailable, Neo4jError

log = logging.getLogger(__name__)

_STRINGS = {"type": "array", "items": {"type": "string"}}
_YES_NO = {"type": "string", "enum": ["Yes", "No"]}
_RATING = {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]}
RISK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["risks", "directly_affected", "indirectly_affected", "process_conditions",
                 "hazop_triggered", "pssr_required", "mitigations", "overall_rating", "reasoning"],
    "properties": {
        "risks": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["severity", "description"],
            "properties": {"severity": _RATING, "description": {"type": "string"}}}},
        "directly_affected": _STRINGS,
        "indirectly_affected": _STRINGS,
        "process_conditions": {"type": "string"},
        "hazop_triggered": _YES_NO,
        "pssr_required": _YES_NO,
        "mitigations": _STRINGS,
        "overall_rating": _RATING,
        "reasoning": {"type": "string"},
    },
}

RISK_ANALYSIS_PROMPT = """
You are a senior process safety engineer reviewing a Management of Change (MoC).

PROPOSED CHANGE:
- Change Type: {change_type}
- Asset: {asset_id}
- Description: {query}

KNOWLEDGE BASE CONTEXT:
{context}

Reply as JSON with these fields:
- risks: the top three risks, each with severity (Low, Medium, High or Critical) and a description
- directly_affected: asset IDs one hop away
- indirectly_affected: asset IDs two or more hops away
- process_conditions: temperature, pressure and flow conditions at risk
- hazop_triggered: Yes or No
- pssr_required: Yes or No
- mitigations: three recommended mitigations
- overall_rating: Low, Medium, High or Critical
- reasoning: 2-3 sentences summarising the overall risk picture
Use only asset IDs that appear in the context.
"""


class RiskEngine:
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.neo4j    = Neo4jClient()

    def analyse(self, change_type: str, asset_id: str, description: str) -> dict:
        try:
            impact_chain = self.neo4j.get_impact_chain(asset_id, depth=GRAPH_DEPTH)
            hazards = self.neo4j.get_hazards_for_asset(asset_id)
            incidents = self.neo4j.get_historical_incidents(asset_id)
            graph_status = "ok"
        except (ServiceUnavailable, Neo4jError, OSError):
            impact_chain = []
            hazards = []
            incidents = []
            graph_status = "unavailable"

        augmented = (
            f"{description}. "
            f"Hazards: {', '.join(h.get('description','') for h in hazards[:3])}. "
            f"Affected assets: {', '.join(n.get('node_name','') for n in impact_chain[:5])}."
        )

        try:
            parsed = self.pipeline.run_json(
                query=augmented,
                prompt_template=RISK_ANALYSIS_PROMPT,
                schema=RISK_SCHEMA,
                name="moc_risk_analysis",
                asset_id=asset_id,
                change_type=change_type
            )
            parsed["llm_status"] = "ok"
        except LLMError as exc:
            # The AI service failed: return the graph evidence without an AI rating rather than failing.
            log.warning("Risk analysis degraded to graph evidence: %s", exc)
            parsed = _graph_only_analysis(impact_chain, hazards)
            parsed["llm_status"] = "unavailable"
        parsed["impact_chain"]    = impact_chain
        parsed["hazards"]         = hazards
        parsed["incidents"]       = incidents
        parsed["graph_status"]    = graph_status
        parsed["direct_assets"]   = [n for n in impact_chain if n.get("hop_distance") == 1]
        parsed["indirect_assets"] = [n for n in impact_chain if n.get("hop_distance", 0) > 1]
        return parsed


def _graph_only_analysis(impact_chain: list, hazards: list) -> dict:
    """What the knowledge graph alone supports, used when the AI service is unavailable."""
    severities = {"Low", "Medium", "High", "Critical"}
    return {
        "risks": [{"severity": h.get("severity") if h.get("severity") in severities else "Medium",
                   "description": h.get("description") or ""} for h in hazards[:3]],
        "directly_affected": [n.get("node_id") for n in impact_chain if n.get("hop_distance") == 1],
        "indirectly_affected": [n.get("node_id") for n in impact_chain if (n.get("hop_distance") or 0) > 1],
        "process_conditions": "",
        "hazop_triggered": "Unknown",
        "pssr_required": "Unknown",
        "mitigations": [],
        "overall_rating": "Unknown",
        "reasoning": ("AI analysis is unavailable right now. The hazards and affected assets shown come from "
                      "the knowledge graph; no overall rating has been assigned."),
    }
