"""
tests/test_rag_preservation.py

Property 2: Preservation Tests
These tests MUST PASS on BOTH unfixed and fixed code.
They confirm that the fix does not break existing retrieval paths.

Run: pytest tests/test_rag_preservation.py -v
"""
import pytest
from unittest.mock import MagicMock


# ── Preservation 1: Direct MoC lookup ─────────────────────────────────────
class TestDirectMocLookupPreservation:
    """
    When moc_id is provided, retrieve() must still call get_moc_full_detail()
    and get_work_orders_for_moc() exactly as before.
    """

    def test_retrieve_with_moc_id_populates_moc_detail(self):
        """retrieve(moc_id=...) must populate context['moc_detail']."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        retriever.vector_store.search = MagicMock(return_value=[])

        mock_detail = {
            "moc_id": "MoC-005", "title": "Catalyst Slide Valve Upgrade",
            "risk_category": "High", "risk_score": 12, "actual_cost": 67500,
            "actual_manhours": 52, "hazop_required": True, "pssr_required": True,
            "asset_name": "SV-204", "asset_id": "SV-204",
            "description": "Upgrade slide valve actuator",
            "final_approver_role": "Process Safety Manager",
            "hazards": [], "incident_occurred": False, "lesson": None,
            "param_name": None, "hazop_outcome": None, "pssr_outcome": None
        }
        retriever.neo4j.get_moc_full_detail = MagicMock(return_value=mock_detail)
        retriever.neo4j.get_work_orders_for_moc = MagicMock(return_value=[])
        retriever.neo4j.get_parameter_changes = MagicMock(return_value=[])
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=[])
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=[])
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        context = retriever.retrieve(query_text="tell me about MoC-005", moc_id="MoC-005")

        assert "moc_detail" in context, "context missing 'moc_detail' key"
        assert context["moc_detail"] is not None, "moc_detail is None"
        assert context["moc_detail"]["moc_id"] == "MoC-005"
        retriever.neo4j.get_moc_full_detail.assert_called_once_with("MoC-005")

    def test_retrieve_with_moc_id_populates_work_orders(self):
        """retrieve(moc_id=...) must populate context['work_orders']."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        retriever.vector_store.search = MagicMock(return_value=[])

        mock_detail = {
            "moc_id": "MoC-005", "title": "Test", "risk_category": "High",
            "risk_score": 12, "actual_cost": 0, "actual_manhours": 0,
            "hazop_required": False, "pssr_required": False,
            "asset_name": "SV-204", "asset_id": "SV-204", "description": "",
            "final_approver_role": "", "hazards": [], "incident_occurred": False,
            "lesson": None, "param_name": None, "hazop_outcome": None, "pssr_outcome": None
        }
        mock_wos = [{"wo_id": "WO-009", "title": "Remove actuator", "actual_hrs": 11}]
        retriever.neo4j.get_moc_full_detail = MagicMock(return_value=mock_detail)
        retriever.neo4j.get_work_orders_for_moc = MagicMock(return_value=mock_wos)
        retriever.neo4j.get_parameter_changes = MagicMock(return_value=[])
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=[])
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=[])
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        context = retriever.retrieve(query_text="work orders for MoC-005", moc_id="MoC-005")

        assert "work_orders" in context, "context missing 'work_orders' key"
        assert context["work_orders"] == mock_wos
        retriever.neo4j.get_work_orders_for_moc.assert_called_once_with("MoC-005")


# ── Preservation 2: Asset-based retrieval ─────────────────────────────────
class TestAssetRetrievalPreservation:
    """
    When asset_id is provided, retrieve() must still populate impact_chain,
    hazards, and incidents exactly as before.
    """

    def test_retrieve_with_asset_id_populates_impact_chain(self):
        """retrieve(asset_id=...) must populate context['impact_chain']."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        retriever.vector_store.search = MagicMock(return_value=[])

        mock_chain = [
            {"node_id": "C-203", "node_name": "C-203", "node_type": "Cyclone", "hop_distance": 1},
            {"node_id": "F-501", "node_name": "F-501", "node_type": "Fractionator", "hop_distance": 2},
        ]
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=mock_chain)
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=[])
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        context = retriever.retrieve(query_text="what does R-201 impact", asset_id="R-201")

        assert "impact_chain" in context, "context missing 'impact_chain' key"
        assert context["impact_chain"] == mock_chain
        retriever.neo4j.get_enriched_impact_chain.assert_called_once_with("R-201", depth=4)

    def test_retrieve_with_asset_id_populates_hazards(self):
        """retrieve(asset_id=...) must populate context['hazards']."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        retriever.vector_store.search = MagicMock(return_value=[])

        mock_hazards = [
            {"hazard_id": "HZ-003", "description": "Overtemperature risk",
             "severity": "Medium", "risk_score": 8, "failure_modes": []}
        ]
        retriever.neo4j.get_enriched_impact_chain = MagicMock(return_value=[])
        retriever.neo4j.get_hazards_for_asset = MagicMock(return_value=mock_hazards)
        retriever.neo4j.get_historical_incidents = MagicMock(return_value=[])
        retriever.neo4j.get_full_connectivity_map = MagicMock(return_value=None)
        retriever.neo4j.get_retrieved_subgraph = MagicMock(return_value={"nodes": [], "links": []})

        context = retriever.retrieve(query_text="hazards for R-201", asset_id="R-201")

        assert "hazards" in context, "context missing 'hazards' key"
        assert context["hazards"] == mock_hazards
        retriever.neo4j.get_hazards_for_asset.assert_called_once_with("R-201")


# ── Preservation 3: Deduplication ─────────────────────────────────────────
class TestDeduplicationPreservation:
    """
    VectorStore.add_mocs() must return 0 when all MoC IDs already exist.
    """

    def test_add_mocs_returns_zero_for_existing_ids(self):
        """add_mocs() must skip MoCs already in the collection."""
        from core.vector_store import VectorStore

        store = VectorStore()
        if store.count() == 0:
            pytest.skip("Vector store is empty — seed first to run deduplication test")

        # Get existing IDs
        existing = store.collection.get()["ids"]
        if not existing:
            pytest.skip("No existing IDs in collection")

        # Build a list of dicts with existing IDs
        existing_mocs = [{"moc_id": mid, "title": "Test", "change_type": "Mechanical",
                          "asset_id": "P-101", "description": "Test"} for mid in existing[:3]]

        result = store.add_mocs(existing_mocs)
        assert result == 0, (
            f"add_mocs() returned {result} instead of 0 for existing IDs. "
            f"Deduplication is broken."
        )


# ── Preservation 4: Context formatter section headers ─────────────────────
class TestContextFormatterPreservation:
    """
    format_context_for_prompt() must still produce all existing section headers
    after the fix is applied.
    """

    def test_format_context_renders_work_orders_section(self):
        """format_context_for_prompt() must render WORK ORDERS: section."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        context = {
            "vector_hits": [],
            "impact_chain": [],
            "hazards": [],
            "similar_mocs": [],
            "lessons": [],
            "incidents": [],
            "risk_assessment": [],
            "work_orders": [
                {"wo_id": "WO-001", "title": "Test WO", "actual_hrs": 10,
                 "actual_cost": 5000, "delay_reason": "none"}
            ],
            "parameters": [],
        }
        result = retriever.format_context_for_prompt(context)
        assert "WORK ORDERS:" in result, (
            f"format_context_for_prompt() missing 'WORK ORDERS:' section.\nOutput: {result[:500]}"
        )

    def test_format_context_renders_hazards_section(self):
        """format_context_for_prompt() must render HAZARDS: section."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        context = {
            "vector_hits": [],
            "impact_chain": [],
            "hazards": [
                {"severity": "High", "risk_score": 12,
                 "description": "Overtemperature risk", "failure_modes": []}
            ],
            "similar_mocs": [],
            "lessons": [],
            "incidents": [],
            "risk_assessment": [],
            "work_orders": [],
            "parameters": [],
        }
        result = retriever.format_context_for_prompt(context)
        assert "HAZARDS:" in result, (
            f"format_context_for_prompt() missing 'HAZARDS:' section.\nOutput: {result[:500]}"
        )

    def test_format_context_renders_similar_mocs_section(self):
        """format_context_for_prompt() must render SEMANTICALLY SIMILAR MoCs: section."""
        from core.rag_pipeline import HybridRetriever

        retriever = HybridRetriever()
        context = {
            "vector_hits": [
                {"moc_id": "MoC-003", "text": "Reactor temperature setpoint",
                 "metadata": {}, "similarity": 0.88}
            ],
            "impact_chain": [],
            "hazards": [],
            "similar_mocs": [],
            "lessons": [],
            "incidents": [],
            "risk_assessment": [],
            "work_orders": [],
            "parameters": [],
        }
        result = retriever.format_context_for_prompt(context)
        assert "SEMANTICALLY SIMILAR" in result, (
            f"format_context_for_prompt() missing 'SEMANTICALLY SIMILAR' section.\nOutput: {result[:500]}"
        )


# ── Preservation 5: _expand_query no-op for unknown terms ─────────────────
class TestExpandQueryNoOp:
    """
    _expand_query() must return the original query unchanged when no known
    domain terms are present. This prevents spurious expansion.
    """

    def test_expand_query_returns_original_for_unknown_terms(self):
        """_expand_query() must not modify queries with no known domain terms."""
        from core.vector_store import _expand_query

        test_cases = [
            "some completely unrelated query",
            "hello world",
            "what is the weather today",
            "random text with no domain keywords",
        ]
        for query in test_cases:
            result = _expand_query(query)
            assert result == query, (
                f"_expand_query() modified a query with no known terms.\n"
                f"Input: {query}\nOutput: {result}"
            )
