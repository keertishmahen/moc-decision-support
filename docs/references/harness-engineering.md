# Reference: harness engineering, as applied here

**Source.** OpenAI, "Harness engineering: leveraging Codex in an agent-first world"
(R. Lopopolo, February 2026). The article describes how a team organised a repository so
coding agents could do the work reliably: engineers design the environment, state intent
and build feedback loops. It is about the repository, not about model calls inside a
product. Read from secondary summaries; the original page blocks automated access.

## What the article recommends, and what this repository does

| Practice | Here |
|---|---|
| `AGENTS.md` as a short table of contents (about 100 lines), not an encyclopedia | `AGENTS.md`; size checked by `tests/structure/test_docs.py`. `CLAUDE.md` points to it |
| `docs/` as the system of record: design docs, execution plans, product specs, references, generated docs | `docs/design-docs/`, `docs/exec-plans/`, `docs/product-specs/`, `docs/references/`, `docs/generated/` |
| Core beliefs written down | `docs/design-docs/core-beliefs.md` |
| Execution plans checked in, with a tech-debt tracker | `docs/exec-plans/` |
| Fixed layers with one-way dependencies | `core.allocation → core → modules → api`, in `ARCHITECTURE.md` |
| Mechanical enforcement by linters and structural tests | `tests/structure/test_architecture.py`; `ruff` at two levels |
| Error messages that tell the reader how to fix the problem | Structure tests and config validation name the file to change and the document to read |
| "Taste invariants" enforced, not reviewed | Model numbers in one file; pure domain package; strict lint on new code |
| Knowledge base kept fresh by checks | Link check, generated API document compared with the app |
| Quality graded per area | `docs/QUALITY.md` |
| Boring, legible technology | Standard library for the model; one gateway for model calls |
| Validate at boundaries | Request models, selection validation, schema-validated model replies |

## Not adopted

- **Per-worktree app instances with browser automation and a local observability stack.**
  Out of proportion for a single-service prototype. The equivalent here is the offline test
  suite on a file-backed graph, which lets an agent verify behaviour without credentials.
- **Agent-to-agent review and automerge, minimal merge gates.** The article qualifies this
  as suited to high-throughput teams with strong guardrails. This repository keeps a test
  gate before deployment.
- **Recurring cleanup agents.** Not set up; `docs/QUALITY.md` and the tech-debt tracker are
  maintained by hand.

## The runtime counterpart

The article does not cover model calls inside an application. The same idea — put the
guardrails in the environment rather than rely on care — is applied to this product's
OpenAI usage in [../design-docs/llm-reliability.md](../design-docs/llm-reliability.md).
