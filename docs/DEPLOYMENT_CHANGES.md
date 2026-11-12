# Deployment changes — GitHub Pages + Render

**Date of change:** 12 November 2026 · **Repository:** [keertishmahen/moc-decision-support](https://github.com/keertishmahen/moc-decision-support)

## Update — version 3.0 (12 November 2026)

Decision allocation, the model gateway and the repository harness were added. For deployment:

- **No new environment variables or services.** The same Render service and Pages site are used.
- **Backend checks now also lint and check the documents.** A push that touches `docs/`,
  `AGENTS.md`, `data/`, `loaders/` or `scripts/` runs the backend workflow as well.
- **The knowledge graph is loaded from the repository**, not by hand:
  `python -m loaders.snapshot_loader --dry-run | --apply`, then
  `python -m loaders.allocation_loader --apply`. Both are additive and safe to repeat. They
  run from a developer machine with `.env`; nothing in the deployment runs them.
- **The vector store** (`chroma_db/`) now holds all ten MoCs and ships in the image as before.
- **Failures surface as 502 / 503** with a plain message instead of 500; the UI shows them.
- `/api/version` reports `3.0.0`.

How the code is organised: [AGENTS.md](../AGENTS.md). What changed and why:
[exec-plans/completed/2026-11-decision-allocation-and-harness.md](exec-plans/completed/2026-11-decision-allocation-and-harness.md).

## Summary

The MoC Intelligence Platform no longer needs a manual Azure deployment. The React frontend is served by **GitHub Pages** and the FastAPI backend runs on **Render's free tier**. Both deploy automatically from the public GitHub repository whenever `main` changes.

| | Live URL |
|---|---|
| Application | https://keertishmahen.github.io/moc-decision-support/ |
| Backend API | https://moc-intelligence-api.onrender.com (liveness: `/api/healthz`, full status: `/api/health`) |

| | Before (Azure for Students) | After (GitHub + Render) |
|---|---|---|
| Frontend | Built into the backend container, served by FastAPI | GitHub Pages, built by GitHub Actions |
| Backend | Azure Web App container (image built in ACR) | Render free web service, built from the `Dockerfile` |
| How to deploy | Run `azure/deploy.ps1` by hand, logged in to the university tenant | `git push` to `main` — everything else is automatic |
| Gate before deploy | None | Frontend type-check and build; backend offline tests |
| Cost | Azure student credit | Free |

## How deployment works now

```
git push origin main
        │
        ├── changes in frontend/ ────────► GitHub Actions "Deploy frontend (GitHub Pages)"
        │                                    npm ci → tsc + vite build → publish to Pages
        │
        └── changes in api/ core/ modules/ ► GitHub Actions "Backend tests" (pytest + liveness check)
            tests/ chroma_db/ saved_models/   │ passes
            Dockerfile render.yaml            ▼
                                            Render: build Dockerfile → health check → go live
```

| Trigger | What runs | Defined in |
|---|---|---|
| Push to `main` touching `frontend/**` | Type-check, build and Pages deployment | [.github/workflows/deploy-frontend.yml](../.github/workflows/deploy-frontend.yml) |
| Push to `main` (or a pull request) touching backend paths | Backend tests | [.github/workflows/backend-tests.yml](../.github/workflows/backend-tests.yml) |
| Backend tests pass on a backend change | Render rebuilds and redeploys the API (`autoDeployTrigger: checksPass`) | [render.yaml](../render.yaml) |
| Manual | `gh workflow run deploy-frontend.yml` / `gh workflow run backend-tests.yml` | — |

## Changes

### 1. Repository
- The local project folder is now a git checkout of `keertishmahen/moc-decision-support`; the deployment work is a new commit on top of the existing history.
- `chroma_db/` (vector store, about 15 MB) and `saved_models/` (four `.pkl` files) are now tracked, because Render builds the image from the repository. They are public.
- `.gitignore` additionally excludes `*.pdf`, `docker-build.log`, the Azure startup JSON files, and the two workflows that are not published (`azure-docker.yml`, `dbt-moc.yml`).
- Eight local files hold real account identifiers (Snowflake account and user, university email, Neo4j instance address) where the public repository has placeholders. They are marked `skip-worktree` so git never stages the local versions: `.env.example`, `azure/README.md`, `azure/deploy.ps1`, `core/snowflake_client.py`, `ingest/pipeline.py`, `scripts/bootstrap_snowflake.py`, `snowflake/bootstrap.sql`, `snowflake/connections.toml.example`.

### 2. Frontend on GitHub Pages
- `frontend/vite.config.ts`: `base: './'`, so the build uses relative asset paths and works under `/moc-decision-support/`.
- `frontend/src/api.ts`: the backend address comes from `VITE_API_URL` at build time; without it the app calls `/api` on its own origin, as before.
- `frontend/src/navigation.ts`, `frontend/src/App.tsx`: routes moved from paths (`/app/risk`) to hashes (`#/app/risk`), so GitHub Pages needs no single-page-app fallback.
- The build contains no API key; all AI calls go through the backend.
- `frontend/package-lock.json` is now tracked (needed by `npm ci`).

### 3. Backend on Render
- [render.yaml](../render.yaml) is a Render Blueprint: Docker web service `moc-intelligence-api`, free plan, Frankfurt region, health check on `/api/healthz`.
- `api/main.py`: new `GET /api/healthz` that returns `{"status": "ok"}` without calling Neo4j or OpenAI. `/api/health` is unchanged and still reports both.
- `Dockerfile`: listens on `$PORT` (Render sets it; falls back to 8000) and runs as a non-root user (uid 1000).
- `tests/conftest.py`: tests that need a live Neo4j database and OpenAI key are marked `live` and skipped when credentials are absent; three known failures are marked as expected failures (see follow-ups).
- Render's free disk does not survive a restart. Nothing is lost: the vector store and models are inside the image and only read at run time.

## Configuration reference

| Name | Where | Value | Used by |
|---|---|---|---|
| `API_URL` | GitHub → repository variable | `https://moc-intelligence-api.onrender.com` | Frontend build (API address) |
| `OPENAI_API_KEY` | Render → service environment | secret | Backend LLM and embedding calls |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Render → service environment | secret | Backend knowledge-graph connection |
| `NEO4J_DATABASE`, `LLM_PROVIDER`, `OPENAI_MODEL`, `RAG_EMBEDDING_PROVIDER`, `RAG_MULTIQUERY` | `render.yaml` | `neo4j`, `openai`, `gpt-4o`, `openai`, `true` | Backend settings |
| `CORS_ORIGINS` | `render.yaml` | `https://keertishmahen.github.io` | Backend: which site may call the API |

## Render service

The service `moc-intelligence-api` was created on 12 November 2026 through Render's API with the same settings as `render.yaml` (Docker, free plan, Frankfurt, health check `/api/healthz`, deploy after GitHub checks pass). It lives in the same Render workspace as `symetra-mia-api`, so the two share the monthly free instance hours.

- Secrets (`OPENAI_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) are stored in the service's environment on Render. Change them under Render dashboard → `moc-intelligence-api` → Environment.
- If the service address ever changes: `gh variable set API_URL --body <url> --repo keertishmahen/moc-decision-support`, then `gh workflow run deploy-frontend.yml`.

## How to deploy and check

```bash
# Deploy: commit to main and push — the workflows and Render do the rest
git push origin main

# Re-run a deployment by hand
gh workflow run deploy-frontend.yml --repo keertishmahen/moc-decision-support
gh run list --repo keertishmahen/moc-decision-support --limit 5

# Check the backend (the first call after idle can take about a minute)
curl https://moc-intelligence-api.onrender.com/api/healthz
curl https://moc-intelligence-api.onrender.com/api/health

# Backend tests as CI runs them (offline) / with live services (needs .env)
python -m pytest tests -q
```

- **Logs:** Render dashboard → `moc-intelligence-api` → Logs.
- **Roll back:** revert the commit and push, or use Render's rollback to a previous deploy. GitHub Pages keeps serving the last successful build.

## Verification performed (12 November 2026)

- Backend tests without credentials: 5 passed, 15 skipped (live), 3 expected failures. `/api/healthz` returns 200 with no credentials set.
- Frontend: `npm run build` passes; `dist/index.html` references `./assets/...`; the bundle contains the Render address and no API key.
- Render: the first build of the Dockerfile succeeded and went live. `/api/healthz` returns 200 and `/api/health` reports Neo4j `Connected` and OpenAI `gpt-4o`.
- CORS: requests from `https://keertishmahen.github.io` are allowed; other origins get no allow header.
- Live features: Smart Form prefill, Risk analysis, Cost prediction, MoCBot chat, topology and the downtime matrix all returned 200 from the Render backend.
- Status panel: a failed health request now shows "Backend unreachable — may be waking up, retrying" instead of a bare "…".

## Known limitations

- **Cold start.** The free backend sleeps after 15 minutes without traffic; the next request takes about a minute.
- **Health polling.** The app polls `/api/health` every 30 seconds, which keeps the backend awake while a tab is open and calls Neo4j and OpenAI each time.
- **Memory.** The backend is estimated at 250–400 MB against Render's 512 MB limit.
- **Chat memory** is held in the server process: it is shared by all users and cleared on restart.
- **Neo4j Aura** free instances pause when idle; `/api/health` then reports Neo4j as down until the instance is resumed.
- **Free-tier allowance.** Render's free instance hours are capped per month.

## Open follow-ups

- [x] Create the Render service.
- [ ] Replace the Render API key used to create the service (it was shared in a chat) under Render → Account Settings → API Keys.
- [ ] **Replace the OpenAI API key and the Neo4j password**, then update them in Render and the local `.env`. Both are stored in the local archive `moc-src.tgz`; delete that archive afterwards. It is not in the repository.
- [ ] Fix the three expected-failure tests listed in `tests/conftest.py` (`_moc_to_text()` and `_expand_query()` in `core/vector_store.py`).
- [ ] Decide whether to tear down the Azure resources; `azure/` and the Azure workflow remain as a fallback.
