"""
api/main.py  —  FastAPI backend for MoC Intelligence Platform
Run: uvicorn api.main:app --reload --port 8000
Production: serves frontend/dist + /api on the same origin.
"""
import core.sqlite_patch  # noqa: F401 — before chromadb import

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.config import FRONTEND_DIST

app = FastAPI(title="MoC Intelligence API", version="1.0.0")

_default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]
_extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy singletons ────────────────────────────────────────────────────────
_smart_forms = None
_risk_engine = None
_cost_predictor = None
_chatbot = None

def get_smart_forms():
    global _smart_forms
    if _smart_forms is None:
        from modules.smart_forms import SmartFormModule
        _smart_forms = SmartFormModule()
    return _smart_forms

def get_risk_engine():
    global _risk_engine
    if _risk_engine is None:
        from modules.risk_engine import RiskEngine
        _risk_engine = RiskEngine()
    return _risk_engine

def get_cost_predictor():
    global _cost_predictor
    if _cost_predictor is None:
        from modules.cost_predictor import CostPredictor
        _cost_predictor = CostPredictor()
    return _cost_predictor

def get_chatbot():
    global _chatbot
    if _chatbot is None:
        from modules.nlp_chatbot import MoCChatbot
        _chatbot = MoCChatbot()
    return _chatbot


def reset_chatbot():
    global _chatbot
    _chatbot = None


def _is_neo4j_connection_error(exc: Exception) -> bool:
    from core.neo4j_client import _is_transient
    return _is_transient(exc)

# ── Request models ─────────────────────────────────────────────────────────
class FormRequest(BaseModel):
    change_type: str
    asset_id: str
    description: str

class RiskRequest(BaseModel):
    change_type: str
    asset_id: str
    description: str

class CostRequest(BaseModel):
    change_type: str
    asset_id: str
    asset_category: str
    risk_level: str
    description: str

class ChatRequest(BaseModel):
    message: str
    asset_id: Optional[str] = None

class GraphContextRequest(BaseModel):
    query: str
    asset_id: Optional[str] = None
    moc_id: Optional[str] = None

# ── Enhancement request models ─────────────────────────────────────────────
class DowntimePropagationRequest(BaseModel):
    asset_id: str
    downtime_hours: float = 24.0
    max_depth: int = 4

class AgentRequest(BaseModel):
    query: str
    max_iterations: int = 6

class ConnectivityRequest(BaseModel):
    asset_id: str

# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/api/version")
def version():
    """Returns current code version to confirm deployment."""
    import modules.nlp_chatbot as m
    has_pid = hasattr(m.MoCChatbot, '_handle_pid_query')
    return {"pid_handler": has_pid, "version": "2.1.1-incident-fix"}

@app.get("/api/health")
def health():
    status = {"neo4j": {"ok": False, "message": "Not checked"},
              "openai": {"ok": False, "message": "Not checked"}}
    try:
        from core.neo4j_client import verify_neo4j_connectivity
        verify_neo4j_connectivity()
        status["neo4j"] = {"ok": True, "message": "Connected"}
    except Exception as e:
        status["neo4j"] = {"ok": False, "message": str(e)[:80]}
    try:
        from core.config import OPENAI_API_KEY, OPENAI_MODEL
        if not OPENAI_API_KEY:
            status["openai"] = {"ok": False, "message": "API key missing"}
        else:
            from openai import OpenAI
            OpenAI(api_key=OPENAI_API_KEY).models.retrieve(OPENAI_MODEL, timeout=8.0)
            status["openai"] = {"ok": True, "message": OPENAI_MODEL}
    except Exception as e:
        status["openai"] = {"ok": False, "message": str(e)[:80]}
    return status

@app.post("/api/forms/prefill")
def forms_prefill(req: FormRequest):
    try:
        m = get_smart_forms()
        suggestions = m.get_prefill_suggestions(req.change_type, req.asset_id, req.description)
        similar     = m.get_similar_mocs_summary(req.change_type, req.asset_id, req.description)
        return {"suggestions": suggestions, "similar_mocs": similar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/risk/analyse")
def risk_analyse(req: RiskRequest):
    try:
        return get_risk_engine().analyse(req.change_type, req.asset_id, req.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cost/predict")
def cost_predict(req: CostRequest):
    try:
        return get_cost_predictor().predict(
            req.change_type, req.asset_id, req.asset_category, req.risk_level, req.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        return get_chatbot().chat(req.message, asset_id=req.asset_id)
    except Exception as e:
        if _is_neo4j_connection_error(e):
            reset_chatbot()
            try:
                return get_chatbot().chat(req.message, asset_id=req.asset_id)
            except Exception as retry_exc:
                raise HTTPException(status_code=500, detail=str(retry_exc))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/reset")
def chat_reset():
    try:
        get_chatbot().reset_memory()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/graph/context")
def graph_context(req: GraphContextRequest):
    try:
        from core.rag_pipeline import RAGPipeline
        p = RAGPipeline()
        ctx = p.get_raw_context(req.query, asset_id=req.asset_id, moc_id=req.moc_id)
        # Serialise — convert any non-serialisable types
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [clean(i) for i in obj]
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            # Handle neo4j DateTime and other special types
            try:
                import json
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
        return clean(ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/assets")
def get_assets():
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient()
        assets = c.get_all_assets()
        c.close()
        return assets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mocs")
def get_mocs():
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient()
        mocs = c.get_all_mocs()
        c.close()
        return mocs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Enhancement 1: Process Asset Connectivity ──────────────────────────────

@app.get("/api/topology")
def get_topology():
    """Full FCC Unit process flow topology as directed edges."""
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient()
        topology = c.get_process_flow_topology()
        c.close()
        return {"edges": topology, "edge_count": len(topology)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connectivity")
def get_connectivity(req: ConnectivityRequest):
    """Full connectivity map for a specific asset."""
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient()
        result = c.get_full_connectivity_map(req.asset_id)
        score  = c.get_asset_connectivity_score(req.asset_id)
        c.close()
        if not result:
            raise HTTPException(status_code=404, detail=f"Asset {req.asset_id} not found")
        return {"connectivity": result, "score": score}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/connectivity")
def get_all_assets_connectivity():
    """All assets with connectivity scores for topology overview."""
    try:
        from core.neo4j_client import Neo4jClient
        c = Neo4jClient()
        assets = c.get_all_assets_with_connectivity()
        c.close()
        return assets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Enhancement 2: Dynamic Downtime Propagation ────────────────────────────

@app.post("/api/downtime/propagate")
def propagate_downtime(req: DowntimePropagationRequest):
    """
    Propagate downtime from a source asset through the process topology.
    Returns all downstream assets with estimated propagated downtime.
    """
    try:
        from core.downtime_propagator import DowntimePropagator, propagation_result_to_dict
        propagator = DowntimePropagator()
        result = propagator.propagate(
            source_asset_id=req.asset_id,
            source_downtime_hours=req.downtime_hours,
            max_depth=req.max_depth,
        )
        return propagation_result_to_dict(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/downtime/matrix")
def get_propagation_matrix():
    """
    Propagation matrix for all high-criticality assets.
    Shows which assets cause the most downstream downtime impact.
    """
    try:
        from core.downtime_propagator import DowntimePropagator
        propagator = DowntimePropagator()
        matrix = propagator.get_propagation_matrix()
        return {"matrix": matrix, "count": len(matrix)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/downtime/moc/{moc_id}")
def propagate_downtime_from_moc(moc_id: str):
    """Propagate downtime using a MoC's actual manhours as the source."""
    try:
        from core.downtime_propagator import DowntimePropagator, propagation_result_to_dict
        propagator = DowntimePropagator()
        result = propagator.propagate_from_moc(moc_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"MoC {moc_id} not found")
        return propagation_result_to_dict(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Enhancement 3: Agent-Based Execution ──────────────────────────────────

@app.post("/api/agent")
def run_agent(req: AgentRequest):
    """
    Run the MoCAgent for advanced multi-step reasoning.
    The agent uses tool calling to orchestrate graph queries,
    vector search, and downtime propagation before answering.
    """
    try:
        from core.moc_agent import run_agent as _run_agent
        result = _run_agent(req.query, max_iterations=req.max_iterations)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Production SPA (same-origin with /api) ─────────────────────────────────
_dist = FRONTEND_DIST
_index = os.path.join(_dist, "index.html")
if os.path.isdir(_dist) and os.path.isfile(_index):
    assets_dir = os.path.join(_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def spa_root():
        return FileResponse(_index)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        # Never shadow API routes (registered above).
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = os.path.join(_dist, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_index)
