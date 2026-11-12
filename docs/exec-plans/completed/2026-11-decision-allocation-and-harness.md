# Human–AI Decision Allocation in the MoC platform + harness engineering

## Context

The MoC Intelligence Platform (FastAPI + Neo4j + ChromaDB + OpenAI, React frontend; live on GitHub Pages + Render) assesses engineering changes but says nothing about **who should decide**. Parth Atiwadkar's MSc thesis defines a computable framework for that: eight characterisation axes → Risk / Complexity / Uncertainty / Impact scores → levels → three factors read against Impact → AI-led / AI-supported / human-led. This work integrates his model into the platform as one application, extends the knowledge graph to hold it, and makes the repo and the OpenAI usage robust ("harness engineering").

Decisions already made by you: reconstruct the ten case characterisations now and confirm with Parth later; restore the full 10-MoC graph to live Neo4j and add the allocation layer; publish the model in the public repo with attribution; harness = repository harness (per the OpenAI article) **and** an OpenAI reliability layer.

### What I established while planning
- **The model reproduces.** From the thesis weights (Fig. 5), thresholds (Fig. 7), factor matrix (Fig. 8) and rule, an independent run gives exactly his published results: 2,592 points → 62 AI-led / 406 AI-supported / 2,124 human-led, 24 of 27 signatures, 64 points in the high-U/low-R/low-C region, and all ten Table 2 rows (MOC-F02 = AI-supported, R 2 / C 1.5 / U 0.5 / I 2.5).
- **The ten thesis cases are the platform's MoC-001…010**, but the live graph holds only 5 MoCs (001–004, 006). The local snapshot `neo4j_query_table_data_2026-5-8.json` has all 10 (188 nodes, 316 relationships). No code can rebuild the live graph today.
- **Five axes are pinned by the thesis scores** for every case (system level, scope, acceptance, occurrence, information); nature and impact type have 2–3 valid combinations per case; duration has no data anywhere (all ten read as permanent).
- **Two inconsistencies inside the thesis** to raise with Parth: (1) Appendix G, Interviewee01 — the recorded selection scores Human-led (same scores as MOC-F01), the table says AI-supported; (2) §5.3 / Appendix E give undefined-duration the same weight as permanent (1) and temporary 0.5, while the instrument (Fig. 5) uses 0.5 and 0. I use the instrument values because only they reproduce his totals.
- **Existing defects** found in the baseline code (listed in Phase 5) — several affect the data the allocation would consume.

## Design principles
1. **AI suggests, a person confirms, a deterministic engine allocates.** No LLM output ever decides the allocation.
2. **One engine, one source of truth.** Model config is a versioned JSON file; the graph holds a projection of it; the frontend never recomputes.
3. **Every recommendation is explainable**: which categories fed each score, the margin to each threshold, which dimension forced escalation.
4. **Nothing existing breaks**: response shapes of current endpoints are unchanged; each phase leaves the app working.

## Target structure (new code only; existing files stay where they are)

```
core/allocation/              pure domain — standard library only, no I/O
  types.py  model.py  engine.py  analysis.py  reference_cases.py
  config/parth_v1_14.json     axes, weights, thresholds, factor matrix, rule, attribution
  config/reference_cases.json ten cases: selection, thesis-expected output, confirmation status
core/llm/                     single OpenAI gateway: timeouts, retries, structured output, typed errors
modules/decision_allocation/  service layer
  evidence.py  characteriser.py  graph_store.py  service.py
api/routes/allocation.py      APIRouter;  api/errors.py  exception → HTTP mapping
loaders/snapshot_loader.py    canonical graph loader;  loaders/allocation_loader.py
data/graph/fcc_graph.json     canonical graph (cleaned from the snapshot)
frontend/src/tabs/DecisionAllocation.tsx  + components/allocation/*
tests/allocation/  tests/api/  tests/structure/  tests/live/
AGENTS.md  ARCHITECTURE.md  docs/{design-docs,exec-plans,product-specs,references,generated,reports}/
```
Layer rule (enforced by a test): `core.allocation` → `core` → `modules` → `api`; imports only point left.

## Phases

### Phase 0 — Baseline and status report
- Run backend and frontend locally; exercise all 18 routes locally and live; back up the current live graph to a local, git-ignored JSON.
- Check the ChromaDB collection (how many MoCs embedded).
- Write `docs/reports/technical-status-report.md`: works / needs attention / reusable for MVP / excluded.

### Phase 1 — Parth's instrument, reproduced (`core/allocation/`)
- `engine.py`: `score(selection)` → raw scores, column maxima, normalised, level + margin per dimension, factors, signature, allocation, explanation (contributing categories, escalating dimensions).
- `analysis.py`: full enumeration, single-axis swing, one-at-a-time weight perturbation, threshold sweep.
- `reference_cases.json`: reconstructed selections for MoC-001…010 (duration = permanent throughout), each marked `reconstructed — pending confirmation`, with the alternatives recorded where the scores allow more than one.
- Tests (offline): thesis totals (62 / 406 / 2,124; 24/27; 64), all ten Table 2 rows, Appendix G rows (Interviewee01 recorded as a known thesis discrepancy), threshold edge cases (R = 2.0 is MED), config validation. Sensitivity figures (Fig. 12/13) are attempted; any that do not reproduce are reported as differences, not forced.
- `tests/structure/test_architecture.py`: layer rule with fix-it error messages.

### Phase 2 — Knowledge graph
- `data/graph/fcc_graph.json` + `loaders/snapshot_loader.py`: idempotent `MERGE` on each label's domain key (`moc_id`, `asset_id`, `wo_id`, …), `SET +=` properties, relationships merged by (start, type, end). **Additive only — nothing deleted.** Dry-run report first, then apply to live Aura, then verify counts (10 MoCs, 22 assets).
- Allocation layer (`loaders/allocation_loader.py`, projected from the JSON config):

| New node | Relationships |
|---|---|
| `AllocationModel` | `-[:DEFINES_AXIS]->CharacterisationAxis`, `-[:SCORES]->Dimension` |
| `CharacterisationAxis` (8) | `-[:HAS_CATEGORY]->AxisCategory` |
| `AxisCategory` (21) | `-[:CONTRIBUTES_TO {weight}]->Dimension` (non-zero weights only) |
| `Dimension` (4), `AllocationMode` (3) | — |
| `DecisionCharacterisation` (one per MoC; scores, levels, signature, status, model version) | `MoC-[:HAS_CHARACTERISATION]->`, `-[:SELECTS]->AxisCategory` ×8, `-[:RECOMMENDS]->AllocationMode`, `-[:ESCALATED_BY]->Dimension`, `-[:EVALUATED_WITH]->AllocationModel` |

- Re-seed the vector store if it lacks any of the ten MoCs.
- `docs/generated/graph-schema.md` generated from the live graph.

### Phase 3 — Integration service and API
- `evidence.py` reuses `Neo4jClient` (`get_moc_full_detail`, `get_risk_assessment`, `get_hazop_pssr`, `get_full_connectivity_map`, `get_asset_connectivity_score`) and `DowntimePropagator.propagate` to assemble the impact assessment for an existing MoC or a proposed change.
- `characteriser.py`: per-axis suggestion with source, evidence and confidence.

| Axis | Source in the platform | Status |
|---|---|---|
| A1 Nature of change | HAZOP flag, action type, criticality, change type | Rule suggestion → confirm |
| A2 System level | MoC criticality, plant-wide area, HAZOP flag; reach from connectivity | Rule suggestion → confirm |
| A3 Duration | **No data in the graph** | User input (default permanent) |
| A4 Scope | Areas located/reached, parameter change | Rule suggestion → confirm |
| A5 Acceptance | HAZOP required (team review) | Rule suggestion → confirm |
| A6 Occurrence | Action type (replace/repair vs planned), procedural change | Rule suggestion → confirm |
| A7 Information | P&ID reference, numeric parameter + threshold, similar-MoC similarity | Rule suggestion → confirm |
| A8 Impact type | Change type, risk-assessment dimensions | Rule suggestion → confirm |

  The rules are heuristics fitted to the same ten cases, so their agreement with the reference set is reported but is not validation. For a proposed change with gaps, an optional "Suggest with AI" call (through the new gateway, schema-validated, labelled as AI-suggested) pre-fills unresolved axes.
- Routes: `GET /api/allocation/model`, `POST /api/allocation/score`, `GET /api/allocation/cases`, `GET /api/allocation/moc/{id}`, `POST /api/allocation/assess`, `GET /api/allocation/analysis/enumeration`.
- **No public write endpoint** (the API has no authentication); confirmed selections for new changes stay in the browser and can be exported. Saving to the graph behind auth goes in the backlog.
- Tests with a fake graph client and fake LLM; `docs/reports/input-mapping.md` and `integration-architecture.md`.

### Phase 4 — Frontend: sixth tab "Decision Allocation"
- Flow on one screen: choose an existing MoC or a proposed change → impact assessment summary → eight axis selectors, each showing where its value came from → four score tiles (level, margin) → three matrices with the active cell → signature, recommendation and "why" → reference-case table (thesis vs computed) → model card crediting Parth's thesis.
- Shared "current change" in `store.ts` so Smart Form → Risk → Cost → Allocation carry the same inputs; a "Continue to Decision Allocation" action on the Risk tab.
- Touch points: `App.tsx` (TABS, panels), `navigation.ts` (TAB_PATHS), `api.ts` (typed functions), `constants.ts`, `components/ui.tsx` (ErrorBox), `onboardingContent.ts` / `Onboarding.tsx` (six workspaces), `KnowledgeGraph.tsx` (new node colours).
- Error boxes on tabs that currently fail silently.

### Phase 5 — Reliability: OpenAI layer and defect fixes
- `core/llm/gateway.py` behind `rag_pipeline.get_llm()` and `moc_agent`: explicit timeout, bounded retries, JSON-schema structured output for form prefill and risk analysis (enum-validated; replaces the line-prefix parsers that silently return "Unknown"), one repair attempt, typed errors, deterministic fallback from graph evidence with an `llm_status` flag.
- Safe prompt templating (user text delimited, no placeholder substitution from user input); chat history kept as structured turns; chat memory per browser session instead of one shared by all users; agent iterations capped; agent tool results made JSON-safe.
- `api/errors.py`: Neo4j down → 503, OpenAI failure → 502, bad input → 422; no raw exception text to the client; request-id logging.
- MoCBot: allocation intent and an agent tool `get_decision_allocation(moc_id)`.
- Defect fixes, each with a test: hazard count always 0 (`neo4j_client.py:1008`); concept search returns all MoCs (`:851`); ignored `depth` / `max_depth`; duplicate impact paths double-counting propagated hours; cost explanation never receives the numbers (`cost_predictor.py:22`); `"wo"` substring query expansion; "Process and Instrumentation" encoded as Other; quick-prompt stale query and unescaped tooltip HTML in the frontend.
- Left as backlog (modelling choices, not defects): SHUTS_DOWN in propagation, man-hours used as downtime, fixed ±25 % confidence intervals.

### Phase 6 — Repository harness (per the article)
- `AGENTS.md` (≈100 lines, a map only) and `CLAUDE.md` pointing to it; one accurate `ARCHITECTURE.md` (the current one repeats sections 5–12 three times); README quick-start corrected.
- `docs/`: `design-docs/` (index, core-beliefs, decision-allocation, llm-reliability), `exec-plans/` (this plan under active → completed, `tech-debt-tracker.md`), `product-specs/`, `references/` (Parth's model summary with attribution), `generated/` (graph schema, API routes), `QUALITY.md` (grade per area).
- Mechanical checks in CI: layer test, docs test (AGENTS.md size, links resolve, generated API doc matches the app), `ruff` (new `pyproject.toml`), frontend type-check; `Makefile` targets `check`, `test`, `lint`.

### Phase 7 — Deploy, demonstrate, hand over
- Work on branch `feat/decision-allocation`; merge to `main` at two points (after Phase 4, after Phase 6) once local checks pass; GitHub Actions + Render deploy as now.
- `docs/reports/mvp-backlog.md`: remaining tasks with effort and priority; `docs/DEPLOYMENT_CHANGES.md` updated.

## Verification
- **Offline:** `python -m pytest tests -q` (engine, reference cases, API with fakes, structure, docs); `ruff check`; `npm run build`.
- **Reproduction:** engine output equals thesis Table 2 for all ten cases and the enumeration totals; differences in sensitivity figures listed explicitly.
- **Graph:** live counts after load (10 MoCs, 22 assets, 10 `DecisionCharacterisation`); Cypher check that every characterisation selects exactly eight categories and its stored signature equals a fresh engine run.
- **Integration (the demo sequence):** MoC-002 → impact assessment → suggested axes → score → **AI-supported, R 2 / C 1.5 / U 0.5 / I 2.5, signature II/II/II**, with the explanation naming the contributing categories; repeat for MoC-001 (human-led through Uncertainty alone).
- **Regression:** all 18 existing routes return the same shapes locally and live; live smoke of Smart Form, Risk, Cost, MoCBot, Process Intelligence; simulated OpenAI and Neo4j failures return clean 502/503 and the UI shows an error box.
- **Live:** both workflows green; Pages loads the new tab; Render health green.
- Not verifiable by me: the look of the UI in a browser — I check it builds and the API responses, you check the screen.

## Risks and open items
- Reconstructed case selections and the fitted suggestion rules need Parth's confirmation; nature/impact-type choices are the least certain.
- Writing to the production graph: additive, backed up first, dry-run before apply.
- Structured-output migration changes how two existing LLM features parse replies; guarded by shape tests and a live check.
- Still outstanding from before: replace the Render API key (shared in chat), the OpenAI key and the Neo4j password.
- Size: this is several days of work in one pass; phases are ordered so the allocation feature (0–4) is usable before the hardening and harness phases land.

---

## Outcome (12 November 2026)

Delivered as planned, with these differences:

- **AI-suggested characterisation was not built.** Proposed changes get rule-based suggestions
  only. It is backlog item 5.
- **22 axis categories**, not 21 as written in the plan's table.
- **Sensitivity figures reproduce** except one threshold-sweep column and one Appendix G row;
  both are documented in `docs/reports/reproduction-report.md`. The Monte Carlo figure cannot
  be checked because the thesis does not name the case.
- **Rule suggestions agree with the reference selections on 79 of 80 axis values.**
- **Request tracing** is a reference id on unexpected errors, not per-request logging.
- **No `tests/live/` folder.** Live checks were run by hand during the work; the pre-existing
  live-marked tests remain.
- **The stale `PROJECT_STRUCTURE.md` was removed** in favour of `AGENTS.md` and `ARCHITECTURE.md`.
- **Additional defects fixed**: a query that asked for a non-existent property on every chat
  turn, and unused imports found by the new lint step.

Reports produced: technical status, reproduction, input mapping, integration architecture and
the MVP backlog, all under `docs/reports/`.
