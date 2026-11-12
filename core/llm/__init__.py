"""core.llm — the application's single gateway to the OpenAI API, plus safe prompt templating."""
from .gateway import (
    LLMError,
    LLMGateway,
    LLMInvalidOutput,
    LLMUnavailable,
    get_gateway,
    set_gateway,
    validate_against_schema,
)
from .prompting import USER_TEXT_NOTICE, fill, quote_user_text

__all__ = [
    "LLMError", "LLMGateway", "LLMInvalidOutput", "LLMUnavailable", "USER_TEXT_NOTICE", "fill",
    "get_gateway", "quote_user_text", "set_gateway", "validate_against_schema",
]
