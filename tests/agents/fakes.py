"""Fake AI/ML components for the agent tests."""
from core.downtime_propagator import PropagatedDowntime, PropagationResult

DESC = "Replace FV-103 with smart control valve to improve temperature regulation and enable remote monitoring"


class FakeRag:
    def get_raw_context(self, query, asset_id=None, change_type=None, moc_id=None):
        return {
            "vector_hits": [{"moc_id": "MoC-002", "similarity": 0.81, "metadata": {"title": "Feed Heater Control Valve Upgrade"}},
                            {"moc_id": "MoC-005", "similarity": 0.55, "metadata": {"title": "Catalyst Control Valve"}}],
            "hazards": [{"hazard_id": "HZ-002", "description": "Temperature control instability", "severity": "Medium"}],
            "incidents": [],
            "lessons": [{"moc_id": "MoC-002", "summary": "Tune the PID loop before start-up"}],
            "similar_mocs": [{"moc_id": "MoC-002", "risk_level": "Medium", "hazop_required": True, "pssr_required": True},
                             {"moc_id": "MoC-005", "risk_level": "High", "hazop_required": True, "pssr_required": True}],
        }


class FakeRisk:
    def __init__(self, hazop="Yes", named=("R-201",), fail=False, llm="ok"):
        self.hazop, self.named, self.fail, self.llm = hazop, list(named), fail, llm

    def analyse(self, change_type, asset_id, description):
        if self.fail:
            raise RuntimeError("risk engine exploded")
        return {"overall_rating": "Medium", "hazop_triggered": self.hazop, "pssr_required": "Yes",
                "risks": [{"severity": "Medium", "description": "Temperature oscillation at R-201"}],
                "mitigations": ["Tune the loop"], "reasoning": "r", "directly_affected": self.named,
                "indirectly_affected": [], "hazards": [{"hazard_id": "HZ-002", "description": "x"}],
                "llm_status": self.llm, "graph_status": "ok"}


class FakeForms:
    def __init__(self, hazop="Yes", tags=("PID-FCC-103",)):
        self.hazop, self.tags = hazop, list(tags)

    def get_prefill_suggestions(self, change_type, asset_id, description):
        return {"approvers": ["Safety Manager"], "documents": ["HAZOP"], "risk_level": "Medium",
                "hazop_required": self.hazop, "pssr_required": "Yes", "scope": "", "pid_tags": self.tags,
                "justification": "", "graph_approvers": [{"approver": "Safety Manager", "freq": 2}],
                "graph_pid_entities": [{"asset_id": asset_id, "pid_refs": ["PID-FCC-103"]}],
                "graph_status": "ok", "llm_status": "ok"}


class FakeCost:
    def predict(self, change_type, asset_id, asset_category, risk_level, description):
        self.args = (asset_category, risk_level)
        return {"cost_estimate": 36000.0, "cost_ci": [27000.0, 45000.0], "downtime_estimate": 26.0,
                "downtime_ci": [18.2, 33.8], "features": {"n_dependencies": 5, "n_hazards": 1},
                "explanation": "e", "models_used": "heuristic", "graph_status": "ok", "llm_status": "ok"}


class FakePropagator:
    def propagate(self, asset_id, hours):
        return PropagationResult(
            source_asset_id=asset_id, source_asset_name=asset_id, source_downtime=hours, total_affected=1,
            total_propagated_hours=20.4,
            affected_assets=[PropagatedDowntime("R-201", "R-201", "Reactor", 5, 1, 20.4, 14.3, 26.5, 0.85,
                                                [asset_id, "R-201"], ["FEEDS"], ["feed"], "AREA-RXR", 1, "High")])


class FakeNeo4j:
    def get_all_assets(self):
        return [{"id": a} for a in ("FV-103", "R-201", "C-203", "P-101", "SV-204", "RG-401")]

    def _run(self, query, params=None):
        return [{"pid": "PID-FCC-103"}, {"pid": "PID-FCC-201"}]
