"""
core/llm/gateway.py — the one place the application talks to the OpenAI chat API.

Why a gateway: every call gets the same timeout, bounded retries and typed errors, and
structured replies are validated against a JSON schema before any caller sees them.
Callers catch `LLMError` and degrade (graph evidence only) instead of failing the request.

    gateway = get_gateway()
    text = gateway.complete(messages)                               # str, never None
    data = gateway.complete_json(messages, schema, name="risk")     # dict matching the schema
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2          # SDK-level retries with backoff on connection errors, 408, 429 and 5xx
DEFAULT_TEMPERATURE = 0.1


class LLMError(Exception):
    """Base class: the AI service could not produce a usable answer."""


class LLMUnavailable(LLMError):
    """The service was unreachable, timed out, was rate-limited or rejected the credentials."""


class LLMInvalidOutput(LLMError):
    """The service answered, but the answer was empty or did not match the required structure."""


def validate_against_schema(data: Any, schema: Dict, path: str = "$") -> List[str]:
    """Check `data` against the subset of JSON Schema this application uses.

    Supported: type (object, array, string, number, integer, boolean), properties, required,
    items, enum. Returns a list of problems; empty means valid.
    """
    problems: List[str] = []
    expected = schema.get("type")
    checks = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    }
    if expected in checks and not checks[expected](data):
        return [f"{path}: expected {expected}, got {type(data).__name__}"]
    if "enum" in schema and data not in schema["enum"]:
        problems.append(f"{path}: {data!r} is not one of {schema['enum']}")
    if expected == "object":
        for key in schema.get("required", []):
            if key not in data:
                problems.append(f"{path}.{key}: missing")
        for key, sub in schema.get("properties", {}).items():
            if key in data:
                problems.extend(validate_against_schema(data[key], sub, f"{path}.{key}"))
    if expected == "array" and "items" in schema:
        for i, item in enumerate(data):
            problems.extend(validate_against_schema(item, schema["items"], f"{path}[{i}]"))
    return problems


class LLMGateway:
    def __init__(self, client: Any = None, model: Optional[str] = None,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS, max_retries: int = DEFAULT_MAX_RETRIES):
        self._client = client
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._lock = threading.Lock()

    # ── client ──────────────────────────────────────────────────────────────────────────────────
    @property
    def model(self) -> str:
        if self._model is None:
            from core.config import OPENAI_MODEL
            self._model = OPENAI_MODEL
        return self._model

    def _get_client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from openai import OpenAI

                    from core.config import OPENAI_API_KEY
                    if not OPENAI_API_KEY:
                        raise LLMUnavailable("OPENAI_API_KEY is not configured.")
                    self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=self._timeout,
                                          max_retries=self._max_retries)
        return self._client

    def _create(self, **kwargs):
        """One chat-completions call; SDK and transport failures become LLMUnavailable."""
        try:
            return self._get_client().chat.completions.create(model=self.model, **kwargs)
        except LLMError:
            raise
        except Exception as exc:                                   # noqa: BLE001 — openai.* and httpx.* errors
            log.warning("OpenAI call failed: %s: %s", type(exc).__name__, str(exc)[:300])
            raise LLMUnavailable(f"AI service call failed ({type(exc).__name__}).") from exc

    # ── text ────────────────────────────────────────────────────────────────────────────────────
    def complete(self, messages: List[Dict], temperature: float = DEFAULT_TEMPERATURE) -> str:
        resp = self._create(messages=messages, temperature=temperature)
        content = resp.choices[0].message.content if resp.choices else None
        if not content or not content.strip():
            raise LLMInvalidOutput("AI service returned an empty answer.")
        return content

    # ── structured ──────────────────────────────────────────────────────────────────────────────
    def complete_json(self, messages: List[Dict], schema: Dict, name: str,
                      validate: Optional[Callable[[Dict], List[str]]] = None,
                      temperature: float = DEFAULT_TEMPERATURE) -> Dict:
        """Return a dict that satisfies `schema` (and the optional extra `validate` check).

        The schema is sent to the API as a strict structured-output format and checked again
        locally. One repair attempt is made with the problems fed back; then LLMInvalidOutput.
        """
        response_format = {"type": "json_schema",
                           "json_schema": {"name": name, "strict": True, "schema": schema}}
        attempt_messages = list(messages)
        problems: List[str] = []
        for attempt in range(2):
            resp = self._create(messages=attempt_messages, temperature=temperature,
                                response_format=response_format)
            message = resp.choices[0].message if resp.choices else None
            content = getattr(message, "content", None)
            if getattr(message, "refusal", None):
                raise LLMInvalidOutput("AI service declined to answer.")
            try:
                data = json.loads(content or "")
            except (TypeError, ValueError):
                problems = ["reply was not valid JSON"]
            else:
                problems = validate_against_schema(data, schema)
                if not problems and validate is not None:
                    problems = list(validate(data))
                if not problems:
                    return data
            log.warning("Structured reply '%s' invalid (attempt %d): %s", name, attempt + 1, "; ".join(problems)[:300])
            attempt_messages = list(messages) + [
                {"role": "assistant", "content": content or ""},
                {"role": "user", "content": "Your reply did not match the required structure: "
                                            + "; ".join(problems)[:600] + ". Reply again with corrected JSON only."},
            ]
        raise LLMInvalidOutput(f"AI service reply for '{name}' did not match the required structure.")

    # ── tool calling (agent) ────────────────────────────────────────────────────────────────────
    def chat_raw(self, **kwargs):
        """Pass-through for tool-calling loops: returns the SDK response, with the same error mapping."""
        return self._create(**kwargs)


_gateway: Optional[LLMGateway] = None
_gateway_lock = threading.Lock()


def get_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        with _gateway_lock:
            if _gateway is None:
                _gateway = LLMGateway()
    return _gateway


def set_gateway(gateway: Optional[LLMGateway]) -> None:
    """Test hook: install a gateway built on a fake client (or None to reset)."""
    global _gateway
    _gateway = gateway
