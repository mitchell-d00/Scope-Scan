# Repository analysis and integration decisions

Analyzed on 2026-10-07 against both repositories' default `main` branches and
the attached `scope-scanner-join(4).zip`. Source revisions and hashes appear in
[PROVENANCE.md](PROVENANCE.md).

## Responsibilities

| Source | Implemented responsibility | Relevant boundary |
|---|---|---|
| Scope-Run-Time | Candidate structures, declared constraints, executable falsifiers, elimination traces, iterative pruning, DRE history | Constraint descriptions alone do not run checks; pre-marked critical violations stop execution |
| Operator Algebra Scanner | Counts and state snapshots to four coordinates, warmed-window signs, nine operator patterns, synthetic sample generators | Best-axis matching can report a partial sign match; real diagnostic accuracy has not been established |
| Supplied ZIP | Run scanner, count labels, turn the dominant label into a SCOPE falsifier | Four candidates only; first-seen winner on ties; no-match reading conflates short and evaluated traces |

SCOPE also provides upstream utility modules and broad theoretical documents.
They are useful context but are not required by the ZIP's join. This repository
keeps the ZIP's runtime dependency footprint and adds only the integration layer.
The inspected runtime includes its published executable-falsifier and DRE fixes;
the upstream historical patch files must not be reapplied.

## Verified source behavior

The five scanner/runtime Python files in the ZIP have Git blob hashes equal to
their corresponding upstream files. The integration file is the ZIP's addition.
The original demo successfully reduces four candidates to one in each case.
That result follows directly from its equality predicate; it is not an independent
test of diagnostic correctness.

For the default eight-state window, the bottleneck has one Hydra transition and
one Onion transition. Its later increase in raw active units is clipped by the
scale coordinate, creating a phase where scale no longer moves. `Counter`'s
first-seen tie resolution selects Hydra in the original demo. Reporting only that
winner hides measured mixed behavior, so the enhanced layer retains both labels.

The original candidate table cannot represent Apple, Gate, Stack, Funnel, Echo,
or Spiral. A trace classified into any of those would eliminate every candidate.
The enhanced layer declares all nine fixed-sign labels plus the no-match label.

The scanner starts matching when `tick_index > window_full_since_tick`, so with
window W it first compares at tick W+1. Its surrounding comments and README claim
W+2; the implementation and tests establish W+1. The formula compares the first
full window with the next full window, which avoids the variable-denominator fill
artifact. It does not demonstrate calibration under all baseline distributions.

## Changes made in this repository

- Preserve the original ZIP demo, scanner, and runtime byte for byte.
- Add a separate API that validates telemetry before measuring it.
- Use exact sign matching by default and expose upstream matching explicitly.
- Preserve trace-summary ties and distinguish insufficient history from no match.
- Add ten-label SCOPE pruning, complete JSON evidence, and a telemetry-file CLI.
- Report DRE history sufficiency alongside its drift flag.
- Add installable package metadata, tests, and a Python-version CI matrix.

The report keeps upstream best-axis labels and scores visible. In upstream mode,
per-tick matching still inherits upstream table-order tie resolution; only the
aggregation across the trace preserves ties. This is stated explicitly rather
than presented as a new probability or confidence estimator.

## What remains to establish

The synthetic tests verify coordinate calculation, matching boundaries, all nine
representable labels, pruning, invalid inputs, reporting, and critical runtime
behaviors. They do not establish generalization to real telemetry.

A future evaluation should collect independently labeled real traces, declare the
measurement window, scale ceiling, epsilon, and matching policy before inspection,
then measure agreement and false positives against that ground truth. Alternative
defensible coordinate definitions should be compared on the same data. Mixed
regimes require timeline analysis rather than a single count summary.

SCOPE's current pruning rule is dependent on the scanner. Independent host-domain
checks could eliminate or retain a diagnosis using evidence external to that
label, but none are invented here. Likewise, two pruning iterations do not fill
the five-iteration DRE interval. No long-term recursion or governance-stability
claim follows from these runs.
