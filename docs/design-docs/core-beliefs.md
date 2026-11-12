# Core beliefs

The principles this codebase is built on, each with its reason. Where a principle can be
checked by a machine it is; the check is named.

## 1. AI suggests, a person confirms, a deterministic engine allocates

The platform operates in a safety-critical domain. A recommendation about who should decide
a change must be reproducible and inspectable, so it is computed by a fixed model
(`core/allocation/`), never by a language model. Language models may suggest inputs and
explain outputs. *Check: `core/allocation` may import the standard library only.*

## 2. One source of truth for every number

The weights, thresholds, factor matrix and rule are written once, in
`core/allocation/config/parth_v1_14.json`. The API serves them; the graph holds a
projection; the frontend fetches them. Copies drift. *Check:
`test_model_numbers_live_only_in_the_config_file`.*

## 3. Published results are a regression suite

The thesis publishes concrete outputs (Table 2, the 2,592-point enumeration, the
sensitivity figures). They are tests. If a change breaks them, either the change is wrong
or the difference is documented in the test. *Check: `tests/allocation/`.*

## 4. Say what is assumed

Where the platform does not know, it says so: a duration axis with no data is labelled
"assumed", a reconstructed characterisation is labelled "pending confirmation", a degraded
answer carries `llm_status: "unavailable"`. A confident-looking guess is worse than a
visible gap.

## 5. Degrade, do not fail

The AI service and the graph are both remote and both fail sometimes. Each feature has a
defined answer for that case, and the response says which part is missing. A 500 with a
stack trace is never the designed behaviour. *Check: `tests/modules/test_degradation.py`,
`tests/api/test_errors.py`.*

## 6. Layers point one way

Domain → infrastructure → services → HTTP. It keeps the model testable without a database
and stops infrastructure concerns leaking into it. *Check:
`tests/structure/test_architecture.py`.*

## 7. The repository is the system of record

A decision that lives in a chat thread or someone's memory is invisible to the next person
and to any coding agent. Decisions go in `docs/design-docs/`, behaviour in
`docs/product-specs/`, debt in `docs/exec-plans/tech-debt-tracker.md`. `AGENTS.md` is a
short map to them. *Check: `tests/structure/test_docs.py`.*

## 8. Taste is captured once, then enforced

When the same mistake is corrected twice, it becomes a test or a lint rule with an error
message that says how to fix it. Review comments do not scale; checks do.

## 9. Additive changes to shared data

The live knowledge graph is shared and has no staging copy. Loaders merge on domain keys,
never delete domain data, run a dry-run first, and are safe to repeat.
