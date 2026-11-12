# Quality grades

A grade per area, so effort goes where the product is weakest. Update the row when you
change the area. Last reviewed: 12 November 2026.

**A** tested, documented, no known defects · **B** works and is tested where it matters,
known limits recorded · **C** works, thinly tested or carrying recorded debt ·
**D** works on the happy path only.

| Area | Path | Grade | Why |
|---|---|---|---|
| Allocation model | `core/allocation/` | A | Pure; reproduces published results; exhaustively enumerated in tests |
| Allocation integration | `modules/decision_allocation/`, `api/routes/` | B | Tested offline on a file-backed graph; rules fitted to ten cases |
| Model gateway and templating | `core/llm/` | A | Typed errors, schema validation, injection-safe templating, all tested |
| Error handling | `api/errors.py` | B | Mapped and tested; no request tracing beyond a reference id |
| Graph access | `core/neo4j_client.py` | C | Large; four defects fixed this cycle; most queries untested offline |
| Retrieval | `core/rag_pipeline.py`, `core/vector_store.py` | C | Works; hardcoded expansions; tests need live services |
| Form prefill, risk | `modules/smart_forms.py`, `modules/risk_engine.py` | B | Structured output and graph-only fallback, tested |
| Cost prediction | `modules/cost_predictor.py` | C | Ten training records; fixed intervals |
| MoCBot | `modules/nlp_chatbot.py` | C | Works; hardcoded prompt facts; keyword routing; answers unverified |
| Agent | `core/moc_agent.py` | C | Bounded and JSON-safe; no offline tests of the loop |
| Downtime propagation | `core/downtime_propagator.py` | C | De-duplicated and tested; man-hours as downtime |
| Graph content and loaders | `data/graph/`, `loaders/` | B | Canonical file, additive loader with dry-run, verification step |
| Frontend: allocation tab | `frontend/src/allocation/`, `tabs/DecisionAllocation.tsx` | B | Typed; not browser-tested automatically |
| Frontend: other tabs | `frontend/src/tabs/` | C | Untyped responses; no tests |
| Deployment | `.github/workflows/`, `render.yaml` | B | Automatic with a test gate; free-tier cold starts |
| Documentation | `AGENTS.md`, `docs/` | B | Structured and link-checked; generated API doc verified in CI |
