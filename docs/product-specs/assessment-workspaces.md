# Product spec — assessment workspaces

The five workspaces that existed before Decision Allocation. One change (type, asset,
description) is shared across Smart Form, Risk and Cost.

| Workspace | Input | Output | Depends on |
|---|---|---|---|
| **Smart Form** | Change type, asset, description | Suggested approvers, documents, risk level, HAZOP / PSSR need, scope, P&ID tags, justification; similar historical MoCs | Graph, vector store, AI |
| **Risk & Impact** | Same | Top risks with severity, directly and indirectly affected assets, conditions at risk, HAZOP / PSSR, mitigations, overall rating | Graph, vector store, AI |
| **Cost Predictor** | Same + asset category, risk level | Cost and downtime estimates with ranges, feature values, AI explanation | Graph, model files, AI (explanation only) |
| **MoCBot** | A question | A grounded answer; the graph neighbourhood and retrieved MoCs | Graph, vector store, AI |
| **Process Intelligence** | An asset, or a question | Connectivity and topology; downtime propagation; multi-step agent answers | Graph; AI for the agent |

## Rules common to all

- A failed request shows an error message; it never fails silently.
- When the AI service is unavailable, Smart Form and Risk answer from the knowledge graph
  and say so; Cost keeps its estimate and replaces the explanation with a notice.
- Values produced by a language model (risk level, HAZOP need, ratings) are suggestions for
  an engineer to review. They are constrained to fixed choices but are not authoritative.
- Chat history belongs to one browser session.

## Known limits

Cost and downtime models are fitted to ten records and are indicative only. Asset and MoC
identifiers quoted in chat answers are not verified against the graph. See
[../exec-plans/tech-debt-tracker.md](../exec-plans/tech-debt-tracker.md).
