"""
tests/modules/test_degradation.py — when the AI service fails, features answer from the graph
instead of failing; structured replies keep the response shape the frontend expects.

Offline: modules are built without their constructors (which open Neo4j and ChromaDB).
"""
import threading
from collections import OrderedDict

from core.downtime_propagator import DowntimePropagator
from core.llm import LLMUnavailable
from modules.nlp_chatbot import MoCChatbot
from modules.risk_engine import RiskEngine
from modules.smart_forms import SmartFormModule

FORM_KEYS = {"approvers", "documents", "risk_level", "hazop_required", "pssr_required", "scope",
             "pid_tags", "justification", "graph_approvers", "graph_pid_entities", "graph_status", "llm_status"}
RISK_KEYS = {"risks", "directly_affected", "indirectly_affected", "process_conditions", "hazop_triggered",
             "pssr_required", "mitigations", "overall_rating", "reasoning", "impact_chain", "hazards",
             "incidents", "graph_status", "direct_assets", "indirect_assets", "llm_status"}


class FakePipeline:
    def __init__(self, reply=None, fail=False):
        self.reply, self.fail, self.calls = reply, fail, []

    def run_json(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise LLMUnavailable("AI service call failed (APITimeoutError).")
        return dict(self.reply)


class FakeGraph:
    def get_common_approvers(self, change_type):
        return [{"approver": "Process Safety Manager", "department": "HSE", "freq": 3}]

    def get_pid_entities_for_asset(self, asset_id):
        return [{"pid_ref": "PID-FCC-101"}]

    def get_similar_mocs(self, change_type, asset_id, top_k=5):
        return [{"moc_id": "MoC-001", "risk_level": "High", "hazop_required": False, "pssr_required": True},
                {"moc_id": "MoC-008", "risk_level": "Medium", "hazop_required": True, "pssr_required": True},
                {"moc_id": "MoC-004", "risk_level": "High", "hazop_required": True, "pssr_required": True}]

    def get_impact_chain(self, asset_id, depth=3):
        return [{"node_id": "R-201", "node_name": "R-201", "node_type": "Reactor", "hop_distance": 1},
                {"node_id": "C-203", "node_name": "C-203", "node_type": "Cyclone", "hop_distance": 2}]

    def get_hazards_for_asset(self, asset_id):
        return [{"hazard_id": "HZ-001", "description": "Feed flow instability", "severity": "High"}]

    def get_historical_incidents(self, asset_id):
        return []


def smart_forms(pipeline):
    m = SmartFormModule.__new__(SmartFormModule)
    m.pipeline, m.neo4j = pipeline, FakeGraph()
    return m


def risk_engine(pipeline):
    m = RiskEngine.__new__(RiskEngine)
    m.pipeline, m.neo4j = pipeline, FakeGraph()
    return m


class TestSmartForm:
    REPLY = {"approvers": ["Safety Manager"], "documents": ["HAZOP"], "risk_level": "Medium", "hazop_required": "Yes",
             "pssr_required": "Yes", "scope": "Feed section", "pid_tags": ["PID-FCC-101"], "justification": "MoC-001."}

    def test_structured_reply_keeps_the_response_shape(self):
        pipeline = FakePipeline(self.REPLY)
        out = smart_forms(pipeline).get_prefill_suggestions("Mechanical", "P-101", "Replace pump")
        assert set(out) == FORM_KEYS
        assert out["llm_status"] == "ok" and out["risk_level"] == "Medium"
        assert pipeline.calls[0]["name"] == "moc_form_prefill" and pipeline.calls[0]["schema"]["type"] == "object"

    def test_ai_failure_degrades_to_graph_evidence(self):
        out = smart_forms(FakePipeline(fail=True)).get_prefill_suggestions("Mechanical", "P-101", "Replace pump")
        assert set(out) == FORM_KEYS
        assert out["llm_status"] == "unavailable"
        assert out["risk_level"] == "High"                              # highest among similar MoCs
        assert out["hazop_required"] == "Yes" and out["pssr_required"] == "Yes"
        assert out["approvers"] == ["Process Safety Manager"]           # from the graph
        assert "unavailable" in out["justification"] and "MoC-001" in out["justification"]


class TestRiskEngine:
    REPLY = {"risks": [{"severity": "High", "description": "x"}], "directly_affected": ["R-201"],
             "indirectly_affected": ["C-203"], "process_conditions": "temperature", "hazop_triggered": "Yes",
             "pssr_required": "Yes", "mitigations": ["m"], "overall_rating": "High", "reasoning": "r"}

    def test_structured_reply_keeps_the_response_shape(self):
        out = risk_engine(FakePipeline(self.REPLY)).analyse("Mechanical", "P-101", "Replace pump")
        assert set(out) == RISK_KEYS
        assert out["llm_status"] == "ok" and out["overall_rating"] == "High"
        assert [a["node_id"] for a in out["direct_assets"]] == ["R-201"]

    def test_ai_failure_returns_graph_evidence_without_a_rating(self):
        out = risk_engine(FakePipeline(fail=True)).analyse("Mechanical", "P-101", "Replace pump")
        assert set(out) == RISK_KEYS
        assert out["llm_status"] == "unavailable"
        assert out["overall_rating"] == "Unknown" and out["hazop_triggered"] == "Unknown"
        assert out["risks"] == [{"severity": "High", "description": "Feed flow instability"}]
        assert out["directly_affected"] == ["R-201"] and out["indirectly_affected"] == ["C-203"]


class TestChatMemory:
    def chatbot(self):
        bot = MoCChatbot.__new__(MoCChatbot)
        bot._memories, bot._memories_lock = OrderedDict(), threading.Lock()
        return bot

    def test_each_session_has_its_own_history(self):
        bot = self.chatbot()
        bot._memory_for("alice").add("q1", "a1")
        assert bot._memory_for("alice").turns() == [("q1", "a1")]
        assert bot._memory_for("bob").turns() == []

    def test_reset_clears_only_the_callers_session(self):
        bot = self.chatbot()
        bot._memory_for("alice").add("q1", "a1")
        bot._memory_for("bob").add("q2", "a2")
        bot.reset_memory("alice")
        assert bot._memory_for("alice").turns() == [] and bot._memory_for("bob").turns() == [("q2", "a2")]

    def test_session_count_is_bounded(self):
        bot = self.chatbot()
        for i in range(bot.MAX_SESSIONS + 5):
            bot._memory_for(f"s{i}")
        assert len(bot._memories) == bot.MAX_SESSIONS and "s0" not in bot._memories


class TestPropagation:
    class Graph:
        """Two routes reach C-203; the query returns one row per route."""

        def get_enriched_impact_chain(self, asset_id, depth=4):
            base = {"node_name": "x", "node_type": "Vessel", "criticality": 4, "flow_types": [], "active_moc_count": 0, "area": "A"}
            return [
                {**base, "node_id": "R-201", "hop_distance": 1, "relationship_chain": ["FEEDS"]},
                {**base, "node_id": "C-203", "hop_distance": 2, "relationship_chain": ["FEEDS", "FEEDS"]},
                {**base, "node_id": "C-203", "hop_distance": 3, "relationship_chain": ["FEEDS", "UPSTREAM_OF", "FEEDS"]},
            ]

        def _run(self, query, params=None):
            return [{"name": "P-101", "asset_id": "P-101", "equipment_type": "Pump", "criticality": 4}]

    def test_an_asset_reached_by_two_routes_is_counted_once(self):
        result = DowntimePropagator(self.Graph()).propagate("P-101", 24.0)
        ids = [a.asset_id for a in result.affected_assets]
        assert sorted(ids) == ["C-203", "R-201"]
        assert result.total_affected == 2
        assert result.total_propagated_hours == round(sum(a.propagated_hours for a in result.affected_assets), 1)
        strongest = next(a for a in result.affected_assets if a.asset_id == "C-203")
        assert strongest.hop_distance == 2                              # the stronger (shorter) route is kept


def test_chat_and_agent_prompts_forbid_emojis():
    from core.moc_agent import AGENT_SYSTEM_PROMPT
    from modules.nlp_chatbot import SYSTEM_PROMPT
    for prompt in (SYSTEM_PROMPT, AGENT_SYSTEM_PROMPT):
        assert "Do not use emojis" in prompt
