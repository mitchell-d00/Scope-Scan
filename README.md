# Scope-Scan

**Mitchell D. McPhetridge — combined research reference implementation**

The Operator Algebra Scanner measures telemetry. SCOPE applies an executable
falsifier to prune candidate labels against those measurements. This repository
builds on the supplied `scope-scanner-join(4).zip` and keeps its original demo intact.

## Run

Python 3.8 or newer; the model, CLI, and tests use the standard library.

```bash
# Original ZIP demonstration, preserved unchanged
python scope_scanner.py

# Combined model with auditable JSON evidence
python -m scope_scanner_join --demo --output report.json

# Analyze a telemetry array
python -m scope_scanner_join --input examples/sealed.json --output report.json

# Run the tests
python -m unittest discover -s tests -v
```

Optional installation adds a command-line entry point:

```bash
python -m pip install .
scope-scanner-join --demo
```

## The combined model

1. Validate a trace's counts and configuration.
2. Compute `r`, `s`, `f`, and `e` using the upstream scanner.
3. Compare consecutive full entropy windows and derive four signs.
4. Match signs to the nine fixed-sign operators.
5. Count matched transitions and retain every label tied for the highest count.
6. Let SCOPE eliminate labels outside that selection set, with named traces.
7. Stop when no additional elimination occurs.

| Coordinate | Measurement | Interpretation |
|---|---|---|
| `r` | `self_calls / total_calls` | Self-call fraction; zero total calls maps to 0 |
| `s` | `min(1, active_units / scale_reference)` | Normalized active breadth, clipped at 1 |
| `f` | `admitted_external / attempted_external` | Admission fraction; zero attempts maps to 1 |
| `e` | `1 - H(states) / log2(window length)` | State repetition; high values mean low diversity |

Changes strictly above `epsilon` become +1; strictly below `-epsilon` become -1;
the remainder become 0. Matching starts at tick `state_window + 1` in the actual
upstream implementation. For the default window of 8, tick 9 is the first
eligible comparison. This corrects the upstream prose's `window + 2` statement.

The enhanced interface uses **exact four-axis matching** by default. The upstream
implementation instead reports the label with most agreeing axes, requiring at
least one agreeing nonzero axis, and resolves equal per-tick scores by table order.
Use `--match-policy upstream` to reproduce that matching algorithm. Both exact and
upstream labels and the upstream axis score are recorded in the timeline.

## Results and ambiguity

The default enhanced demo gives:

| Synthetic trace | Matched-transition counts | Retained labels | Status |
|---|---|---|---|
| Sealed component | Onion: 3 | Onion | `matched` |
| Bottleneck | Hydra: 1, Onion: 1 | Hydra, Onion | `ambiguous` |
| Self-reference collapse | Mirror: 2 | Mirror | `matched` |
| Healthy baseline | None | no match | `no_match` |

The ZIP's bottleneck demo chooses Hydra because it appears first in a tie.
The enhanced model retains both labels. A shorter measurement window changes
which transitions are included: `--state-window 4` yields Hydra: 5, Onion: 1.
These are window-dependent summaries, not confidence probabilities. Counts
exclude unmatched comparisons, so a retained label need not describe most of
the trace. Inspect the timeline for mixed behavior and scale saturation.

`insufficient_history` means there are no eligible comparisons. All ten candidate
labels remain and no falsifier is attached. `no_match` means comparisons were
evaluated but no operator met the declared matching rule; it does **not** establish
that the system is healthy or that its signs were all zero.

## Input and API

The CLI accepts a JSON array containing exactly these six fields per tick:

```json
[
  {
    "self_calls": 2,
    "total_calls": 10,
    "active_units": 3,
    "admitted_external": 10,
    "attempted_external": 10,
    "state_snapshot": "state_0"
  }
]
```

Counts must be nonnegative integers; `self_calls <= total_calls` and
`admitted_external <= attempted_external`. State snapshots must be strings.
The CLI rejects unknown fields, malformed counts, and invalid configuration.
Input order is the time order; there is no timestamp or irregular-sampling model.

```python
from scope_scanner_join import ScannerConfig, analyze_trace

report = analyze_trace(ticks, title="component A", config=ScannerConfig(
    state_window=8, scale_reference=10, epsilon=0.02, match_policy="exact",
))
print(report["status"], report["selected_labels"])
print(report["scope"]["eliminations"])
```

JSON reports include configuration, original telemetry, per-tick measurements,
sign vectors, match counts, selected labels, SCOPE survivors, elimination reasons,
and DRE history sufficiency. Reports are deterministic and JSON-compatible.

## Scope of the evidence

This join is a **label-consistency and pruning prototype**. The SCOPE predicate
checks membership in a set selected by the scanner. It does not independently
validate the scanner, demonstrate causation, or establish production diagnostic
accuracy. Ground-truth falsifiers and real telemetry evaluation remain future work.

Scanner state diversity (`e`) and SCOPE Dynamic Recursive Entropy (DRE) are distinct
quantities. DRE here tracks changes in viable candidate count, new applied
falsifiers, and eliminative work. These short SCOPE runs stop after one or two
iterations, before the default five-observation drift window is filled. A false
`drift_detected` flag accompanied by insufficient history is not evidence against
long-term drift.

Lens, Compass, and Ratchet remain outside the fixed-sign scanner. Neither the
original demo nor the enhanced interface controls the system being measured.

## Files

| Path | Role |
|---|---|
| `scope_scanner.py` | Original ZIP join demo, unchanged |
| `operator_scanner.py` | Upstream scanner and synthetic samples, unchanged |
| `scope_runtime/` | Upstream SCOPE runtime from the ZIP, unchanged |
| `scope_scanner_join/` | Validated API, exact/upstream policies, CLI, JSON evidence |
| `tests/` | Standard-library integration and runtime regression tests |
| `examples/` | Input trace and reproducible enhanced demo output |
| `docs/ANALYSIS.md` | Analysis of both repositories and the ZIP |
| `docs/PROVENANCE.md` | Source revisions, file hashes, licensing notes |

Source repositories:

- [Scope-Run-Time](https://github.com/mitchell-d00/Scope-Run-Time)
- [The Operator Algebra Scanner](https://github.com/mitchell-d00/The-Operator-Algebra-Scanner-Grounding-Recursion-Scale-Flow-and-Entropy-in-Measured-Telemetry)

The SCOPE MIT license is retained in `LICENSE`. The inspected scanner repository
does not include a license file; see `docs/PROVENANCE.md` for the attribution and
the distinction from the ZIP's blanket MIT statement.
