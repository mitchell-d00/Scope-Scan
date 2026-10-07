# Source provenance and attribution

Author of the source models: **Mitchell D. McPhetridge**.

## Source snapshots

| Source | Inspected revision |
|---|---|
| [Scope-Run-Time](https://github.com/mitchell-d00/Scope-Run-Time) | `352d8733913fb14d91adb4fe227aa782988f363c` |
| [Operator Algebra Scanner](https://github.com/mitchell-d00/The-Operator-Algebra-Scanner-Grounding-Recursion-Scale-Flow-and-Entropy-in-Measured-Telemetry) | `f73a8fafee77deac400978ffd5297ef0d1e8c8dc` |
| Uploaded combined model | `scope-scanner-join(4).zip`, supplied 2026-10-07 |

The scanner and four runtime files below are preserved byte for byte from the
ZIP. Their Git blob SHAs were independently calculated and compared to the
corresponding upstream repository file SHAs; every comparison passed.

| File | Git blob SHA |
|---|---|
| `operator_scanner.py` | `58d288c3923d03e729a3c917dfcb241609cc845e` |
| `scope_runtime/__init__.py` | `be0fec152b18faee7dd439f8fe1c3eeae2870693` |
| `scope_runtime/models.py` | `ff3b3227b33ac457536a9d3898e397767bcfaa25` |
| `scope_runtime/dre.py` | `4d982c2e743b8ccf46b536df812d1a7a2edb495b` |
| `scope_runtime/runtime.py` | `9cfe85dd6a92a843ed82107b67a2c07d8adf6617` |
| `scope_scanner.py` (ZIP integration) | `7b07a21e1f0d33b415db4e4aa54f7af56990b43c` |

The upstream READMEs are retained as source context in `SCOPE_UPSTREAM.md` and
`SCANNER_UPSTREAM.md`. Their historical claims and relative links belong to the
upstream projects; the current combined behavior is documented in this project's
root README and `ANALYSIS.md`.

## Licensing

The inspected SCOPE repository includes the MIT license with copyright
`2026 Mitchell D McPhetridge`. That notice is preserved in the root `LICENSE`
for the SCOPE implementation.

The inspected scanner repository has no license file and its README does not
declare a license. The uploaded ZIP says both upstream projects are MIT, but
that statement is not corroborated by the scanner repository snapshot. This
join retains attribution and does not invent an upstream scanner license or
apply a blanket package license declaration. The repository owner can resolve
that declaration separately.

## Integration additions

`scope_scanner_join/`, `tests/`, package metadata, CI, generated examples, and
analysis documents are additions for this combined repository. The original
ZIP's `scope_scanner.py`, `operator_scanner.py`, and `scope_runtime/` are unchanged.
