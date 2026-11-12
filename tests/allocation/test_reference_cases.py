"""
tests/allocation/test_reference_cases.py — thesis Table 2 and Appendix G, reproduced.

Offline: no database, no network.
"""
import pytest

from core.allocation import score
from core.allocation.reference_cases import compare_all, reference_case_for_moc, reference_cases
from core.allocation.types import Allocation

# Thesis Table 2: case -> (R, C, U, I, signature, allocation)
TABLE_2 = {
    "MOC-F01": (1.5, 1, 1, 1.5, "II/I/III", Allocation.HUMAN_LED),
    "MOC-F02": (2, 1.5, 0.5, 2.5, "II/II/II", Allocation.AI_SUPPORTED),
    "MOC-F03": (2.5, 3, 0.5, 4.5, "III/III/III", Allocation.HUMAN_LED),
    "MOC-F04": (1.5, 1, 1.5, 1.5, "II/I/III", Allocation.HUMAN_LED),
    "MOC-F05": (2.5, 3, 0.5, 4.5, "III/III/III", Allocation.HUMAN_LED),
    "MOC-F06": (2, 2.5, 0.5, 3.5, "III/III/III", Allocation.HUMAN_LED),
    "MOC-F07": (2.5, 0, 0, 2.5, "III/I/I", Allocation.HUMAN_LED),
    "MOC-F08": (2.5, 2.5, 1.5, 3, "III/III/III", Allocation.HUMAN_LED),
    "MOC-F09": (3, 4, 2, 5, "III/III/III", Allocation.HUMAN_LED),
    "MOC-F10": (2, 3, 0.5, 4, "III/III/III", Allocation.HUMAN_LED),
}


def test_there_are_ten_reference_cases_mapped_to_the_ten_mocs():
    cases = reference_cases()
    assert [c.case_id for c in cases] == sorted(TABLE_2)
    assert [c.moc_id for c in cases] == [f"MoC-{i:03d}" for i in range(1, 11)]


@pytest.mark.parametrize("case_id", sorted(TABLE_2))
def test_engine_reproduces_thesis_table_2(case_id):
    case = next(c for c in reference_cases() if c.case_id == case_id)
    r = score(case.selection)
    R, C, U, I, signature, allocation = TABLE_2[case_id]
    assert {d: r.dimensions[d].score for d in "RCUI"} == {"R": R, "C": C, "U": U, "I": I}
    assert r.signature == signature
    assert r.allocation is allocation


def test_stored_expectations_agree_with_table_2():
    for row in compare_all():
        assert row["matches"], f"{row['case_id']} differs on {row['differences']}"


def test_moc_f02_is_the_only_ai_supported_case():
    allocations = {row["case_id"]: row["computed"]["allocation"] for row in compare_all()}
    assert [k for k, v in allocations.items() if v == "AI_SUPPORTED"] == ["MOC-F02"]
    assert not [k for k, v in allocations.items() if v == "AI_LED"]


def test_f01_and_f04_are_escalated_by_uncertainty_alone():
    for moc in ("MoC-001", "MoC-004"):
        r = score(reference_case_for_moc(moc).selection)
        assert r.escalated_by == ("U",), moc
        assert r.dimensions["C"].level.value == "LOW"


def test_f03_and_f05_characterise_identically():
    assert reference_case_for_moc("MoC-003").selection == reference_case_for_moc("MoC-005").selection


def test_every_case_is_marked_as_a_reconstruction():
    assert {c.status for c in reference_cases()} == {"reconstructed-pending-confirmation"}


# ── Appendix G: the four practitioner characterisations of MoC-001 ───────────────────────────────
APPENDIX_G = {
    "Interviewee01": ({"A1": "operational", "A2": "unit", "A3": "permanent", "A4": "local", "A5": "individual",
                       "A6": "situational", "A7": "deterministic", "A8": "technical"}, Allocation.AI_SUPPORTED),
    "Interviewee02": ({"A1": "operational", "A2": "unit", "A3": "permanent", "A4": "local", "A5": "collective",
                       "A6": "situational", "A7": "partially_defined", "A8": "technical"}, Allocation.HUMAN_LED),
    "Interviewee03": ({"A1": "operational", "A2": "system", "A3": "temporary", "A4": "local", "A5": "collective",
                       "A6": "by_procedure", "A7": "partially_defined", "A8": "technical"}, Allocation.AI_SUPPORTED),
    "Interviewee04": ({"A1": "operational", "A2": "system", "A3": "undefined_duration", "A4": "general",
                       "A5": "collective", "A6": "situational", "A7": "partially_defined", "A8": "economic"},
                      Allocation.HUMAN_LED),
}


@pytest.mark.parametrize("who", ["Interviewee02", "Interviewee03", "Interviewee04"])
def test_engine_reproduces_appendix_g_framework_allocation(who):
    selection, published = APPENDIX_G[who]
    assert score(selection).allocation is published


def test_appendix_g_interviewee01_is_a_known_discrepancy_in_the_thesis():
    """The selection recorded for Interviewee01 has the same scores as MOC-F01 (Human-led in
    Table 2), yet Appendix G lists the framework allocation as AI-supported. The engine follows
    the published model, so it returns Human-led. Open question for the author."""
    selection, published = APPENDIX_G["Interviewee01"]
    r = score(selection)
    assert {d: r.dimensions[d].score for d in "RCUI"} == {"R": 1.5, "C": 1, "U": 1, "I": 1.5}
    assert r.allocation is Allocation.HUMAN_LED
    assert published is Allocation.AI_SUPPORTED
