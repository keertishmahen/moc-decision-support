"""
tests/allocation/test_engine.py — the engine reproduces the thesis instrument.

Offline: no database, no network.
"""
import copy
import json

import pytest

from core.allocation import SelectionError, default_model, score
from core.allocation.engine import level_for, validate_selection
from core.allocation.model import DEFAULT_MODEL_FILE, ModelConfigError, parse_model
from core.allocation.types import Allocation, Level

BASE = {"A1": "operational", "A2": "unit", "A3": "temporary", "A4": "local",
        "A5": "individual", "A6": "by_procedure", "A7": "deterministic", "A8": "technical"}


def sel(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class TestModelStructure:
    def test_space_has_2592_points(self):
        assert default_model().space_size == 2592

    def test_column_maxima_follow_from_the_zero_structure(self):
        m = default_model()
        assert {d.id: m.column_max(d.id) for d in m.dimensions} == {"R": 3, "C": 4, "U": 2, "I": 5}

    def test_boundaries_match_thesis_figure_7(self):
        m = default_model()
        expected = {"R": (1.49, 2.00), "C": (1.48, 2.48), "U": (0.48, 0.99), "I": (1.48, 2.97)}
        for dim, (lo, hi) in expected.items():
            got_lo, got_hi = m.boundaries(dim)
            assert got_lo == pytest.approx(lo, abs=0.006)
            assert got_hi == pytest.approx(hi, abs=0.006)

    def test_uncertainty_shares_no_axis_with_risk(self):
        m = default_model()
        risk_axes = {a.id for a in m.axes if a.max_weight("R") > 0}
        uncertainty_axes = {a.id for a in m.axes if a.max_weight("U") > 0}
        assert risk_axes == {"A1", "A3", "A8"}
        assert uncertainty_axes == {"A6", "A7"}
        assert not (risk_axes & uncertainty_axes)

    def test_complexity_and_uncertainty_share_only_change_occurrence(self):
        m = default_model()
        complexity_axes = {a.id for a in m.axes if a.max_weight("C") > 0}
        uncertainty_axes = {a.id for a in m.axes if a.max_weight("U") > 0}
        assert complexity_axes & uncertainty_axes == {"A6"}


class TestLevels:
    def test_below_lower_boundary_is_low(self):
        assert level_for(1.0, 1.485, 2.001) is Level.LOW

    def test_at_lower_boundary_is_med(self):
        assert level_for(1.485, 1.485, 2.001) is Level.MED

    def test_at_upper_boundary_is_high(self):
        assert level_for(2.001, 1.485, 2.001) is Level.HIGH

    def test_risk_score_of_exactly_2_is_med_not_high(self):
        # 0.667 x 3 = 2.001, so a raw Risk of 2.0 stays MED (thesis Table 2, MOC-F02).
        r = score(sel(A1="tactical", A3="permanent"))            # R = 0.5 + 1 + 0.5
        assert r.dimensions["R"].score == 2.0
        assert r.dimensions["R"].level is Level.MED


class TestScoring:
    def test_lowest_point_is_ai_led(self):
        r = score(BASE)
        assert r.allocation is Allocation.AI_LED
        assert r.signature == "I/I/I"

    def test_every_axis_at_maximum_is_human_led(self):
        r = score({"A1": "strategic", "A2": "system", "A3": "permanent", "A4": "general",
                   "A5": "collective", "A6": "situational", "A7": "undefined", "A8": "economic"})
        assert {d: r.dimensions[d].score for d in "RCUI"} == {"R": 3, "C": 4, "U": 2, "I": 5}
        assert r.signature == "III/III/III"
        assert r.allocation is Allocation.HUMAN_LED

    def test_thesis_figure_10_example(self):
        # Dashboard screenshot: scores 2.50 / 0.00 / 0.50 / 2.50, signature III/I/II, HUMAN-LED,
        # margins 0.50 / 1.48 / 0.02 / 0.47.
        r = score({"A1": "strategic", "A2": "unit", "A3": "permanent", "A4": "local",
                   "A5": "individual", "A6": "by_procedure", "A7": "partially_defined", "A8": "technical"})
        assert {d: r.dimensions[d].score for d in "RCUI"} == {"R": 2.5, "C": 0, "U": 0.5, "I": 2.5}
        assert r.signature == "III/I/II"
        assert r.allocation is Allocation.HUMAN_LED
        margins = {d: round(r.dimensions[d].margin, 2) for d in "RCUI"}
        assert margins == {"R": 0.5, "C": 1.48, "U": 0.02, "I": 0.47} or margins == {"R": 0.5, "C": 1.48, "U": 0.02, "I": 0.48}

    def test_uncertainty_alone_can_force_human_led(self):
        r = score({"A1": "operational", "A2": "unit", "A3": "permanent", "A4": "local",
                   "A5": "individual", "A6": "situational", "A7": "deterministic", "A8": "technical"})
        assert r.escalated_by == ("U",)
        assert r.allocation is Allocation.HUMAN_LED
        assert any("Uncertainty alone" in reason for reason in r.reasons)

    def test_result_is_deterministic(self):
        s = sel(A1="tactical", A6="situational")
        assert score(s).to_dict() == score(s).to_dict()

    def test_contributions_sum_to_the_score(self):
        r = score(sel(A1="strategic", A2="system", A4="general", A7="undefined"))
        for d in r.dimensions.values():
            assert sum(c.weight for c in d.contributions) == pytest.approx(d.score)

    def test_flips_report_single_axis_changes_that_move_the_allocation(self):
        r = score(BASE)
        assert r.allocation is Allocation.AI_LED
        assert r.flips, "the lowest point must be sensitive to at least one axis"
        for f in r.flips:
            changed = dict(BASE)
            changed[f.axis_id] = f.to_category
            assert score(changed).allocation is f.allocation
            assert f.allocation is not r.allocation

    def test_to_dict_is_json_serialisable(self):
        json.dumps(score(BASE).to_dict())


class TestValidation:
    def test_missing_axis_is_rejected_with_the_valid_choices(self):
        incomplete = dict(BASE)
        del incomplete["A3"]
        with pytest.raises(SelectionError) as e:
            score(incomplete)
        assert "A3" in str(e.value) and "permanent" in str(e.value)

    def test_unknown_category_is_rejected(self):
        with pytest.raises(SelectionError):
            score(sel(A1="existential"))

    def test_unknown_axis_is_rejected(self):
        with pytest.raises(SelectionError):
            validate_selection(default_model(), {**BASE, "A9": "x"})


class TestConfigValidation:
    def _raw(self):
        return json.loads(DEFAULT_MODEL_FILE.read_text(encoding="utf-8"))

    def test_shipped_config_parses(self):
        assert parse_model(self._raw()).version == "1.14"

    def test_inverted_thresholds_are_rejected(self):
        raw = copy.deepcopy(self._raw())
        raw["dimensions"][0]["low"], raw["dimensions"][0]["high"] = 0.8, 0.4
        with pytest.raises(ModelConfigError):
            parse_model(raw)

    def test_unknown_rule_is_rejected(self):
        raw = copy.deepcopy(self._raw())
        raw["allocation_rule"]["id"] = "weighted-sum"
        with pytest.raises(ModelConfigError) as e:
            parse_model(raw)
        assert "engine.py" in str(e.value)

    def test_weight_on_unknown_dimension_is_rejected(self):
        raw = copy.deepcopy(self._raw())
        raw["axes"][0]["categories"][0]["weights"] = {"X": 1}
        with pytest.raises(ModelConfigError):
            parse_model(raw)
