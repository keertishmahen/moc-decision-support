# Multi-stage: build React SPA, then run FastAPI + ChromaDB + ML models.
FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist \
    CHROMA_PERSIST_DIR=/app/chroma_db \
    MODEL_DIR=/app/saved_models \
    PORT=8000 \
    WEBSITES_PORT=8000

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY core/ ./core/
COPY modules/ ./modules/
COPY saved_models/ ./saved_models/
COPY chroma_db/ ./chroma_db/
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Run as a non-root user; Chroma opens its sqlite file read-write.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/healthz')" || exit 1

# Render injects PORT; Azure and local runs fall back to 8000.
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
