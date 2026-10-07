"""SCOPE Runtime - Structured Constraint-Oriented Pruning Protocol.

Core data models and runtime infrastructure for constraint-governed recursive admissibility.
"""

from .models import (
    CandidateStructure,
    Constraint,
    Falsifier,
    ResolutionLevel,
    ScopeRun,
    EliminationTrace,
    EliminationCategory,
)
from .runtime import ScopeRuntime, ScopeExecutionResult
from .dre import DRECalculator, DREResult

__version__ = "0.1.0"
__author__ = "Mitchell D. McPhetridge"

__all__ = [
    "CandidateStructure",
    "Constraint",
    "Falsifier",
    "ResolutionLevel",
    "ScopeRun",
    "EliminationTrace",
    "EliminationCategory",
    "ScopeRuntime",
    "ScopeExecutionResult",
    "DRECalculator",
    "DREResult",
]
