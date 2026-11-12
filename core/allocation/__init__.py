"""
core.allocation — Human–AI decision allocation for Management of Change.

A deterministic implementation of the framework in Parth Pandit Atiwadkar's MSc thesis
(Cranfield University, 2026): a change is characterised on eight categorical axes,
scored on Risk, Complexity, Uncertainty and Impact, and mapped to AI-led,
AI-supported or human-led control.

This package is pure domain logic: standard library only, no database, no network,
no LLM. That is enforced by tests/structure/test_architecture.py.
"""
from .engine import SelectionError, score, validate_selection
from .model import AllocationModel, ModelConfigError, default_model, load_model
from .types import Allocation, AllocationResult, Factor, Level

__all__ = [
    "Allocation", "AllocationModel", "AllocationResult", "Factor", "Level", "ModelConfigError",
    "SelectionError", "default_model", "load_model", "score", "validate_selection",
]
