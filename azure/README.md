# Azure Student Free Deploy — MoC Intelligence Platform

## Architecture

- **Azure App Service** (Linux, SKU `F1` Free) serves FastAPI + built React SPA on one origin.
- **Neo4j Aura Free** holds the knowledge graph.
- Secrets live in **App Settings** only (never commit `.env`).

## One-time setup

1. Install [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) and log in:

```powershell
az login
# Sign in and select your Azure subscription
az account show
```

2. Confirm Neo4j Aura is **Running** at https://console.neo4j.io

3. In PowerShell (do not commit these):

```powershell
$env:NEO4J_URI      = "neo4j+s://YOUR.databases.neo4j.io"
$env:NEO4J_USER     = "YOUR_USERNAME"   # Aura may call this NEO4J_USERNAME
$env:NEO4J_PASSWORD = "YOUR_PASSWORD"
$env:OPENAI_API_KEY = "sk-..."
```

4. Seed Aura (from repo root):

```powershell
python core/seed_neo4j.py
# optional: python seed_vector_store.py
```

## Deploy

```powershell
cd azure
.\deploy.ps1
# Or override names:
# .\deploy.ps1 -ResourceGroup rg-moc-student -Location uksouth -AppName moc-intel-demo
```

The script builds `frontend/dist`, creates RG + F1 plan + web app, sets app settings, zip-deploys, and prints the public URL.

## Local production-like run

```powershell
cd frontend; npm run build; cd ..
$env:FRONTEND_DIST = "frontend\dist"
uvicorn api.main:app --host 0.0.0.0 --port 8000
# open http://127.0.0.1:8000/
```

## Docker (optional)

```powershell
docker build -t moc-intel .
docker run -p 8000:8000 `
  -e NEO4J_URI -e NEO4J_USER -e NEO4J_PASSWORD -e OPENAI_API_KEY `
  moc-intel
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `az login` required | Run `az login` then re-run `deploy.ps1` |
| F1 create fails | Region may not allow Free; try `-Location westeurope` or `-Sku B1` (uses student credit) |
| Neo4j fail in `/api/health` | Check Aura Running + App Settings `NEO4J_*` |
| Blank UI | Ensure `frontend/dist` was included in zip (`npm run build` succeeded) |
| Cold start / sleep | Free F1 has no Always On; first request after idle can be slow |

## Deployed resources (example)

| Resource | Value |
|----------|--------|
| Resource group | `rg-moc-platform` (Sweden Central) |
| App Service plan | `plan-moc-platform` (**B1** — F1 free was too limited / region-restricted) |
| Web app | `moc-intel-student` |
| URL | https://moc-intel-student.azurewebsites.net |
| Neo4j Aura | `neo4j+s://YOUR_INSTANCE.databases.neo4j.io` (seeded) |

**Note:** Student policy blocks App Service in some regions (e.g. `uksouth`). Prefer `swedencentral` / regions where you already have RGs.

If the site returns **503**, check startup: App Service → Log stream, or re-run deploy after installing [Docker Desktop](https://www.docker.com/products/docker-desktop/) and use the Dockerfile path (more reliable than Oryx for this stack).

```powershell
# After Docker is installed:
docker build -t moc-intel .
# Push to a registry you control, then:
# az webapp config container set -g rg-moc-platform -n moc-intel-student --docker-custom-image-name <your-image>
```

## Env mapping

| Aura / Azure | App (`core/config.py`) |
|--------------|------------------------|
| `NEO4J_URI` | `NEO4J_URI` |
| `NEO4J_USERNAME` | `NEO4J_USER` (alias accepted) |
| `NEO4J_PASSWORD` | `NEO4J_PASSWORD` |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` |

