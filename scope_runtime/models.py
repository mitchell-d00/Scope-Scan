"""SCOPE data models and core structures."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


class ResolutionLevel(Enum):
    """Hierarchical resolution levels for SCOPE runs."""
    STRATEGIC = "strategic"
    TECHNICAL = "technical"
    OPERATIONAL = "operational"
    THEORETICAL = "theoretical"
    LOCAL = "local"


class EliminationCategory(Enum):
    """Three forms of elimination tracked by SCOPE."""
    EPISTEMIC = "epistemic"        # Reduction of viable candidates
    OPERATIONAL = "operational"    # Reduction of failure exposure
    GOVERNANCE = "governance"      # Reduction of oversight complexity


@dataclass
class CandidateStructure:
    """A candidate structure under evaluation."""
    name: str
    description: str
    key_assumptions: List[str]
    dependencies: List[str]
    operational_distinctions: List[str]
    eliminated: bool = False
    elimination_reason: Optional[str] = None
    
    def assumption_count(self) -> int:
        """Return number of assumptions."""
        return len(self.key_assumptions)
    
    def dependency_count(self) -> int:
        """Return number of dependencies."""
        return len(self.dependencies)


@dataclass
class Constraint:
    """An explicit operational constraint."""
    name: str
    description: str
    critical: bool
    verifiable: bool
    domain: Optional[str] = None
    violated: bool = False
    violation_evidence: Optional[str] = None


@dataclass
class Falsifier:
    """A falsifier for testing candidate viability.

    `test_method` remains the human-readable description (for reporting).
    `check` is the actual executable predicate: given a candidate, return
    True if the falsifier TRIGGERS (i.e. the candidate fails this check).
    If `check` is None, the falsifier is descriptive-only and cannot
    contribute to elimination -- this is intentional so an unwired
    falsifier can't silently pretend to have been applied.
    """
    name: str
    description: str
    test_method: str
    domain: str
    criticality: float  # 0.0 to 1.0
    check: Optional[Callable[["CandidateStructure"], bool]] = None
    applied: bool = False
    result: Optional[bool] = None  # True if falsifier triggered
    evidence: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the check and its yield weight at construction."""
        if self.check is not None and not callable(self.check):
            raise TypeError("check must be callable or None")
        if not 0.0 <= self.criticality <= 1.0:
            raise ValueError("criticality must be between 0.0 and 1.0")

    def is_executable(self) -> bool:
        return self.check is not None


@dataclass
class EliminationTrace:
    """Record of a single elimination event."""
    timestamp: datetime
    candidate_name: str
    category: EliminationCategory
    reason: str
    falsifier_applied: Optional[str] = None
    constraint_violated: Optional[str] = None
    epistemic_yield: float = 0.0  # Reduction in candidate count
    operational_yield: float = 0.0  # Improvement in failure detection
    governance_yield: float = 0.0  # Reduction in overhead
    
    def total_yield(self) -> float:
        """Sum of all elimination yields."""
        return self.epistemic_yield + self.operational_yield + self.governance_yield


@dataclass
class ScopeRun:
    """Complete SCOPE run specification."""
    host_domain: str
    resolution_level: ResolutionLevel
    candidate_claim_set: List[CandidateStructure]
    explicit_constraints: List[Constraint]
    dependency_structure: Dict[str, List[str]]
    domain_indexed_falsifiers: List[Falsifier]
    operational_discrimination_metric: str
    governance_recursion_cost: float  # 0.0 to 1.0
    scoring_procedure: str
    termination_trigger: str
    decommissioning_condition: str
    
    # Optional fields
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def total_candidates(self) -> int:
        """Return total candidate count."""
        return len(self.candidate_claim_set)
    
    def total_constraints(self) -> int:
        """Return total constraint count."""
        return len(self.explicit_constraints)
    
    def total_falsifiers(self) -> int:
        """Return total falsifier count."""
        return len(self.domain_indexed_falsifiers)
    
    def critical_constraints(self) -> List[Constraint]:
        """Return only critical constraints."""
        return [c for c in self.explicit_constraints if c.critical]
    
    def get_falsifiers_for_domain(self, domain: str) -> List[Falsifier]:
        """Get all falsifiers for a specific domain."""
        return [f for f in self.domain_indexed_falsifiers if f.domain == domain]

