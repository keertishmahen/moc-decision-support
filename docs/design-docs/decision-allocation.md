# Decision allocation: implementation and integration

How Parth Atiwadkar's Human–AI decision-allocation framework is built into the platform.
The model itself is summarised in
[../references/decision-allocation-model.md](../references/decision-allocation-model.md).

## Shape

```
core/allocation/                 pure model, standard library only
  config/parth_v1_14.json        axes, weights, thresholds, factor matrix, rule
  config/reference_cases.json    ten FCC cases: selection + published output
  types.py  model.py             value types; config loading and validation
  engine.py                      score(selection) -> AllocationResult
  analysis.py                    enumeration, swing, weight perturbation, threshold sweep, Monte Carlo
  reference_cases.py             compare engine output with the published output

modules/decision_allocation/     integration with the platform
  graph_store.py                 read-only Cypher: MoC facts, asset facts, reach, stored characterisation
  characteriser.py               eight axis suggestions with source, confidence and evidence
  service.py                     assess_moc / assess_change / score / reference_cases

core/allocation_lookup.py        allocation of an MoC, for MoCBot and the agent
loaders/allocation_loader.py     projection of the model into Neo4j
api/routes/allocation.py         HTTP
frontend/src/allocation/, tabs/DecisionAllocation.tsx
```

## Decisions

**The engine is deterministic and has no dependencies.** The thesis instrument is additive
and categorical, so its whole behaviour can be enumerated. Keeping the engine pure makes
that enumeration a unit test and lets the result be reproduced anywhere.

**Configuration, not code, holds the model.** Changing a weight is a JSON edit plus a
loader run. The allocation rule is named in the config and implemented in `engine.py`;
an unknown rule name is rejected at load time with a message pointing at the engine.

**Suggestions are rules over graph facts, with evidence.** `characteriser.py` maps facts
such as the HAZOP flag, criticality, areas, action type and parameter values to axis
values. The rules were fitted to the ten reference cases (79 of 80 axis values agree), so
that agreement is a consistency check, not a validation. Each suggestion carries a
confidence; low-confidence ones are highlighted for confirmation.

**The result is explained, not just stated.** `AllocationResult` carries, per dimension,
the contributing categories, the level boundaries and the margin; the dimensions that
forced escalation; and the single-axis changes that would move the allocation.

**The graph holds a projection.** `AllocationModel`, `CharacterisationAxis`,
`AxisCategory`, `Dimension`, `AllocationMode` and one `DecisionCharacterisation` per MoC,
linked by `DEFINES_AXIS`, `HAS_CATEGORY`, `CONTRIBUTES_TO {weight}`, `SCORES`,
`HAS_CHARACTERISATION`, `SELECTS`, `RECOMMENDS`, `ESCALATED_BY`, `EVALUATED_WITH`. The
loader verifies the stored signature against a fresh engine run.

**No write endpoint.** The API has no authentication, so nothing in `/api/allocation`
writes to the graph. A confirmed characterisation for a new change stays in the browser and
can be exported as JSON. Persisting it needs authentication first (see the backlog).

**The graph is optional for scoring.** If Neo4j is down, `score`, the reference cases and
reference MoCs still work; the response reports `graph_status: "unavailable"`.

## Reproduction status

Reproduced exactly: the 2,592-point enumeration (62 / 406 / 2,124), 24 of 27 signatures,
the 64-point region, all ten Table 2 rows, the single-axis swing (Fig. 11), the
weight-perturbation shares (Fig. 12) and four of five threshold-sweep columns (Fig. 13).

Documented differences and open questions for the author are listed in
[../reports/reproduction-report.md](../reports/reproduction-report.md).
