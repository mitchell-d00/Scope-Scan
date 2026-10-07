"""SCOPE runtime execution engine."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import ScopeRun, EliminationTrace, EliminationCategory, CandidateStructure
from .dre import DRECalculator, DREResult


@dataclass
class ScopeExecutionResult:
    """Result of executing a SCOPE run."""
    scope_run: ScopeRun
    execution_started: datetime
    execution_completed: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Execution state
    iteration_count: int = 0
    final_viable_candidates: int = 0
    initial_candidate_count: int = 0
    
    # Traces and diagnostics
    elimination_traces: List[EliminationTrace] = field(default_factory=list)
    dre_history: List[DREResult] = field(default_factory=list)
    detected_failure_modes: List[str] = field(default_factory=list)
    execution_log: List[str] = field(default_factory=list)
    
    # Final state
    admissible: bool = True
    termination_reason: Optional[str] = None
    
    def add_log_entry(self, message: str) -> None:
        """Add entry to execution log."""
        timestamp = datetime.now().isoformat()
        self.execution_log.append(f"[{timestamp}] {message}")
    
    def add_elimination_trace(self, trace: EliminationTrace) -> None:
        """Record an elimination event."""
        self.elimination_traces.append(trace)
    
    def survival_rate(self) -> float:
        """Calculate candidate survival rate."""
        if self.initial_candidate_count == 0:
            return 0.0
        return self.final_viable_candidates / self.initial_candidate_count
    
    def elapsed_time(self) -> float:
        """Get execution duration in seconds."""
        if self.execution_completed:
            return (self.execution_completed - self.execution_started).total_seconds()
        return 0.0


class ScopeRuntime:
    """SCOPE protocol runtime executor."""
    
    def __init__(self, scope_run: ScopeRun):
        """Initialize SCOPE runtime.
        
        Args:
            scope_run: Specification for this SCOPE run.
        """
        self.scope_run = scope_run
        self.dre_calculator = DRECalculator(window_size=5)
        self.result = ScopeExecutionResult(
            scope_run=scope_run,
            execution_started=datetime.now(),
            initial_candidate_count=scope_run.total_candidates(),
        )

    @property
    def specification(self) -> ScopeRun:
        """Expose the run specification used by the documented API."""
        return self.scope_run
    
    def execute(self, max_iterations: int = 8) -> ScopeExecutionResult:
        """Execute SCOPE protocol as a real loop, matching the paper's own
        pseudocode: 'while EliminativeWorkExists(Graph): ...'.

        A single pass through Constrain/Pressure/Prune/Measure cannot,
        by construction, ever accumulate the DRE history window needed
        to detect drift (window_size=5). This loops the pressure/prune/
        measure cycle until either no further eliminative work occurs
        or max_iterations is hit.
        """
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1:
            raise ValueError("max_iterations must be a positive integer")
        self.result.add_log_entry(
            f"SCOPE execution started: {self.scope_run.host_domain}"
        )

        try:
            self._phase_constrain()

            previous_viable = sum(1 for c in self.scope_run.candidate_claim_set if not c.eliminated)

            for iteration in range(1, max_iterations + 1):
                self.result.iteration_count = iteration
                self.result.add_log_entry(f"--- Iteration {iteration} ---")

                applied_before = {id(f) for f in self.scope_run.domain_indexed_falsifiers if f.applied}
                newly_eliminated = self._phase_pressure_and_prune()
                new_falsifiers = sum(
                    1 for f in self.scope_run.domain_indexed_falsifiers
                    if f.applied and id(f) not in applied_before
                )

                viable_now = sum(
                    1 for c in self.scope_run.candidate_claim_set if not c.eliminated
                )

                self._phase_measure(
                    previous_viable=previous_viable,
                    viable_now=viable_now,
                    eliminated_this_round=newly_eliminated,
                    new_falsifiers=new_falsifiers,
                )

                previous_viable = viable_now

                if self.result.dre_history[-1].drift_detected:
                    break

                if newly_eliminated == 0:
                    self.result.add_log_entry(
                        "No eliminative work this iteration -- stopping loop."
                    )
                    break

            self._check_termination()

        except Exception as e:
            self.result.add_log_entry(f"Execution error: {str(e)}")
            self.result.admissible = False
            self.result.termination_reason = f"Execution error: {str(e)}"

        finally:
            self.result.execution_completed = datetime.now()
            self.result.duration_seconds = self.result.elapsed_time()
            self.result.final_viable_candidates = sum(
                1 for c in self.scope_run.candidate_claim_set if not c.eliminated
            )

        return self.result
    
    def _phase_constrain(self) -> None:
        """Constrain: Validate that constraints are satisfiable."""
        self.result.add_log_entry(
            f"Phase 1: CONSTRAIN - Validating {len(self.scope_run.explicit_constraints)} constraints"
        )
        
        critical = self.scope_run.critical_constraints()
        self.result.add_log_entry(
            f"  - Critical constraints: {len(critical)}"
        )
        self.result.add_log_entry(
            f"  - Total candidates: {len(self.scope_run.candidate_claim_set)}"
        )
        violated = [c.name for c in critical if c.violated]
        if violated:
            raise ValueError("Critical constraints already violated: " + ", ".join(violated))
    
    def _phase_pressure_and_prune(self) -> int:
        """Pressure + Prune, actually connected.

        For each surviving candidate, every executable falsifier is
        actually called against it. If it triggers (returns True), the
        candidate is eliminated with a real reason and a real reference
        to which falsifier did it. Falsifiers with no `check` are logged
        as descriptive-only and never contribute to elimination.
        """
        self.result.add_log_entry(
            f"PRESSURE+PRUNE - {len(self.scope_run.domain_indexed_falsifiers)} falsifiers "
            f"against {sum(1 for c in self.scope_run.candidate_claim_set if not c.eliminated)} "
            f"surviving candidates"
        )

        eliminated_count = 0

        for candidate in self.scope_run.candidate_claim_set:
            if candidate.eliminated:
                continue

            for falsifier in self.scope_run.domain_indexed_falsifiers:
                if not falsifier.is_executable():
                    self.result.add_log_entry(
                        f"  - SKIP (no executable check): {falsifier.name} "
                        f"-- descriptive only, cannot eliminate anything"
                    )
                    continue

                falsifier.applied = True
                triggered = falsifier.check(candidate)
                if not isinstance(triggered, bool):
                    raise TypeError(f"Falsifier '{falsifier.name}' must return bool")
                # Aggregate over the run; a later passing candidate cannot erase a trigger.
                falsifier.result = bool(falsifier.result) or triggered

                if triggered:
                    falsifier.result = True
                    candidate.eliminated = True
                    candidate.elimination_reason = (
                        f"Falsified by '{falsifier.name}': {falsifier.description}"
                    )
                    eliminated_count += 1

                    trace = EliminationTrace(
                        timestamp=datetime.now(),
                        candidate_name=candidate.name,
                        category=EliminationCategory.EPISTEMIC,
                        reason=candidate.elimination_reason,
                        falsifier_applied=falsifier.name,
                        epistemic_yield=falsifier.criticality,
                    )
                    self.result.add_elimination_trace(trace)
                    self.result.add_log_entry(
                        f"  - ELIMINATED: {candidate.name} via {falsifier.name} "
                        f"(criticality {falsifier.criticality})"
                    )
                    break

        self.result.add_log_entry(f"  - Eliminated this iteration: {eliminated_count}")
        return eliminated_count

    def _phase_measure(self, previous_viable: int, viable_now: int, eliminated_this_round: int,
                       new_falsifiers: int) -> None:
        """Measure: Calculate eliminative work and DRE for this iteration."""
        dre_result = self.dre_calculator.calculate(
            viable_candidates=viable_now,
            previous_viable_count=previous_viable,
            new_falsifiers=new_falsifiers,
            eliminative_work=eliminated_this_round * 0.25,
        )

        self.result.dre_history.append(dre_result)
        self.result.add_log_entry(
            f"  - ΔH: {dre_result.delta_h:.3f}  "
            f"viable: {dre_result.viable_candidate_count}  "
            f"drift: {dre_result.drift_detected}"
        )
    
    def _check_termination(self) -> None:
        """Check if termination conditions are met."""
        # final_viable_candidates isn't set until execute()'s `finally` block,
        # so compute survival rate directly here instead of via self.result
        # (previously this always logged 0.0%, even on healthy runs).
        viable_now = sum(
            1 for c in self.scope_run.candidate_claim_set if not c.eliminated
        )
        total = self.result.initial_candidate_count
        survival_rate_now = (viable_now / total) if total else 0.0

        if not self.result.dre_history:
            self.result.add_log_entry(
                f"Admissibility maintained - survival rate: {survival_rate_now:.1%}"
            )
            return

        latest_dre = self.result.dre_history[-1]

        if latest_dre.drift_detected:
            self.result.admissible = False
            self.result.termination_reason = "Recursive drift detected"
            self.result.add_log_entry(
                "TERMINATION: Recursive drift condition met"
            )
        else:
            self.result.add_log_entry(
                f"Admissibility maintained - survival rate: {survival_rate_now:.1%}"
            )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate execution report."""
        return {
            "run_info": {
                "host_domain": self.scope_run.host_domain,
                "resolution_level": self.scope_run.resolution_level.value,
                "execution_started": self.result.execution_started.isoformat(),
                "execution_completed": (
                    self.result.execution_completed.isoformat()
                    if self.result.execution_completed
                    else None
                ),
                "duration_seconds": self.result.elapsed_time(),
            },
            "candidates": {
                "total": self.result.initial_candidate_count,
                "survived": self.result.final_viable_candidates,
                "survival_rate": self.result.survival_rate(),
            },
            "falsifiers": {
                "total": len(self.scope_run.domain_indexed_falsifiers),
                "total_applied": sum(f.applied for f in self.scope_run.domain_indexed_falsifiers),
                "executable": sum(f.is_executable() for f in self.scope_run.domain_indexed_falsifiers),
                "triggered": sum(f.result is True for f in self.scope_run.domain_indexed_falsifiers),
            },
            "constraints": {
                "total": self.scope_run.total_constraints(),
                "critical": len(self.scope_run.critical_constraints()),
                "violated": sum(c.violated for c in self.scope_run.explicit_constraints),
            },
            "dre_results": {
                "final_delta_h": (
                    self.result.dre_history[-1].delta_h
                    if self.result.dre_history
                    else 0.0
                ),
                "drift_detected": (
                    self.result.dre_history[-1].drift_detected
                    if self.result.dre_history
                    else False
                ),
                "final_eliminative_work": sum(
                    t.total_yield() for t in self.result.elimination_traces
                ),
            },
            "failure_modes": self.result.detected_failure_modes,
            "surviving_structures": [
                {
                    "name": c.name,
                    "assumptions_count": c.assumption_count(),
                }
                for c in self.scope_run.candidate_claim_set
                if not c.eliminated
            ],
            "admissible": self.result.admissible,
            "termination_reason": self.result.termination_reason,
        }

