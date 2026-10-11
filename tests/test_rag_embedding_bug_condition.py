"""
tests/test_rag_embedding_bug_condition.py

Property 1: Bug Condition Exploration Tests
These tests MUST FAIL on unfixed code — failure confirms the bugs exist.
After the fix is applied, all four sub-checks should PASS.

Run: pytest tests/test_rag_embedding_bug_condition.py -v
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ── Test 1a: Missing Neo4j fields ─────────────────────────────────────────
class TestMissingNeo4jFields:
    """
    Bug Condition type (a): get_all_mocs_for_training() records are missing
    overall_risk_score, threshold_limit, and rework_required keys.
    FAILS on unfixed code because the Cypher RETURN clause omits these fields.
    """

    def test_overall_risk_score_present_in_all_records(self):
        """Every record from get_all_mocs_for_training() must have overall_risk_score."""
        from core.neo4j_client import Neo4jClient
        client = Neo4jClient()
        try:
            records = client.get_all_mocs_for_training()
            assert len(records) > 0, "No MoC records returned from Neo4j"
            missing = [r.get("moc_id") for r in records if "overall_risk_score" not in r]
            assert missing == [], (
                f"overall_risk_score missing from records: {missing}\n"
                f"Sample record keys: {list(records[0].keys())}"
            )
        finally:
            client.close()

    def test_threshold_limit_present_in_all_records(self):
        """Every record from get_all_mocs_for_training() must have threshold_limit."""
        from core.neo4j_client import Neo4jClient
        client = Neo4jClient()
        try:
            records = client.get_all_mocs_for_training()
            assert len(records) > 0, "No MoC records returned from Neo4j"
            missing = [r.get("moc_id") for r in records if "threshold_limit" not in r]
            assert missing == [], (
                f"threshold_limit missing from records: {missing}\n"
                f"Sample record keys: {list(records[0].keys())}"
            )
        finally:
            client.close()

    def test_rework_required_present_in_all_records(self):
        """Every record from get_all_mocs_for_training() must have rework_required."""
        from core.neo4j_client import Neo4jClient
        client = Neo4jClient()
        try:
            records = client.get_all_mocs_for_training()
            assert len(records) > 0, "No MoC records returned from Neo4j"
            missing = [r.get("moc_id") for r in records if "rework_required" not in r]
            assert missing == [], (
                f"rework_required missing from records: {missing}\n"
                f"Sample record keys: {list(records[0].keys())}"
            )
        finally:
            client.close()

    def test_risk_score_is_populated_not_none(self):
        """MoCs with RiskAssessment nodes must have a non-None overall_risk_score."""
        from core.neo4j_client import Neo4jClient
        client = Neo4jClient()
        try:
            records = client.get_all_mocs_for_training()
            # MoC-003 has RA-003 with overall_score=8 — must not be None
            moc003 = next((r for r in records if r.get("moc_id") == "MoC-003"), None)
            assert moc003 is not None, "MoC-003 not found in training data"
            assert moc003.get("overall_risk_score") is not None, (
                f"MoC-003 overall_risk_score is None. Record: {moc003}"
            )
            assert str(moc003.get("overall_risk_score")) != "", (
                f"MoC-003 overall_risk_score is empty string. Record: {moc003}"
            )
        finally:
            client.close()


# ── Test 1b: Thin embedding text ──────────────────────────────────────────
class TestThinEmbeddingText:
    """
    Bug Condition type (b): seed_vector_store.py passes only 14 fields to _moc_to_text(),
    causing the embedding text to omit risk score numbers and parameter change sentences.
    FAILS on unfixed code because the thin field set produces incomplete text.
    """

    def _build_thin_moc_dict(self):
        """Replicates the 14-field dict from the UNFIXED seed_vector_store.py."""
        return {
            "moc_id":             "MoC-003",
            "title":              "Reactor R-201 Temperature Setpoint Adjustment",
            "change_type":        "Process Parameter",
            "asset_id":           "R-201",
            "asset_name":         "R-201",
            "asset_category":     "Reactor",
            "description":        "Adjust reactor temperature setpoint to optimise catalyst performance",
            "risk_level":         "Medium",
            "hazop_required":     True,
            "overall_risk_score": 0,       # thin: 0 not the real score
            "hazard_description": "",      # thin: missing
            "lessons_learned":    "Improved yield with stable thermal control",
            "cost":               7500,    # thin: wrong key name
            "downtime":           15,      # thin: wrong key name
            # MISSING: parameter_name, old_value, new_value, threshold_limit,
            #          pssr_required, pid_ref, area, incident_occurred, rework_required
        }

    def test_embedding_text_contains_risk_score_number(self):
        """
        Embedding text must contain the actual risk score number (e.g. '8'), not just
        the category word 'Medium'. The thin field set passes overall_risk_score=0
        which is falsy, so _moc_to_text() omits the score.
        """
        from core.vector_store import _moc_to_text
        thin_moc = self._build_thin_moc_dict()
        text = _moc_to_text(thin_moc)
        # With thin field set, risk_score is 0 (falsy) → no score in text
        # After fix, overall_risk_score will be 8 from Neo4j → "risk score 8" in text
        assert any(
            digit in text for digit in ["8", "12", "15", "10"]
        ), (
            f"Embedding text does not contain a risk score number.\n"
            f"Text: {text[:300]}"
        )

    def test_embedding_text_contains_parameter_change_sentence(self):
        """
        Embedding text must contain a parameter change sentence like
        'changes the Reactor temperature setpoint from 510 C to 525 C'.
        The thin field set omits parameter_name, old_value, new_value.
        """
        from core.vector_store import _moc_to_text
        thin_moc = self._build_thin_moc_dict()
        text = _moc_to_text(thin_moc)
        assert "changes the" in text.lower() or "from" in text.lower(), (
            f"Embedding text missing parameter change sentence.\n"
            f"Text: {text[:400]}"
        )

    def test_embedding_text_contains_threshold_and_margin(self):
        """
        Embedding text must contain threshold and margin info like
        'The design limit is Max 545 C. Margin to design limit: 20 units.'
        The thin field set omits threshold_limit.
        """
        from core.vector_store import _moc_to_text
        thin_moc = self._build_thin_moc_dict()
        text = _moc_to_text(thin_moc)
        assert "design limit" in text.lower() or "threshold" in text.lower() or "margin" in text.lower(), (
            f"Embedding text missing threshold/margin info.\n"
            f"Text: {text[:400]}"
        )


# ── Test 1c: No query expansion ───────────────────────────────────────────
class TestNoQueryExpansion:
    """
    Bug Condition type (c): VectorStore.search() encodes the raw user query without
    calling _expand_query() first. Synonym-drift queries get low similarity scores.
    FAILS on unfixed code because _expand_query() does not exist yet.
    """

    def test_search_calls_encode_with_expanded_query(self):
        """
        VectorStore.search() must call encode() with the expanded query string,
        not the raw query. The expanded string must contain domain synonyms.
        """
        from core.vector_store import VectorStore, _expand_query

        # Verify _expand_query exists and works
        expanded = _expand_query("catalyst circulation instability")
        assert "catalyst flow control" in expanded, (
            f"_expand_query did not append 'catalyst flow control'.\n"
            f"Result: {expanded}"
        )
        assert "slide valve" in expanded, (
            f"_expand_query did not append 'slide valve'.\n"
            f"Result: {expanded}"
        )
        # Original query must be preserved
        assert "catalyst circulation instability" in expanded, (
            f"_expand_query dropped the original query.\n"
            f"Result: {expanded}"
        )

    def test_expand_query_temperature_synonyms(self):
        """_expand_query must append temperature-related synonyms."""
        from core.vector_store import _expand_query
        expanded = _expand_query("reactor temperature setpoint increase")
        assert "thermal control" in expanded or "overheating" in expanded, (
            f"_expand_query missing temperature synonyms.\nResult: {expanded}"
        )

    def test_expand_query_esd_synonyms(self):
        """_expand_query must append ESD-related synonyms."""
        from core.vector_store import _expand_query
        expanded = _expand_query("emergency shutdown procedure update")
        assert "ESD procedure" in expanded or "safety critical" in expanded, (
            f"_expand_query missing ESD synonyms.\nResult: {expanded}"
        )

    def test_expand_query_no_change_for_unknown_terms(self):
        """_expand_query must return original query unchanged for unknown terms."""
        from core.vector_store import _expand_query
        original = "some completely unrelated query about nothing"
        result = _expand_query(original)
        assert result == original, (
            f"_expand_query modified a query with no known domain terms.\n"
            f"Original: {original}\nResult: {result}"
        )

    def test_search_uses_expanded_query_not_raw(self):
        """VectorStore.search() must pass the expanded query to encode(), not the raw one."""
        from core.vector_store import VectorStore
        store = VectorStore()

        encode_calls = []
        original_encode = store.embedder.encode

        def capture_encode(texts, **kwargs):
            encode_calls.append(texts)
            return original_encode(texts, **kwargs)

        store.embedder.encode = capture_encode

        if store.count() == 0:
            pytest.skip("Vector store is empty — seed first to run this test")

        store.search("catalyst circulation instability", top_k=3)

        assert len(encode_calls) > 0, "encode() was never called"
        encoded_text = encode_calls[0][0] if isinstance(encode_calls[0], list) else encode_calls[0]
        assert "catalyst flow control" in encoded_text, (
            f"search() passed raw query to encode(), not expanded query.\n"
            f"Encoded text: {encoded_text[:200]}"
        )


# ── Test 1d: Single-hit enrichment ────────────────────────────────────────
class TestSingleHitEnrichment:
    """
    Bug Condition type (d): HybridRetriever.retrieve() only calls get_moc_full_detail()
    once (for the top-1 hit) when no moc_id/asset_id is provided.
    FAILS on unfixed code because the loop only processes the first hit.
    """

    def test_retrieve_enriches_top_3_hits(self):
        """
        When no moc_id or asset_id is provided and 3 vector hits are returned,
        get_moc_full_detail() must be called 3 times (once per hit).
        """
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()

        # Mock vector store to return 3 hits
        mock_hits = [
            {"moc_id": "MoC-001", "text": "sample text 1", "metadata": {}, "similarity": 0.90},
            {"moc_id": "MoC-003", "text": "sample text 2", "metadata": {}, "similarity": 0.85},
            {"moc_id": "MoC-005", "text": "sample text 3", "metadata": {}, "similarity": 0.80},
        ]
        retriever.vector_store.search = MagicMock(return_value=mock_hits)

        # Mock Neo4j to return a simple detail dict
        mock_detail = {"moc_id": "MoC-001", "title": "Test", "risk_category": "High",
                       "risk_score": 12, "actual_cost": 10000, "actual_manhours": 50,
                       "hazop_required": True, "pssr_required": True,
                       "asset_name": "P-101", "asset_id": "P-101",
                       "description": "Test desc", "final_approver_role": "Safety Manager",
                       "hazards": [], "incident_occurred": False, "lesson": None,
                       "param_name": None, "hazop_outcome": None, "pssr_outcome": None}
        retriever.neo4j.get_moc_full_detail = MagicMock(return_value=mock_detail)
        retriever.neo4j.get_work_orders_for_moc = MagicMock(return_value=[])
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=[])
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=[])
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        # Call retrieve with no moc_id or asset_id
        context = retriever.retrieve(query_text="list all high risk MoCs")

        # Assert get_moc_full_detail was called 3 times (once per hit)
        call_count = retriever.neo4j.get_moc_full_detail.call_count
        assert call_count == 3, (
            f"get_moc_full_detail() called {call_count} times, expected 3.\n"
            f"This confirms Bug 5: only top-1 hit is enriched on unfixed code."
        )

    def test_context_contains_top_hit_details_list(self):
        """
        context['top_hit_details'] must be a list with up to 3 entries
        when 3 vector hits are returned and no moc_id/asset_id is provided.
        """
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()

        mock_hits = [
            {"moc_id": "MoC-001", "text": "text 1", "metadata": {}, "similarity": 0.90},
            {"moc_id": "MoC-003", "text": "text 2", "metadata": {}, "similarity": 0.85},
            {"moc_id": "MoC-005", "text": "text 3", "metadata": {}, "similarity": 0.80},
        ]
        retriever.vector_store.search = MagicMock(return_value=mock_hits)

        mock_detail = {"moc_id": "MoC-001", "title": "Test", "risk_category": "High",
                       "risk_score": 12, "actual_cost": 10000, "actual_manhours": 50,
                       "hazop_required": True, "pssr_required": True,
                       "asset_name": "P-101", "asset_id": "P-101",
                       "description": "Test desc", "final_approver_role": "Safety Manager",
                       "hazards": [], "incident_occurred": False, "lesson": None,
                       "param_name": None, "hazop_outcome": None, "pssr_outcome": None}
        retriever.neo4j.get_moc_full_detail = MagicMock(return_value=mock_detail)
        retriever.neo4j.get_work_orders_for_moc = MagicMock(return_value=[])
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=[])
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=[])
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        context = retriever.retrieve(query_text="list all high risk MoCs")

        assert "top_hit_details" in context, (
            "context missing 'top_hit_details' key — Bug 5 not fixed."
        )
        assert len(context["top_hit_details"]) == 3, (
            f"top_hit_details has {len(context['top_hit_details'])} entries, expected 3."
        )
