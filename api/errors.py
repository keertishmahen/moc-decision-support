"""
api/errors.py — turn failures into honest HTTP responses.

    knowledge graph unreachable   -> 503  (retry later)
    AI service failed             -> 502  (upstream problem)
    bad request data              -> 422
    anything else                 -> 500  with a reference id, never the raw exception text

The detail sent to the client is a short, safe sentence. The full exception goes to the
server log together with the reference id, so a report from a user can be traced.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from core.allocation import SelectionError
from core.llm import LLMError, LLMInvalidOutput

log = logging.getLogger("moc.api")

GRAPH_DOWN = "The knowledge graph is temporarily unavailable. Please try again in a moment."
LLM_DOWN = "The AI service did not respond. Please try again in a moment."
LLM_BAD = "The AI service returned an answer that could not be used. Please try again."


def _is_graph_failure(exc: BaseException) -> bool:
    try:
        from neo4j.exceptions import DriverError, Neo4jError
        if isinstance(exc, (DriverError, Neo4jError)):
            return True
    except Exception:                                               # pragma: no cover — driver always installed
        pass
    try:
        from core.neo4j_client import _is_transient
        return _is_transient(exc)
    except Exception:                                               # pragma: no cover
        return False


def to_http_error(exc: BaseException) -> HTTPException:
    """Map an exception raised inside a route to the HTTPException the client should receive."""
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, SelectionError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, LLMInvalidOutput):
        log.warning("AI reply unusable: %s", exc)
        return HTTPException(status_code=502, detail=LLM_BAD)
    if isinstance(exc, LLMError):
        log.warning("AI service unavailable: %s", exc)
        return HTTPException(status_code=502, detail=LLM_DOWN)
    if _is_graph_failure(exc):
        log.warning("Knowledge graph unavailable: %s: %s", type(exc).__name__, str(exc)[:300])
        return HTTPException(status_code=503, detail=GRAPH_DOWN)
    ref = uuid.uuid4().hex[:8]
    log.error("Unhandled error [ref %s]", ref, exc_info=exc)
    return HTTPException(status_code=500, detail=f"Something went wrong on the server (reference {ref}).")


def json_safe(value: Any) -> Any:
    """Recursively convert driver types (Neo4j dates, sets, ...) into JSON-serialisable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:                                           # noqa: BLE001
            return str(value)
    return str(value)


def install_error_handlers(app: FastAPI) -> None:
    """Safety net for exceptions that escape a route (routes normally call to_http_error themselves)."""

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):        # noqa: ANN202
        http = to_http_error(exc)
        return JSONResponse(status_code=http.status_code, content={"detail": http.detail})
