# Technical status report — MoC demonstrator baseline

**Date:** 12 November 2026 · **Scope:** the ontology-driven MoC demonstrator as deployed
(GitHub Pages + Render), before and after the decision-allocation work.

## Summary

The demonstrator ran end to end: all 18 API routes answered and every tab worked. The main
finding was in the data, not the code: **the live knowledge graph and the vector store held
5 of the 10 MoC records** (52 nodes, 66 relationships), although the application and its
prompts describe 10. Both have been restored to the full set (now 239 nodes and 503
relationships including the allocation layer). A second group of findings were defects in
queries and in how model replies were handled; the ones that were unambiguous are fixed and
covered by tests.

## What works (verified against the live deployment)

| Component | Status | Evidence |
|---|---|---|
| Neo4j knowledge graph | Working; now complete | 10 MoCs, 22 assets, 21 work orders; loader dry-run reports nothing left to add |
| Ontology / schema | Working as a property-graph schema | 28 node labels incl. allocation layer; see `docs/generated/graph-schema.md`. No OWL file exists in the repository |
| Change assessment: Smart Form | Working | Structured suggestions with graph approvers; live call returns risk level, HAZOP, PSSR, justification citing MoC ids |
| Change assessment: Risk & Impact | Working | Live call returns rated risks, affected assets, mitigations |
| Impact / dependency analysis | Working | Connectivity map, topology (46 edges), downtime propagation and matrix |
| MoCBot | Working | Grounded answers with per-session memory; reports decision allocation |
| Agent | Working | Tool-calling loop over 11 tools |
| Cost / downtime estimation | Working | KNN + calibrated heuristic; AI explanation now receives the numbers |
| Decision allocation (new) | Working | Thesis outputs reproduced; integrated with the graph, API and UI |
| Deployment | Working | Push to `main` deploys frontend and backend automatically |

## What needed attention

**Fixed in this work**

| Issue | Effect | Fix |
|---|---|---|
| Live graph and vector store held 5 of 10 MoCs | MoC-005, 007, 008, 009, 010 could not be retrieved; `/api/mocs` listed 5; MoCBot answered about missing MoCs from its prompt text | Canonical graph file + additive loader; vector store re-seeded |
| No reproducible source for the graph | The live graph could not be rebuilt from the repository | `data/graph/fcc_graph.json` + `loaders/snapshot_loader.py` |
| Model replies parsed by line prefix | A reply with different formatting silently became "Unknown" | Schema-validated structured output |
| No timeout or error policy on model calls | A slow call could hang a request; any failure was a raw 500 | Gateway with timeout, bounded retries, typed errors, graph-only fallback |
| Prompt templating re-read inserted text | A description containing `{context}` was substituted | One-pass templating, delimited user text |
| Cost explanation never received the estimate | The model was sent the literal placeholder | Format specs honoured |
| Chat memory shared by all users | Users saw each other's history; reset cleared everyone | Memory per browser session |
| Chat history rebuilt from text | Multi-line answers truncated; a user could forge an assistant turn | Structured turns |
| Hazard count in connectivity score always 0 | Wrong pattern in the query | Query corrected |
| Concept search returned every MoC | Filter attached to an optional match | Query corrected |
| `max_depth` ignored | Traversal depth was hardcoded | Bounded depth honoured |
| Propagation counted an asset once per path | Inflated totals and repeated rows | One row per asset, strongest route |
| "wo" matched inside words | "hello world" triggered work-order expansion | Word-boundary match |
| "Process and Instrumentation" encoded as Other | Cost model lost the change type for MoC-006-like changes | Both spellings mapped |
| Agent iterations unbounded | A caller could trigger many paid calls | Capped at 8 |
| Raw exception text sent to clients | Internal details exposed | Fixed messages with a reference id; 502/503 where appropriate |
| Tabs failed silently | A failed request showed nothing | Error boxes; degraded-answer notices |
| Agent quick prompts ran the previous query | Stale state | Query passed explicitly |
| Tooltip HTML not escaped | Database strings rendered as HTML | Escaped |

**Still open** (see `docs/exec-plans/tech-debt-tracker.md` and the backlog)

- No authentication or rate limiting on the API.
- MoCBot's system prompt hardcodes plant facts that can drift from the graph.
- Man-hours are used as downtime in several places; cost confidence intervals are fixed percentages.
- The Emergency Shutdown system's `SHUTS_DOWN` links are not part of downtime propagation.
- Two tests are recorded as expected failures (embedding text fixtures).
- No frontend test runner or linter.
- OpenAI key, Neo4j password and Render API key should be replaced (exposed during setup).

## What can be reused directly for the client-facing MVP

- The knowledge graph, its canonical file and loaders.
- The decision-allocation engine, service, API and tab.
- Graph access (`core/neo4j_client.py`), impact/dependency queries, downtime propagation.
- The model gateway and error handling.
- Smart Form, Risk & Impact, MoCBot; the deployment pipeline.

## What can be left out of the immediate MVP

- The Snowflake → dbt → Neo4j pipeline (`ingest/`, `dbt_moc/`, `snowflake/`): not needed to run the application.
- The Streamlit interface (`app.py`) and Azure deployment files: superseded.
- The agent tab, if a narrower demonstration is preferred: MoCBot covers the same questions.
- Cost prediction as a headline feature: it is trained on ten records and should be presented as indicative.
