# Tech-debt tracker

Known weaknesses, most consequential first. Add an entry when you find one you are not
fixing now; remove it in the change that fixes it. Scheduled work is in
[../reports/mvp-backlog.md](../reports/mvp-backlog.md).

## Security and operations

| Item | Detail | Where |
|---|---|---|
| No authentication or rate limiting | Any caller can run paid model calls. This is why the allocation API has no write endpoint | `api/` |
| Credentials to replace | OpenAI key, Neo4j password and Render API key were exposed during deployment setup | hosting dashboards |
| Health check calls OpenAI and Neo4j | `/api/health` is polled every 30 s by the UI; each poll reaches both services | `api/main.py`, `frontend/src/App.tsx` |
| Free hosting sleeps | First request after 15 idle minutes takes about a minute | Render |

## Data and model

| Item | Detail | Where |
|---|---|---|
| Reference characterisations are reconstructions | Chosen to reproduce published scores; awaiting the author's confirmation | `core/allocation/config/reference_cases.json` |
| Suggestion rules are fitted to ten cases | 79/80 agreement is not validation | `modules/decision_allocation/characteriser.py` |
| No duration, trigger or approval-stage data | Axes A3, A6 and A5 rely on assumption or proxy | graph content |
| Man-hours used as downtime | `actual_manhours` stands in for downtime hours | `core/neo4j_client.py`, `core/downtime_propagator.py` |
| Fixed confidence intervals | Cost ±25 %, downtime ±30 %, regardless of data | `modules/cost_predictor.py` |
| Cost model fitted to ten records | KNN k=2 blended 40/60 with a heuristic keyed to the same records | `modules/cost_predictor.py`, `train_predictor.py` |
| ESD links not propagated | `SHUTS_DOWN` is absent from the traversal; propagation from ESD-SYS returns nothing | `core/neo4j_client.py` |
| Asset names equal ids | `Asset.name` holds the id, so prompts and UI show ids twice | graph content |
| Legacy seed builds a different schema | `core/seed_neo4j.py` creates labels the queries do not use; use `loaders/snapshot_loader.py` | `core/seed_neo4j.py` |
| Orphaned vector-store segments | About 20 unused segment folders left by earlier resets | `chroma_db/` |

## AI features

| Item | Detail | Where |
|---|---|---|
| Hardcoded plant facts in the chat prompt | MoC table, asset list and topology are written into the system prompt and can drift from the graph | `modules/nlp_chatbot.py` |
| Ids in chat answers not verified | Free-text answers may cite an asset or MoC that does not exist | `modules/nlp_chatbot.py`, `core/moc_agent.py` |
| Keyword intent routing is order-dependent | "impact" matches the risk intent before the impact intent | `modules/nlp_chatbot.py` |
| MoC-specific branches in query expansion | Hardcoded expansions for individual MoC ids | `core/vector_store.py` |
| No answer-quality evaluation set | Reliability is tested; answer quality is not measured | — |
| Heavy chat turns | Cost/downtime questions build a new predictor (new clients, nested model call) | `modules/nlp_chatbot.py` |

## Code and tooling

| Item | Detail | Where |
|---|---|---|
| Two expected-failure tests | Fixtures omit fields `_moc_to_text` needs; the stated reasons are inaccurate | `tests/conftest.py` |
| Module tests need live services | Most pre-existing tests are marked `live` and skip in CI | `tests/test_rag_*.py` |
| Lint is two-level | Older code is held only to syntax/unused-import rules | `pyproject.toml`, `Makefile` |
| Frontend has no tests or linter | The only gate is the type-check | `frontend/` |
| Original API client is untyped | Responses are `any` | `frontend/src/api.ts` |
| Deep links reset to the landing page | The app always opens on onboarding | `frontend/src/App.tsx` |
| Superseded code still present | Streamlit `app.py`, Azure files, Snowflake pipeline | repository root |
| Unpinned root requirements | `requirements.txt` lists unused packages; the image uses `requirements-docker.txt` | `requirements.txt` |
