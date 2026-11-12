"""
tests/allocation/test_analysis.py — thesis chapter 7 figures, reproduced by enumeration.

Offline: no database, no network.
"""
import pytest

from core.allocation import analysis, default_model
from core.allocation.reference_cases import reference_case_for_moc


@pytest.fixture(scope="module")
def enumeration():
    return analysis.enumerate_space(default_model())


class TestEnumeration:                                   # thesis Section 7.1, Fig. 11
    def test_allocation_counts(self, enumeration):
        assert enumeration["total"] == 2592
        assert enumeration["allocations"] == {"AI_LED": 62, "AI_SUPPORTED": 406, "HUMAN_LED": 2124}

    def test_allocation_shares(self, enumeration):
        shares = {k: round(100 * v, 1) for k, v in enumeration["shares"].items()}
        assert shares == {"AI_LED": 2.4, "AI_SUPPORTED": 15.7, "HUMAN_LED": 81.9}

    def test_24_of_27_signatures_are_reached(self, enumeration):
        assert enumeration["signatures_reached"] == 24
        assert enumeration["signatures_possible"] == 27
        assert enumeration["signatures_unreached"] == ["II/III/I", "III/II/I", "III/III/I"]

    def test_high_uncertainty_low_risk_low_complexity_region(self, enumeration):
        assert enumeration["high_uncertainty_low_risk_low_complexity_points"] == 64

    def test_most_frequent_signatures(self, enumeration):
        counts = enumeration["signature_counts"]
        published = {"III/III/III": 918, "II/II/III": 220, "II/III/III": 180, "III/III/II": 156,
                     "II/I/III": 140, "I/III/III": 136, "III/II/III": 120, "I/II/III": 98}
        assert {k: counts[k] for k in published} == published


def test_single_axis_swing_matches_figure_11():
    swing = {s["axis_id"]: {d: v for d, v in s["span"].items() if v} for s in analysis.single_axis_swing()}
    assert swing == {
        "A1": {"R": 1.0, "I": 1.0}, "A2": {"C": 1.0, "I": 1.0}, "A3": {"R": 1.0, "I": 1.0},
        "A4": {"C": 1.0, "I": 1.0}, "A5": {"C": 1.0}, "A6": {"C": 1.0, "U": 1.0},
        "A7": {"U": 1.0}, "A8": {"R": 0.5, "I": 0.5},
    }


def test_weight_perturbation_matches_figure_12():
    """±20 %: share of the space whose allocation flips, per axis->dimension link (mean of -20 % and +20 %)."""
    rows = {(r["axis_id"], r["dimension"]): 100 * r["flip_share_mean"] for r in analysis.weight_perturbation(pct=0.20)}
    published = {("A8", "I"): 6.6, ("A7", "U"): 4.2, ("A1", "I"): 3.4, ("A3", "I"): 3.4, ("A2", "I"): 3.1,
                 ("A8", "R"): 2.5, ("A6", "U"): 2.3, ("A1", "R"): 1.8, ("A3", "R"): 1.8, ("A4", "I"): 1.8}
    for link, pct in published.items():
        assert rows[link] == pytest.approx(pct, abs=0.06), link
    assert max(rows, key=rows.get) == ("A8", "I")
    assert [link for link, pct in rows.items() if pct > 5] == [("A8", "I")]


class TestThresholdSweep:                                # thesis Fig. 13
    PUBLISHED = {0.15: [96, 78, 61, 42, 28], 0.25: [93, 77, 60, 42, 28], 0.33: [85, 74, 57, 40, 26],
                 0.45: [None, 64, 51, 38, 23], 0.55: [None, None, 40, 31, 19]}

    def test_all_columns_without_boundary_ties_match(self):
        sweep = analysis.threshold_sweep()
        assert sweep["highs"] == [0.45, 0.55, 0.67, 0.75, 0.85]
        for row in sweep["rows"]:
            for col in (0, 1, 2, 4):
                assert row["human_led_pct"][col] == self.PUBLISHED[row["low"]][col], (row["low"], col)

    def test_range_is_19_to_96_percent(self):
        values = [v for row in analysis.threshold_sweep()["rows"] for v in row["human_led_pct"] if v is not None]
        assert (min(values), max(values)) == (19, 96)

    def test_0_75_column_depends_on_how_a_boundary_tie_is_resolved(self):
        """Documented difference. With high = 0.75 exactly, scores on the boundary (Complexity 3.0,
        Uncertainty 1.5) are HIGH under the Section 6.1 rule and the column reads 58/56/53/47/37.
        The published column (42/42/40/38/31) appears when the boundary sits just above 0.75."""
        exact = [r["human_led_pct"][0] for r in analysis.threshold_sweep(highs=(0.75,))["rows"]]
        nudged = [r["human_led_pct"][0] for r in analysis.threshold_sweep(highs=(0.7500001,))["rows"]]
        assert exact == [58, 56, 53, 47, 37]
        assert nudged == [self.PUBLISHED[low][3] for low in (0.15, 0.25, 0.33, 0.45, 0.55)]


def test_monte_carlo_is_reproducible_and_stable_for_the_maximal_case():
    selection = reference_case_for_moc("MoC-009").selection
    a = analysis.monte_carlo_stability(selection, draws=300, seed=7)
    b = analysis.monte_carlo_stability(selection, draws=300, seed=7)
    assert a == b
    assert a["stability"] == 1.0 and a["baseline_allocation"] == "HUMAN_LED"


def test_published_scores_do_not_determine_a_unique_characterisation():
    """Why the reference selections are marked as reconstructions."""
    counts = {moc: sum(1 for _ in analysis.matching_selections(reference_case_for_moc(moc).expected["scores"]))
              for moc in ("MoC-001", "MoC-002", "MoC-009")}
    assert counts == {"MoC-001": 20, "MoC-002": 10, "MoC-009": 2}
