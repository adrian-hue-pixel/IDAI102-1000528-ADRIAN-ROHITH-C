"""Cited carbon-model research. No network access or UI dependencies."""

from .model import comparison, estimate, factors, manifest, monthly, references
from .planner import counterexample, greedy, optimize

__all__ = [
    "comparison",
    "counterexample",
    "estimate",
    "factors",
    "greedy",
    "manifest",
    "monthly",
    "optimize",
    "references",
]
