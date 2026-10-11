#!/bin/bash
# Azure App Service entrypoint — finds Oryx wwwroot or /tmp extract, then starts gunicorn.
set -e
log() { echo "[moc-run] $*" >&2; }

candidates=()
if [ -d /home/site/wwwroot ]; then candidates+=(/home/site/wwwroot); fi
# shellcheck disable=SC2046
for d in $(ls -d /tmp/8dee* 2>/dev/null || true); do candidates+=("$d"); done
# Directory containing this script (when shipped inside the extract/tarball)
here="$(cd "$(dirname "$0")" && pwd)"
candidates+=("$here")

APP_ROOT=""
for d in "${candidates[@]}"; do
  [ -n "$d" ] || continue
  if [ -d "$d/api" ] && { [ -x "$d/antenv/bin/gunicorn" ] || [ -x "$d/antenv/bin/python" ]; }; then
    APP_ROOT="$d"
    break
  fi
done

if [ -z "$APP_ROOT" ]; then
  for d in "${candidates[@]}"; do
    [ -n "$d" ] && [ -x "$d/antenv/bin/gunicorn" ] || continue
    APP_ROOT="$d"
    break
  done
fi

if [ -z "$APP_ROOT" ]; then
  log "FATAL: no app root with antenv. wwwroot listing:"
  ls -la /home/site/wwwroot 2>&1 | head -40 >&2 || true
  log "tmp:"
  ls -la /tmp 2>&1 | head -30 >&2 || true
  exit 1
fi

log "APP_ROOT=$APP_ROOT api=$([ -d "$APP_ROOT/api" ] && echo yes || echo no) gunicorn=$([ -x "$APP_ROOT/antenv/bin/gunicorn" ] && echo yes || echo no)"

export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/home/site/wwwroot/chroma_db}"
mkdir -p "$CHROMA_PERSIST_DIR"
if [ "$APP_ROOT" != /home/site/wwwroot ] && [ -d "$APP_ROOT/chroma_db" ]; then
  cp -a "$APP_ROOT/chroma_db/." "$CHROMA_PERSIST_DIR/" 2>/dev/null || true
fi

# App source must be on PYTHONPATH — Oryx often only adds antenv site-packages.
export PYTHONPATH="$APP_ROOT${PYTHONPATH:+:$PYTHONPATH}"
cd "$APP_ROOT"

if [ -x "$APP_ROOT/antenv/bin/gunicorn" ]; then
  GUNI="$APP_ROOT/antenv/bin/gunicorn"
elif [ -x "$APP_ROOT/antenv/bin/python" ]; then
  exec "$APP_ROOT/antenv/bin/python" -m gunicorn \
    --bind=0.0.0.0:8000 --timeout 120 -w 1 \
    -k uvicorn.workers.UvicornWorker --chdir "$APP_ROOT" \
    --pythonpath "$APP_ROOT" \
    api.main:app
else
  log "FATAL: antenv python/gunicorn missing under $APP_ROOT"
  exit 1
fi

# Prefer app:app (installed/root app.py) then api.main:app
TARGET="api.main:app"
if [ -f "$APP_ROOT/app.py" ]; then
  TARGET="app:app"
fi

log "exec $GUNI $TARGET"
exec "$GUNI" \
  --bind=0.0.0.0:8000 \
  --timeout 120 \
  -w 1 \
  -k uvicorn.workers.UvicornWorker \
  --chdir "$APP_ROOT" \
  --pythonpath "$APP_ROOT" \
  "$TARGET"
