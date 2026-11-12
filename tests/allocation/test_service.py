"""
tests/allocation/test_service.py — graph facts -> suggested characterisation -> allocation.

Offline: the knowledge graph is replaced by data/graph/fcc_graph.json (see tests/file_graph.py).
"""
import pytest

from modules.decision_allocation import NotFound
from modules.decision_allocation.characteriser import ChangeFacts, facts_from_moc, suggest

LOWEST = {"A1": "operational", "A2": "unit", "A3": "temporary", "A4": "local",
          "A5": "individual", "A6": "by_procedure", "A7": "deterministic", "A8": "technical"}


class TestDemoSequence:
    def test_moc_002_is_ai_supported_with_the_published_scores(self, allocation_service):
        a = allocation_service.assess_moc("MoC-002")
        assert a["result"]["scores"] == {"R": 2.0, "C": 1.5, "U": 0.5, "I": 2.5}
        assert a["result"]["signature"] == "II/II/II"
        assert a["result"]["allocation"] == "AI_SUPPORTED"
        assert a["subject"]["case_id"] == "MOC-F02" and a["subject"]["asset_id"] == "FV-103"

    def test_the_recommendation_is_explained_by_the_decision_characteristics(self, allocation_service):
        result = allocation_service.assess_moc("MoC-002")["result"]
        text = " ".join(result["reasons"])
        for expected in ("Tactical", "Sub-system level", "Collective", "Partially defined", "factor II"):
            assert expected in text
        risk = next(d for d in result["dimensions"] if d["id"] == "R")
        assert {c["category"] for c in risk["contributions"]} == {"Tactical", "Permanent change", "Technical"}

    def test_moc_001_is_human_led_through_uncertainty_alone(self, allocation_service):
        a = allocation_service.assess_moc("MoC-001")
        assert a["result"]["allocation"] == "HUMAN_LED"
        assert a["result"]["escalated_by"] == ["U"]

    def test_impact_assessment_comes_from_the_graph(self, allocation_service):
        impact = allocation_service.assess_moc("MoC-002")["impact_assessment"]
        assert impact["asset"]["criticality"] == 3 and impact["asset"]["areas"] == ["AREA-FEED"]
        assert impact["safety"] == {"hazop_required": True, "pssr_required": True, "shutdown_required": True}
        assert impact["reach"]["direct"] == ["R-201"]
        assert impact["reach"]["assets_affected"] >= 8
        assert impact["risk_assessment"]["category"] == "Medium"

    def test_every_axis_reports_its_suggestion_and_evidence(self, allocation_service):
        axes = allocation_service.assess_moc("MoC-002")["axes"]
        assert [a["axis_id"] for a in axes] == [f"A{i}" for i in range(1, 9)]
        for a in axes:
            assert a["suggested"]["evidence"] and a["suggested"]["confidence"] in {"high", "medium", "low"}
            assert a["reference"]["status"] == "reconstructed-pending-confirmation"

    def test_duration_is_flagged_as_an_assumption(self, allocation_service):
        a3 = next(a for a in allocation_service.assess_moc("MoC-005")["axes"] if a["axis_id"] == "A3")
        assert a3["suggested"]["source"] == "default" and a3["suggested"]["confidence"] == "low"


class TestReferenceCases:
    def test_all_ten_cases_reproduce(self, allocation_service):
        cases = allocation_service.reference_cases()
        assert cases["reproduced"] == 10 and cases["total"] == 10

    def test_rule_suggestions_agree_with_the_reference_on_79_of_80_axis_values(self, allocation_service):
        """A consistency check, not a validation: the rules were fitted to these ten cases."""
        cases = allocation_service.reference_cases()["cases"]
        assert sum(c["rule_agreement"]["agreeing_axes"] for c in cases) == 79
        differing = {c["moc_id"]: c["rule_agreement"]["differing_axes"]
                     for c in cases if c["rule_agreement"]["differing_axes"]}
        assert differing == {"MoC-008": ["A8"]}


class TestProposedChange:
    def test_a_proposal_gets_suggestions_marked_for_confirmation(self, allocation_service):
        a = allocation_service.assess_change("Instrumentation", "FV-103", "Upgrade the valve positioner")
        assert a["subject"]["kind"] == "proposed" and a["characterisation_status"] == "suggested"
        assert all(x["reference"] is None for x in a["axes"])
        assert a["result"]["allocation"] in {"AI_LED", "AI_SUPPORTED", "HUMAN_LED"}
        assert a["impact_assessment"]["history"]["mocs_on_asset"] == ["MoC-002"]

    def test_known_hazop_need_changes_the_suggestion(self, allocation_service):
        without = allocation_service.assess_change("Mechanical", "P-101", "Planned impeller upgrade", hazop_required=False)
        with_hazop = allocation_service.assess_change("Mechanical", "P-101", "Planned impeller upgrade", hazop_required=True)
        assert without["selection"]["A5"] == "individual" and with_hazop["selection"]["A5"] == "collective"

    def test_temporary_wording_is_picked_up(self, allocation_service):
        a = allocation_service.assess_change("Mechanical", "P-101", "Temporary bypass of the feed pump until further notice")
        assert a["selection"]["A3"] == "undefined_duration"

    def test_unknown_asset_is_not_found(self, allocation_service):
        with pytest.raises(NotFound):
            allocation_service.assess_change("Mechanical", "NOPE-1", "x")

    def test_unknown_moc_is_not_found(self, allocation_service):
        with pytest.raises(NotFound):
            allocation_service.assess_moc("MoC-999")


class TestGraphUnavailable:
    def test_reference_case_still_scores_without_the_graph(self, offline_service):
        a = offline_service.assess_moc("MoC-002")
        assert a["graph_status"] == "unavailable"
        assert a["impact_assessment"] is None
        assert a["result"]["allocation"] == "AI_SUPPORTED"
        assert all(x["suggested"] is None for x in a["axes"])

    def test_scoring_and_cases_do_not_need_the_graph(self, offline_service):
        assert offline_service.score(LOWEST)["allocation"] == "AI_LED"
        cases = offline_service.reference_cases()
        assert cases["reproduced"] == 10 and cases["graph_status"] == "unavailable"

    def test_proposal_degrades_to_low_confidence_suggestions(self, offline_service):
        a = offline_service.assess_change("Mechanical", "P-101", "Replace the pump")
        assert a["graph_status"] == "unavailable" and a["impact_assessment"]["reach"]["available"] is False


class TestRules:
    def test_facts_are_read_from_the_graph_record(self, file_graph):
        f = facts_from_moc(file_graph.get_moc_facts(None, "MoC-006"))
        assert f.hazop_required is True and f.numeric_parameter and f.criticality == 4
        assert f.action_type == "Parameter and equipment change" and not f.reactive

    def test_plant_wide_change_is_system_level_and_general(self):
        s = suggest(ChangeFacts(kind="moc", change_type="Procedural", areas=["AREA-ALL"], hazop_required=True))
        assert (s["A2"].value, s["A4"].value, s["A8"].value) == ("system", "general", "organisational")

    def test_unknown_hazop_lowers_confidence_and_stays_cautious(self):
        s = suggest(ChangeFacts(change_type="Mechanical", description="Planned upgrade", criticality=3))
        assert s["A5"].value == "collective" and s["A5"].confidence == "low"
