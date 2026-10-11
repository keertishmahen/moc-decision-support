"""
core/config.py  — Central configuration, loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Neo4j ──────────────────────────────────────────────────────────────────
# Aura Free often exports NEO4J_USERNAME; accept that alias for NEO4J_USER.
NEO4J_URI      = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER     = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "")

# ── LLM ───────────────────────────────────────────────────────────────────
LLM_PROVIDER   = os.getenv("LLM_PROVIDER",  "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL",   "gpt-4o")

# ── Embeddings ────────────────────────────────────────────────────────────
RAG_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "openai")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── Vector store (ChromaDB) ───────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION  = os.getenv("CHROMA_COLLECTION", "moc_records")

# ── RAG retrieval ─────────────────────────────────────────────────────────
TOP_K_SIMILAR = 5
GRAPH_DEPTH   = 3

# ── ML models ─────────────────────────────────────────────────────────────
MODEL_DIR        = os.getenv("MODEL_DIR", "./saved_models")
COST_MODEL_PATH  = f"{MODEL_DIR}/cost_predictor.pkl"
DOWN_MODEL_PATH  = f"{MODEL_DIR}/downtime_predictor.pkl"
SCALER_PATH      = f"{MODEL_DIR}/feature_scaler.pkl"

# ── Frontend static (production) ──────────────────────────────────────────
FRONTEND_DIST = os.getenv(
    "FRONTEND_DIST",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist"),
)
