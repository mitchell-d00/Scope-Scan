"""Join the Operator Algebra Scanner to SCOPE.

The scanner measures a telemetry trace and names the operator its sign
vector matches. SCOPE does not re-measure. It holds candidate readings of
that trace and deletes every reading the scan did not produce.

A reading with no executable contradiction is kept. A scan with no operator
match keeps only the "no match" reading. That is the checklist, not a new
entropy claim.
"""

from collections import Counter
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from operator_scanner import (
    OperatorScanner,
    sample_bottleneck,
    sample_healthy_baseline,
    sample_sealed_component,
    sample_self_reference_collapse,
)
from scope_runtime import (
    CandidateStructure,
    Constraint,
    Falsifier,
    ResolutionLevel,
    ScopeRun,
    ScopeRuntime,
)

READINGS = (
    ("Onion", "Sealed: corrective flow is blocked and nothing else is moving."),
    ("Hydra", "Bottleneck: scale is expanding while external admission shrinks."),
    ("Mirror", "Self-reference rising: checks turn inward and active scope shrinks."),
    ("no match", "No fixed-sign generator. Trace is stable on the warmed window."),
)


def scan(ticks):
    scanner = OperatorScanner()
    for tick in ticks:
        scanner.tick(**tick)
    hits = [row["operator"] for row in scanner.log if row["operator"]]
    dominant = Counter(hits).most_common(1)[0][0] if hits else None
    return scanner, dominant, hits


def run_case(title, ticks):
    scanner, dominant, hits = scan(ticks)
    measured = dominant if dominant else "no match"

    def contradicts(candidate, expected=measured):
        return candidate.name != expected

    scope_run = ScopeRun(
        host_domain=f"Telemetry reading: {title}",
        resolution_level=ResolutionLevel.OPERATIONAL,
        candidate_claim_set=[
            CandidateStructure(
                name=name,
                description=text,
                key_assumptions=[f"This trace is {name}."],
                dependencies=["scanner sign match on warmed ticks"],
                operational_distinctions=[text],
            )
            for name, text in READINGS
        ],
        explicit_constraints=[
            Constraint(
                name="Warm window required",
                description="A sign match counts only after both ticks postdate a full entropy window.",
                critical=True,
                verifiable=True,
                domain="telemetry",
            )
        ],
        dependency_structure={"reading": ["scanner sign match on warmed ticks"]},
        domain_indexed_falsifiers=[
            Falsifier(
                name="Scanner sign mismatch",
                description="Drop a reading whose named operator is not the scan's dominant match.",
                test_method="candidate.name != dominant warmed-window operator, or 'no match' if none",
                domain="telemetry",
                criticality=0.9,
                check=contradicts,
            )
        ],
        operational_discrimination_metric="dominant operator on warmed ticks",
        governance_recursion_cost=0.1,
        scoring_procedure="one executable check: name must equal the scan",
        termination_trigger="stop when an iteration eliminates nothing",
        decommissioning_condition="one reading remains, or no check fired",
        metadata={"measured": measured, "hit_counts": dict(Counter(hits))},
    )

    print("\n" + "=" * 72)
    print(title)
    print(scanner.summary())
    print(f"Dominant reading handed to SCOPE: {measured}")
    result = ScopeRuntime(scope_run).execute()
    survivors = [c.name for c in scope_run.candidate_claim_set if not c.eliminated]
    eliminated = [
        f"{c.name}: {c.elimination_reason}"
        for c in scope_run.candidate_claim_set
        if c.eliminated
    ]
    print(f"SCOPE {result.initial_candidate_count} -> {result.final_viable_candidates}")
    print("Kept:", ", ".join(survivors) or "(none)")
    for line in eliminated:
        print("Dropped:", line)
    return measured, survivors


def main():
    cases = [
        ("Sealed component", sample_sealed_component()),
        ("Bottleneck", sample_bottleneck()),
        ("Self-reference collapse", sample_self_reference_collapse()),
        ("Healthy baseline", sample_healthy_baseline()),
    ]
    print("Scanner measures. SCOPE prunes every reading the measurement does not match.")
    outcomes = [(title, *run_case(title, ticks)) for title, ticks in cases]
    print("\n" + "=" * 72)
    print("JOIN")
    for title, measured, survivors in outcomes:
        ok = survivors == [measured]
        print(f"  {title}: scan={measured}  scope={survivors}  {'ok' if ok else 'MISMATCH'}")


if __name__ == "__main__":
    main()
