# Reference: the Human–AI decision-allocation model

**Source.** Parth Pandit Atiwadkar, *Human–AI Decision Allocation in Knowledge-Driven
Management of Change (MoC)*, MSc thesis, Engineering and Management of Manufacturing
Systems, Cranfield University, August 2026. Supervisor: Dr Jelena Milisavljevic Syed.
Instrument version 1.14.

This page summarises the model as implemented. The numbers are held in
`core/allocation/config/parth_v1_14.json`; if this page and the file disagree, the file is right.

## Pipeline

1. A change is characterised on **eight categorical axes** (one category each).
2. Each category carries a weight of 0, 0.5 or 1 against four **dimensions**: Risk (R),
   Complexity (C), Uncertainty (U), Impact (I). A dimension's score is the sum of the
   selected categories' weights.
3. Each score is levelled **LOW / MED / HIGH** against two thresholds, set as fractions of
   that dimension's maximum. A score on a boundary takes the higher level.
4. R, C and U are each read against the shared **Impact** level on the same 3×3 matrix,
   giving a **factor** I, II or III.
5. The three factors form a **signature** (for example `II/I/III`), mapped to an allocation:
   any III → **human-led**; all I → **AI-led**; otherwise **AI-supported**.

## Axes and weights (R / C / U / I)

| Axis | Categories |
|---|---|
| A1 Nature of change | Operational 0/0/0/0 · Tactical 0.5/0/0/0.5 · Strategic 1/0/0/1 |
| A2 System level | Unit 0/0/0/0 · Sub-system 0/0.5/0/0.5 · System 0/1/0/1 |
| A3 Duration of change | Temporary/periodic 0/0/0/0 · Undefined duration 0.5/0/0/0.5 · Permanent 1/0/0/1 |
| A4 Scope of change | Local 0/0/0/0 · General 0/1/0/1 |
| A5 Acceptance of change | Individual 0/0/0/0 · Collective 0/1/0/0 |
| A6 Change occurrence | By procedure 0/0/0/0 · Situational 0/1/1/0 |
| A7 Availability of information | Deterministic 0/0/0/0 · Partially defined 0/0/0.5/0 · Undefined 0/0/1/0 |
| A8 Change impact type | Social 0.5/0/0/0.5 · Organisational 1/0/0/1 · Technical 0.5/0/0/0.5 · Economic 1/0/0/1 |

Column maxima: R 3, C 4, U 2, I 5. Uncertainty shares no axis with Risk and only A6 with
Complexity; that disjointness is what lets uncertainty escalate a change on its own.

## Thresholds (fraction of maximum → raw score)

| Dimension | LOW \| MED | MED \| HIGH |
|---|---|---|
| Risk | 0.495 → 1.485 | 0.667 → 2.001 |
| Complexity | 0.370 → 1.48 | 0.620 → 2.48 |
| Uncertainty | 0.240 → 0.48 | 0.495 → 0.99 |
| Impact | 0.295 → 1.475 | 0.595 → 2.975 |

## Factor matrix (dimension level ↓, Impact level →)

| | LOW | MED | HIGH |
|---|---|---|---|
| **HIGH** | II | III | III |
| **MED** | I | II | III |
| **LOW** | I | I | II |

## Properties of the whole space

2,592 characterisations: 62 AI-led (2.4 %), 406 AI-supported (15.7 %), 2,124 human-led
(81.9 %). 24 of 27 signatures occur; `II/III/I`, `III/II/I` and `III/III/I` cannot.

## Status of the numbers

The thesis states that the weights are placeholder magnitudes justified from literature,
that the thresholds influence the outcome far more than the weights and are the least
grounded, and that the allocation rule is a conservative design decision. Four
practitioners each allocated one level less conservatively than the model.

## The ten reference cases

Thesis Table 2, mapped to MoC-001 … MoC-010. The thesis publishes scores, not axis
selections, so the selections in `reference_cases.json` are reconstructions that reproduce
the published scores, marked `reconstructed-pending-confirmation`. See
[../reports/reproduction-report.md](../reports/reproduction-report.md).
