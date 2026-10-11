# MoC Intelligence Platform - Architecture Documentation

> **Version:** 2.0  |  **Last Updated:** 2025  |  **Platform:** FCC Unit Management of Change AI Decision Support System

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [Neo4j Knowledge Graph Schema](#5-neo4j-knowledge-graph-schema)
6. [FCC Unit Process Topology](#6-fcc-unit-process-topology)
7. [Hybrid RAG Pipeline](#7-hybrid-rag-pipeline)
8. [MoCBot - Conversational AI](#8-mocbot---conversational-ai)
9. [Enhancement 1: Process Asset Connectivity Modelling](#9-enhancement-1-process-asset-connectivity-modelling)
10. [Enhancement 2: Dynamic Downtime Propagation](#10-enhancement-2-dynamic-downtime-propagation)
11. [Enhancement 3: Agent-Based Execution](#11-enhancement-3-agent-based-execution)
12. [API Endpoints](#12-api-endpoints)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Data Flow Diagrams](#14-data-flow-diagrams)
15. [Configuration](#15-configuration)
16. [The 10 MoC Scenarios](#16-the-10-moc-scenarios)

---

## 1. Overview

The **MoC Intelligence Platform** is an AI-powered decision support system for managing
**Management of Change (MoC)** processes in an FCC (Fluid Catalytic Cracking) Unit at Refinery A.

### What It Does

The platform digitises and augments the traditional MoC workflow by combining:

- **Knowledge Graph (Neo4j)** — 22 node types encoding the full FCC Unit asset topology,
  process relationships, hazards, risk assessments, work orders, and historical MoC records
- **Vector Search (ChromaDB + OpenAI embeddings)** — semantic similarity retrieval over all 10 MoC records
- **Large Language Model (GPT-4o)** — grounded natural language reasoning anchored to retrieved graph data
- **ML Prediction (scikit-learn KNN)** — calibrated cost and downtime estimation from historical patterns
- **React Frontend** — five specialised tabs covering the full MoC lifecycle

### Core Capabilities

| Capability | Description |
|---|---|
| Smart Form Prefill | AI auto-populates MoC forms using RAG over historical records |
| Risk & Impact Analysis | Graph traversal identifies downstream asset impacts and hazards |
| Cost & Downtime Prediction | KNN + heuristic ML model predicts costs and manhours |
| MoCBot Chatbot | 20-intent conversational AI with hybrid RAG + graph augmentation |
| Process Intelligence | Connectivity analysis, downtime propagation, agent reasoning |

### Business Context

The FCC Unit is the heart of the refinery, converting heavy gas oil into valuable products.
Any change to its 22 assets must go through a rigorous 5-stage approval workflow.
The platform reduces MoC cycle time, improves risk visibility, and captures institutional knowledge
from 10 historical MoC records covering mechanical, instrumentation, process parameter, and procedural changes.

---

## 2. High-Level Architecture

```
                        MoC Intelligence Platform

  +------------------------------------------------------------------+
  |                     React Frontend (Vite)                        |
  |  +----------+ +-----------+ +----------+ +--------+ +--------+  |
  |  |SmartForm | |RiskAnalysis| |CostPredict| |MoCBot  | |Process |  |
  |  |  Tab 1   | |   Tab 2   | |  Tab 3   | | Tab 4  | |Intel.  |  |
  |  +----------+ +-----------+ +----------+ +--------+ |Tab 5   |  |
  |                                                      +--------+  |
  +------------------------------|-----------------------------------+
                                 | HTTP/REST (Axios)
                                 v
  +------------------------------------------------------------------+
  |                  FastAPI Backend (Uvicorn)                       |
  |  api/main.py  --  16 REST endpoints  --  Pydantic validation     |
  |  Lazy singleton modules: SmartForms, RiskEngine, CostPredictor,  |
  |  MoCChatbot, DowntimePropagator, MoCAgent                        |
  +---------|------------|------------|------------|------------------+
            |            |            |            |
            v            v            v            v
  +---------+--+  +------+------+  +-+----------+ +-----------+
  | Neo4j Graph|  |ChromaDB     |  |OpenAI      | |scikit-    |
  | Database   |  |Vector Store |  |GPT-4o      | |learn KNN  |
  | (22 node   |  |(text-embed- |  |text-embed- | |Cost/Down- |
  |  types,    |  | 3-small)    |  |3-small     | |time Model |
  |  30+ rels) |  |             |  |            | |           |
  +------------+  +-------------+  +------------+ +-----------+
```

### Request Flow

1. User interacts with a React tab (form input, chat message, asset selector)
2. Axios sends a POST/GET request to the FastAPI backend
3. The relevant module (chatbot, risk engine, etc.) is invoked via lazy singleton
4. The **HybridRetriever** runs ChromaDB vector search + Neo4j graph traversal in parallel
5. Retrieved context is formatted and injected into the GPT-4o system prompt
6. The LLM generates a grounded, structured markdown response
7. The response is returned to the frontend and rendered

---

## 3. Technology Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI component framework |
| Vite | 6 | Build tool and dev server |
| TypeScript | 5 | Type-safe frontend code |
| Tailwind CSS | 3 | Utility-first styling |
| Zustand | 5 | Lightweight global state management |
| TanStack Query | 5 | Server state, caching, and async data fetching |
| Recharts | 2 | Data visualisation (bar charts, radar charts) |
| Framer Motion | 11 | Animations and transitions |
| Axios | 1 | HTTP client for API calls |

### Backend

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.115 | REST API framework with automatic OpenAPI docs |
| Uvicorn | 0.32 | ASGI server for FastAPI |
| Python | 3.11+ | Backend runtime |
| Pydantic | 2 | Request/response validation |

### AI / ML

| Technology | Version | Purpose |
|---|---|---|
| OpenAI GPT-4o | latest | LLM for grounded natural language generation |
| text-embedding-3-small | latest | OpenAI embedding model for vector search |
| ChromaDB | 0.5 | Local vector store with cosine similarity search |
| scikit-learn | 1.5 | KNN model for cost and downtime prediction |

### Database

| Technology | Version | Purpose |
|---|---|---|
| Neo4j | 5 | Graph database for FCC Unit knowledge graph |
| neo4j Python driver | 5 | Cypher query execution from Python |

---

## 4. Repository Structure

```
Moc/
├── api/
│   ├── main.py              # FastAPI backend -- all 16 REST endpoints, lazy singletons,
│   │                        #   CORS middleware, Pydantic request models
│   └── __init__.py
├── core/
│   ├── config.py            # Central config loaded from .env
│   │                        #   (NEO4J_URI, OPENAI_API_KEY, OPENAI_MODEL, TOP_K_SIMILAR)
│   ├── neo4j_client.py      # Neo4j driver -- all graph queries (50+ methods)
│   │                        #   Covers: MoC lookup, asset connectivity, impact chains,
│   │                        #   hazards, incidents, work orders, PID references,
│   │                        #   risk scores, topology, propagation matrix
│   ├── rag_pipeline.py      # Hybrid RAG: ChromaDB + Neo4j -> GPT-4o
│   │                        #   HybridRetriever.retrieve() + format_context_for_prompt()
│   ├── vector_store.py      # ChromaDB with OpenAI embeddings + query expansion
│   │                        #   30+ domain synonym mappings, cosine similarity top-5
│   ├── downtime_propagator.py  # Dynamic downtime propagation across asset topology
│   │                           #   DowntimePropagator, PropagationResult, coupling coefficients
│   ├── moc_agent.py         # OpenAI function-calling agent (10 tools, max 6 iterations)
│   │                        #   MoCAgent.run() -- reasoning loop with tool dispatch
│   └── seed_neo4j.py        # Seeds Neo4j with FCC Unit dataset (10 MoCs, 22 assets)
├── modules/
│   ├── nlp_chatbot.py       # MoCBot -- 20 intents, hybrid RAG + graph augmentation
│   │                        #   MoCChatbot, SimpleMemory(k=8), intent routing,
│   │                        #   _intent_augment(), _broad_query_augment(), PID short-circuit
│   ├── smart_forms.py       # Smart Form auto-prefill module
│   │                        #   SmartFormModule -- RAG-based field suggestions,
│   │                        #   similar MoC lookup, approver recommendations
│   ├── risk_engine.py       # Risk & Impact analysis module
│   │                        #   RiskEngine -- graph traversal risk scoring,
│   │                        #   hazard identification, impact chain analysis
│   └── cost_predictor.py    # Cost & Downtime ML prediction module
│                            #   CostPredictor -- calibrated heuristic + KNN blend
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root layout -- sidebar, tab navigation, routing
│   │   ├── store.ts             # Zustand global state (selected asset, active tab,
│   │   │                        #   chat history, propagation results)
│   │   ├── api.ts               # Axios API client -- all endpoint calls with types
│   │   ├── constants.ts         # Asset IDs, change types, risk levels, colour maps
│   │   ├── components/
│   │   │   ├── ui.tsx           # Shared UI components:
│   │   │   │                    #   Card, KpiCard, Gauge, Badge, Spinner, ErrorBanner
│   │   │   ├── KnowledgeGraph.tsx  # Force-directed graph visualisation (D3 / SVG)
│   │   │   │                       #   Renders Neo4j topology as interactive node-link diagram
│   │   │   └── MarkdownMessage.tsx # Lightweight markdown renderer for chat responses
│   │   │                           #   Handles headings, bold, tables, code blocks
│   │   └── tabs/
│   │       ├── SmartForm.tsx    # Tab 1: AI-powered MoC form prefill
│   │       │                    #   Asset selector, change type, description input,
│   │       │                    #   AI suggestions panel, similar MoCs list
│   │       ├── RiskAnalysis.tsx # Tab 2: Risk & impact assessment
│   │       │                    #   Risk score radar chart, impact chain tree,
│   │       │                    #   hazard list, Recharts bar chart
│   │       ├── CostPredictor.tsx # Tab 3: ML cost & downtime prediction
│   │       │                     #   Input form, prediction result card,
│   │       │                     #   confidence interval display, similar MoC costs
│   │       ├── MoCBot.tsx       # Tab 4: Conversational AI with agent mode
│   │       │                    #   Chat interface, agent mode toggle, markdown rendering,
│   │       │                    #   propagation right panel, connectivity panel,
│   │       │                    #   tool call log display
│   │       └── ProcessIntelligence.tsx  # Tab 5: Connectivity, propagation, agent
│   │                                    #   Topology viewer, connectivity analyser,
│   │                                    #   downtime propagation matrix, agent reasoning
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── app.py                   # Streamlit standalone UI (alternative to React)
│                            #   Single-file UI for quick demos without the React build
├── nlp_chatbot.py           # Root shim -> modules/nlp_chatbot.py
├── rag_pipeline.py          # Root shim -> core/rag_pipeline.py
├── cost_predictor.py        # Root shim -> modules/cost_predictor.py
├── chroma_db/               # Persisted ChromaDB vector store (binary files)
└── .env                     # NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                             #   OPENAI_API_KEY, OPENAI_MODEL, TOP_K_SIMILAR
```

---
## 5. Neo4j Knowledge Graph Schema

### Node Types (22 types)

| Node Type | Key Properties | Description |
|---|---|---|
| `MoC` | moc_id, title, change_type, actual_cost, actual_manhours, risk_category, hazop_required, pssr_required, incident_occurred, lessons_learned | Core Management of Change record |
| `Asset` | asset_id, name, equipment_type, criticality (1-5) | FCC Unit physical asset |
| `Hazard` | hazard_id, description, category, source | Process hazard identified by a MoC |
| `RiskAssessment` | risk_id, risk_category, overall_score, likelihood, risk_people, risk_asset, risk_community, risk_environment | Quantified risk evaluation |
| `LessonsLearned` | ll_id, text | Captured lesson from MoC implementation |
| `Personnel` | person_id, role, department | Approver or reviewer |
| `Incident` | incident_id, name, description, outcome | Implementation incident record |
| `HAZOP` | hazop_id, name, required, reason | Hazard and Operability Study requirement |
| `PSSR` | pssr_id, name, required, reason | Pre-Startup Safety Review requirement |
| `Parameter` | param_id, parameter_name, old_value, new_value, threshold | Process parameter change record |
| `WorkOrder` | wo_id, title, work_type, status, planned_duration, actual_duration, estimated_cost, actual_cost, delay_reason | Maintenance work order |
| `MaintenanceActivity` | activity_id, title, safety_req | Individual maintenance task |
| `ImplementationOutcome` | outcome_id, result, description | MoC implementation result |
| `ApprovalStage` | stage_id, order, stage, role, timestamp | One stage in the 5-stage approval workflow |
| `FailureMode` | fm_id, mode, consequence, likelihood, description | Equipment failure mode |
| `PIDDocument` | pid_ref, version | Piping and Instrumentation Diagram reference |
| `Area` | area_id, name | Plant area (e.g. Reactor Section, Regeneration Section) |
| `Department` | dept_id, name | Organisational department |
| `RiskScore` | score_id, overall, category | Aggregated risk score node |
| `Plant` | plant_id, name | Refinery plant node |
| `ProcessUnit` | unit_id, name | FCC process unit grouping |
| `_GraphConfig` | config_id, version, seeded_at | Graph metadata and version tracking |

### Relationship Types (29 types)

| Relationship | From | To | Description |
|---|---|---|---|
| `TARGETS` | MoC | Asset | MoC targets a specific asset for change |
| `BELONGS_TO` | Asset | Area | Asset belongs to a plant area |
| `PART_OF` | Asset | ProcessUnit | Asset is part of a process unit |
| `UPSTREAM_OF` | Asset | Asset | Asset is upstream in the process flow |
| `DEPENDS_ON` | Asset | Asset | Asset has a functional dependency |
| `IMPACTS` | Asset | Asset | Asset directly impacts another |
| `CONTROLS_FLOW_TO` | Asset | Asset | Asset controls flow to another (valve/controller) |
| `FEEDS` | Asset | Asset | Asset feeds material/energy to another |
| `CONNECTS` | Asset | Asset | Physical connection between assets |
| `SHUTS_DOWN` | Asset | Asset | ESD system shuts down an asset |
| `IDENTIFIES` | MoC | Hazard | MoC identifies a process hazard |
| `REQUIRES` | MoC | RiskAssessment | MoC requires a risk assessment |
| `EVALUATES` | RiskAssessment | Hazard | Risk assessment evaluates a hazard |
| `SCORED_AS` | RiskAssessment | RiskScore | Risk assessment produces a score |
| `APPROVED_BY` | MoC | Personnel | MoC is approved by a person |
| `GENERATES` | MoC | WorkOrder | MoC generates a work order |
| `EXECUTED_ON` | WorkOrder | Asset | Work order is executed on an asset |
| `PERFORMED_BY` | WorkOrder | Department | Work order is performed by a department |
| `RESULTS_IN` | MoC | ImplementationOutcome | MoC results in an implementation outcome |
| `RELATED_TO` | Incident | MoC | Incident is related to a MoC |
| `GENERATED_LESSON` | MoC | LessonsLearned | MoC generated a lesson learned |
| `REQUIRES_HAZOP` | MoC | HAZOP | MoC requires a HAZOP study |
| `REQUIRES_PSSR` | MoC | PSSR | MoC requires a PSSR |
| `CHANGES_PARAMETER` | MoC | Parameter | MoC changes a process parameter |
| `HAS_PARAMETER` | Asset | Parameter | Asset has an operating parameter |
| `MANIFESTS_AS` | Hazard | FailureMode | Hazard manifests as a failure mode |
| `INCLUDES_ACTIVITY` | WorkOrder | MaintenanceActivity | Work order includes a maintenance activity |
| `REFERENCES_PID` | MoC | PIDDocument | MoC references a P&ID document |
| `LOCATED_IN` | MoC | Area | MoC is located in a plant area |

### 5-Stage Approval Workflow

Every MoC passes through five approval stages, encoded as `ApprovalStage` nodes:

| Stage | Name | Assigned Roles |
|---|---|---|
| 1 | Change Identification | Initiating Engineer / Technician |
| 2 | Screening | Operations Supervisor / Unit Superintendent |
| 3 | Risk Assessment | Process Safety Engineer / HSE Engineer / Mechanical Integrity Engineer |
| 4 | Implementation Planning | Maintenance Manager / Instrumentation Engineer / Process Engineer |
| 5 | Final Approval | Safety Manager / Process Safety Manager / HSE Manager / Maintenance Manager |

---

## 6. FCC Unit Process Topology

The FCC Unit contains **14 primary process assets** (plus 8 supporting assets) connected in a directed graph.
The topology is stored in Neo4j and queried by the connectivity and propagation modules.

### Primary Asset List

| Asset ID | Name | Equipment Type | Criticality |
|---|---|---|---|
| P-101 | Feed Pump | Centrifugal Pump | 4 |
| FV-103 | Feed Control Valve | Control Valve | 3 |
| R-201 | Riser Reactor | Reactor | 5 |
| C-203 | Cyclone Separator | Separator | 4 |
| SV-204 | Catalyst Slide Valve | Slide Valve | 5 |
| S-301 | Catalyst Stripper | Stripper | 4 |
| RG-401 | Regenerator Vessel | Regenerator | 5 |
| EX-403 | Flue Gas Expander | Expander/Turbine | 3 |
| CTL-205 | Catalyst Transfer Line | Transfer Line | 5 |
| F-501 | Main Fractionator | Distillation Column | 5 |
| WGC-401 | Wet Gas Compressor | Compressor | 5 |
| P-502 | Reflux Pump | Centrifugal Pump | 4 |
| K-402 | Air Blower | Blower | 4 |
| ESD-SYS | Emergency Shutdown System | Safety System | 5 |

### Process Flow Topology (Directed Graph)

```
                    FCC Unit Process Flow

  [V-101 Feed Drum]
       |
       v FEEDS
  [P-101 Feed Pump] ----FEEDS----> [E-102 Feed Heater]
                                         |
                                         v CONTROLS_FLOW_TO
                                   [FV-103 Feed Control Valve]
                                         |
                                         v FEEDS
  [WGC-401 Wet Gas Compressor] ---> [R-201 Riser Reactor] <--- [CTL-205 Transfer Line]
  (recycle loop)                          |                           ^
                                    /-----+-----\                     |
                                   v             v                    |
                            [C-203 Cyclone]  [SV-204 Slide Valve]    |
                                   |               |                  |
                                   v               v                  |
                            [RG-401 Regenerator] <--+                 |
                                   |                                  |
                            /------+------\                           |
                           v              v                           |
                    [EX-403 Expander]  [CTL-205] ----------------------+
                           |
                           v FEEDS
                    [FG-404 Flue Gas Piping]

  [S-301 Catalyst Stripper] --FEEDS--> [RG-401]
  [K-402 Air Blower] --------FEEDS--> [RG-401]

  [R-201] --FEEDS--> [F-501 Fractionator]
                           |
                    /------+------\
                   v              v
           [WGC-401]          [P-502 Reflux Pump]
           (recycle)          [P-503 Rebooster Pump]
                              [P-504 Product Pump]

  [ESD-SYS] --SHUTS_DOWN--> R-201, SV-204, RG-401, EX-403, F-501
```

### Asset Connections Summary

| Source Asset | Relationship | Target Asset | Flow Type |
|---|---|---|---|
| P-101 (Feed Pump) | FEEDS | R-201 (Reactor) | Feed oil |
| FV-103 (Feed Control Valve) | CONTROLS_FLOW_TO | R-201 (Reactor) | Feed flow control |
| R-201 (Reactor) | FEEDS | C-203 (Cyclone Separator) | Reactor effluent |
| R-201 (Reactor) | CONTROLS_FLOW_TO | SV-204 (Catalyst Slide Valve) | Catalyst flow |
| C-203 (Cyclone) | FEEDS | RG-401 (Regenerator) | Spent catalyst |
| SV-204 (Slide Valve) | FEEDS | RG-401 (Regenerator) | Catalyst control |
| S-301 (Catalyst Stripper) | FEEDS | RG-401 (Regenerator) | Stripped catalyst |
| RG-401 (Regenerator) | FEEDS | EX-403 (Flue Gas Expander) | Flue gas energy |
| RG-401 (Regenerator) | CIRCULATES_TO | CTL-205 (Transfer Line) | Regenerated catalyst |
| CTL-205 (Transfer Line) | FEEDS | R-201 (Reactor) | Regenerated catalyst (loop) |
| R-201 (Reactor) | FEEDS | F-501 (Fractionator) | Reactor products |
| F-501 (Fractionator) | FEEDS | WGC-401 (Wet Gas Compressor) | Wet gas |
| F-501 (Fractionator) | FEEDS | P-502 (Reflux Pump) | Reflux liquid |
| WGC-401 (Wet Gas Compressor) | FEEDS | R-201 (Reactor) | Recycle gas |
| K-402 (Air Blower) | FEEDS | RG-401 (Regenerator) | Combustion air |
| ESD-SYS | SHUTS_DOWN | R-201, SV-204, RG-401, EX-403, F-501 | Emergency shutdown |

---

## 7. Hybrid RAG Pipeline

The `HybridRetriever` in `core/rag_pipeline.py` is the core retrieval engine.
It combines vector similarity search with graph traversal to produce rich, grounded context for GPT-4o.

### Pipeline Steps

#### Step 1: ChromaDB Vector Search

- Model: `text-embedding-3-small` (OpenAI)
- Similarity metric: cosine similarity
- Returns top-5 semantically similar MoC records
- Each hit includes: `moc_id`, `similarity score`, `text snippet`
- The vector store is pre-populated by `core/seed_neo4j.py` using all 10 MoC records

#### Step 2: Query Expansion (`_expand_query`)

Before embedding, the query is expanded using 30+ domain synonym mappings:

```python
SYNONYMS = {
    'reactor':    ['R-201', 'riser', 'FCC reactor', 'cracking unit'],
    'pump':       ['P-101', 'P-502', 'centrifugal pump', 'feed pump'],
    'valve':      ['FV-103', 'SV-204', 'control valve', 'slide valve'],
    'regenerator':['RG-401', 'regen', 'catalyst regeneration'],
    'fractionator':['F-501', 'main column', 'distillation'],
    'compressor': ['WGC-401', 'wet gas compressor'],
    # ... 25+ more mappings
}
```

#### Step 3: Neo4j Graph Traversal

When an `asset_id` is resolved, the retriever runs four parallel graph queries:

1. **`get_enriched_impact_chain(asset_id, depth=4)`** — traverses 7 relationship types
   (`UPSTREAM_OF`, `DEPENDS_ON`, `IMPACTS`, `CONTROLS_FLOW_TO`, `FEEDS`, `CONNECTS`, `CIRCULATES_TO`)
   up to depth 4, returning each downstream node with:
   - `node_id`, `node_name`, `node_type`
   - `hop_distance`, `criticality`
   - `relationship_chain` (list of rel types along the path)
   - `area`, `active_moc_count`

2. **`get_full_connectivity_map(asset_id)`** — returns all direct upstream and downstream
   neighbours with relationship types and flow metadata

3. **`get_hazards_for_asset(asset_id)`** — all hazards linked via MoC -> IDENTIFIES -> Hazard

4. **`get_historical_incidents(asset_id)`** — incidents linked via Incident -> RELATED_TO -> MoC -> TARGETS -> Asset

#### Step 4: Context Formatting

The `format_context_for_prompt()` method assembles all retrieved data into structured text sections:

```
DIRECT MoC RECORD:          <- Most specific, always first
  MoC ID | Title | Change Type | Asset
  Risk | Cost | Manhours | HAZOP | PSSR
  Hazards | Incident | Lesson | Parameter change

WORK ORDERS:                 <- Planned vs actual hours and costs

PARAMETER CHANGE:            <- Old value -> new value (threshold)

SEMANTICALLY SIMILAR MoCs:  <- Top-3 vector hits with similarity scores

ENRICHED ASSET IMPACT CHAIN: <- Direct (1 hop) and indirect (2+ hops)
  Ranked by criticality/hop_distance
  Each node: asset_id, name, criticality, relationship chain, area

PROCESS CONNECTIVITY MAP:    <- Upstream and downstream with rel types

HAZARDS:                     <- With failure modes and risk scores

HISTORICAL INCIDENTS:        <- Past incidents with outcomes

LESSONS LEARNED:             <- Captured lessons with recommendations
```

#### Step 5: GPT-4o Synthesis

The formatted context is injected into the `SYSTEM_PROMPT` template and sent to GPT-4o with:
- `temperature=0.1` (low randomness for factual grounding)
- Strict rules: cite MoC IDs, asset IDs, costs, risk scores
- Mandatory markdown formatting (headings, tables, bullet lists)
- No generic advice — every answer anchored to retrieved data

### RAG Pipeline Class Diagram

```
RAGPipeline
  +-- HybridRetriever
  |     +-- VectorStore (ChromaDB + text-embedding-3-small)
  |     +-- Neo4jClient (50+ Cypher query methods)
  |     +-- retrieve(query, asset_id, moc_id) -> context dict
  |     +-- format_context_for_prompt(context) -> str
  +-- LLM (OpenAI GPT-4o wrapper)
  +-- run(query, prompt_template, ...) -> str
  +-- get_raw_context(query, ...) -> dict
```

---

## 8. MoCBot - Conversational AI

MoCBot is the conversational interface in `modules/nlp_chatbot.py`.
It routes every user message through a 20-intent classification system before
fetching targeted graph data and generating a grounded response.

### Intent Categories (20 intents)

| Intent | Trigger Keywords | Graph Augmentation |
|---|---|---|
| `moc_lookup` | moc-0, tell me about moc, details of | HAZOP/PSSR status, approval stages, parameter changes, direct impacts |
| `asset_history` | history of, past changes to, changes on | All MoCs targeting the asset |
| `risk_query` | risk, hazard, hazop, pssr, danger, impact | Risk assessments, hazards, HAZOP/PSSR nodes |
| `cost_query` | cost, price, budget, how much, predict cost | Cost data from MoC records, ML prediction |
| `downtime_query` | downtime, how long, manhours, planned vs actual | Work order analytics, propagation data |
| `approval_query` | approve, approver, sign off, who needs, stage | ApprovalStage nodes, Personnel roles |
| `lessons_query` | lesson, went wrong, failure, incident, near miss | LessonsLearned nodes, Incident records |
| `impact_query` | impact, downstream, upstream, connected, propagate | Full connectivity map, enriched chain, downtime propagation |
| `parameter_query` | setpoint, temperature, pressure, threshold, margin | Parameter nodes, threshold checks |
| `wo_query` | work order, wo-, maintenance, planned vs actual | WorkOrder nodes with overrun analysis |
| `pid_query` | pid, p&id, pid-fcc, drawing, document reference | PIDDocument nodes (short-circuit bypass) |
| `new_moc_query` | start a new moc, initiate moc, required fields | Smart form guidance |
| `checklist_query` | checklist, commissioning, verify after, close out | Implementation verification steps |
| `comparison_query` | compare, vs, versus, which is higher | Multi-MoC context fetch |
| `risk_score_filter` | risk score >=, high risk mocs, score above | get_mocs_by_risk_score() |
| `concept_search` | find mocs, similar mocs, mocs involving | get_mocs_by_concept() |
| `training_query` | training, procedure update, operator training | get_mocs_requiring_training() |
| `threshold_check` | exceed, above limit, design limit, escalation | Parameter threshold comparison |
| `failure_mode` | failure mode, equipment failure, manifests as | FailureMode nodes via Hazard |
| `general` | (fallback) | Broad vector search only |

### Key Methods

#### `_intent_augment(intent, message, asset_id, moc_id)`

Fetches targeted graph data based on the detected intent. Examples:
- `moc_lookup`: fetches HAZOP/PSSR status, approval stages, parameter changes, direct process impacts
- `impact_query`: fetches full connectivity map, enriched impact chain, downtime propagation
- `wo_query`: fetches work order analytics with planned vs actual overrun
- `parameter_query`: fetches parameter thresholds and computes margin to design limit

#### `_broad_query_augment(intent, message)`

Handles dataset-wide queries that don't target a specific asset/MoC:
- HAZOP/PSSR summary across all 10 MoCs
- All incidents and rework records
- Cost overview sorted by actual cost
- Risk score filtering (e.g. all MoCs with risk >= 12)
- P&ID reference lookup
- Concept search across all MoC titles and descriptions
- Training/procedure update queries
- Planned vs actual work order analytics

#### PID Short-Circuit

When `intent == 'pid_query'`, MoCBot bypasses the full RAG pipeline and performs a direct
Neo4j lookup via `get_mocs_by_pid()`. This avoids LLM noise for exact P&ID reference queries.
The PID number is normalised to `PID-FCC-xxx` format before querying.

#### Natural Language Asset Resolution

The `_extract_asset_id()` function maps 40+ natural language names to asset IDs:

```python
ASSET_NAME_MAP = {
    'reactor':          'R-201',
    'riser':            'R-201',
    'feed pump':        'P-101',
    'slide valve':      'SV-204',
    'regenerator':      'RG-401',
    'fractionator':     'F-501',
    'transfer line':    'CTL-205',
    'wet gas compressor': 'WGC-401',
    # ... 30+ more mappings
}
```

#### `SimpleMemory(k=8)`

Maintains a rolling window of the last 8 conversation turns using a `deque`.
History is formatted as `User: ... / MoCBot: ...` pairs and prepended to each LLM call.

#### Agent Mode

When agent mode is enabled in the UI, the chat request is routed to `POST /api/agent`
instead of `POST /api/chat`. The `MoCAgent` class handles the request using OpenAI
function calling (see Section 11).

---
## 9. Enhancement 1: Process Asset Connectivity Modelling

Enhancement 1 adds deep process topology awareness to the platform.
Four new Neo4j query methods expose the full FCC Unit connectivity graph to all modules.

### `get_full_connectivity_map(asset_id)`

Returns all direct upstream and downstream neighbours of an asset with:
- `asset_id`, `name`, `equipment_type`, `criticality`
- `rel_type` — the relationship type (FEEDS, CONTROLS_FLOW_TO, etc.)
- `flow_type` — the flow medium (catalyst, feed oil, flue gas, etc.)
- `direction` — upstream or downstream

Used by: MoCBot `impact_query` augmentation, RAG pipeline context formatting,
Process Intelligence tab connectivity panel.

### `get_enriched_impact_chain(asset_id, depth=4)`

Traverses 7 relationship types up to depth 4 and returns every reachable downstream asset:

```cypher
MATCH path = (src:Asset {asset_id: $asset_id})
             -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|FEEDS|CONNECTS|CIRCULATES_TO*1..4]->
             (b:Asset)
RETURN DISTINCT b.asset_id, b.name, b.equipment_type, b.criticality,
       length(path) AS hop_distance,
       [rel IN relationships(path) | type(rel)] AS relationship_chain,
       [rel IN relationships(path) | rel.flow_type] AS flow_types
ORDER BY hop_distance, b.criticality DESC
```

Each result node includes `relationship_chain` — the exact sequence of relationship types
from source to target, enabling precise impact path explanation.

### `get_asset_connectivity_score(asset_id)`

Computes a weighted connectivity score for an asset:

| Factor | Weight | Description |
|---|---|---|
| Criticality | x10 | Asset criticality rating (1-5) |
| Downstream connections | x5 | Number of assets this asset feeds into |
| Upstream connections | x3 | Number of assets that feed into this asset |
| Active MoCs | x4 | Number of MoC records targeting this asset |
| Hazards | x6 | Number of hazards identified for this asset |
| ESD shutdown target | x15 | Whether ESD-SYS shuts down this asset |

Higher score = more critical node in the process network.
Used by the Process Intelligence tab to rank assets by network importance.

### `get_process_flow_topology()`

Returns the complete FCC Unit directed graph as a list of edges:

```python
{
    'source_id': 'P-101',
    'source_name': 'Feed Pump',
    'rel_type': 'FEEDS',
    'target_id': 'R-201',
    'target_name': 'Riser Reactor',
    'flow_type': 'feed_oil',
    'source_criticality': 4,
    'target_criticality': 5,
}
```

Used by: MoCAgent `get_process_topology` tool, KnowledgeGraph.tsx force-directed visualisation.

### Integration with MoCBot

When `intent == 'impact_query'`, `_intent_augment()` calls all four methods and prepends
the results to the RAG context as structured sections:

```
DOWNSTREAM CONNECTIONS FROM {asset_id} (direct):
  -> R-201 (Riser Reactor) | rel=FEEDS | flow=feed_oil | crit=5
  -> FV-103 (Feed Control Valve) | rel=CONTROLS_FLOW_TO | crit=3

UPSTREAM CONNECTIONS:
  ^ V-101 (Feed Surge Drum) | rel=FEEDS | crit=3

CONNECTIVITY SCORE: 87 (criticality=40, downstream=25, upstream=9, MoCs=8, hazards=0, ESD=0)

DOWNTIME PROPAGATION (24h source):
  1. R-201 (Riser Reactor): 20.4h | coupling=0.85 | High risk
  2. F-501 (Fractionator): 12.2h | coupling=0.51 | Medium risk
```

---

## 10. Enhancement 2: Dynamic Downtime Propagation

The `DowntimePropagator` class in `core/downtime_propagator.py` models how downtime
at one asset propagates through the FCC Unit process topology to downstream assets.

### Coupling Coefficients

Each relationship type has a coupling coefficient representing how much of the upstream
downtime propagates through that connection:

| Relationship Type | Coupling Coefficient | Rationale |
|---|---|---|
| SHUTS_DOWN | 0.95 | ESD shutdown — near-total coupling |
| FEEDS | 0.85 | Direct material/energy flow — very high coupling |
| CONTROLS_FLOW_TO | 0.80 | Control dependency — high coupling |
| CIRCULATES_TO | 0.75 | Catalyst circulation — high coupling |
| UPSTREAM_OF | 0.65 | Generic upstream — moderate-high coupling |
| IMPACTS | 0.60 | Explicit impact relationship |
| DEPENDS_ON | 0.50 | Functional dependency — moderate coupling |
| CONNECTS | 0.40 | Physical connection — lower coupling |

### Hop Decay Factor

Each additional hop reduces propagation by a decay factor of **0.70**:

```
Hop 1: coupling x 0.70^0 = coupling x 1.00
Hop 2: coupling x 0.70^1 = coupling x 0.70
Hop 3: coupling x 0.70^2 = coupling x 0.49
Hop 4: coupling x 0.70^3 = coupling x 0.34
```

### Criticality Amplifiers

High-criticality assets amplify the propagated downtime they receive:

| Criticality | Amplifier | Effect |
|---|---|---|
| 5 (Critical) | x1.20 | 20% amplification |
| 4 (High) | x1.05 | 5% amplification |
| 3 (Medium) | x0.90 | 10% reduction |
| 2 (Low) | x0.75 | 25% reduction |
| 1 (Minimal) | x0.60 | 40% reduction |

### Propagation Formula

```
propagated_hours = source_hours x coupling_factor x criticality_amplifier

where:
  coupling_factor = product of (COUPLING_COEFFICIENTS[rel] x HOP_DECAY^i)
                    for each relationship in the path
  criticality_amplifier = CRITICALITY_AMPLIFIER[target_criticality]
```

### `propagate(source_asset_id, source_downtime_hours, max_depth=4)`

Main propagation method. Returns a `PropagationResult` containing:

```python
PropagationResult(
    source_asset_id='P-101',
    source_asset_name='Feed Pump',
    source_downtime=24.0,
    total_affected=8,
    total_propagated_hours=142.3,
    affected_assets=[
        PropagatedDowntime(
            asset_id='R-201',
            propagated_hours=20.4,
            confidence_low=14.3,
            confidence_high=26.5,
            coupling_factor=0.850,
            hop_distance=1,
            risk_level='High',
            relationship_chain=['FEEDS'],
        ),
        # ... more assets ranked by propagated_hours
    ],
    summary='Downtime propagation from P-101 ...'
)
```

### `propagate_from_moc(moc_id)`

Convenience method that:
1. Fetches the MoC's target asset and actual manhours from Neo4j
2. Uses `actual_manhours` (or `estimated_manhours` as fallback) as `source_downtime_hours`
3. Calls `propagate()` and returns the full `PropagationResult`

Used by: `GET /api/downtime/moc/{moc_id}` endpoint.

### `get_propagation_matrix()`

Computes a risk matrix for all high-criticality assets (criticality >= 4):
- Uses a standard 24-hour source downtime for comparison
- Returns each asset's total propagated hours and top affected asset
- Sorted by total propagated hours descending
- Used by the Process Intelligence tab propagation matrix view

### Confidence Intervals

Each `PropagatedDowntime` includes an 80% confidence interval:
- Direct connections (1 hop): +/- 30%
- Indirect connections (2+ hops): +/- 50%

### Risk Classification

| Risk Level | Condition |
|---|---|
| Critical | propagated_hours x criticality >= 200 |
| High | propagated_hours x criticality >= 80 |
| Medium | propagated_hours x criticality >= 30 |
| Low | propagated_hours x criticality < 30 |

### Integration

- **MoCBot**: `impact_query` augmentation calls `propagate()` and prepends ranked results to context
- **Process Intelligence Tab**: Right panel shows propagation results as a ranked table
- **API**: `POST /api/downtime/propagate`, `GET /api/downtime/matrix`, `GET /api/downtime/moc/{moc_id}`

---

## 11. Enhancement 3: Agent-Based Execution

The `MoCAgent` class in `core/moc_agent.py` implements an OpenAI function-calling agent
for advanced multi-step reasoning over the FCC Unit knowledge graph.

### Agent Architecture

```
User Query
    |
    v
MoCAgent.run()
    |
    v
[Iteration Loop - max 6 iterations]
    |
    +-- GPT-4o: Analyse query, decide which tools to call
    |
    +-- Tool calls (parallel):
    |     get_moc_detail | get_asset_connectivity | propagate_downtime
    |     search_similar_mocs | get_impact_chain | get_risk_assessment
    |     get_process_topology | get_connectivity_score
    |     get_work_orders | get_hazards_for_asset
    |
    +-- Tool results appended to message history
    |
    +-- GPT-4o: Synthesise results or call more tools
    |
    v
Final Answer (when no more tool calls needed)
    |
    v
Return: {response, tool_calls_made, iterations, context_used}
```

### 10 Agent Tools

| Tool | Arguments | Returns | Use Case |
|---|---|---|---|
| `get_moc_detail` | moc_id | Full MoC record with risk, costs, hazards, WOs | MoC-specific queries |
| `get_asset_connectivity` | asset_id | Full connectivity map (upstream + downstream) | Impact analysis |
| `propagate_downtime` | asset_id, downtime_hours | PropagationResult with ranked affected assets | Downtime impact queries |
| `search_similar_mocs` | query, top_k | Top-k semantically similar MoC records | Historical precedent search |
| `get_impact_chain` | asset_id, depth | Enriched impact chain with relationship types | Deep impact tracing |
| `get_risk_assessment` | moc_id | Risk scores, HAZOP/PSSR outcomes | Risk queries |
| `get_process_topology` | (none) | Complete FCC directed graph (50 edges) | Topology analysis |
| `get_connectivity_score` | asset_id | Weighted connectivity score | Network criticality ranking |
| `get_work_orders` | moc_id | Work orders with planned vs actual | Maintenance analytics |
| `get_hazards_for_asset` | asset_id | Hazards with failure modes and risk scores | Safety analysis |

### Reasoning Loop

1. **Analyse**: GPT-4o receives the user query and decides which tools to call first
2. **Call tools**: One or more tools are called in parallel
3. **Observe**: Tool results are appended to the message history
4. **Iterate**: GPT-4o decides whether to call more tools or generate a final answer
5. **Final answer**: When no more tool calls are needed, GPT-4o synthesises all results
6. **Max iterations**: If 6 iterations are reached, a final answer is forced

### Agent Mode in MoCBot UI

The MoCBot tab has an agent mode toggle. When enabled:
- Chat requests are routed to `POST /api/agent` instead of `POST /api/chat`
- The response includes `tool_calls_made` — a log of every tool call and its result
- The UI renders the tool call log below the response, showing:
  - Tool name and arguments
  - Result summary
  - Number of iterations

### Example Agent Trace

Query: *'What would happen if R-201 goes offline for 48 hours?'*

```
Iteration 1:
  Tool: propagate_downtime(asset_id='R-201', downtime_hours=48)
  Result: 12 assets affected, 847h total propagated downtime

Iteration 2:
  Tool: get_asset_connectivity(asset_id='R-201')
  Result: 4 downstream, 3 upstream connections

Iteration 3:
  Tool: get_hazards_for_asset(asset_id='R-201')
  Result: 2 hazards (thermal stress, catalyst circulation instability)

Final Answer: Structured markdown response citing all tool results
```

---

## 12. API Endpoints

All endpoints are defined in `api/main.py`. The server runs on `http://localhost:8000`.

### Endpoint Reference

| Method | Path | Request Body | Response | Description |
|---|---|---|---|---|
| GET | `/api/health` | - | `{neo4j: {ok, message}, openai: {ok, message}}` | Service health check |
| GET | `/api/assets` | - | `[{id, name, type, criticality, area}]` | All FCC Unit assets |
| GET | `/api/mocs` | - | `[{moc_id, title, change_type, cost, manhours, asset_id}]` | All MoC records |
| POST | `/api/forms/prefill` | `{change_type, asset_id, description}` | `{suggestions, similar_mocs}` | AI form prefill |
| POST | `/api/risk/analyse` | `{change_type, asset_id, description}` | Risk analysis result | Risk & impact analysis |
| POST | `/api/cost/predict` | `{change_type, asset_id, asset_category, risk_level, description}` | `{predicted_cost, predicted_downtime, confidence}` | ML cost prediction |
| POST | `/api/chat` | `{message, asset_id?}` | `{response, intent, asset_id_used, moc_id_used, vector_hits}` | MoCBot chat |
| POST | `/api/chat/reset` | - | `{ok: true}` | Reset conversation memory |
| POST | `/api/graph/context` | `{query, asset_id?, moc_id?}` | Raw RAG context dict | Debug: raw retrieval context |
| GET | `/api/topology` | - | `{edges, edge_count}` | Full FCC process topology |
| POST | `/api/connectivity` | `{asset_id}` | `{connectivity, score}` | Asset connectivity map + score |
| GET | `/api/assets/connectivity` | - | `[{asset_id, name, criticality, connectivity_score, ...}]` | All assets with scores |
| POST | `/api/downtime/propagate` | `{asset_id, downtime_hours, max_depth?}` | PropagationResult | Downtime propagation |
| GET | `/api/downtime/matrix` | - | `{matrix, count}` | Propagation risk matrix |
| GET | `/api/downtime/moc/{moc_id}` | - | PropagationResult | Propagate from MoC manhours |
| POST | `/api/agent` | `{query, max_iterations?}` | `{response, tool_calls_made, iterations, context_used}` | Agent-based reasoning |

### Request/Response Models

```python
class FormRequest(BaseModel):
    change_type: str
    asset_id: str
    description: str

class ChatRequest(BaseModel):
    message: str
    asset_id: Optional[str] = None

class DowntimePropagationRequest(BaseModel):
    asset_id: str
    downtime_hours: float = 24.0
    max_depth: int = 4

class AgentRequest(BaseModel):
    query: str
    max_iterations: int = 6
```

### CORS Configuration

The API allows requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:5174` (Vite alternate)
- `http://localhost:3000` (Create React App)

---
## 13. Frontend Architecture

The React frontend is a single-page application with five tabs, each corresponding to
a distinct MoC workflow capability. State is managed by Zustand; data fetching by TanStack Query.

### Tab 1: Smart Form (SmartForm.tsx)

**Purpose**: AI-powered MoC form prefill using RAG over historical records.

**User Flow**:
1. User selects an asset from the dropdown (populated from GET /api/assets)
2. User selects a change type (Mechanical, Instrumentation, Process Parameter, etc.)
3. User enters a description of the proposed change
4. Clicks Get AI Suggestions -> POST /api/forms/prefill
5. AI suggestions panel shows: recommended risk level, approvers, HAZOP/PSSR requirements,
   estimated cost range, and relevant hazards
6. Similar MoCs panel shows top-3 historical MoCs with costs and outcomes

**Key Components**: Asset selector, change type dropdown, description textarea,
AI suggestions card, similar MoCs list with cost badges.

### Tab 2: Risk and Impact Analysis (RiskAnalysis.tsx)

**Purpose**: Graph traversal risk analysis with Recharts visualisations.

**User Flow**:
1. User selects asset and change type
2. Clicks Analyse Risk -> POST /api/risk/analyse
3. Results show:
   - Risk score radar chart (people, asset, community, environment dimensions)
   - Impact chain tree (direct and indirect downstream assets)
   - Hazard list with failure modes and severity badges
   - HAZOP/PSSR requirement flags
   - Historical incidents for the asset

**Key Components**: Recharts RadarChart, impact chain tree view, hazard cards,
risk score KPI cards, HAZOP/PSSR badges.

### Tab 3: Cost Predictor (CostPredictor.tsx)

**Purpose**: ML-based cost and downtime prediction using calibrated KNN model.

**User Flow**:
1. User fills in: asset, change type, asset category, risk level, description
2. Clicks Predict -> POST /api/cost/predict
3. Results show:
   - Predicted cost with confidence interval (Recharts bar chart)
   - Predicted downtime in hours
   - Model confidence score
   - Similar historical MoCs with actual costs for comparison

**Key Components**: Input form, prediction result card with Gauge component,
confidence interval bar, similar MoC cost comparison table.

### Tab 4: MoCBot (MoCBot.tsx)

**Purpose**: Conversational AI with agent mode, markdown rendering, and side panels.

**User Flow**:
1. User types a message in the chat input
2. Standard mode: POST /api/chat -> MoCChatbot with 20-intent routing
3. Agent mode (toggle): POST /api/agent -> MoCAgent with tool calling
4. Response rendered as markdown (MarkdownMessage.tsx)
5. Right panel shows downtime propagation results if impact query detected
6. Connectivity panel shows asset connectivity map if asset resolved
7. Tool call log shown below response in agent mode

**Key Components**: Chat message list, input bar, agent mode toggle,
MarkdownMessage renderer, propagation right panel (ranked table),
connectivity panel (upstream/downstream lists), tool call log accordion.

### Tab 5: Process Intelligence (ProcessIntelligence.tsx)

**Purpose**: Topology viewer, connectivity analyser, downtime propagation matrix, agent reasoning.

**Sub-sections**:

1. **Topology Viewer**: Force-directed graph (KnowledgeGraph.tsx) showing all FCC Unit assets
   and their connections. Nodes sized by criticality, edges coloured by relationship type.

2. **Connectivity Analyser**: Select an asset to see its full connectivity map,
   connectivity score breakdown, and ranked downstream impacts.

3. **Downtime Propagation**: Enter an asset and downtime hours to run propagation analysis.
   Results shown as a ranked table with coupling factors, confidence intervals, and risk levels.

4. **Propagation Matrix**: GET /api/downtime/matrix shows all high-criticality assets
   ranked by total propagated downtime impact.

5. **Agent Reasoning**: Free-text query box that routes to POST /api/agent.
   Shows the full tool call trace and final synthesised answer.

### Global State (Zustand store.ts)

The Zustand store holds:
- selectedAsset: currently selected asset ID
- activeTab: current tab index (0-4)
- chatHistory: array of ChatMessage objects
- propagationResult: last PropagationResult from downtime propagation
- connectivityData: last ConnectivityMap from connectivity analysis
- agentMode: boolean toggle for agent vs standard chat

---

## 14. Data Flow Diagrams

### Standard Chat Query Flow

`
User types message
       |
       v
MoCBot.tsx: POST /api/chat {message, asset_id}
       |
       v
api/main.py: get_chatbot().chat(message, asset_id)
       |
       v
MoCChatbot.chat()
  1. _detect_intent(message)          -> intent category
  2. _extract_moc_id(message)         -> moc_id or None
  3. _extract_asset_id(message)       -> asset_id or None
  4. PID short-circuit check          -> return early if pid_query
  5. neo4j.search_mocs_by_keyword()   -> fallback moc/asset if none found
  6. pipeline.retriever.retrieve()    -> context dict
     |-- VectorStore.search()         -> top-5 similar MoCs
     |-- neo4j.get_enriched_impact_chain() -> downstream assets
     |-- neo4j.get_full_connectivity_map() -> upstream/downstream
     |-- neo4j.get_hazards_for_asset()     -> hazards
     +-- neo4j.get_historical_incidents()  -> incidents
  7. _intent_augment()                -> targeted graph data
  8. _broad_query_augment()           -> dataset-wide data
  9. format_context_for_prompt()      -> structured text
 10. llm.invoke(messages)             -> GPT-4o response
 11. memory.add(human, ai)            -> update conversation history
       |
       v
{response, intent, asset_id_used, moc_id_used, vector_hits}
       |
       v
MarkdownMessage.tsx renders response
`

### Agent Mode Flow

`
User types message (agent mode ON)
       |
       v
MoCBot.tsx: POST /api/agent {query, max_iterations=6}
       |
       v
api/main.py: run_agent(query)
       |
       v
MoCAgent.run(query)
  messages = [system_prompt, user_query]
  loop (max 6 iterations):
    |
    +-- GPT-4o: chat.completions.create(tools=AGENT_TOOLS)
    |     -> tool_calls or final_answer
    |
    +-- if tool_calls:
    |     for each tool_call:
    |       _execute_tool(tool_name, args)
    |         -> neo4j query / propagator / vector search
    |       append tool result to messages
    |
    +-- if no tool_calls: return final answer
  |
  v
{response, tool_calls_made, iterations, context_used}
       |
       v
MoCBot.tsx renders response + tool call log
`

### Downtime Propagation Flow

`
User selects asset + enters downtime hours
       |
       v
ProcessIntelligence.tsx: POST /api/downtime/propagate
  {asset_id: R-201, downtime_hours: 48.0, max_depth: 4}
       |
       v
api/main.py: DowntimePropagator().propagate()
       |
       v
DowntimePropagator.propagate(R-201, 48.0)
  1. neo4j.get_enriched_impact_chain(R-201, depth=4)
     -> list of downstream nodes with relationship chains
  2. for each node:
     coupling = _compute_coupling(rel_chain, hops)
       = product of COUPLING_COEFFICIENTS[rel] x HOP_DECAY^i
     crit_amp = CRITICALITY_AMPLIFIER[criticality]
     propagated = 48.0 x coupling x crit_amp
     if propagated >= 0.5h: add to affected list
  3. Sort by propagated_hours DESC
  4. Build PropagationResult with summary
       |
       v
PropagationResult serialised to JSON
       |
       v
ProcessIntelligence.tsx renders ranked table:
  Asset | Propagated Hours | CI | Coupling | Risk Level | Hops
`

---

## 15. Configuration

All configuration is loaded from .env via core/config.py.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| NEO4J_URI | Yes | - | Neo4j connection URI (bolt://localhost:7687) |
| NEO4J_USER | Yes | neo4j | Neo4j username |
| NEO4J_PASSWORD | Yes | - | Neo4j password |
| OPENAI_API_KEY | Yes | - | OpenAI API key for GPT-4o and embeddings |
| OPENAI_MODEL | No | gpt-4o | OpenAI model name |
| TOP_K_SIMILAR | No | 5 | Number of vector search results to retrieve |

### Example .env file

`
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
TOP_K_SIMILAR=5
`

### Starting the Platform

`
Step 1: Start Neo4j (ensure it is running)
Step 2: Seed the knowledge graph (first time only)
        python core/seed_neo4j.py
Step 3: Start the FastAPI backend
        uvicorn api.main:app --reload
Step 4: Start the React frontend
        npm run dev (from frontend/ directory)
Step 5: Open http://localhost:5173
`

---

## 16. The 10 MoC Scenarios

The platform is seeded with 10 real-world FCC Unit MoC scenarios covering all major
change types. These records form the knowledge base for all AI modules.

| MoC ID | Title | Change Type | Target Asset | Risk Score | Risk Category | Actual Cost | Manhours | Incident |
|---|---|---|---|---|---|---|---|---|
| MoC-001 | Feed Pump P-101 Replacement | Mechanical | P-101 | 12 | High | 118000 | 96h | No |
| MoC-002 | Feed Heater Control Valve FV-103 Upgrade | Instrumentation | FV-103 | 8 | Medium | 36500 | 48h | No |
| MoC-003 | Reactor R-201 Temperature Setpoint 510 to 525 degC | Process Parameter | R-201 | 8 | Medium | 7500 | 16h | No |
| MoC-004 | Cyclone Separator C-203 Inspection/Repair | Mechanical Maintenance | C-203 | 12 | High | 102000 | 120h | No |
| MoC-005 | Catalyst Slide Valve SV-204 Control System Upgrade | Instrumentation | SV-204 | 12 | High | 67500 | 72h | No |
| MoC-006 | Catalyst Stripper Steam Optimization S-301 | Process and Instrumentation | S-301 | 12 | High | 92000 | 88h | Yes: steam leakage |
| MoC-007 | Flue Gas Expander EX-403 Performance Upgrade | Mechanical Efficiency | EX-403 | 8 | Medium | 78000 | 64h | Yes: misalignment trip |
| MoC-008 | Fractionator Reflux Pump P-502 Replacement | Mechanical | P-502 | 12 | High | 135000 | 104h | Yes: alignment issue |
| MoC-009 | Emergency Shutdown Procedure Update | Procedural | ESD-SYS | 10 | High | 22000 | 32h | No |
| MoC-010 | Catalyst Transfer Line CTL-205 Reinforcement | Mechanical Integrity | CTL-205 | 15 | High | 165000 | 144h | Yes: weld defect |

### Key Observations

- Highest cost: MoC-010 (165K) -- CTL-205 reinforcement with weld defect incident
- Highest risk score: MoC-010 (15) -- only MoC with risk score above 12
- Most incidents: MoC-006, MoC-007, MoC-008, MoC-010 (4 of 10 MoCs had incidents)
- Lowest cost: MoC-003 (7.5K) -- process parameter change (setpoint adjustment)
- HAZOP required: MoC-001, MoC-003, MoC-004, MoC-005, MoC-006, MoC-010
- PSSR required: MoC-001, MoC-002, MoC-004, MoC-005, MoC-006, MoC-007, MoC-008, MoC-010

### MoC-003 Parameter Change Detail

MoC-003 is the only process parameter change in the dataset:
- Parameter: Reactor R-201 temperature setpoint
- Old value: 510 degC
- New value: 525 degC
- Design limit (threshold): 545 degC
- Margin to limit: 20 degC (3.7% below maximum)

### P&ID Document References

| P&ID Reference | Version | Associated MoC(s) |
|---|---|---|
| PID-FCC-101 | Rev 3 | MoC-001 (Feed Pump) |
| PID-FCC-103 | Rev 2 | MoC-002 (Feed Control Valve) |
| PID-FCC-201 | Rev 5 | MoC-003 (Reactor Temperature) |
| PID-FCC-203 | Rev 4 | MoC-004 (Cyclone Separator) |
| PID-FCC-204 | Rev 3 | MoC-005 (Catalyst Slide Valve) |
| PID-FCC-301 | Rev 2 | MoC-006 (Catalyst Stripper) |
| PID-FCC-403 | Rev 4 | MoC-007 (Flue Gas Expander) |
| PID-FCC-502 | Rev 3 | MoC-008 (Reflux Pump) |
| PID-FCC-LINE | Rev 2 | MoC-010 (Transfer Line) |

---

## Appendix: Key Design Decisions

### Why Neo4j?

The FCC Unit process topology is inherently a graph -- assets connect to other assets
through typed relationships with metadata. Neo4j Cypher makes it natural to express
multi-hop traversals like find all assets within 4 hops of R-201 via FEEDS or
CONTROLS_FLOW_TO relationships. A relational database would require complex recursive CTEs.

### Why Hybrid RAG (Vector + Graph)?

Vector search alone retrieves semantically similar MoCs but misses process topology context.
Graph traversal alone is precise but requires exact asset/MoC IDs. The hybrid approach:
- Vector search handles fuzzy, semantic queries (what happened with pump replacements?)
- Graph traversal provides precise, structured context (exact costs, relationships, paths)
- Together they give GPT-4o both breadth (similar cases) and depth (exact graph data)

### Why OpenAI Function Calling for the Agent?

The agent needs to decide dynamically which data to fetch based on the query.
OpenAI function calling provides a structured interface where GPT-4o can:
- Declare which tools it wants to call with typed arguments
- Receive structured JSON results
- Iterate until it has enough information
This is more reliable than prompt-based tool selection and handles multi-step reasoning naturally.

### Why Calibrated Heuristic + KNN for Cost Prediction?

With only 10 training samples, a pure ML model would overfit. The cost predictor uses:
- A calibrated heuristic model based on change type, asset criticality, and risk level
- A KNN model (k=3) that finds the most similar historical MoCs by feature vector
- A weighted blend of both, with the heuristic weighted higher for low-similarity cases
This gives reasonable predictions even for change types not well-represented in the dataset.

---

*End of Architecture Documentation*
## 5. Neo4j Knowledge Graph Schema

### Node Types (22 types)

| Node Type | Key Properties | Description |
|---|---|---|
| `MoC` | moc_id, title, change_type, actual_cost, actual_manhours, risk_category, hazop_required, pssr_required, incident_occurred, lessons_learned | Core Management of Change record |
| `Asset` | asset_id, name, equipment_type, criticality (1-5) | FCC Unit physical asset |
| `Hazard` | hazard_id, description, category, source | Process hazard identified by a MoC |
| `RiskAssessment` | risk_id, risk_category, overall_score, likelihood, risk_people, risk_asset, risk_community, risk_environment | Quantified risk evaluation |
| `LessonsLearned` | ll_id, text | Captured lesson from MoC implementation |
| `Personnel` | person_id, role, department | Approver or reviewer |
| `Incident` | incident_id, name, description, outcome | Implementation incident record |
| `HAZOP` | hazop_id, name, required, reason | Hazard and Operability Study requirement |
| `PSSR` | pssr_id, name, required, reason | Pre-Startup Safety Review requirement |
| `Parameter` | param_id, parameter_name, old_value, new_value, threshold | Process parameter change record |
| `WorkOrder` | wo_id, title, work_type, status, planned_duration, actual_duration, estimated_cost, actual_cost, delay_reason | Maintenance work order |
| `MaintenanceActivity` | activity_id, title, safety_req | Individual maintenance task |
| `ImplementationOutcome` | outcome_id, result, description | MoC implementation result |
| `ApprovalStage` | stage_id, order, stage, role, timestamp | One stage in the 5-stage approval workflow |
| `FailureMode` | fm_id, mode, consequence, likelihood, description | Equipment failure mode |
| `PIDDocument` | pid_ref, version | Piping and Instrumentation Diagram reference |
| `Area` | area_id, name | Plant area (e.g. Reactor Section, Regeneration Section) |
| `Department` | dept_id, name | Organisational department |
| `RiskScore` | score_id, overall, category | Aggregated risk score node |
| `Plant` | plant_id, name | Refinery plant node |
| `ProcessUnit` | unit_id, name | FCC process unit grouping |
| `_GraphConfig` | config_id, version, seeded_at | Graph metadata and version tracking |

### Relationship Types (29 types)

| Relationship | From | To | Description |
|---|---|---|---|
| `TARGETS` | MoC | Asset | MoC targets a specific asset for change |
| `BELONGS_TO` | Asset | Area | Asset belongs to a plant area |
| `PART_OF` | Asset | ProcessUnit | Asset is part of a process unit |
| `UPSTREAM_OF` | Asset | Asset | Asset is upstream in the process flow |
| `DEPENDS_ON` | Asset | Asset | Asset has a functional dependency |
| `IMPACTS` | Asset | Asset | Asset directly impacts another |
| `CONTROLS_FLOW_TO` | Asset | Asset | Asset controls flow to another (valve/controller) |
| `FEEDS` | Asset | Asset | Asset feeds material/energy to another |
| `CONNECTS` | Asset | Asset | Physical connection between assets |
| `SHUTS_DOWN` | Asset | Asset | ESD system shuts down an asset |
| `IDENTIFIES` | MoC | Hazard | MoC identifies a process hazard |
| `REQUIRES` | MoC | RiskAssessment | MoC requires a risk assessment |
| `EVALUATES` | RiskAssessment | Hazard | Risk assessment evaluates a hazard |
| `SCORED_AS` | RiskAssessment | RiskScore | Risk assessment produces a score |
| `APPROVED_BY` | MoC | Personnel | MoC is approved by a person |
| `GENERATES` | MoC | WorkOrder | MoC generates a work order |
| `EXECUTED_ON` | WorkOrder | Asset | Work order is executed on an asset |
| `PERFORMED_BY` | WorkOrder | Department | Work order is performed by a department |
| `RESULTS_IN` | MoC | ImplementationOutcome | MoC results in an implementation outcome |
| `RELATED_TO` | Incident | MoC | Incident is related to a MoC |
| `GENERATED_LESSON` | MoC | LessonsLearned | MoC generated a lesson learned |
| `REQUIRES_HAZOP` | MoC | HAZOP | MoC requires a HAZOP study |
| `REQUIRES_PSSR` | MoC | PSSR | MoC requires a PSSR |
| `CHANGES_PARAMETER` | MoC | Parameter | MoC changes a process parameter |
| `HAS_PARAMETER` | Asset | Parameter | Asset has an operating parameter |
| `MANIFESTS_AS` | Hazard | FailureMode | Hazard manifests as a failure mode |
| `INCLUDES_ACTIVITY` | WorkOrder | MaintenanceActivity | Work order includes a maintenance activity |
| `REFERENCES_PID` | MoC | PIDDocument | MoC references a P&ID document |
| `LOCATED_IN` | MoC | Area | MoC is located in a plant area |

### 5-Stage Approval Workflow

Every MoC passes through five approval stages, encoded as `ApprovalStage` nodes:

| Stage | Name | Assigned Roles |
|---|---|---|
| 1 | Change Identification | Initiating Engineer / Technician |
| 2 | Screening | Operations Supervisor / Unit Superintendent |
| 3 | Risk Assessment | Process Safety Engineer / HSE Engineer / Mechanical Integrity Engineer |
| 4 | Implementation Planning | Maintenance Manager / Instrumentation Engineer / Process Engineer |
| 5 | Final Approval | Safety Manager / Process Safety Manager / HSE Manager / Maintenance Manager |

---

## 6. FCC Unit Process Topology

The FCC Unit contains **14 primary process assets** (plus 8 supporting assets) connected in a directed graph.
The topology is stored in Neo4j and queried by the connectivity and propagation modules.

### Primary Asset List

| Asset ID | Name | Equipment Type | Criticality |
|---|---|---|---|
| P-101 | Feed Pump | Centrifugal Pump | 4 |
| FV-103 | Feed Control Valve | Control Valve | 3 |
| R-201 | Riser Reactor | Reactor | 5 |
| C-203 | Cyclone Separator | Separator | 4 |
| SV-204 | Catalyst Slide Valve | Slide Valve | 5 |
| S-301 | Catalyst Stripper | Stripper | 4 |
| RG-401 | Regenerator Vessel | Regenerator | 5 |
| EX-403 | Flue Gas Expander | Expander/Turbine | 3 |
| CTL-205 | Catalyst Transfer Line | Transfer Line | 5 |
| F-501 | Main Fractionator | Distillation Column | 5 |
| WGC-401 | Wet Gas Compressor | Compressor | 5 |
| P-502 | Reflux Pump | Centrifugal Pump | 4 |
| K-402 | Air Blower | Blower | 4 |
| ESD-SYS | Emergency Shutdown System | Safety System | 5 |

### Process Flow Topology (Directed Graph)

```
                    FCC Unit Process Flow

  [V-101 Feed Drum]
       |
       v FEEDS
  [P-101 Feed Pump] ----FEEDS----> [E-102 Feed Heater]
                                         |
                                         v CONTROLS_FLOW_TO
                                   [FV-103 Feed Control Valve]
                                         |
                                         v FEEDS
  [WGC-401 Wet Gas Compressor] ---> [R-201 Riser Reactor] <--- [CTL-205 Transfer Line]
  (recycle loop)                          |                           ^
                                    /-----+-----\                     |
                                   v             v                    |
                            [C-203 Cyclone]  [SV-204 Slide Valve]    |
                                   |               |                  |
                                   v               v                  |
                            [RG-401 Regenerator] <--+                 |
                                   |                                  |
                            /------+------\                           |
                           v              v                           |
                    [EX-403 Expander]  [CTL-205] ----------------------+
                           |
                           v FEEDS
                    [FG-404 Flue Gas Piping]

  [S-301 Catalyst Stripper] --FEEDS--> [RG-401]
  [K-402 Air Blower] --------FEEDS--> [RG-401]

  [R-201] --FEEDS--> [F-501 Fractionator]
                           |
                    /------+------\
                   v              v
           [WGC-401]          [P-502 Reflux Pump]
           (recycle)          [P-503 Rebooster Pump]
                              [P-504 Product Pump]

  [ESD-SYS] --SHUTS_DOWN--> R-201, SV-204, RG-401, EX-403, F-501
```

### Asset Connections Summary

| Source Asset | Relationship | Target Asset | Flow Type |
|---|---|---|---|
| P-101 (Feed Pump) | FEEDS | R-201 (Reactor) | Feed oil |
| FV-103 (Feed Control Valve) | CONTROLS_FLOW_TO | R-201 (Reactor) | Feed flow control |
| R-201 (Reactor) | FEEDS | C-203 (Cyclone Separator) | Reactor effluent |
| R-201 (Reactor) | CONTROLS_FLOW_TO | SV-204 (Catalyst Slide Valve) | Catalyst flow |
| C-203 (Cyclone) | FEEDS | RG-401 (Regenerator) | Spent catalyst |
| SV-204 (Slide Valve) | FEEDS | RG-401 (Regenerator) | Catalyst control |
| S-301 (Catalyst Stripper) | FEEDS | RG-401 (Regenerator) | Stripped catalyst |
| RG-401 (Regenerator) | FEEDS | EX-403 (Flue Gas Expander) | Flue gas energy |
| RG-401 (Regenerator) | CIRCULATES_TO | CTL-205 (Transfer Line) | Regenerated catalyst |
| CTL-205 (Transfer Line) | FEEDS | R-201 (Reactor) | Regenerated catalyst (loop) |
| R-201 (Reactor) | FEEDS | F-501 (Fractionator) | Reactor products |
| F-501 (Fractionator) | FEEDS | WGC-401 (Wet Gas Compressor) | Wet gas |
| F-501 (Fractionator) | FEEDS | P-502 (Reflux Pump) | Reflux liquid |
| WGC-401 (Wet Gas Compressor) | FEEDS | R-201 (Reactor) | Recycle gas |
| K-402 (Air Blower) | FEEDS | RG-401 (Regenerator) | Combustion air |
| ESD-SYS | SHUTS_DOWN | R-201, SV-204, RG-401, EX-403, F-501 | Emergency shutdown |

---

## 7. Hybrid RAG Pipeline

The `HybridRetriever` in `core/rag_pipeline.py` is the core retrieval engine.
It combines vector similarity search with graph traversal to produce rich, grounded context for GPT-4o.

### Pipeline Steps

#### Step 1: ChromaDB Vector Search

- Model: `text-embedding-3-small` (OpenAI)
- Similarity metric: cosine similarity
- Returns top-5 semantically similar MoC records
- Each hit includes: `moc_id`, `similarity score`, `text snippet`
- The vector store is pre-populated by `core/seed_neo4j.py` using all 10 MoC records

#### Step 2: Query Expansion (`_expand_query`)

Before embedding, the query is expanded using 30+ domain synonym mappings:

```python
SYNONYMS = {
    'reactor':    ['R-201', 'riser', 'FCC reactor', 'cracking unit'],
    'pump':       ['P-101', 'P-502', 'centrifugal pump', 'feed pump'],
    'valve':      ['FV-103', 'SV-204', 'control valve', 'slide valve'],
    'regenerator':['RG-401', 'regen', 'catalyst regeneration'],
    'fractionator':['F-501', 'main column', 'distillation'],
    'compressor': ['WGC-401', 'wet gas compressor'],
    # ... 25+ more mappings
}
```

#### Step 3: Neo4j Graph Traversal

When an `asset_id` is resolved, the retriever runs four parallel graph queries:

1. **`get_enriched_impact_chain(asset_id, depth=4)`** — traverses 7 relationship types
   (`UPSTREAM_OF`, `DEPENDS_ON`, `IMPACTS`, `CONTROLS_FLOW_TO`, `FEEDS`, `CONNECTS`, `CIRCULATES_TO`)
   up to depth 4, returning each downstream node with:
   - `node_id`, `node_name`, `node_type`
   - `hop_distance`, `criticality`
   - `relationship_chain` (list of rel types along the path)
   - `area`, `active_moc_count`

2. **`get_full_connectivity_map(asset_id)`** — returns all direct upstream and downstream
   neighbours with relationship types and flow metadata

3. **`get_hazards_for_asset(asset_id)`** — all hazards linked via MoC -> IDENTIFIES -> Hazard

4. **`get_historical_incidents(asset_id)`** — incidents linked via Incident -> RELATED_TO -> MoC -> TARGETS -> Asset

#### Step 4: Context Formatting

The `format_context_for_prompt()` method assembles all retrieved data into structured text sections:

```
DIRECT MoC RECORD:          <- Most specific, always first
  MoC ID | Title | Change Type | Asset
  Risk | Cost | Manhours | HAZOP | PSSR
  Hazards | Incident | Lesson | Parameter change

WORK ORDERS:                 <- Planned vs actual hours and costs

PARAMETER CHANGE:            <- Old value -> new value (threshold)

SEMANTICALLY SIMILAR MoCs:  <- Top-3 vector hits with similarity scores

ENRICHED ASSET IMPACT CHAIN: <- Direct (1 hop) and indirect (2+ hops)
  Ranked by criticality/hop_distance
  Each node: asset_id, name, criticality, relationship chain, area

PROCESS CONNECTIVITY MAP:    <- Upstream and downstream with rel types

HAZARDS:                     <- With failure modes and risk scores

HISTORICAL INCIDENTS:        <- Past incidents with outcomes

LESSONS LEARNED:             <- Captured lessons with recommendations
```

#### Step 5: GPT-4o Synthesis

The formatted context is injected into the `SYSTEM_PROMPT` template and sent to GPT-4o with:
- `temperature=0.1` (low randomness for factual grounding)
- Strict rules: cite MoC IDs, asset IDs, costs, risk scores
- Mandatory markdown formatting (headings, tables, bullet lists)
- No generic advice — every answer anchored to retrieved data

### RAG Pipeline Class Diagram

```
RAGPipeline
  +-- HybridRetriever
  |     +-- VectorStore (ChromaDB + text-embedding-3-small)
  |     +-- Neo4jClient (50+ Cypher query methods)
  |     +-- retrieve(query, asset_id, moc_id) -> context dict
  |     +-- format_context_for_prompt(context) -> str
  +-- LLM (OpenAI GPT-4o wrapper)
  +-- run(query, prompt_template, ...) -> str
  +-- get_raw_context(query, ...) -> dict
```

---

## 8. MoCBot - Conversational AI

MoCBot is the conversational interface in `modules/nlp_chatbot.py`.
It routes every user message through a 20-intent classification system before
fetching targeted graph data and generating a grounded response.

### Intent Categories (20 intents)

| Intent | Trigger Keywords | Graph Augmentation |
|---|---|---|
| `moc_lookup` | moc-0, tell me about moc, details of | HAZOP/PSSR status, approval stages, parameter changes, direct impacts |
| `asset_history` | history of, past changes to, changes on | All MoCs targeting the asset |
| `risk_query` | risk, hazard, hazop, pssr, danger, impact | Risk assessments, hazards, HAZOP/PSSR nodes |
| `cost_query` | cost, price, budget, how much, predict cost | Cost data from MoC records, ML prediction |
| `downtime_query` | downtime, how long, manhours, planned vs actual | Work order analytics, propagation data |
| `approval_query` | approve, approver, sign off, who needs, stage | ApprovalStage nodes, Personnel roles |
| `lessons_query` | lesson, went wrong, failure, incident, near miss | LessonsLearned nodes, Incident records |
| `impact_query` | impact, downstream, upstream, connected, propagate | Full connectivity map, enriched chain, downtime propagation |
| `parameter_query` | setpoint, temperature, pressure, threshold, margin | Parameter nodes, threshold checks |
| `wo_query` | work order, wo-, maintenance, planned vs actual | WorkOrder nodes with overrun analysis |
| `pid_query` | pid, p&id, pid-fcc, drawing, document reference | PIDDocument nodes (short-circuit bypass) |
| `new_moc_query` | start a new moc, initiate moc, required fields | Smart form guidance |
| `checklist_query` | checklist, commissioning, verify after, close out | Implementation verification steps |
| `comparison_query` | compare, vs, versus, which is higher | Multi-MoC context fetch |
| `risk_score_filter` | risk score >=, high risk mocs, score above | get_mocs_by_risk_score() |
| `concept_search` | find mocs, similar mocs, mocs involving | get_mocs_by_concept() |
| `training_query` | training, procedure update, operator training | get_mocs_requiring_training() |
| `threshold_check` | exceed, above limit, design limit, escalation | Parameter threshold comparison |
| `failure_mode` | failure mode, equipment failure, manifests as | FailureMode nodes via Hazard |
| `general` | (fallback) | Broad vector search only |

### Key Methods

#### `_intent_augment(intent, message, asset_id, moc_id)`

Fetches targeted graph data based on the detected intent. Examples:
- `moc_lookup`: fetches HAZOP/PSSR status, approval stages, parameter changes, direct process impacts
- `impact_query`: fetches full connectivity map, enriched impact chain, downtime propagation
- `wo_query`: fetches work order analytics with planned vs actual overrun
- `parameter_query`: fetches parameter thresholds and computes margin to design limit

#### `_broad_query_augment(intent, message)`

Handles dataset-wide queries that don't target a specific asset/MoC:
- HAZOP/PSSR summary across all 10 MoCs
- All incidents and rework records
- Cost overview sorted by actual cost
- Risk score filtering (e.g. all MoCs with risk >= 12)
- P&ID reference lookup
- Concept search across all MoC titles and descriptions
- Training/procedure update queries
- Planned vs actual work order analytics

#### PID Short-Circuit

When `intent == 'pid_query'`, MoCBot bypasses the full RAG pipeline and performs a direct
Neo4j lookup via `get_mocs_by_pid()`. This avoids LLM noise for exact P&ID reference queries.
The PID number is normalised to `PID-FCC-xxx` format before querying.

#### Natural Language Asset Resolution

The `_extract_asset_id()` function maps 40+ natural language names to asset IDs:

```python
ASSET_NAME_MAP = {
    'reactor':          'R-201',
    'riser':            'R-201',
    'feed pump':        'P-101',
    'slide valve':      'SV-204',
    'regenerator':      'RG-401',
    'fractionator':     'F-501',
    'transfer line':    'CTL-205',
    'wet gas compressor': 'WGC-401',
    # ... 30+ more mappings
}
```

#### `SimpleMemory(k=8)`

Maintains a rolling window of the last 8 conversation turns using a `deque`.
History is formatted as `User: ... / MoCBot: ...` pairs and prepended to each LLM call.

#### Agent Mode

When agent mode is enabled in the UI, the chat request is routed to `POST /api/agent`
instead of `POST /api/chat`. The `MoCAgent` class handles the request using OpenAI
function calling (see Section 11).

---
## 9. Enhancement 1: Process Asset Connectivity Modelling

Enhancement 1 adds deep process topology awareness to the platform.
Four new Neo4j query methods expose the full FCC Unit connectivity graph to all modules.

### `get_full_connectivity_map(asset_id)`

Returns all direct upstream and downstream neighbours of an asset with:
- `asset_id`, `name`, `equipment_type`, `criticality`
- `rel_type` — the relationship type (FEEDS, CONTROLS_FLOW_TO, etc.)
- `flow_type` — the flow medium (catalyst, feed oil, flue gas, etc.)
- `direction` — upstream or downstream

Used by: MoCBot `impact_query` augmentation, RAG pipeline context formatting,
Process Intelligence tab connectivity panel.

### `get_enriched_impact_chain(asset_id, depth=4)`

Traverses 7 relationship types up to depth 4 and returns every reachable downstream asset:

```cypher
MATCH path = (src:Asset {asset_id: $asset_id})
             -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|FEEDS|CONNECTS|CIRCULATES_TO*1..4]->
             (b:Asset)
RETURN DISTINCT b.asset_id, b.name, b.equipment_type, b.criticality,
       length(path) AS hop_distance,
       [rel IN relationships(path) | type(rel)] AS relationship_chain,
       [rel IN relationships(path) | rel.flow_type] AS flow_types
ORDER BY hop_distance, b.criticality DESC
```

Each result node includes `relationship_chain` — the exact sequence of relationship types
from source to target, enabling precise impact path explanation.

### `get_asset_connectivity_score(asset_id)`

Computes a weighted connectivity score for an asset:

| Factor | Weight | Description |
|---|---|---|
| Criticality | x10 | Asset criticality rating (1-5) |
| Downstream connections | x5 | Number of assets this asset feeds into |
| Upstream connections | x3 | Number of assets that feed into this asset |
| Active MoCs | x4 | Number of MoC records targeting this asset |
| Hazards | x6 | Number of hazards identified for this asset |
| ESD shutdown target | x15 | Whether ESD-SYS shuts down this asset |

Higher score = more critical node in the process network.
Used by the Process Intelligence tab to rank assets by network importance.

### `get_process_flow_topology()`

Returns the complete FCC Unit directed graph as a list of edges:

```python
{
    'source_id': 'P-101',
    'source_name': 'Feed Pump',
    'rel_type': 'FEEDS',
    'target_id': 'R-201',
    'target_name': 'Riser Reactor',
    'flow_type': 'feed_oil',
    'source_criticality': 4,
    'target_criticality': 5,
}
```

Used by: MoCAgent `get_process_topology` tool, KnowledgeGraph.tsx force-directed visualisation.

### Integration with MoCBot

When `intent == 'impact_query'`, `_intent_augment()` calls all four methods and prepends
the results to the RAG context as structured sections:

```
DOWNSTREAM CONNECTIONS FROM {asset_id} (direct):
  -> R-201 (Riser Reactor) | rel=FEEDS | flow=feed_oil | crit=5
  -> FV-103 (Feed Control Valve) | rel=CONTROLS_FLOW_TO | crit=3

UPSTREAM CONNECTIONS:
  ^ V-101 (Feed Surge Drum) | rel=FEEDS | crit=3

CONNECTIVITY SCORE: 87 (criticality=40, downstream=25, upstream=9, MoCs=8, hazards=0, ESD=0)

DOWNTIME PROPAGATION (24h source):
  1. R-201 (Riser Reactor): 20.4h | coupling=0.85 | High risk
  2. F-501 (Fractionator): 12.2h | coupling=0.51 | Medium risk
```

---

## 10. Enhancement 2: Dynamic Downtime Propagation

The `DowntimePropagator` class in `core/downtime_propagator.py` models how downtime
at one asset propagates through the FCC Unit process topology to downstream assets.

### Coupling Coefficients

Each relationship type has a coupling coefficient representing how much of the upstream
downtime propagates through that connection:

| Relationship Type | Coupling Coefficient | Rationale |
|---|---|---|
| SHUTS_DOWN | 0.95 | ESD shutdown — near-total coupling |
| FEEDS | 0.85 | Direct material/energy flow — very high coupling |
| CONTROLS_FLOW_TO | 0.80 | Control dependency — high coupling |
| CIRCULATES_TO | 0.75 | Catalyst circulation — high coupling |
| UPSTREAM_OF | 0.65 | Generic upstream — moderate-high coupling |
| IMPACTS | 0.60 | Explicit impact relationship |
| DEPENDS_ON | 0.50 | Functional dependency — moderate coupling |
| CONNECTS | 0.40 | Physical connection — lower coupling |

### Hop Decay Factor

Each additional hop reduces propagation by a decay factor of **0.70**:

```
Hop 1: coupling x 0.70^0 = coupling x 1.00
Hop 2: coupling x 0.70^1 = coupling x 0.70
Hop 3: coupling x 0.70^2 = coupling x 0.49
Hop 4: coupling x 0.70^3 = coupling x 0.34
```

### Criticality Amplifiers

High-criticality assets amplify the propagated downtime they receive:

| Criticality | Amplifier | Effect |
|---|---|---|
| 5 (Critical) | x1.20 | 20% amplification |
| 4 (High) | x1.05 | 5% amplification |
| 3 (Medium) | x0.90 | 10% reduction |
| 2 (Low) | x0.75 | 25% reduction |
| 1 (Minimal) | x0.60 | 40% reduction |

### Propagation Formula

```
propagated_hours = source_hours x coupling_factor x criticality_amplifier

where:
  coupling_factor = product of (COUPLING_COEFFICIENTS[rel] x HOP_DECAY^i)
                    for each relationship in the path
  criticality_amplifier = CRITICALITY_AMPLIFIER[target_criticality]
```

### `propagate(source_asset_id, source_downtime_hours, max_depth=4)`

Main propagation method. Returns a `PropagationResult` containing:

```python
PropagationResult(
    source_asset_id='P-101',
    source_asset_name='Feed Pump',
    source_downtime=24.0,
    total_affected=8,
    total_propagated_hours=142.3,
    affected_assets=[
        PropagatedDowntime(
            asset_id='R-201',
            propagated_hours=20.4,
            confidence_low=14.3,
            confidence_high=26.5,
            coupling_factor=0.850,
            hop_distance=1,
            risk_level='High',
            relationship_chain=['FEEDS'],
        ),
        # ... more assets ranked by propagated_hours
    ],
    summary='Downtime propagation from P-101 ...'
)
```

### `propagate_from_moc(moc_id)`

Convenience method that:
1. Fetches the MoC's target asset and actual manhours from Neo4j
2. Uses `actual_manhours` (or `estimated_manhours` as fallback) as `source_downtime_hours`
3. Calls `propagate()` and returns the full `PropagationResult`

Used by: `GET /api/downtime/moc/{moc_id}` endpoint.

### `get_propagation_matrix()`

Computes a risk matrix for all high-criticality assets (criticality >= 4):
- Uses a standard 24-hour source downtime for comparison
- Returns each asset's total propagated hours and top affected asset
- Sorted by total propagated hours descending
- Used by the Process Intelligence tab propagation matrix view

### Confidence Intervals

Each `PropagatedDowntime` includes an 80% confidence interval:
- Direct connections (1 hop): +/- 30%
- Indirect connections (2+ hops): +/- 50%

### Risk Classification

| Risk Level | Condition |
|---|---|
| Critical | propagated_hours x criticality >= 200 |
| High | propagated_hours x criticality >= 80 |
| Medium | propagated_hours x criticality >= 30 |
| Low | propagated_hours x criticality < 30 |

### Integration

- **MoCBot**: `impact_query` augmentation calls `propagate()` and prepends ranked results to context
- **Process Intelligence Tab**: Right panel shows propagation results as a ranked table
- **API**: `POST /api/downtime/propagate`, `GET /api/downtime/matrix`, `GET /api/downtime/moc/{moc_id}`

---

## 11. Enhancement 3: Agent-Based Execution

The `MoCAgent` class in `core/moc_agent.py` implements an OpenAI function-calling agent
for advanced multi-step reasoning over the FCC Unit knowledge graph.

### Agent Architecture

```
User Query
    |
    v
MoCAgent.run()
    |
    v
[Iteration Loop - max 6 iterations]
    |
    +-- GPT-4o: Analyse query, decide which tools to call
    |
    +-- Tool calls (parallel):
    |     get_moc_detail | get_asset_connectivity | propagate_downtime
    |     search_similar_mocs | get_impact_chain | get_risk_assessment
    |     get_process_topology | get_connectivity_score
    |     get_work_orders | get_hazards_for_asset
    |
    +-- Tool results appended to message history
    |
    +-- GPT-4o: Synthesise results or call more tools
    |
    v
Final Answer (when no more tool calls needed)
    |
    v
Return: {response, tool_calls_made, iterations, context_used}
```

### 10 Agent Tools

| Tool | Arguments | Returns | Use Case |
|---|---|---|---|
| `get_moc_detail` | moc_id | Full MoC record with risk, costs, hazards, WOs | MoC-specific queries |
| `get_asset_connectivity` | asset_id | Full connectivity map (upstream + downstream) | Impact analysis |
| `propagate_downtime` | asset_id, downtime_hours | PropagationResult with ranked affected assets | Downtime impact queries |
| `search_similar_mocs` | query, top_k | Top-k semantically similar MoC records | Historical precedent search |
| `get_impact_chain` | asset_id, depth | Enriched impact chain with relationship types | Deep impact tracing |
| `get_risk_assessment` | moc_id | Risk scores, HAZOP/PSSR outcomes | Risk queries |
| `get_process_topology` | (none) | Complete FCC directed graph (50 edges) | Topology analysis |
| `get_connectivity_score` | asset_id | Weighted connectivity score | Network criticality ranking |
| `get_work_orders` | moc_id | Work orders with planned vs actual | Maintenance analytics |
| `get_hazards_for_asset` | asset_id | Hazards with failure modes and risk scores | Safety analysis |

### Reasoning Loop

1. **Analyse**: GPT-4o receives the user query and decides which tools to call first
2. **Call tools**: One or more tools are called in parallel
3. **Observe**: Tool results are appended to the message history
4. **Iterate**: GPT-4o decides whether to call more tools or generate a final answer
5. **Final answer**: When no more tool calls are needed, GPT-4o synthesises all results
6. **Max iterations**: If 6 iterations are reached, a final answer is forced

### Agent Mode in MoCBot UI

The MoCBot tab has an agent mode toggle. When enabled:
- Chat requests are routed to `POST /api/agent` instead of `POST /api/chat`
- The response includes `tool_calls_made` — a log of every tool call and its result
- The UI renders the tool call log below the response, showing:
  - Tool name and arguments
  - Result summary
  - Number of iterations

### Example Agent Trace

Query: *'What would happen if R-201 goes offline for 48 hours?'*

```
Iteration 1:
  Tool: propagate_downtime(asset_id='R-201', downtime_hours=48)
  Result: 12 assets affected, 847h total propagated downtime

Iteration 2:
  Tool: get_asset_connectivity(asset_id='R-201')
  Result: 4 downstream, 3 upstream connections

Iteration 3:
  Tool: get_hazards_for_asset(asset_id='R-201')
  Result: 2 hazards (thermal stress, catalyst circulation instability)

Final Answer: Structured markdown response citing all tool results
```

---

## 12. API Endpoints

All endpoints are defined in `api/main.py`. The server runs on `http://localhost:8000`.

### Endpoint Reference

| Method | Path | Request Body | Response | Description |
|---|---|---|---|---|
| GET | `/api/health` | - | `{neo4j: {ok, message}, openai: {ok, message}}` | Service health check |
| GET | `/api/assets` | - | `[{id, name, type, criticality, area}]` | All FCC Unit assets |
| GET | `/api/mocs` | - | `[{moc_id, title, change_type, cost, manhours, asset_id}]` | All MoC records |
| POST | `/api/forms/prefill` | `{change_type, asset_id, description}` | `{suggestions, similar_mocs}` | AI form prefill |
| POST | `/api/risk/analyse` | `{change_type, asset_id, description}` | Risk analysis result | Risk & impact analysis |
| POST | `/api/cost/predict` | `{change_type, asset_id, asset_category, risk_level, description}` | `{predicted_cost, predicted_downtime, confidence}` | ML cost prediction |
| POST | `/api/chat` | `{message, asset_id?}` | `{response, intent, asset_id_used, moc_id_used, vector_hits}` | MoCBot chat |
| POST | `/api/chat/reset` | - | `{ok: true}` | Reset conversation memory |
| POST | `/api/graph/context` | `{query, asset_id?, moc_id?}` | Raw RAG context dict | Debug: raw retrieval context |
| GET | `/api/topology` | - | `{edges, edge_count}` | Full FCC process topology |
| POST | `/api/connectivity` | `{asset_id}` | `{connectivity, score}` | Asset connectivity map + score |
| GET | `/api/assets/connectivity` | - | `[{asset_id, name, criticality, connectivity_score, ...}]` | All assets with scores |
| POST | `/api/downtime/propagate` | `{asset_id, downtime_hours, max_depth?}` | PropagationResult | Downtime propagation |
| GET | `/api/downtime/matrix` | - | `{matrix, count}` | Propagation risk matrix |
| GET | `/api/downtime/moc/{moc_id}` | - | PropagationResult | Propagate from MoC manhours |
| POST | `/api/agent` | `{query, max_iterations?}` | `{response, tool_calls_made, iterations, context_used}` | Agent-based reasoning |

### Request/Response Models

```python
class FormRequest(BaseModel):
    change_type: str
    asset_id: str
    description: str

class ChatRequest(BaseModel):
    message: str
    asset_id: Optional[str] = None

class DowntimePropagationRequest(BaseModel):
    asset_id: str
    downtime_hours: float = 24.0
    max_depth: int = 4

class AgentRequest(BaseModel):
    query: str
    max_iterations: int = 6
```

### CORS Configuration

The API allows requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:5174` (Vite alternate)
- `http://localhost:3000` (Create React App)

---
## 5. Neo4j Knowledge Graph Schema

### Node Types (22 types)

| Node Type | Key Properties | Description |
|---|---|---|
| `MoC` | moc_id, title, change_type, actual_cost, actual_manhours, risk_category, hazop_required, pssr_required, incident_occurred, lessons_learned | Core Management of Change record |
| `Asset` | asset_id, name, equipment_type, criticality (1-5) | FCC Unit physical asset |
| `Hazard` | hazard_id, description, category, source | Process hazard identified by a MoC |
| `RiskAssessment` | risk_id, risk_category, overall_score, likelihood, risk_people, risk_asset, risk_community, risk_environment | Quantified risk evaluation |
| `LessonsLearned` | ll_id, text | Captured lesson from MoC implementation |
| `Personnel` | person_id, role, department | Approver or reviewer |
| `Incident` | incident_id, name, description, outcome | Implementation incident record |
| `HAZOP` | hazop_id, name, required, reason | Hazard and Operability Study requirement |
| `PSSR` | pssr_id, name, required, reason | Pre-Startup Safety Review requirement |
| `Parameter` | param_id, parameter_name, old_value, new_value, threshold | Process parameter change record |
| `WorkOrder` | wo_id, title, work_type, status, planned_duration, actual_duration, estimated_cost, actual_cost, delay_reason | Maintenance work order |
| `MaintenanceActivity` | activity_id, title, safety_req | Individual maintenance task |
| `ImplementationOutcome` | outcome_id, result, description | MoC implementation result |
| `ApprovalStage` | stage_id, order, stage, role, timestamp | One stage in the 5-stage approval workflow |
| `FailureMode` | fm_id, mode, consequence, likelihood, description | Equipment failure mode |
| `PIDDocument` | pid_ref, version | Piping and Instrumentation Diagram reference |
| `Area` | area_id, name | Plant area (e.g. Reactor Section, Regeneration Section) |
| `Department` | dept_id, name | Organisational department |
| `RiskScore` | score_id, overall, category | Aggregated risk score node |
| `Plant` | plant_id, name | Refinery plant node |
| `ProcessUnit` | unit_id, name | FCC process unit grouping |
| `_GraphConfig` | config_id, version, seeded_at | Graph metadata and version tracking |

### Relationship Types (29 types)

| Relationship | From | To | Description |
|---|---|---|---|
| `TARGETS` | MoC | Asset | MoC targets a specific asset for change |
| `BELONGS_TO` | Asset | Area | Asset belongs to a plant area |
| `PART_OF` | Asset | ProcessUnit | Asset is part of a process unit |
| `UPSTREAM_OF` | Asset | Asset | Asset is upstream in the process flow |
| `DEPENDS_ON` | Asset | Asset | Asset has a functional dependency |
| `IMPACTS` | Asset | Asset | Asset directly impacts another |
| `CONTROLS_FLOW_TO` | Asset | Asset | Asset controls flow to another (valve/controller) |
| `FEEDS` | Asset | Asset | Asset feeds material/energy to another |
| `CONNECTS` | Asset | Asset | Physical connection between assets |
| `SHUTS_DOWN` | Asset | Asset | ESD system shuts down an asset |
| `IDENTIFIES` | MoC | Hazard | MoC identifies a process hazard |
| `REQUIRES` | MoC | RiskAssessment | MoC requires a risk assessment |
| `EVALUATES` | RiskAssessment | Hazard | Risk assessment evaluates a hazard |
| `SCORED_AS` | RiskAssessment | RiskScore | Risk assessment produces a score |
| `APPROVED_BY` | MoC | Personnel | MoC is approved by a person |
| `GENERATES` | MoC | WorkOrder | MoC generates a work order |
| `EXECUTED_ON` | WorkOrder | Asset | Work order is executed on an asset |
| `PERFORMED_BY` | WorkOrder | Department | Work order is performed by a department |
| `RESULTS_IN` | MoC | ImplementationOutcome | MoC results in an implementation outcome |
| `RELATED_TO` | Incident | MoC | Incident is related to a MoC |
| `GENERATED_LESSON` | MoC | LessonsLearned | MoC generated a lesson learned |
| `REQUIRES_HAZOP` | MoC | HAZOP | MoC requires a HAZOP study |
| `REQUIRES_PSSR` | MoC | PSSR | MoC requires a PSSR |
| `CHANGES_PARAMETER` | MoC | Parameter | MoC changes a process parameter |
| `HAS_PARAMETER` | Asset | Parameter | Asset has an operating parameter |
| `MANIFESTS_AS` | Hazard | FailureMode | Hazard manifests as a failure mode |
| `INCLUDES_ACTIVITY` | WorkOrder | MaintenanceActivity | Work order includes a maintenance activity |
| `REFERENCES_PID` | MoC | PIDDocument | MoC references a P&ID document |
| `LOCATED_IN` | MoC | Area | MoC is located in a plant area |

### 5-Stage Approval Workflow

Every MoC passes through five approval stages, encoded as `ApprovalStage` nodes:

| Stage | Name | Assigned Roles |
|---|---|---|
| 1 | Change Identification | Initiating Engineer / Technician |
| 2 | Screening | Operations Supervisor / Unit Superintendent |
| 3 | Risk Assessment | Process Safety Engineer / HSE Engineer / Mechanical Integrity Engineer |
| 4 | Implementation Planning | Maintenance Manager / Instrumentation Engineer / Process Engineer |
| 5 | Final Approval | Safety Manager / Process Safety Manager / HSE Manager / Maintenance Manager |

---

## 6. FCC Unit Process Topology

The FCC Unit contains **14 primary process assets** (plus 8 supporting assets) connected in a directed graph.
The topology is stored in Neo4j and queried by the connectivity and propagation modules.

### Primary Asset List

| Asset ID | Name | Equipment Type | Criticality |
|---|---|---|---|
| P-101 | Feed Pump | Centrifugal Pump | 4 |
| FV-103 | Feed Control Valve | Control Valve | 3 |
| R-201 | Riser Reactor | Reactor | 5 |
| C-203 | Cyclone Separator | Separator | 4 |
| SV-204 | Catalyst Slide Valve | Slide Valve | 5 |
| S-301 | Catalyst Stripper | Stripper | 4 |
| RG-401 | Regenerator Vessel | Regenerator | 5 |
| EX-403 | Flue Gas Expander | Expander/Turbine | 3 |
| CTL-205 | Catalyst Transfer Line | Transfer Line | 5 |
| F-501 | Main Fractionator | Distillation Column | 5 |
| WGC-401 | Wet Gas Compressor | Compressor | 5 |
| P-502 | Reflux Pump | Centrifugal Pump | 4 |
| K-402 | Air Blower | Blower | 4 |
| ESD-SYS | Emergency Shutdown System | Safety System | 5 |

### Process Flow Topology (Directed Graph)

```
                    FCC Unit Process Flow

  [V-101 Feed Drum]
       |
       v FEEDS
  [P-101 Feed Pump] ----FEEDS----> [E-102 Feed Heater]
                                         |
                                         v CONTROLS_FLOW_TO
                                   [FV-103 Feed Control Valve]
                                         |
                                         v FEEDS
  [WGC-401 Wet Gas Compressor] ---> [R-201 Riser Reactor] <--- [CTL-205 Transfer Line]
  (recycle loop)                          |                           ^
                                    /-----+-----\                     |
                                   v             v                    |
                            [C-203 Cyclone]  [SV-204 Slide Valve]    |
                                   |               |                  |
                                   v               v                  |
                            [RG-401 Regenerator] <--+                 |
                                   |                                  |
                            /------+------\                           |
                           v              v                           |
                    [EX-403 Expander]  [CTL-205] ----------------------+
                           |
                           v FEEDS
                    [FG-404 Flue Gas Piping]

  [S-301 Catalyst Stripper] --FEEDS--> [RG-401]
  [K-402 Air Blower] --------FEEDS--> [RG-401]

  [R-201] --FEEDS--> [F-501 Fractionator]
                           |
                    /------+------\
                   v              v
           [WGC-401]          [P-502 Reflux Pump]
           (recycle)          [P-503 Rebooster Pump]
                              [P-504 Product Pump]

  [ESD-SYS] --SHUTS_DOWN--> R-201, SV-204, RG-401, EX-403, F-501
```

### Asset Connections Summary

| Source Asset | Relationship | Target Asset | Flow Type |
|---|---|---|---|
| P-101 (Feed Pump) | FEEDS | R-201 (Reactor) | Feed oil |
| FV-103 (Feed Control Valve) | CONTROLS_FLOW_TO | R-201 (Reactor) | Feed flow control |
| R-201 (Reactor) | FEEDS | C-203 (Cyclone Separator) | Reactor effluent |
| R-201 (Reactor) | CONTROLS_FLOW_TO | SV-204 (Catalyst Slide Valve) | Catalyst flow |
| C-203 (Cyclone) | FEEDS | RG-401 (Regenerator) | Spent catalyst |
| SV-204 (Slide Valve) | FEEDS | RG-401 (Regenerator) | Catalyst control |
| S-301 (Catalyst Stripper) | FEEDS | RG-401 (Regenerator) | Stripped catalyst |
| RG-401 (Regenerator) | FEEDS | EX-403 (Flue Gas Expander) | Flue gas energy |
| RG-401 (Regenerator) | CIRCULATES_TO | CTL-205 (Transfer Line) | Regenerated catalyst |
| CTL-205 (Transfer Line) | FEEDS | R-201 (Reactor) | Regenerated catalyst (loop) |
| R-201 (Reactor) | FEEDS | F-501 (Fractionator) | Reactor products |
| F-501 (Fractionator) | FEEDS | WGC-401 (Wet Gas Compressor) | Wet gas |
| F-501 (Fractionator) | FEEDS | P-502 (Reflux Pump) | Reflux liquid |
| WGC-401 (Wet Gas Compressor) | FEEDS | R-201 (Reactor) | Recycle gas |
| K-402 (Air Blower) | FEEDS | RG-401 (Regenerator) | Combustion air |
| ESD-SYS | SHUTS_DOWN | R-201, SV-204, RG-401, EX-403, F-501 | Emergency shutdown |

---

## 7. Hybrid RAG Pipeline

The `HybridRetriever` in `core/rag_pipeline.py` is the core retrieval engine.
It combines vector similarity search with graph traversal to produce rich, grounded context for GPT-4o.

### Pipeline Steps

#### Step 1: ChromaDB Vector Search

- Model: `text-embedding-3-small` (OpenAI)
- Similarity metric: cosine similarity
- Returns top-5 semantically similar MoC records
- Each hit includes: `moc_id`, `similarity score`, `text snippet`
- The vector store is pre-populated by `core/seed_neo4j.py` using all 10 MoC records

#### Step 2: Query Expansion (`_expand_query`)

Before embedding, the query is expanded using 30+ domain synonym mappings:

```python
SYNONYMS = {
    'reactor':    ['R-201', 'riser', 'FCC reactor', 'cracking unit'],
    'pump':       ['P-101', 'P-502', 'centrifugal pump', 'feed pump'],
    'valve':      ['FV-103', 'SV-204', 'control valve', 'slide valve'],
    'regenerator':['RG-401', 'regen', 'catalyst regeneration'],
    'fractionator':['F-501', 'main column', 'distillation'],
    'compressor': ['WGC-401', 'wet gas compressor'],
    # ... 25+ more mappings
}
```

#### Step 3: Neo4j Graph Traversal

When an `asset_id` is resolved, the retriever runs four parallel graph queries:

1. **`get_enriched_impact_chain(asset_id, depth=4)`** — traverses 7 relationship types
   (`UPSTREAM_OF`, `DEPENDS_ON`, `IMPACTS`, `CONTROLS_FLOW_TO`, `FEEDS`, `CONNECTS`, `CIRCULATES_TO`)
   up to depth 4, returning each downstream node with:
   - `node_id`, `node_name`, `node_type`
   - `hop_distance`, `criticality`
   - `relationship_chain` (list of rel types along the path)
   - `area`, `active_moc_count`

2. **`get_full_connectivity_map(asset_id)`** — returns all direct upstream and downstream
   neighbours with relationship types and flow metadata

3. **`get_hazards_for_asset(asset_id)`** — all hazards linked via MoC -> IDENTIFIES -> Hazard

4. **`get_historical_incidents(asset_id)`** — incidents linked via Incident -> RELATED_TO -> MoC -> TARGETS -> Asset

#### Step 4: Context Formatting

The `format_context_for_prompt()` method assembles all retrieved data into structured text sections:

```
DIRECT MoC RECORD:          <- Most specific, always first
  MoC ID | Title | Change Type | Asset
  Risk | Cost | Manhours | HAZOP | PSSR
  Hazards | Incident | Lesson | Parameter change

WORK ORDERS:                 <- Planned vs actual hours and costs

PARAMETER CHANGE:            <- Old value -> new value (threshold)

SEMANTICALLY SIMILAR MoCs:  <- Top-3 vector hits with similarity scores

ENRICHED ASSET IMPACT CHAIN: <- Direct (1 hop) and indirect (2+ hops)
  Ranked by criticality/hop_distance
  Each node: asset_id, name, criticality, relationship chain, area

PROCESS CONNECTIVITY MAP:    <- Upstream and downstream with rel types

HAZARDS:                     <- With failure modes and risk scores

HISTORICAL INCIDENTS:        <- Past incidents with outcomes

LESSONS LEARNED:             <- Captured lessons with recommendations
```

#### Step 5: GPT-4o Synthesis

The formatted context is injected into the `SYSTEM_PROMPT` template and sent to GPT-4o with:
- `temperature=0.1` (low randomness for factual grounding)
- Strict rules: cite MoC IDs, asset IDs, costs, risk scores
- Mandatory markdown formatting (headings, tables, bullet lists)
- No generic advice — every answer anchored to retrieved data

### RAG Pipeline Class Diagram

```
RAGPipeline
  +-- HybridRetriever
  |     +-- VectorStore (ChromaDB + text-embedding-3-small)
  |     +-- Neo4jClient (50+ Cypher query methods)
  |     +-- retrieve(query, asset_id, moc_id) -> context dict
  |     +-- format_context_for_prompt(context) -> str
  +-- LLM (OpenAI GPT-4o wrapper)
  +-- run(query, prompt_template, ...) -> str
  +-- get_raw_context(query, ...) -> dict
```

---

## 8. MoCBot - Conversational AI

MoCBot is the conversational interface in `modules/nlp_chatbot.py`.
It routes every user message through a 20-intent classification system before
fetching targeted graph data and generating a grounded response.

### Intent Categories (20 intents)

| Intent | Trigger Keywords | Graph Augmentation |
|---|---|---|
| `moc_lookup` | moc-0, tell me about moc, details of | HAZOP/PSSR status, approval stages, parameter changes, direct impacts |
| `asset_history` | history of, past changes to, changes on | All MoCs targeting the asset |
| `risk_query` | risk, hazard, hazop, pssr, danger, impact | Risk assessments, hazards, HAZOP/PSSR nodes |
| `cost_query` | cost, price, budget, how much, predict cost | Cost data from MoC records, ML prediction |
| `downtime_query` | downtime, how long, manhours, planned vs actual | Work order analytics, propagation data |
| `approval_query` | approve, approver, sign off, who needs, stage | ApprovalStage nodes, Personnel roles |
| `lessons_query` | lesson, went wrong, failure, incident, near miss | LessonsLearned nodes, Incident records |
| `impact_query` | impact, downstream, upstream, connected, propagate | Full connectivity map, enriched chain, downtime propagation |
| `parameter_query` | setpoint, temperature, pressure, threshold, margin | Parameter nodes, threshold checks |
| `wo_query` | work order, wo-, maintenance, planned vs actual | WorkOrder nodes with overrun analysis |
| `pid_query` | pid, p&id, pid-fcc, drawing, document reference | PIDDocument nodes (short-circuit bypass) |
| `new_moc_query` | start a new moc, initiate moc, required fields | Smart form guidance |
| `checklist_query` | checklist, commissioning, verify after, close out | Implementation verification steps |
| `comparison_query` | compare, vs, versus, which is higher | Multi-MoC context fetch |
| `risk_score_filter` | risk score >=, high risk mocs, score above | get_mocs_by_risk_score() |
| `concept_search` | find mocs, similar mocs, mocs involving | get_mocs_by_concept() |
| `training_query` | training, procedure update, operator training | get_mocs_requiring_training() |
| `threshold_check` | exceed, above limit, design limit, escalation | Parameter threshold comparison |
| `failure_mode` | failure mode, equipment failure, manifests as | FailureMode nodes via Hazard |
| `general` | (fallback) | Broad vector search only |

### Key Methods

#### `_intent_augment(intent, message, asset_id, moc_id)`

Fetches targeted graph data based on the detected intent. Examples:
- `moc_lookup`: fetches HAZOP/PSSR status, approval stages, parameter changes, direct process impacts
- `impact_query`: fetches full connectivity map, enriched impact chain, downtime propagation
- `wo_query`: fetches work order analytics with planned vs actual overrun
- `parameter_query`: fetches parameter thresholds and computes margin to design limit

#### `_broad_query_augment(intent, message)`

Handles dataset-wide queries that don't target a specific asset/MoC:
- HAZOP/PSSR summary across all 10 MoCs
- All incidents and rework records
- Cost overview sorted by actual cost
- Risk score filtering (e.g. all MoCs with risk >= 12)
- P&ID reference lookup
- Concept search across all MoC titles and descriptions
- Training/procedure update queries
- Planned vs actual work order analytics

#### PID Short-Circuit

When `intent == 'pid_query'`, MoCBot bypasses the full RAG pipeline and performs a direct
Neo4j lookup via `get_mocs_by_pid()`. This avoids LLM noise for exact P&ID reference queries.
The PID number is normalised to `PID-FCC-xxx` format before querying.

#### Natural Language Asset Resolution

The `_extract_asset_id()` function maps 40+ natural language names to asset IDs:

```python
ASSET_NAME_MAP = {
    'reactor':          'R-201',
    'riser':            'R-201',
    'feed pump':        'P-101',
    'slide valve':      'SV-204',
    'regenerator':      'RG-401',
    'fractionator':     'F-501',
    'transfer line':    'CTL-205',
    'wet gas compressor': 'WGC-401',
    # ... 30+ more mappings
}
```

#### `SimpleMemory(k=8)`

Maintains a rolling window of the last 8 conversation turns using a `deque`.
History is formatted as `User: ... / MoCBot: ...` pairs and prepended to each LLM call.

#### Agent Mode

When agent mode is enabled in the UI, the chat request is routed to `POST /api/agent`
instead of `POST /api/chat`. The `MoCAgent` class handles the request using OpenAI
function calling (see Section 11).

---
