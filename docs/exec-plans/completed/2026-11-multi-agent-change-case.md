# Multi-agent change assessment with a trust and provenance layer

Completed November 2026. Design: [../../design-docs/multi-agent-trust.md](../../design-docs/multi-agent-trust.md).

## Goal

Answer three questions for one engineering change (what happens, who should decide, why
trust it), reusing the existing components and without a new trust-scoring algorithm.

## Decisions

- The suggested multi-agent article could not be read (HTTP 403). Established patterns are
  used and documented as general patterns.
- The trust layer implements four elements: contributing agent and role; knowledge origin;
  evidence with identifiable sources; uncertainties, assumptions, missing information and
  human checkpoints.
- UI: a new "Change Case" tab, first in the rail and the landing tab, plus a "Why this
  recommendation?" panel on Decision Allocation.
- Human review is recorded in the browser and exported; nothing is stored on the server.

## Steps

1. `core/provenance/`: pure types and ledger; added to the layer purity test.
2. `modules/agents/`: seven agents wrapping existing modules, a rule-based verifier, a
   supervisor with stages, parallel fan-out and failure isolation.
3. `modules/decision_allocation/provenance.py`: allocation provenance, also returned by the
   allocation routes.
4. `api/routes/case.py`: `GET /api/case/agents`, `POST /api/case/assess`.
5. Offline tests in `tests/agents/` (fake AI/ML components, file-backed graph).
6. `docs/generated/agents.md` generated from the registry and checked in CI.
7. Frontend: `src/case/`, `tabs/ChangeCase.tsx`, Why panel on Decision Allocation, print styles.
8. Docs, strict lint paths, screenshots in both themes, deploy.

## Verification

- Offline: every agent contributes; MoC-002 gives AI-supported II/II/II; a fabricated asset
  id is flagged; a HAZOP disagreement becomes a conflict and a checkpoint; a failing Risk
  agent leaves Cost and Allocation running on stated assumptions; registry and API contracts.
- Live (local backend, Neo4j + OpenAI): all agents OK, evidence from every source kind, the
  verifier flagged P&ID tags proposed by the model that are not in the graph.
- Visual: Change Case and both Why panels in light and dark themes.

## Follow-up (v3.2): live agent panel

The four-column stage grid became an "Intelligence Agents" side panel with an "Activity"
feed, fed by a streamed endpoint (`POST /api/case/assess/stream`) so each agent's status is
shown as it happens. Tests cover event order, a failing listener, a failed agent, and the
stream's first, last and error lines.
