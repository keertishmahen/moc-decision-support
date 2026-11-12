# AGENTS.md — map of this repository

This file is a table of contents, not a manual. Read the linked document for the area you
are working in; do not rely on this page for detail. Anything not written in this
repository does not exist for the next person or agent — record decisions in `docs/`.

## What this is

MoC Intelligence Platform: decision support for Management of Change (MoC) on one Fluid
Catalytic Cracking unit. A Neo4j knowledge graph + vector search + OpenAI models assess a
proposed change (form prefill, risk, cost, downtime), and a deterministic model recommends
who should decide it: AI-led, AI-supported or human-led. Research prototype on synthetic data.

## Where things are

| Area | Path | Read first |
|---|---|---|
| Architecture, layers, request flow | — | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Decision-allocation model (pure) | `core/allocation/` | [docs/design-docs/decision-allocation.md](docs/design-docs/decision-allocation.md) |
| Model numbers (single source) | `core/allocation/config/*.json` | [docs/references/decision-allocation-model.md](docs/references/decision-allocation-model.md) |
| Graph evidence → axis suggestions → service | `modules/decision_allocation/` | [docs/reports/input-mapping.md](docs/reports/input-mapping.md) |
| OpenAI gateway, prompt templating | `core/llm/` | [docs/design-docs/llm-reliability.md](docs/design-docs/llm-reliability.md) |
| Graph access, RAG, agent, propagation | `core/` | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Form prefill, risk, cost, chatbot | `modules/` | [ARCHITECTURE.md](ARCHITECTURE.md) |
| HTTP routes and error mapping | `api/` | [docs/generated/api-routes.md](docs/generated/api-routes.md) |
| Knowledge graph content and loaders | `data/graph/`, `loaders/` | [docs/generated/graph-schema.md](docs/generated/graph-schema.md) |
| Frontend (React + Vite) | `frontend/src/` | [docs/design-docs/frontend.md](docs/design-docs/frontend.md) |
| Deployment (GitHub Pages + Render) | `.github/workflows/`, `render.yaml` | [docs/DEPLOYMENT_CHANGES.md](docs/DEPLOYMENT_CHANGES.md) |
| What the product must do | — | [docs/product-specs/index.md](docs/product-specs/index.md) |
| Known debt and open questions | — | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |
| Quality grade per area | — | [docs/QUALITY.md](docs/QUALITY.md) |
| Plans, past and current | `docs/exec-plans/` | [docs/exec-plans/README.md](docs/exec-plans/README.md) |

## Commands

```
make check     # lint + offline tests + docs check + frontend type-check (same as CI)
make test      # 130+ offline tests: no database, no OpenAI key needed
make lint      # ruff, two levels (see pyproject.toml)
make docs      # regenerate docs/generated/
make api       # backend on :8000        make web   # frontend on :5173
```

Tests that need the live graph and an OpenAI key are marked `live` and skip themselves
without credentials. Run them locally with a populated `.env`.

## Rules that are enforced by tests

These fail the build; the failure message says how to fix it.

1. **Layers point one way**: `core.allocation` → `core` → `modules` → `api`. A layer never
   imports from one to its right. (`tests/structure/test_architecture.py`)
2. **`core/allocation` is pure**: standard library only. No database, network or LLM.
3. **Model numbers live once**, in `core/allocation/config/`. Not in code, not in the frontend.
4. **Published results stay reproduced**: thesis Table 2 and the 2,592-point enumeration.
   (`tests/allocation/`)
5. **Docs stay true**: this file stays short, its links resolve, and
   `docs/generated/api-routes.md` matches the app. (`tests/structure/test_docs.py`)

## Working principles

Short form; the reasons are in [docs/design-docs/core-beliefs.md](docs/design-docs/core-beliefs.md).

- AI suggests, a person confirms, a deterministic engine allocates. No model output decides an allocation.
- Every model call goes through `core.llm.get_gateway()`. Structured replies are schema-validated.
- When the AI service or the graph fails, degrade and say so (`llm_status`, `graph_status`); do not return a 500.
- Validate at boundaries; never send raw exception text to a client (`api/errors.py`).
- Prefer an existing helper over a new one. Search `core/neo4j_client.py` before writing Cypher.
- When you fix a class of mistake twice, encode it as a test or lint rule, then note it here.

## Before you finish

- `make check` passes.
- Behaviour changes are reflected in `docs/` (design doc, product spec, or tech-debt tracker).
- No secrets, account identifiers or private documents in the diff. Eight local files carry real
  identifiers and are marked skip-worktree; see [docs/DEPLOYMENT_CHANGES.md](docs/DEPLOYMENT_CHANGES.md).
