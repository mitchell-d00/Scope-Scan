"""Dynamic Recursive Entropy (DRE) calculator.

Implements the core admissibility diagnostic from McPhetridge (2026):
"Using Recursive Entropy as a Tool to Break Recursive Entropy Loops"
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime
import math


@dataclass
class DREResult:
    """Results from a single DRE calculation."""
    timestamp: datetime
    delta_h: float  # Change in viable multiplicity
    viable_candidate_count: int
    new_falsifiers_count: int
    eliminative_work: float
    drift_detected: bool
    
    # Interval tracking
    interval_start: Optional[datetime] = None
    interval_end: Optional[datetime] = None
    interval_length: int = 0  # Number of iterations in interval
    
    # Diagnostic metadata
    multiplicity_trend: Optional[str] = None  # "contracting", "stable", "expanding"
    falsifier_production_rate: float = 0.0
    elimination_momentum: float = 0.0


class DRECalculator:
    """Calculates Dynamic Recursive Entropy for admissibility diagnostics.
    
    Core principle (McPhetridge 2026):
    Recursive continuation is non-admissible when:
    - ΔH ≥ 0 (viable multiplicity fails to contract)
    - AND F^new = 0 (no new executable falsifiers emerge)
    - AND E = 0 (eliminative work ceases)
    across a bounded interval [t-n, t].
    """
    
    def __init__(self, window_size: int = 5):
        """Initialize DRE calculator.
        
        Args:
            window_size: Number of iterations to track for drift detection.
        """
        if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size < 1:
            raise ValueError("window_size must be a positive integer")
        self.window_size = window_size
        self.history: List[DREResult] = []
    
    def calculate(
        self,
        viable_candidates: int,
        previous_viable_count: int,
        new_falsifiers: int,
        eliminative_work: float,
    ) -> DREResult:
        """Calculate DRE for current iteration.
        
        Args:
            viable_candidates: Current count of viable candidates.
            previous_viable_count: Previous iteration's viable candidate count.
            new_falsifiers: Count of newly produced falsifiers.
            eliminative_work: Total eliminative work in this iteration.
        
        Returns:
            DREResult with diagnostic information.
        """
        # Calculate ΔH (change in multiplicity)
        delta_h = viable_candidates - previous_viable_count
        
        # Determine multiplicity trend
        if delta_h < 0:
            trend = "contracting"
        elif delta_h == 0:
            trend = "stable"
        else:
            trend = "expanding"
        
        # Calculate falsifier production rate
        falsifier_rate = new_falsifiers / max(1, viable_candidates)
        
        # Check for drift condition
        drift_detected = self._check_drift_condition(delta_h, new_falsifiers, eliminative_work)
        
        result = DREResult(
            timestamp=datetime.now(),
            delta_h=delta_h,
            viable_candidate_count=viable_candidates,
            new_falsifiers_count=new_falsifiers,
            eliminative_work=eliminative_work,
            drift_detected=drift_detected,
            multiplicity_trend=trend,
            falsifier_production_rate=falsifier_rate,
        )
        
        self.history.append(result)
        return result
    
    def _check_drift_condition(self, delta_h: float, new_falsifiers: int, eliminative_work: float) -> bool:
        """Check if recursive drift condition is met.
        
        Drift detected when all three conditions hold across window:
        1. ΔH ≥ 0 (multiplicity not contracting)
        2. F^new = 0 (no new falsifiers)
        3. E ≈ 0 (minimal eliminative work)
        """
        if len(self.history) < self.window_size - 1:
            return False
        
        # Check last N iterations
        # Include the current observation: it has not yet been appended by calculate().
        recent = self.history[-(self.window_size - 1):] if self.window_size > 1 else []
        
        all_delta_h_non_negative = all(r.delta_h >= 0 for r in recent)
        all_no_falsifiers = all(r.new_falsifiers_count == 0 for r in recent)
        all_minimal_work = all(r.eliminative_work < 0.01 for r in recent)
        
        return (all_delta_h_non_negative and all_no_falsifiers and all_minimal_work
                and delta_h >= 0 and new_falsifiers == 0 and eliminative_work < 0.01)
    
    def check_admissibility(
        self,
        current_delta_h: float,
        current_falsifiers: int,
        current_work: float,
    ) -> Tuple[bool, str]:
        """Check if recursive continuation remains admissible.
        
        Evaluates a proposed current observation without adding it to history.

        Returns:
            (admissible: bool, reason: str)
        """
        if len(self.history) < self.window_size - 1:
            return True, "Insufficient history for drift detection"
        
        # Check drift condition
        if self._check_drift_condition(current_delta_h, current_falsifiers, current_work):
            return False, (
                f"Recursive drift detected: ΔH={current_delta_h} >= 0, "
                f"F^new={current_falsifiers}, E={current_work:.3f}"
            )
        
        return True, "Admissibility conditions satisfied"
    
    def get_window_summary(self) -> dict:
        """Get summary statistics for current window."""
        if not self.history:
            return {
                "window_size": self.window_size,
                "available_iterations": 0,
                "avg_delta_h": 0.0,
                "avg_falsifiers": 0,
                "avg_work": 0.0,
            }
        
        recent = self.history[-self.window_size:]
        
        return {
            "window_size": self.window_size,
            "available_iterations": len(recent),
            "avg_delta_h": sum(r.delta_h for r in recent) / len(recent),
            "avg_falsifiers": sum(r.new_falsifiers_count for r in recent) / len(recent),
            "avg_work": sum(r.eliminative_work for r in recent) / len(recent),
            "contraction_rate": sum(1 for r in recent if r.delta_h < 0) / len(recent),
        }

