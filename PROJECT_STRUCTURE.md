# Project Structure

This document describes the current structure of the MoC project and the role of each major file/folder.

## Root Layout

```text
Moc/
├─ app.py
├─ requirements.txt
├─ .env
├─ setup_and_run.py
├─ train_predictor.py
├─ seed_vector_store.py
├─ moc_system_architecture_7e800cfd.plan.md
├─ core/
├─ modules/
├─ chroma_db/
├─ saved_models/
├─ __pycache__/
├─ config.py
├─ rag_pipeline.py
├─ vector_store.py
├─ neo4j_client.py
├─ smart_forms.py
├─ risk_engine.py
├─ cost_predictor.py
├─ nlp_chatbot.py
└─ train_out.txt
```

## Core Application Files

- `app.py`
  - Main Streamlit frontend (tabs, sidebar, UI components, user interaction flow).
- `requirements.txt`
  - Python dependencies for UI, Neo4j, vector DB, LLM, and ML stack.
- `.env`
  - Environment variables (Neo4j connection, OpenAI settings, provider flags).
- `setup_and_run.py`
  - Utility startup script (project bootstrap helper).

## Data Seeding and Training

- `seed_vector_store.py`
  - Loads MoC records into Chroma vector store.
- `train_predictor.py`
  - Trains cost/downtime models and writes artifacts to `saved_models/`.
- `train_out.txt`
  - Training output/log snapshot.

## Architecture / Documentation

- `moc_system_architecture_7e800cfd.plan.md`
  - Architecture and system flow description for the MoC platform.

## Core Package (`core/`)

Primary backend implementation used by the app:

- `core/config.py`
  - Canonical runtime configuration.
- `core/rag_pipeline.py`
  - Hybrid retrieval + prompt orchestration.
- `core/vector_store.py`
  - Chroma embedding/index/search logic.
- `core/neo4j_client.py`
  - Neo4j query client and graph access helpers.
- `core/seed_neo4j.py`
  - Neo4j seeding script for sample MoC/work-order graph data.
- `core/__init__.py`
  - Package marker.

## Feature Modules (`modules/`)

Domain-level logic plugged into UI tabs:

- `modules/smart_forms.py`
  - Smart prefill suggestions for MoC forms.
- `modules/risk_engine.py`
  - Risk and impact analysis workflows.
- `modules/cost_predictor.py`
  - Cost and downtime prediction logic.
- `modules/nlp_chatbot.py`
  - Conversational MoCBot logic, intents, and deterministic status paths.
- `modules/__init__.py`
  - Package marker.

## Runtime Data Directories

- `chroma_db/`
  - Persistent Chroma vector database files.
- `saved_models/`
  - Trained ML artifacts (predictors/scalers).
- `__pycache__/`
  - Python bytecode cache files.

## Note on Duplicate Root Files

Root-level files such as `config.py`, `rag_pipeline.py`, `vector_store.py`, `neo4j_client.py`, and module mirrors (`smart_forms.py`, etc.) exist alongside the package-based implementation in `core/` and `modules/`.

Current app imports are package-based (`core.*`, `modules.*`), so `core/` and `modules/` should be treated as the primary implementation path.
