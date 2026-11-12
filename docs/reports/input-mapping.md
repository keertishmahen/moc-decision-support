# Input mapping — MoC demonstrator data to the eight characterisation axes

**Date:** 12 November 2026 · Implemented in `modules/decision_allocation/characteriser.py`.

## How to read this

For each axis: what the knowledge graph can supply, the rule that turns it into a suggested
value, and whether a person must supply or confirm it. Every suggestion is shown in the UI
with its evidence and a confidence; **all eight remain editable**.

| Axis | Graph inputs | Suggestion rule | Source of the final value |
|---|---|---|---|
| **A1 Nature of change** | MoC `change_type`, `action_type`, `criticality_rating`, `hazop_required`; plant-wide area | Plant-wide, or criticality 5 with a control/parameter change → strategic. Replacement/repair with no HAZOP → operational. Otherwise tactical | Graph suggestion → **expert confirms** |
| **A2 System level** | `criticality_rating`, located areas, `hazop_required`; downstream reach | Plant-wide or criticality 5 → system. HAZOP required → sub-system. No HAZOP → unit | Graph suggestion → **expert confirms** |
| **A3 Duration of change** | **None.** No MoC record has a duration field | Assumed permanent; "temporary / bypass / trial" wording in the description → temporary or undefined | **User input** |
| **A4 Scope of change** | `LOCATED_IN` areas, parameter old/new values, `hazop_required`, A2 result | More than one area, plant-wide, or system level → general. A quantified parameter change with HAZOP → general. Otherwise local | Graph suggestion → expert confirms |
| **A5 Acceptance of change** | `hazop_required` | HAZOP required → collective. Not required → individual | Graph (high confidence when HAZOP is required) |
| **A6 Change occurrence** | `action_type`, `change_type` | Replace/repair, or a procedural change → situational. Planned upgrade, optimisation, set-point change → by procedure | Graph suggestion → expert confirms |
| **A7 Availability of information** | `REFERENCES_PID`, parameter values, `hazop_reason` ("like-for-like"), `hazop_required` | No P&ID and no quantified parameter → undefined. No HAZOP and like-for-like or quantified → deterministic. Otherwise partially defined | Graph suggestion → expert confirms |
| **A8 Change impact type** | `change_type` | Procedural → organisational. Efficiency/energy → economic. Otherwise technical | Graph suggestion → **expert confirms** |

## Retrieval summary

| Source | Axes |
|---|---|
| Retrieved from the knowledge graph with reasonable confidence | A2, A4, A5, A6, A7 |
| Suggested from the graph but judgement-dependent | A1, A8 |
| Requires user input (no data) | A3 |

For a **proposed change** (not yet a record) the graph supplies only asset-level facts
(criticality, area, downstream reach, history). HAZOP, PSSR and shutdown need come from the
Smart Form or Risk tab, or from the user; without them the suggestions are marked low
confidence.

## Supporting evidence shown alongside (impact assessment)

Target asset, equipment type and criticality; areas; downstream assets reached and the
dependency chain; HAZOP / PSSR / shutdown flags; risk-assessment category and score;
parameter change and limit; P&ID references; MoCs and incidents on the asset.

## How good are the rules?

On the ten reference cases the rules agree with the reference selections on **79 of 80**
axis values (the exception is MoC-008, impact type). This is a consistency check only: the
rules were written against these same ten cases and the reference selections are
themselves reconstructions. It is not evidence that the rules generalise.

Two observations for the model's author:

- **Graph reach and expert characterisation differ.** FV-103 reaches 11 downstream assets
  in 4 areas, yet MOC-F02 is characterised as sub-system and local. System level and scope
  as judged by an engineer are not the same thing as topological reach.
- **Practitioners disagreed on five of eight axes** for one case (thesis Section 8.2). The
  platform therefore treats characterisation as a proposal to be confirmed.

## Gaps that would make more axes retrievable

| Gap | Add to the graph |
|---|---|
| Duration (A3) | `MoC.duration_type`, `MoC.expiry_date` |
| Acceptance (A5) | Approval stages linked to each MoC (one `ApprovalStage` node exists, unlinked) |
| Occurrence (A6) | `MoC.trigger` (failure, audit, improvement, regulation) |
| Impact type (A8) | Primary objective affected, or use the risk-assessment dimensions (people, asset, community, environment) |
