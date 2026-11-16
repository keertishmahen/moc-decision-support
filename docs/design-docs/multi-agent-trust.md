# Multi-agent change assessment and the trust layer

Status: implemented (v3.1; live progress v3.2). Product behaviour: [../product-specs/change-case.md](../product-specs/change-case.md).
Agent line-up (generated): [../generated/agents.md](../generated/agents.md).

## Decision

One engineering change is assessed by a fixed team of agents. Each agent wraps code the
platform already had, and records what it produced, from which knowledge source, on which
evidence and with which gaps. A rule-based verifier checks the language-model agents. The
result answers three questions:

1. **What happens if we make this change?** Equipment and dependencies reached, risks,
   review needs, cost and downtime.
2. **Who should make the decision?** AI-led, AI-supported or human-led, from the existing
   decision-allocation model ([decision-allocation.md](decision-allocation.md)).
3. **Why should we trust the recommendation?** Which agent contributed what, where the
   knowledge came from, the supporting evidence, what was verified or conflicts, the gaps
   that remain, and where a person must verify or approve.

There is **no new trust score**. Trust is shown as traceability (who, from where, on what
evidence) plus independent checks, using signals the components already produce
(`llm_status`, `graph_status`, axis confidence, characterisation status, threshold margins).

## Why agents, and which patterns

The components existed as separate tabs that each called their own module; nothing recorded
which component produced a statement or how far it could be relied on. Wrapping them as
agents with one shared ledger gives that record without rewriting them.

These are general multi-agent patterns. A specific article was suggested as a reference but
could not be retrieved, so nothing here is attributed to it.

| Pattern | Where | Why |
|---|---|---|
| Supervisor (hierarchical) | `Supervisor` plans and runs the stages, assembles the case | Routing is fixed code, so the process is inspectable and repeatable |
| Parallel fan-out | Agents within a stage run on a thread pool | The wait is about the slowest agent per stage |
| Sequential stages with shared state | Later stages read earlier results from a blackboard | Cost needs the risk rating; allocation needs the HAZOP/PSSR finding |
| Independent verifier (critic) | `VerificationAgent`, stage 4, rule-based | Trust comes from checking, not from an agent vouching for itself |
| Human in the loop | Checkpoints on every case; review recorded by a person | An allocation is advice, never decision authority |

An LLM-routed planner was rejected: the line-up is small and fixed, and model-chosen routing
would make the process itself something that needs verifying.

## Provenance model (`core/provenance/`, standard library only)

| Type | Meaning |
|---|---|
| `SourceKind` | Ontology, knowledge graph, engineering records, engineering documents, computational model, ML model, LLM interpretation, user input, assumption |
| `Evidence` | One cited item: `id = "<source>:<reference>"` (e.g. `knowledge_graph:Asset:R-201`), label, detail. De-duplicated per case |
| `Finding` | A statement by one agent, its `Basis` (deterministic, rule, ml, llm, retrieval), evidence ids, an existing confidence signal, and a `Verification` (verified, unverified, conflict, not applicable) |
| `Gap` | An assumption, uncertainty or missing item, with the agent that raised it |
| `HumanCheckpoint` | What to verify or approve, why, and which role; verification before approval |
| `AgentContribution` | Agent, role, pattern, stage, basis, components reused, source kinds, status, duration, findings, gaps |

`summarise()` turns the ledger into the `why_trust` block of a case and the `provenance`
block on `/api/allocation/moc/{id}`, `/assess` and `/score`. Language-model statements are
always labelled `llm` with `llm_interpretation` evidence; allocation findings are never `llm`.
`tests/agents/test_agents.py` holds these as contracts.

## Verification rules

The verifier compares the language-model agents with the graph and with each other:

- Asset ids named by the Risk agent exist in the graph and fall within the computed reach.
- P&ID tags proposed by the Review agent exist as documents in the graph.
- The Risk and Review agents agree on HAZOP and PSSR, and agree with most similar past MoCs.
  A disagreement becomes a conflict and a checkpoint for the Process Safety Manager; the
  allocation is then computed without assuming either answer.
- The risk rating sits within the range of similar past MoCs.
- Degraded or failed agents are listed as missing information.

A rule marks another agent's finding verified or conflict; it never downgrades a conflict.
The verifier checks identifiers, flags and ratings. It does not judge the meaning of free
text, and the Why panel says so.

## Failure behaviour

Each agent runs in isolation; an exception marks it `failed` with the exception type only
(no message text reaches the client). Dependencies are declared two ways:

- `needs`: hard. If a needed agent did not succeed, this agent is `skipped`.
- `reads`: soft. The agent runs and states an assumption instead (for example the Cost agent
  uses risk level "Medium" and says so if the Risk agent failed).

A case therefore degrades instead of failing. If OpenAI is down, the Risk and Review agents
return graph-only results with status `degraded`.

## Live progress

`Supervisor.assess(request, on_event=...)` reports progress to an optional listener:
`run_started`, `stage_started`, `agent_started`, `agent_finished` (status, duration, summary),
`agent_skipped`, `run_finished` (counts). Agent events are emitted from the worker threads as
each agent starts and ends, so they arrive in real time. A failing listener is ignored; it
never changes the case.

`POST /api/case/assess/stream` runs the supervisor in a worker thread and streams those
events as NDJSON, then one `case` line (or an `error` line with the same safe message the
plain endpoint would give). Input is validated before streaming, so bad input is still a 422.
The response sets `Cache-Control: no-cache` and `X-Accel-Buffering: no` against proxy buffering.

The browser reads the stream with `fetch` (`streamCase` in `frontend/src/case/api.ts`) and
drives the "Intelligence Agents" cards and the "Activity" feed from it. If the stream cannot
be read before the first event, it falls back to `POST /api/case/assess` and says so in the feed.

## Human review

The Change Case screen records reviewer, role, decision (accept, accept with changes, reject,
escalate), notes and the checkpoints dealt with. It is kept in the browser and included in
the exported JSON. Nothing is stored on the server: there is no authentication, and a
write endpoint without it would let anyone sign off a change. The record is labelled
"advice record, not decision authority".

## Code

| Path | Holds |
|---|---|
| `core/provenance/` | Types, `Ledger`, `summarise` |
| `modules/agents/` | `base.py`, `specialists.py`, `verifier.py`, `registry.py`, `supervisor.py` |
| `modules/decision_allocation/provenance.py` | Provenance of an allocation, reused by the agent and the allocation routes |
| `api/routes/case.py` | `GET /api/case/agents`, `POST /api/case/assess` |
| `frontend/src/case/`, `tabs/ChangeCase.tsx` | Types, Why panel, pipeline, checkpoints, review form |

## Limits

Recorded in [../exec-plans/tech-debt-tracker.md](../exec-plans/tech-debt-tracker.md): the
Risk and Review agents each run their own retrieval; the verifier does not read free text;
a full case takes 20 to 60 seconds with three model calls; review records are not kept on
the server. A run cannot be cancelled once started.
