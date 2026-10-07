"""Measure once, declare a selection policy, then prune by that evidence.

Survival establishes consistency with the scanner's selection rule, not
independent confirmation of a system diagnosis.
"""

from collections import Counter
from dataclasses import dataclass
import math
from numbers import Real

from operator_scanner import CATEGORY, OPERATORS, OperatorScanner
from scope_runtime import (
    CandidateStructure, Constraint, Falsifier, ResolutionLevel, ScopeRun, ScopeRuntime,
)

NO_MATCH = "no match"
FIELDS = (
    "self_calls", "total_calls", "active_units", "admitted_external",
    "attempted_external", "state_snapshot",
)


@dataclass(frozen=True)
class ScannerConfig:
    scale_reference: float = 10.0
    state_window: int = 8
    epsilon: float = 0.02
    match_policy: str = "exact"

    def __post_init__(self):
        for name in ("scale_reference", "epsilon"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite and numeric")
        if self.scale_reference <= 0:
            raise ValueError("scale_reference must be positive")
        if self.epsilon < 0:
            raise ValueError("epsilon must be nonnegative")
        if isinstance(self.state_window, bool) or not isinstance(self.state_window, int) or self.state_window < 2:
            raise ValueError("state_window must be an integer of at least 2")
        if self.match_policy not in ("exact", "upstream"):
            raise ValueError("match_policy must be 'exact' or 'upstream'")


def _validate_tick(tick, index):
    if not isinstance(tick, dict) or set(tick) != set(FIELDS):
        raise ValueError(f"tick {index}: expected exactly {', '.join(FIELDS)}")
    for name in FIELDS[:-1]:
        value = tick[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"tick {index}: {name} must be a nonnegative integer")
    if tick["self_calls"] > tick["total_calls"]:
        raise ValueError(f"tick {index}: self_calls exceeds total_calls")
    if tick["admitted_external"] > tick["attempted_external"]:
        raise ValueError(f"tick {index}: admitted_external exceeds attempted_external")
    if not isinstance(tick["state_snapshot"], str):
        raise ValueError(f"tick {index}: state_snapshot must be a string")


def _scope_selection(allowed, title):
    names = list(OPERATORS) + [NO_MATCH]
    candidates = [
        CandidateStructure(
            name=name, description=CATEGORY.get(name, "No operator matched evaluated transitions."),
            key_assumptions=["Eligible under the declared trace-selection policy."],
            dependencies=["validated telemetry", "warm-window sign comparisons"],
            operational_distinctions=[name],
        ) for name in names
    ]
    enough_history = allowed is not None
    falsifiers = []
    if enough_history:
        falsifiers.append(Falsifier(
            name="Trace-selection mismatch",
            description="Label is outside the set selected from measured comparisons.",
            test_method="candidate.name not in selected_labels",
            domain="telemetry", criticality=0.9,
            check=lambda candidate: candidate.name not in allowed,
        ))
    run = ScopeRun(
        host_domain=f"Telemetry reading: {title}", resolution_level=ResolutionLevel.OPERATIONAL,
        candidate_claim_set=candidates,
        explicit_constraints=[Constraint(
            name="Comparable entropy windows", description="Both windows in a comparison must be full.",
            critical=True, verifiable=True, domain="telemetry",
        )],
        dependency_structure={"reading": ["validated telemetry", "warm-window sign comparisons"]},
        domain_indexed_falsifiers=falsifiers,
        operational_discrimination_metric="most frequent matched labels; preserve equal-count ties",
        governance_recursion_cost=0.1,
        scoring_procedure="executable membership check against the measured selection set",
        termination_trigger="stop when no further elimination occurs",
        decommissioning_condition="selection set reached or insufficient measurement history",
        metadata={"selected_labels": sorted(allowed) if enough_history else [],
                  "history_sufficient": enough_history},
    )
    runtime = ScopeRuntime(run)
    result = runtime.execute()
    if not result.admissible:
        raise RuntimeError(result.termination_reason)
    return {
        "initial_candidates": result.initial_candidate_count,
        "survivors": [c.name for c in candidates if not c.eliminated],
        "eliminations": [
            {"candidate": t.candidate_name, "reason": t.reason, "falsifier": t.falsifier_applied}
            for t in result.elimination_traces
        ],
        "iterations": result.iteration_count,
        "termination_reason": "no further elimination",
        "history_sufficient": enough_history,
        "dre": {
            "window_size": runtime.dre_calculator.window_size,
            "observations": len(result.dre_history),
            "history_sufficient": len(result.dre_history) >= runtime.dre_calculator.window_size,
            "drift_detected": any(r.drift_detected for r in result.dre_history),
            "delta_h": [r.delta_h for r in result.dre_history],
        },
    }


def analyze_trace(ticks, *, title="trace", config=None):
    """Return a JSON-compatible evidence report; input ticks are never modified.

    Exact matching requires all four signs to agree. Upstream mode reproduces
    the scanner's best-axis label, including its insertion-order tie behavior.
    Aggregate ties are preserved under either policy. Votes count matched
    transitions only: the selected label need not cover most of the trace.
    """
    config = config or ScannerConfig()
    scanner = OperatorScanner(config.scale_reference, config.state_window, config.epsilon)
    rows = []
    counts = Counter()
    for index, tick in enumerate(ticks, 1):
        _validate_tick(tick, index)
        result = scanner.tick(**tick)
        sign = result["sign"]
        exact = next((name for name, spec in OPERATORS.items() if spec["sign"] == sign), None)
        label = exact if config.match_policy == "exact" else result["operator"]
        if label is not None:
            counts[label] += 1
        rows.append({
            "tick": index, "telemetry": dict(tick), "rsfe": list(result["rsfe"]),
            "sign": list(sign) if sign is not None else None,
            "comparison_evaluated": sign is not None, "window_full": result["warmed_up"],
            "operator": label, "category": CATEGORY.get(label),
            "exact_operator": exact, "upstream_operator": result["operator"],
            "upstream_match_strength": result.get("match_strength"),
        })
    evaluated = sum(row["comparison_evaluated"] for row in rows)
    if not evaluated:
        status, selected = "insufficient_history", None
    elif not counts:
        status, selected = "no_match", {NO_MATCH}
    else:
        highest = max(counts.values())
        selected = {name for name, count in counts.items() if count == highest}
        status = "ambiguous" if len(selected) > 1 else "matched"
    return {
        "schema_version": "1.0", "title": title, "status": status,
        "config": {
            "scale_reference": config.scale_reference, "state_window": config.state_window,
            "epsilon": config.epsilon, "match_policy": config.match_policy,
        },
        "selection_policy": "highest count among matched transitions; retain all tied labels",
        "tick_count": len(rows), "evaluated_comparisons": evaluated,
        "unmatched_comparisons": evaluated - sum(counts.values()),
        "hit_counts": dict(sorted(counts.items())),
        "selected_labels": sorted(selected) if selected is not None else [],
        "timeline": rows, "scope": _scope_selection(selected, title),
    }
