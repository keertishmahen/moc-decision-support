# MoC Decision Support — ontology-grounded LLM reasoning over industrial change records

A decision-support system for **Management of Change (MoC)** in process industries. Engineering changes to a
plant — swapping a pump, re-rating a vessel, altering an operating envelope — carry risk that is usually buried
in scattered historical records. This system puts that history into a knowledge graph and lets an engineer
interrogate it in natural language, with every answer traceable back to the records it came from.

Built as an MSc research project at Cranfield University.

> **All data in this repository is synthetic.** The demo graph describes a fictional refinery
> (`REFINERY-A`, `FCC-UNIT`, pump `P-101`, `MoC-001`…). No real plant, client or operational data is included.

---

## Why it is built this way

An LLM that answers plant-safety questions from parametric memory is the wrong tool: it will produce a fluent,
plausible answer with no way for the engineer to check it. The design constraint here was that **every assertion
the system makes has to be attributable**.

That shapes the architecture:

- The authoritative state lives in a **Neo4j knowledge graph** — assets, changes, work orders and the
  dependencies between them — not in the model's weights.
- Retrieval runs over that structured ontology plus a **ChromaDB** vector index of the supporting text, so
  answers are grounded in retrieved records rather than generated from scratch.
- Risk and impact suggestions come from **dependency-graph traversal** over the real asset relationships, so the
  reasoning can be inspected as a path through the graph.
- Cost and downtime estimates come from a **statistical model trained on historical change records**, kept
  separate from the language model, because a number that will inform a shutdown decision should not be a
  token prediction.

The LLM's job is to translate between the engineer's question and these systems, and to explain what came back.
It is deliberately not the place where facts are stored.

## Architecture

```
source systems ──dlt──▶ Snowflake BRONZE ──dbt──▶ SILVER / GOLD
                                                     │
                                       ┌─────────────┴──────────────┐
                                       ▼                            ▼
                             Neo4j knowledge graph         ChromaDB vector store
                                       │                            │
                                       └──────────┬─────────────────┘
                                                  ▼
                                      RAG + reasoning layer (core/)
                                                  │
                      ┌───────────────────────────┼───────────────────────┐
                      ▼                           ▼                       ▼
               smart guided forms          risk / impact engine    cost & downtime model
                                                  │
                                       Streamlit UI  ·  FastAPI  ·  React frontend
```

| Layer | Location |
|---|---|
| Ingestion (dlt → Snowflake) | `ingest/` |
| Transformation (dbt) | `dbt_moc/` |
| Graph content and loading | `data/graph/fcc_graph.json`, `loaders/` |
| Human–AI decision allocation | `core/allocation/` (model), `modules/decision_allocation/` (integration) |
| Model gateway | `core/llm/` |
| RAG pipeline & agent | `core/rag_pipeline.py`, `core/moc_agent.py` |
| Graph & vector clients | `core/neo4j_client.py`, `core/vector_store.py` |
| Risk, cost, forms, chat | `modules/` |
| Dependency propagation | `core/downtime_propagator.py` |
| API | `api/` (FastAPI) |
| UI | `frontend/` (Vite + React + TS); `app.py` is an earlier Streamlit interface |
| Tests | `tests/` (pytest) |

## Human–AI decision allocation

Beyond assessing a change, the platform recommends **who should decide it**: AI-led,
AI-supported or human-led. A change is characterised on eight axes, scored for risk,
complexity, uncertainty and impact, and mapped to an allocation by a fixed, inspectable
model. The knowledge graph suggests the characterisation with its evidence; an engineer
confirms it; no language model takes part in the scoring.

The model is the work of **Parth Pandit Atiwadkar** (*Human–AI Decision Allocation in
Knowledge-Driven Management of Change*, MSc thesis, Cranfield University, 2026; supervisor
Dr Jelena Milisavljevic Syed). This repository reimplements it from the thesis and
reproduces its published results as tests. See
[docs/references/decision-allocation-model.md](docs/references/decision-allocation-model.md)
and [docs/reports/reproduction-report.md](docs/reports/reproduction-report.md).

## Working in this repository

Start with [AGENTS.md](AGENTS.md), a short map of the code and documents.
[ARCHITECTURE.md](ARCHITECTURE.md) describes the layers and request flows; `docs/` holds
design decisions, product specs, reports and the backlog.

## Running it

Requires Python 3.11+, a Neo4j instance (Aura or local) and an OpenAI API key. Snowflake is only needed for the
full ingestion pipeline — the demo runs without it.

```bash
pip install -r requirements-docker.txt pytest ruff
cp .env.example .env                          # fill in your own credentials
python -m loaders.snapshot_loader --apply     # load the synthetic graph (additive, repeatable)
python -m loaders.allocation_loader --apply   # add the decision-allocation layer
python seed_vector_store.py                   # build the vector index
uvicorn api.main:app --reload --port 8000     # API on :8000
cd frontend && npm install && npm run dev     # UI on :5173
```

`make help` lists the everyday commands; `make check` runs what CI runs.

Full data pipeline (needs Snowflake):

```bash
make pipeline                 # dlt → Snowflake → dbt → Neo4j
```

Tests:

```bash
python -m pytest tests        # offline: no database or API key needed
```

Tests that need the live graph and an OpenAI key skip themselves when credentials are absent.

`tests/test_rag_embedding_bug_condition.py` and `tests/test_rag_preservation.py` are regression tests written
around real retrieval failures found during development — an embedding mismatch that silently returned
irrelevant context, and a case where re-seeding dropped documents from a collection. Both are the kind of bug
that produces a confident wrong answer rather than an error, which is why they have tests.

## Status

Research prototype. The ingestion, graph, RAG and risk layers work end to end on the synthetic dataset; the
cost model is trained on a small record set and should be read as a proof of concept rather than a calibrated
estimator.

## Licence

MIT — see [LICENSE](LICENSE).
