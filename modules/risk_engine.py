"""
modules/risk_engine.py  —  Module 2: Risk & Impact via Dependency Graph Reasoning
"""
from core.rag_pipeline import RAGPipeline
from core.neo4j_client import Neo4jClient
from core.config import GRAPH_DEPTH
from neo4j.exceptions import ServiceUnavailable, Neo4jError

RISK_ANALYSIS_PROMPT = """
You are a senior process safety engineer reviewing a Management of Change (MoC).

PROPOSED CHANGE:
- Change Type: {change_type}
- Asset: {asset_id}
- Description: {query}

KNOWLEDGE BASE CONTEXT:
{context}

Respond in this EXACT format:

TOP_RISKS:
1. [SEVERITY: High/Medium/Low] <Risk description>
2. [SEVERITY: ...] <...>
3. [SEVERITY: ...] <...>

DIRECTLY_AFFECTED_ASSETS: <comma-separated asset IDs>
INDIRECTLY_AFFECTED_ASSETS: <comma-separated — 2+ hops>
PROCESS_CONDITIONS_AT_RISK: <temperature, pressure, flow conditions>
HAZOP_TRIGGERED: <Yes | No>
PSSR_REQUIRED: <Yes | No>

RECOMMENDED_MITIGATIONS:
- <Mitigation 1>
- <Mitigation 2>
- <Mitigation 3>

OVERALL_RISK_RATING: <Low | Medium | High | Critical>
REASONING: <2-3 sentences summarising the overall risk picture>
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

        raw = self.pipeline.run(
            query=augmented,
            prompt_template=RISK_ANALYSIS_PROMPT,
            asset_id=asset_id,
            change_type=change_type
        )
        parsed = _parse_risk_response(raw)
        parsed["impact_chain"]    = impact_chain
        parsed["hazards"]         = hazards
        parsed["incidents"]       = incidents
        parsed["graph_status"]    = graph_status
        parsed["direct_assets"]   = [n for n in impact_chain if n.get("hop_distance") == 1]
        parsed["indirect_assets"] = [n for n in impact_chain if n.get("hop_distance", 0) > 1]
        return parsed


def _parse_risk_response(raw: str) -> dict:
    result = {
        "risks": [], "directly_affected": [], "indirectly_affected": [],
        "process_conditions": "", "hazop_triggered": "Unknown",
        "pssr_required": "Unknown", "mitigations": [],
        "overall_rating": "Unknown", "reasoning": "",
    }
    current_section = None
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("TOP_RISKS:"):
            current_section = "risks"
        elif line.startswith("DIRECTLY_AFFECTED_ASSETS:"):
            val = line.split(":", 1)[1].strip()
            result["directly_affected"] = [v.strip() for v in val.split(",") if v.strip()]
        elif line.startswith("INDIRECTLY_AFFECTED_ASSETS:"):
            val = line.split(":", 1)[1].strip()
            result["indirectly_affected"] = [v.strip() for v in val.split(",") if v.strip()]
        elif line.startswith("PROCESS_CONDITIONS_AT_RISK:"):
            result["process_conditions"] = line.split(":", 1)[1].strip()
            current_section = None
        elif line.startswith("HAZOP_TRIGGERED:"):
            result["hazop_triggered"] = line.split(":", 1)[1].strip()
        elif line.startswith("PSSR_REQUIRED:"):
            result["pssr_required"] = line.split(":", 1)[1].strip()
        elif line.startswith("RECOMMENDED_MITIGATIONS:"):
            current_section = "mitigations"
        elif line.startswith("OVERALL_RISK_RATING:"):
            result["overall_rating"] = line.split(":", 1)[1].strip()
            current_section = None
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()
            current_section = None
        elif current_section == "risks" and line[0].isdigit():
            sev, desc = "Medium", line
            if "[SEVERITY:" in line:
                try:
                    sev  = line.split("[SEVERITY:")[1].split("]")[0].strip()
                    desc = line.split("]", 1)[1].strip()
                except IndexError:
                    pass
            result["risks"].append({"severity": sev, "description": desc})
        elif current_section == "mitigations" and line.startswith("-"):
            result["mitigations"].append(line.lstrip("- ").strip())
    return result
