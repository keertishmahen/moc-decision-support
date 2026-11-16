# Change Case

The guided starting point of the platform: one proposed engineering change, assessed end to
end, with the reasons laid open. Design: [../design-docs/multi-agent-trust.md](../design-docs/multi-agent-trust.md).

## Who uses it

The engineer preparing a change, and the reviewer or approver who has to decide whether to
rely on the platform's assessment.

## What the user can do

| # | The user can | Acceptance |
|---|---|---|
| 1 | Describe a change (type, asset, description) or load the MoC-002 example | Assessment starts only with a description of at least 5 characters |
| 2 | See the agents run in stages | Each agent shows waiting, running, OK, degraded, failed or skipped, with its time |
| 3 | Read **what happens**: assets reached, critical assets, propagated downtime, risks, HAZOP/PSSR, approvers, documents, cost and downtime with ranges, similar past changes | Each part has a "Why?" that shows only the agents behind it |
| 4 | Read **who should decide**: AI-led, AI-supported or human-led, with the R/C/U signature | Same result as the Decision Allocation tab for the same input |
| 5 | Open **Why this recommendation?** | Shows claims with their verification, evidence grouped by knowledge source, contributing agents and their roles, assumptions/uncertainties/missing information, and human checkpoints |
| 6 | Tick checkpoints and record a review (name, role, decision, notes) | Kept in this browser; labelled "advice record, not decision authority" |
| 7 | Export the case as JSON, or print it | Export includes the case, the review and the notice; print uses the light theme and omits navigation |
| 8 | Open the allocation in Decision Allocation to adjust the eight axes | The Decision Allocation tab also has "Why this recommendation?" |

## Rules

- Language-model output is always labelled as such and is never presented as verified unless
  a rule checked it against the graph.
- A conflict between agents is never resolved automatically; it becomes a human checkpoint.
- Every case ends with an approval checkpoint for the organisation's accountable approver.
- One failing agent does not fail the case; its part is shown as missing.
- Nothing is written to the knowledge graph or stored on the server.
