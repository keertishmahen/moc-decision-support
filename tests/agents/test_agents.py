"""
tests/agents/test_agents.py — the multi-agent assessment and its provenance, offline.

The language-model and ML components are replaced by fakes; graph reads use the file-backed
graph (tests/file_graph.py via the allocation_service fixture).
"""

from fakes import DESC, FakeCost, FakeForms, FakeRisk

from core.provenance import Basis, SourceKind
from modules.agents import ChangeRequest, registry


def run(sup, **kw):
    req = {"change_type": "Instrumentation", "asset_id": "FV-103", "description": DESC, **kw}
    return sup.assess(ChangeRequest(**req))


def contributions(case):
    return {c["agent"]: c for c in case["why_trust"]["contributions"]}


class TestPipeline:
    def test_every_agent_runs_and_contributes(self, make_supervisor):
        case = run(make_supervisor())
        c = contributions(case)
        assert set(c) == {"supervisor", "retrieval", "impact", "risk", "review", "cost", "allocation", "verifier"}
        assert all(x["status"] == "ok" for x in c.values()), {k: v["status"] for k, v in c.items()}
        assert [s["agents"] for s in case["trace"]["stages"]] == [["retrieval", "impact"], ["risk", "review"],
                                                                   ["cost", "allocation"], ["verifier"]]

    def test_the_case_answers_the_three_questions(self, make_supervisor):
        case = run(make_supervisor())
        assert case["what_happens"]["reach"]["direct"] == ["R-201"]
        assert case["what_happens"]["risk"]["overall_rating"] == "Medium"
        assert case["what_happens"]["cost"]["cost_estimate"] == 36000.0
        assert case["who_decides"]["result"]["allocation"] in {"AI_LED", "AI_SUPPORTED", "HUMAN_LED"}
        assert case["why_trust"]["counts"]["evidence"] > 10

    def test_reference_moc_uses_its_characterisation(self, make_supervisor):
        case = run(make_supervisor(), moc_id="MoC-002")
        r = case["who_decides"]["result"]
        assert (r["allocation"], r["signature"]) == ("AI_SUPPORTED", "II/II/II")

    def test_cost_agent_receives_category_and_rating_from_other_agents(self, make_supervisor):
        cost = FakeCost()
        run(make_supervisor(cost_predictor=cost))
        assert cost.args == ("Control Valve", "Medium")


class TestProvenance:
    def test_every_source_kind_in_the_brief_is_represented(self, make_supervisor):
        sources = set(run(make_supervisor())["why_trust"]["evidence_by_source"])
        for kind in ("ontology", "knowledge_graph", "engineering_record", "document", "computational_model",
                     "ml_model", "llm_interpretation", "user_input"):
            assert kind in sources, kind

    def test_language_model_findings_are_labelled_as_such(self, make_supervisor):
        case = run(make_supervisor())
        risk = [f for f in case["why_trust"]["findings"] if f["agent"] == "risk"]
        assert risk and all(f["basis"] == "llm" for f in risk)
        assert any(e.startswith("llm_interpretation:") for f in risk for e in f["evidence"])

    def test_the_allocation_is_deterministic_and_never_llm(self, make_supervisor):
        case = run(make_supervisor())
        alloc = [f for f in case["why_trust"]["findings"] if f["agent"] == "allocation"]
        assert alloc and all(f["basis"] != "llm" for f in alloc)
        rec = [f for f in alloc if f["statement"].startswith("Recommended allocation")]
        assert rec and any(e.startswith("computational_model:") for e in rec[0]["evidence"])

    def test_approval_checkpoint_states_allocation_is_not_authority(self, make_supervisor):
        cps = run(make_supervisor())["why_trust"]["checkpoints"]
        approve = [c for c in cps if c["what"] == "Approve or reject the change."]
        assert approve and approve[0]["kind"] == "approval" and "not decision authority" in approve[0]["why"]
        assert cps[-1]["kind"] == "approval"                      # verification comes before approval

    def test_assumptions_and_uncertainties_are_listed(self, make_supervisor):
        why = run(make_supervisor())["why_trust"]
        texts = " ".join(g["text"] for g in why["assumptions"] + why["uncertainties"])
        assert "24-hour outage" in texts and "illustrative" in texts and "not yet empirically calibrated" in texts


class TestVerification:
    def test_consistent_claims_are_verified(self, make_supervisor):
        why = run(make_supervisor())["why_trust"]
        assert why["counts"]["conflicts"] == 0
        risk_rating = next(f for f in why["findings"] if f["statement"].startswith("Overall risk rated"))
        assert risk_rating["verification"] == "verified"

    def test_a_fabricated_asset_is_flagged(self, make_supervisor):
        why = run(make_supervisor(risk_engine=FakeRisk(named=("R-201", "XV-999"))))["why_trust"]
        assert any("XV-999" in f["statement"] and f["verification"] == "conflict" for f in why["findings"])
        assert any("XV-999" in c["what"] for c in why["checkpoints"])

    def test_disagreement_on_hazop_becomes_a_conflict_for_a_person(self, make_supervisor):
        case = run(make_supervisor(risk_engine=FakeRisk(hazop="No"), smart_forms=FakeForms(hazop="Yes")))
        why = case["why_trust"]
        assert any(f["statement"] == "HAZOP: the Review and Risk agents disagree." for f in why["conflicts"])
        assert any(c["what"] == "Decide whether a HAZOP is required." and c["role"] == "Process Safety Manager"
                   for c in why["checkpoints"])
        assert any("did not agree on whether a HAZOP" in g["text"] for g in why["uncertainties"])

    def test_unknown_pid_tag_is_flagged(self, make_supervisor):
        why = run(make_supervisor(smart_forms=FakeForms(tags=("P&ID-103",))))["why_trust"]
        assert any("P&ID-103" in f["statement"] for f in why["conflicts"])


class TestDegradation:
    def test_one_failing_agent_does_not_sink_the_case(self, make_supervisor):
        case = run(make_supervisor(risk_engine=FakeRisk(fail=True)))
        c = contributions(case)
        assert c["risk"]["status"] == "failed" and c["risk"]["error"] == "RuntimeError"
        assert "exploded" not in str(case)                        # no internal error text leaks
        assert c["cost"]["status"] == "ok" and c["allocation"]["status"] == "ok"
        assert any("given 'Medium'" in g["text"] for g in case["why_trust"]["assumptions"])
        assert any("Risk Assessment Agent failed" in g["text"] for g in case["why_trust"]["missing"])

    def test_ai_service_down_marks_the_agent_degraded(self, make_supervisor):
        case = run(make_supervisor(risk_engine=FakeRisk(llm="unavailable")))
        assert contributions(case)["risk"]["status"] == "degraded"


class TestRegistry:
    def test_every_agent_declares_role_sources_and_components(self):
        reg = registry()
        assert len(reg["agents"]) == 7 and reg["supervisor"]["pattern"] == "supervisor"
        for a in reg["agents"]:
            assert a["role"] and a["sources"] and a["components"], a["id"]

    def test_basis_and_sources_are_consistent(self):
        for a in registry()["agents"]:
            if a["basis"] == Basis.LLM.value:
                assert SourceKind.LLM_INTERPRETATION.value in a["sources"], a["id"]
            if a["basis"] == Basis.DETERMINISTIC.value:
                assert SourceKind.LLM_INTERPRETATION.value not in a["sources"], a["id"]

    def test_exactly_one_verifier_runs_last(self):
        reg = registry()
        verifiers = [a for a in reg["agents"] if a["pattern"] == "verifier"]
        assert len(verifiers) == 1 and reg["stages"][-1] == [verifiers[0]["id"]]


class TestProgressEvents:
    def test_events_follow_the_run_order(self, make_supervisor):
        events = []
        case = make_supervisor().assess(
            ChangeRequest("Instrumentation", "FV-103", DESC), on_event=events.append)
        types = [e["type"] for e in events]
        assert types[0] == "run_started" and types[-1] == "run_finished"
        assert events[0]["run_id"] == case["run_id"]
        assert types.count("stage_started") == 4
        finished = {e["agent"]: e for e in events if e["type"] == "agent_finished"}
        assert set(finished) == {"retrieval", "impact", "risk", "review", "cost", "allocation", "verifier"}
        assert all(e["status"] == "ok" and e["duration_ms"] >= 0 for e in finished.values())
        # every agent starts before it finishes, and stage n finishes before stage n+1 starts
        pos = {(e["type"], e.get("agent")): i for i, e in enumerate(events)}
        for a in finished:
            assert pos[("agent_started", a)] < pos[("agent_finished", a)]
        assert pos[("agent_finished", "risk")] < pos[("agent_started", "cost")]
        assert pos[("agent_finished", "allocation")] < pos[("agent_started", "verifier")]
        assert events[-1]["counts"] == case["why_trust"]["counts"]

    def test_a_failing_listener_does_not_affect_the_case(self, make_supervisor):
        def broken(_event):
            raise RuntimeError("listener down")
        case = make_supervisor().assess(ChangeRequest("Instrumentation", "FV-103", DESC), on_event=broken)
        assert all(c["status"] == "ok" for c in case["why_trust"]["contributions"])

    def test_a_failed_agent_is_reported_without_its_error_text(self, make_supervisor):
        events = []
        make_supervisor(risk_engine=FakeRisk(fail=True)).assess(
            ChangeRequest("Instrumentation", "FV-103", DESC), on_event=events.append)
        risk = next(e for e in events if e["type"] == "agent_finished" and e["agent"] == "risk")
        assert risk["status"] == "failed" and "exploded" not in str(events)
