# The Operator Algebra Scanner

Grounding Recursion, Scale, Flow, and Entropy in Measured Telemetry

**Mitchell D. McPhetridge** — 2026

---

## Overview

This repository documents the Operator Algebra Scanner — a concrete, measured diagnostic tool that bridges the gap between the formal Operator Algebra (from *"An Operator Algebra Over Recursion, Scale, Flow, and Entropy"*) and real system telemetry.

The paper defines real, computable formulas for four abstract coordinates:

- **r** (Recursion): `self_calls / total_calls`
- **s** (Scale): `active_units / scale_reference`
- **f** (Flow): `admitted_external / attempted_external`
- **e** (Entropy): `1 - normalized_entropy(recent_state_snapshots)`

The scanner watches these four numbers move over time and matches the *direction* of movement (the sign vector) against the nine fixed-sign generators from the Operator Algebra's Table 2.1, producing human-readable diagnoses like:

- **Onion** → `SEALED (flow blocked, nothing else moving)`
- **Hydra** → `BOTTLENECK (scale expanding while flow is constrained)`
- **Mirror** → `SELF-REFERENCE RISING (turning inward, away from external checks)`

---

## Key Results

Tested against four synthetic telemetry traces engineered to represent known failure patterns:

1. ✅ **Sealed component** → correctly identified as **Onion**
2. ✅ **Bottleneck** → correctly identified as **Hydra** (then **Onion** once scale plateaued)
3. ✅ **Self-reference collapse** → correctly identified as **Mirror**
4. ✅ **Healthy baseline** → correctly identified as **no match** (zero false positives after bug fixes)

### What This Establishes

- A concrete, computable, auditable way to turn abstract sign vectors into real telemetry diagnostics
- That the mapping correctly separates three distinct failure signatures from a stable baseline
- The exact bugs encountered (two rounds of fixes) and how they were diagnosed and resolved

### What This Does NOT Establish

- That these specific formulas are the *only* defensible choice (they are one reasonable choice)
- That the approach generalizes to unengineered real-world telemetry
- Anything about AI cognition, hallucination, or consciousness (it doesn't claim to)

---

## Files in This Repository

- **`The Operator Algebra Scanner - Grounding Recursion, Scale, Flow, and Entropy in Measured Telemetry.txt`**  
  The full paper, including positioning, abstract, methodology, results from both bug-fix rounds, and all appendices.

- **`operator_scanner.py`**  
  The complete, working Python implementation. Requires only Python standard library (`math`, `collections`). Runs four synthetic test traces and produces exact output matching the paper.

- **`scanner_run_log.txt`**  
  The exact, unedited console output from running the scanner against all four test cases.

---

## How to Run

```bash
# 1. No external dependencies — just Python 3
python operator_scanner.py
```

The script will output:
- All four test traces, tick-by-tick
- The measured (r, s, f, e) values at each step
- Operator matches and human-readable categories
- A summary count of matches per operator

---

## The Bug (and the Fix)

The paper documents, in full, a two-round measurement bug:

**Round 1 Bug**: Shannon entropy normalized by `log2(n)` where `n` is the window size. During fill-up, `n` grows every tick, so the normalizing denominator itself grows even though true diversity is constant. This artificially manufactured a rising entropy value, causing a false "Apple" match on the stable baseline.

**Round 1 Fix (Incomplete)**: Gate matching until the current tick's window is full. But this still compared a warmed-up tick against a not-yet-warmed-up previous tick, leaving one more false positive.

**Round 2 Fix (Complete)**: Require *both* ticks in any tick-to-tick comparison to postdate the point the entropy window first became full. After this fix, all four traces matched their predictions exactly, with zero false positives.

Both the bug and both fixes are preserved in the code (rather than silently patched) for transparency.

---

## Known Limitations (Stated Plainly)

The scanner needs at least `state_window + 2` ticks of history before reporting anything. On short traces or low-frequency telemetry, it will legitimately report no matches — that is the fix working correctly, not a new bug, but it is a real constraint to know about before using this on production data.

---

## Kill Conditions

This work explicitly embraces three "kill conditions" — scenarios where it should report negative results rather than be quietly dropped:

1. If, when pointed at real (non-synthetic) telemetry from an actual running system, the scanner's matches do not correspond to independently-verifiable ground truth, that should be reported as a negative result.

2. If a different, equally defensible choice of r/s/f/e formulas produces materially different diagnoses on the same system, that is evidence the mapping is underdetermined.

3. If extending this to the Lens, Compass, or Ratchet operators requires assumptions not already tested here, those assumptions must be stated and tested separately.

---

## Why This Matters

Most diagnostic tools either assert their correctness without proof or hide their bugs behind one-off patches. This repository takes the opposite stance: all code, the exact bug, both fixes, and the exact reproducible run output are included. Nothing is smoothed over.

The goal is not to claim the Operator Algebra is "right" or that this is the only way to measure recursion, scale, flow, and entropy. The goal is to provide one concrete, defensible, auditable measurement that others can examine, argue with, and potentially improve.

---

## References

- The underlying Operator Algebra framework comes from *"An Operator Algebra Over Recursion, Scale, Flow, and Entropy"*
- All twelve operators and the sign table (Table 2.1) are taken directly from that work
- This scanner implements nine of the fixed-sign generators (Onion, Apple, Gate, Stack, Mirror, Funnel, Hydra, Echo, Spiral); Lens, Compass, and Ratchet are left out as they require parameterization beyond the scope of this version




Repository Note

The accompanying implementation is available as an open-source reference implementation intended to make every claim in this paper directly reproducible. The repository includes the complete scanner, synthetic telemetry traces, and the exact console output used to produce the reported results. It is presented as a research prototype rather than a validated production diagnostic: its purpose is to provide a concrete, inspectable mapping from the abstract Operator Algebra to measurable telemetry, while inviting independent testing, alternative telemetry mappings, and evaluation against real-world systems. Future validation on non-synthetic telemetry will determine the practical utility and generality of the approach.

