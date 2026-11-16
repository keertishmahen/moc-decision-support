"""
modules.agents — multi-agent change assessment with a trust and provenance layer.

A deterministic Supervisor runs specialist agents (each wrapping existing platform code)
in stages, a rule-based Verification agent checks the language-model agents, and every
output is recorded with its producing agent, source kind, evidence and gaps
(see core.provenance and docs/design-docs/multi-agent-trust.md).
"""
from .base import ChangeRequest, Toolbox
from .registry import registry
from .supervisor import Supervisor

__all__ = ["ChangeRequest", "Supervisor", "Toolbox", "registry"]
