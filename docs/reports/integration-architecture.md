# Integration architecture — MoC demonstrator + decision-allocation model

**Date:** 12 November 2026

## Approach

The simplest integration that keeps both pieces intact: the allocation model becomes a
self-contained package inside the existing backend, fed by the existing knowledge graph and
shown in a new tab. The model's logic is not altered; its numbers are loaded from a
configuration file transcribed from the thesis.

```
Proposed or existing change
        │
        ▼
┌──────────────────────────── existing demonstrator ────────────────────────────┐
│ Neo4j knowledge graph   →   impact / dependency assessment                    │
│ (assets, MoCs, HAZOP, PSSR, risk assessments, parameters, P&IDs, work orders) │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │ facts
                                    ▼
              modules/decision_allocation/characteriser.py
              eight axis suggestions, each with source, confidence, evidence
                                    │
                                    ▼
              Engineer confirms or overrides in the Decision Allocation tab
                                    │ eight selections
                                    ▼
┌──────────────────────── decision-allocation model (unchanged logic) ──────────┐
│ core/allocation/engine.py                                                     │
│ weights → R, C, U, I scores → levels → factors against Impact → signature     │
│ → AI-led / AI-supported / human-led, with reasons and sensitivity             │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │
                                    ▼
        UI · API · MoCBot and agent (report the result) · knowledge graph (stored per MoC)
```

## Components

| Piece | Location | Role |
|---|---|---|
| Model | `core/allocation/` | Deterministic engine and analysis; no dependencies |
| Model configuration | `core/allocation/config/` | Weights, thresholds, matrix, rule; ten reference cases |
| Graph reads | `modules/decision_allocation/graph_store.py` | MoC facts, asset facts, downstream reach |
| Mapping | `modules/decision_allocation/characteriser.py` | Graph facts → suggested axis values |
| Orchestration | `modules/decision_allocation/service.py` | Assess an MoC or a proposed change; score |
| API | `api/routes/allocation.py` | Eight read-only endpoints under `/api/allocation` |
| Graph layer | `loaders/allocation_loader.py` | Model and characterisations stored in Neo4j |
| UI | `frontend/src/tabs/DecisionAllocation.tsx` | The flow on one screen |

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/allocation/model` | Axes, weights, thresholds, matrix, rule, attribution |
| `POST /api/allocation/score` | Score eight selections (no database or AI involved) |
| `GET /api/allocation/moc/{id}` | Impact assessment + suggested and reference characterisation + result |
| `POST /api/allocation/assess` | The same for a proposed change |
| `GET /api/allocation/cases` | Ten reference cases: published output next to computed output |
| `GET /api/allocation/mocs` | MoC records with their stored allocation |
| `GET /api/allocation/moc/{id}/graph` | Graph neighbourhood of an MoC's characterisation |
| `GET /api/allocation/analysis/enumeration` | Shares over the whole space |

## Knowledge-graph extension

New nodes: `AllocationModel` (1), `CharacterisationAxis` (8), `AxisCategory` (22),
`Dimension` (4), `AllocationMode` (3), `DecisionCharacterisation` (10).

New relationships: `DEFINES_AXIS`, `HAS_CATEGORY`, `CONTRIBUTES_TO {weight}`, `SCORES`,
`HAS_CHARACTERISATION` (MoC → characterisation), `SELECTS` (characterisation → category),
`RECOMMENDS` (→ allocation mode), `ESCALATED_BY` (→ dimension at factor III),
`EVALUATED_WITH` (→ model).

Example query — which MoCs are human-led because of uncertainty alone:

```cypher
MATCH (m:MoC)-[:HAS_CHARACTERISATION]->(dc)-[:RECOMMENDS]->(:AllocationMode {mode_id: 'HUMAN_LED'})
MATCH (dc)-[:ESCALATED_BY]->(d:Dimension)
WITH m, collect(d.name) AS dims
WHERE dims = ['Uncertainty']
RETURN m.moc_id, m.title
```

## Demonstration sequence

1. Open **Decision Allocation**; MoC-002 (Feed Heater Control Valve Upgrade) is loaded.
2. **Impact assessment** from the graph: FV-103, criticality 3, feeds R-201, HAZOP and PSSR required.
3. **Eight axes** suggested with evidence: tactical, sub-system, permanent (assumed), local,
   collective, by procedure, partially defined, technical.
4. **Scores**: Risk 2, Complexity 1.5, Uncertainty 0.5, Impact 2.5; signature II/II/II.
5. **Recommendation: AI-supported**, with the reasons and the single-axis changes that would move it.
6. Switch to MoC-001: human-led, escalated by Uncertainty alone.
7. Or start from **Smart Form → Risk** with a new change and continue to Decision Allocation.

## Design constraints kept

- The model's numbers are written once and never restated in code or the frontend.
- No language model takes part in scoring.
- Nothing in the allocation API writes to the graph (the API has no authentication).
- If the graph is unavailable, scoring and the reference cases still work.
