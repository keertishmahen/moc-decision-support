# Architecture

MoC Intelligence Platform, version 3.0. One FastAPI backend, one React frontend, one Neo4j
knowledge graph, one vector store, and the OpenAI API.

## System

```
Browser (GitHub Pages)                    Render (Docker)
┌──────────────────────┐   HTTPS/JSON   ┌────────────────────────────────────────────┐
│ React + Vite         │ ─────────────► │ FastAPI  api/                              │
│ six tabs             │                │   ├─ modules/   form, risk, cost, chatbot, │
└──────────────────────┘                │   │             decision_allocation        │
                                        │   └─ core/      graph, RAG, agent, llm,    │
                                        │                 allocation (pure model)    │
                                        └───────┬───────────────┬──────────────┬─────┘
                                                │               │              │
                                        Neo4j Aura        ChromaDB        OpenAI API
                                        knowledge graph   (in image)      (via core/llm)
```

## Layers

Imports point in one direction only. `tests/structure/test_architecture.py` enforces it.

```
core.allocation  ──►  core  ──►  modules  ──►  api  ──►  (frontend, over HTTP)
pure model            infra      services      HTTP
```

| Layer | Path | May import | Holds |
|---|---|---|---|
| Domain | `core/allocation/` | standard library only | Decision-allocation model: types, config loader, engine, analysis, reference cases |
| Infrastructure | `core/` | domain, third-party | `neo4j_client`, `vector_store`, `rag_pipeline`, `moc_agent`, `downtime_propagator`, `llm/` gateway, `allocation_lookup` |
| Services | `modules/` | core | `smart_forms`, `risk_engine`, `cost_predictor`, `nlp_chatbot`, `decision_allocation/` |
| HTTP | `api/` | modules, core | `main.py` (routes), `routes/allocation.py`, `errors.py` |
| Loaders | `loaders/` | core | `snapshot_loader`, `allocation_loader`, legacy `graph_loader` |

Cross-cutting concerns enter through one interface each: model calls through
`core.llm.get_gateway()`, graph access through `core.neo4j_client.Neo4jClient`, error
mapping through `api.errors.to_http_error`.

## Request flows

**Assessment (Smart Form, Risk, Cost).** Route → module → graph queries for evidence +
`RAGPipeline` (vector search and graph context) → one model call through the gateway.
Form prefill and risk analysis use schema-validated structured output. If the model call
fails the module answers from graph evidence and sets `llm_status: "unavailable"`.

**Decision allocation.** `GET /api/allocation/moc/{id}` or `POST /api/allocation/assess`:

```
change ─► graph_store (facts, reach) ─► characteriser (8 axis suggestions + evidence)
       ─► person confirms / overrides in the UI ─► POST /api/allocation/score
       ─► core.allocation.engine (deterministic) ─► scores, levels, factors, signature, allocation, reasons
```

No model call is involved in scoring. If the graph is down, scoring and the ten reference
cases still work (`graph_status: "unavailable"`).

**MoCBot and the agent.** Keyword intent routing → graph and vector retrieval → model call.
Chat memory is per browser session. The agent is an OpenAI tool-calling loop (11 tools,
at most 8 iterations). Both report an MoC's allocation from `core.allocation_lookup`; they
do not derive it.

## Data

- **Knowledge graph.** Canonical content is `data/graph/fcc_graph.json` (190 nodes, 311
  relationships, 10 MoCs), loaded additively by `loaders/snapshot_loader.py`. The
  allocation layer (model, axes, categories, dimensions, one characterisation per MoC) is a
  projection of `core/allocation/config/` written by `loaders/allocation_loader.py`.
  Live schema: [docs/generated/graph-schema.md](docs/generated/graph-schema.md).
- **Vector store.** `chroma_db/`, one embedded document per MoC, built from the graph and
  shipped inside the Docker image. Read-only at run time.
- **Cost models.** `saved_models/*.pkl` (KNN blended with a calibrated heuristic).
- **Model configuration.** `core/allocation/config/parth_v1_14.json` and
  `reference_cases.json`. The only place weights and thresholds are written.

## Failure behaviour

| Failure | Response |
|---|---|
| Knowledge graph unreachable | 503 with a plain message; allocation scoring still works |
| OpenAI call fails or times out | form/risk/cost degrade to graph evidence; chat and agent return 502 |
| Model reply does not match the schema | one repair attempt, then treated as above |
| Invalid characterisation | 422 naming the axis and the valid choices |
| Anything else | 500 with a reference id; details go to the server log only |

## Deployment

Push to `main`. GitHub Actions builds and publishes the frontend to GitHub Pages and runs
the backend checks; Render builds the Docker image and deploys once the checks pass.
Details: [docs/DEPLOYMENT_CHANGES.md](docs/DEPLOYMENT_CHANGES.md).

## Further reading

- API: [docs/generated/api-routes.md](docs/generated/api-routes.md)
- Decisions and their reasons: [docs/design-docs/index.md](docs/design-docs/index.md)
- What is weak or unfinished: [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md)
