# Using the OpenAI API reliably

Every model call in the application goes through `core/llm/`. This document records what
that layer guarantees and why.

## Guarantees

| Concern | Mechanism | Where |
|---|---|---|
| A slow or hung call | 60 s timeout on every request | `LLMGateway` |
| Transient failures | SDK retries with backoff, at most 2 | `LLMGateway` |
| Failure type | `LLMUnavailable` (no answer) or `LLMInvalidOutput` (unusable answer); nothing else escapes | `gateway.py` |
| Empty answer | Raised as `LLMInvalidOutput`, never returned as `None` | `complete()` |
| Free-text parsing | Replaced by JSON-schema structured output for form prefill and risk analysis | `complete_json()` |
| Wrong enum or missing field | Local schema validation, one repair attempt with the problems fed back | `validate_against_schema()` |
| Prompt injection through inserted text | One-pass templating; user text delimited and declared as data | `prompting.py` |
| Forged or truncated chat history | History passed as structured turns | `rag_pipeline._build_messages` |
| Shared chat memory | One memory per browser session, at most 200 sessions | `nlp_chatbot.MoCChatbot` |
| Unbounded agent cost | At most 8 iterations, enforced in the request model and the agent | `api/main.py`, `moc_agent.py` |
| Leaked internals | Clients receive a fixed sentence; details go to the log | `api/errors.py` |

## Behaviour when the model is unavailable

| Feature | Behaviour | Marker |
|---|---|---|
| Form prefill | Risk level, HAZOP and PSSR from the majority of similar historical MoCs; approvers from the graph | `llm_status: "unavailable"` |
| Risk analysis | Hazards and affected assets from the graph; overall rating "Unknown" | `llm_status: "unavailable"` |
| Cost prediction | Estimate unaffected (it comes from the model files); explanation replaced by a notice | `llm_status: "unavailable"` |
| Decision allocation | Unaffected; no model call is involved | — |
| MoCBot, agent | HTTP 502 with a plain message | — |

## Why these choices

**Structured output over text parsing.** The previous parsers matched line prefixes; a
reply with markdown bold or numbering produced "Unknown" without any error. A schema makes
the failure visible and the enum values trustworthy.

**Validate locally as well.** The API's strict mode is the first line; the local validator
keeps the guarantee if the model or SDK behaviour changes, and lets tests run offline.

**One pass over the template.** The earlier substitution applied placeholders in sequence,
so a description containing `{context}` was itself substituted. A single regex pass over
the template never re-reads inserted values. Format specs are honoured, which also fixed
the cost explanation receiving literal `{cost_estimate:,.0f}` instead of the number.

**Degrade rather than fail for assessments.** The graph evidence is useful on its own, and
the user can see from the marker that the AI part is missing.

## Not done

Listed in [../exec-plans/tech-debt-tracker.md](../exec-plans/tech-debt-tracker.md): the
chatbot system prompt hardcodes facts that can drift from the graph; asset and MoC ids
cited in free-text chat answers are not verified against the graph; there is no
authentication or rate limiting; there is no recorded evaluation set for answer quality.
