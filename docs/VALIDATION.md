# Validation

Local validation completed on Python 3.12 on 2026-10-07.

- `python -m unittest discover -s tests -v`: 20 tests passed.
- Original `python scope_scanner.py`: four demonstration cases completed and
  each preserved the label selected by the original ZIP.
- Enhanced `python -m scope_scanner_join --demo`: four cases produced the
  documented labels, with the default bottleneck tie retained.
- JSON-file CLI: `examples/sealed.json` produces Onion and named elimination
  evidence; malformed input is rejected with exit status 2.
- A wheel built with `pip wheel --no-deps --no-build-isolation`, installed into
  an isolated target, and ran both the module and console entry point from
  outside the source tree; their demo reports matched.
- All five original scanner/runtime files matched their upstream Git blob SHAs;
  all six source Python files matched the ZIP byte for byte.

The tests cover all nine operator sign patterns using independently constructed
coordinate transitions, exact versus partial matching, window fill boundaries,
no-match versus insufficient history, ties, input validation, scale saturation,
zero-denominator conventions, repeatability, CLI output, executable SCOPE checks,
constraint failure, and DRE's current-observation window behavior.

The CI configuration additionally targets Python 3.8 and 3.13. Those versions
were not executed locally; the configured CI matrix is not a claim that remote
GitHub checks have already passed. Tests use synthetic data and do not establish
real-system diagnostic accuracy.
