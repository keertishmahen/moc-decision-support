# Development backlog — towards the client-facing MVP

**Date:** 12 November 2026 · Effort is working days for one developer and is an estimate.
Priority: **P1** needed before a client sees it, **P2** needed for a credible MVP,
**P3** improvement.

## Dependencies on other people

| Item | Who | Blocks |
|---|---|---|
| Confirm the axis selections of the ten reference cases, or share the instrument's case register | Parth | Removing "pending confirmation" from every reference case |
| Answer the three thesis questions (Appendix G row, undefined-duration weight, Monte Carlo case) | Parth | Closing the reproduction report |
| Decide whether characterisation rules should follow expert judgement or graph topology where they differ | Parth, supervisor | Rule refinement (item 6) |
| Replace the OpenAI key, Neo4j password and Render API key | Repository owner | Nothing technically; should be done before wider sharing |

## Backlog

| # | Task | Why | Priority | Effort |
|---|---|---|---|---|
| 1 | Replace reconstructed case selections with confirmed ones; rerun loader | The ten cases are reconstructions today | P1 | 0.5 |
| 2 | Authentication on the API (single shared token or login) and rate limiting | The API is open; model calls cost money | P1 | 2 |
| 3 | Save a confirmed characterisation to the graph (who, when, what was overridden) | Confirmed values currently stay in the browser; needs item 2 | P1 | 2 |
| 4 | Add duration, trigger and approval-stage data to MoC records and the form | Three axes have little or no data (see input mapping) | P2 | 2 |
| 5 | AI-suggested characterisation for a proposed change, through the gateway with a schema, shown as a suggestion with rationale | Proposed changes get low-confidence suggestions today | P2 | 2 |
| 6 | Refine the suggestion rules with Parth; test them on cases not used to write them | Rules are fitted to ten cases | P2 | 3 |
| 7 | Decision Allocation in the Smart Form flow as a single guided journey (form → risk → cost → allocation → summary export) | One continuous demonstration for a client | P2 | 3 |
| 8 | Sensitivity panel in the UI (threshold sweep, weight perturbation, Monte Carlo for the current case) | The analysis exists in the backend only | P3 | 2 |
| 9 | Editable model configuration for what-if analysis (weights, thresholds) without changing the baseline | Thesis shows thresholds dominate; clients will ask | P3 | 3 |
| 10 | Ground MoCBot's system prompt in the graph instead of hardcoded plant facts | Facts in the prompt can drift from the data | P2 | 2 |
| 11 | Verify asset and MoC ids cited in chat answers against the graph | Free-text answers are not checked | P2 | 1.5 |
| 12 | Evaluation set for the AI features (fixed questions with expected facts), run on demand | No measure of answer quality today | P2 | 3 |
| 13 | Separate downtime from man-hours; data-driven confidence intervals for cost | Modelling shortcuts in cost and propagation | P3 | 3 |
| 14 | Include ESD `SHUTS_DOWN` links in propagation (modelling decision needed) | Propagation from the ESD system returns nothing | P3 | 1 |
| 15 | Frontend tests and linting; type the original API client | Only a type-check gate exists | P3 | 2 |
| 16 | Fix or rewrite the two expected-failure tests on embedding text | Fixtures omit fields the function needs | P3 | 0.5 |
| 17 | Paid or always-on hosting for demonstrations | Free tier sleeps after 15 minutes; first request takes about a minute | P2 | 0.5 |
| 18 | Remove superseded code (Streamlit app, Azure files, root-level duplicates) after agreement | Clutter and stale documentation | P3 | 1 |

## Suggested order

**Week 1 (≈ 5 days):** items 1, 2, 3 — confirmed cases, a protected API, saved characterisations.
**Week 2 (≈ 5 days):** items 4, 5, 17 — the data and AI assistance that make proposed changes work well, and reliable hosting.
**Week 3 (≈ 6 days):** items 6, 7 — rules reviewed with Parth and one guided journey for the client demonstration.
**After:** 10–12 for trustworthiness of the chat features, then 8–9 for analysis, then the rest.

Total for P1 + P2: about 23 days.
