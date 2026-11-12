"""
tests/allocation/test_lookup.py — what MoCBot and the agent are told about an MoC's allocation.

Offline.
"""
from core.allocation_lookup import allocation_summary, allocation_summary_text
from modules.nlp_chatbot import _asks_about_allocation


class StoredGraph:
    """A graph holding MoC-002's characterisation."""

    def _run(self, query, params=None):
        if params["moc_id"] != "MoC-002":
            return []
        return [{"status": "reconstructed-pending-confirmation",
                 "categories": ["A1.tactical", "A2.sub_system", "A3.permanent", "A4.local",
                                "A5.collective", "A6.by_procedure", "A7.partially_defined", "A8.technical"]}]


class BrokenGraph:
    def _run(self, query, params=None):
        raise ConnectionError("graph offline (test)")


def test_summary_uses_the_characterisation_stored_in_the_graph():
    s = allocation_summary(StoredGraph(), "MoC-002")
    assert s["allocation"] == "AI-supported"
    assert s["signature_risk_complexity_uncertainty"] == "II/II/II"
    assert s["scores"] == {"Risk": 2.0, "Complexity": 1.5, "Uncertainty": 0.5, "Impact": 2.5}
    assert s["escalated_by"] == []


def test_summary_falls_back_to_the_reference_file_when_the_graph_fails():
    s = allocation_summary(BrokenGraph(), "MoC-001")
    assert s["allocation"] == "Human-led" and s["escalated_by"] == ["Uncertainty"]


def test_unknown_moc_reports_an_error_instead_of_guessing():
    assert "error" in allocation_summary(StoredGraph(), "MoC-999")


def test_context_text_tells_the_model_to_report_not_rederive():
    text = allocation_summary_text(StoredGraph(), "MoC-002")
    assert "Recommended allocation: AI-supported" in text
    assert "do not re-derive" in text


def test_allocation_questions_are_recognised():
    assert _asks_about_allocation("Who should decide MoC-002 — should it be AI-led?")
    assert _asks_about_allocation("What is the decision allocation for MoC-009?")
    assert not _asks_about_allocation("What was the cost of MoC-003?")
