"""
tests/llm/test_gateway.py — the OpenAI gateway: typed errors, schema validation, one repair attempt.

Offline: a fake client stands in for the OpenAI SDK.
"""
import json
from types import SimpleNamespace

import pytest

from core.llm import (
    LLMGateway,
    LLMInvalidOutput,
    LLMUnavailable,
    validate_against_schema,
)

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["rating", "risks"],
    "properties": {
        "rating": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
}


def reply(content, refusal=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal, tool_calls=None))])


class FakeClient:
    """Returns queued replies (or raises queued exceptions) and records every call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def gateway(*outcomes):
    client = FakeClient(*outcomes)
    return LLMGateway(client=client, model="test-model"), client


class TestText:
    def test_returns_the_text(self):
        g, client = gateway(reply("hello"))
        assert g.complete([{"role": "user", "content": "hi"}]) == "hello"
        assert client.calls[0]["model"] == "test-model"

    def test_empty_answer_is_invalid_output_not_none(self):
        g, _ = gateway(reply(None))
        with pytest.raises(LLMInvalidOutput):
            g.complete([{"role": "user", "content": "hi"}])

    def test_sdk_failure_becomes_llm_unavailable_without_leaking_details(self):
        g, _ = gateway(TimeoutError("connect to api.openai.com timed out, key sk-secret"))
        with pytest.raises(LLMUnavailable) as e:
            g.complete([{"role": "user", "content": "hi"}])
        assert "sk-secret" not in str(e.value)


class TestStructured:
    def test_valid_reply_is_returned_as_a_dict(self):
        g, client = gateway(reply(json.dumps({"rating": "High", "risks": ["a"]})))
        assert g.complete_json([{"role": "user", "content": "x"}], SCHEMA, "risk") == {"rating": "High", "risks": ["a"]}
        fmt = client.calls[0]["response_format"]
        assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True

    def test_invalid_enum_triggers_one_repair_attempt(self):
        g, client = gateway(reply(json.dumps({"rating": "Severe", "risks": []})),
                            reply(json.dumps({"rating": "High", "risks": []})))
        assert g.complete_json([{"role": "user", "content": "x"}], SCHEMA, "risk")["rating"] == "High"
        assert len(client.calls) == 2
        assert "did not match the required structure" in client.calls[1]["messages"][-1]["content"]

    def test_two_bad_replies_raise_invalid_output(self):
        g, client = gateway(reply("not json"), reply(json.dumps({"rating": "High"})))
        with pytest.raises(LLMInvalidOutput):
            g.complete_json([{"role": "user", "content": "x"}], SCHEMA, "risk")
        assert len(client.calls) == 2

    def test_extra_validation_is_applied(self):
        g, _ = gateway(reply(json.dumps({"rating": "High", "risks": []})), reply(json.dumps({"rating": "High", "risks": []})))
        with pytest.raises(LLMInvalidOutput):
            g.complete_json([{"role": "user", "content": "x"}], SCHEMA, "risk", validate=lambda d: ["needs a risk"])

    def test_refusal_is_invalid_output(self):
        g, _ = gateway(reply(None, refusal="I can't help with that"))
        with pytest.raises(LLMInvalidOutput):
            g.complete_json([{"role": "user", "content": "x"}], SCHEMA, "risk")


class TestSchemaValidator:
    def test_reports_missing_wrong_type_and_enum(self):
        problems = validate_against_schema({"rating": "Severe", "risks": "none"}, SCHEMA)
        assert any("not one of" in p for p in problems)
        assert any("expected array" in p for p in problems)
        assert validate_against_schema({"risks": []}, SCHEMA) == ["$.rating: missing"]

    def test_valid_data_has_no_problems(self):
        assert validate_against_schema({"rating": "Low", "risks": ["x"]}, SCHEMA) == []

    def test_shipped_schemas_are_strict_format_compatible(self):
        """OpenAI strict structured outputs need every property required and no extra properties."""
        from modules.risk_engine import RISK_SCHEMA
        from modules.smart_forms import FORM_SCHEMA

        def check(schema, path="$"):
            if schema.get("type") == "object":
                assert schema.get("additionalProperties") is False, path
                assert sorted(schema["required"]) == sorted(schema["properties"]), path
                for key, sub in schema["properties"].items():
                    check(sub, f"{path}.{key}")
            if schema.get("type") == "array":
                check(schema["items"], f"{path}[]")

        check(FORM_SCHEMA)
        check(RISK_SCHEMA)
