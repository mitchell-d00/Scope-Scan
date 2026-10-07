import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from operator_scanner import (
    OPERATORS, OperatorScanner, sample_bottleneck, sample_healthy_baseline,
    sample_sealed_component, sample_self_reference_collapse,
)
from scope_scanner_join import ScannerConfig, analyze_trace
from scope_scanner_join.__main__ import main


def trace_for(sign, window=4):
    """Independent two-endpoint construction for any fixed sign vector."""
    base = dict(self_calls=5, total_calls=10, active_units=5,
                admitted_external=5, attempted_external=10)
    # A repeated window has e=1. A diverse window has e=0.
    states = ["same"] * window if sign[3] < 0 else [f"s{i}" for i in range(window)]
    ticks = [dict(base, state_snapshot=state) for state in states]
    last = dict(base)
    last["self_calls"] += sign[0]
    last["active_units"] += sign[1]
    last["admitted_external"] += sign[2]
    last["state_snapshot"] = states[-1] if sign[3] > 0 else "new"
    return ticks + [last]


class JoinTests(unittest.TestCase):
    def test_original_synthetic_outcomes_with_explicit_tie(self):
        cases = [
            (sample_sealed_component, "matched", ["Onion"]),
            (sample_bottleneck, "ambiguous", ["Hydra", "Onion"]),
            (sample_self_reference_collapse, "matched", ["Mirror"]),
            (sample_healthy_baseline, "no_match", ["no match"]),
        ]
        for sample, status, selected in cases:
            with self.subTest(sample=sample.__name__):
                result = analyze_trace(sample())
                self.assertEqual(result["status"], status)
                self.assertEqual(result["selected_labels"], selected)
                self.assertEqual(set(result["scope"]["survivors"]), set(selected))
                self.assertEqual(len(result["scope"]["eliminations"]), 10 - len(selected))

    def test_four_tick_window_changes_aggregation(self):
        result = analyze_trace(sample_bottleneck(), config=ScannerConfig(state_window=4))
        self.assertEqual(result["hit_counts"], {"Hydra": 5, "Onion": 1})
        self.assertEqual(result["selected_labels"], ["Hydra"])

    def test_every_fixed_sign_operator_is_representable(self):
        for name, spec in OPERATORS.items():
            with self.subTest(operator=name):
                result = analyze_trace(trace_for(spec["sign"]), config=ScannerConfig(state_window=4))
                self.assertEqual(result["selected_labels"], [name])
                self.assertEqual(result["scope"]["survivors"], [name])
                self.assertEqual(result["timeline"][-1]["sign"], list(spec["sign"]))

    def test_approximate_upstream_label_is_not_exact_evidence(self):
        ticks = trace_for((1, 1, -1, 0))
        exact = analyze_trace(ticks, config=ScannerConfig(state_window=4))
        upstream = analyze_trace(ticks, config=ScannerConfig(state_window=4, match_policy="upstream"))
        self.assertEqual(exact["status"], "no_match")
        self.assertIsNotNone(upstream["timeline"][-1]["operator"])
        self.assertEqual(upstream["timeline"][-1]["upstream_match_strength"], "3/4 axes")

    def test_warm_boundary_is_window_plus_one(self):
        ticks = sample_sealed_component()
        for size, expected in ((0, 0), (7, 0), (8, 0), (9, 1), (12, 4)):
            with self.subTest(size=size):
                result = analyze_trace(ticks[:size])
                self.assertEqual(result["evaluated_comparisons"], expected)
                if not expected:
                    self.assertEqual(result["status"], "insufficient_history")
                    self.assertEqual(result["scope"]["initial_candidates"], 10)
                    self.assertEqual(len(result["scope"]["survivors"]), 10)
                    self.assertEqual(result["scope"]["eliminations"], [])
        rows = analyze_trace(ticks)["timeline"]
        self.assertTrue(rows[7]["window_full"])
        self.assertFalse(rows[7]["comparison_evaluated"])
        self.assertTrue(rows[8]["comparison_evaluated"])

    def test_baseline_has_no_fill_artifact(self):
        for window in (3, 4, 8):
            with self.subTest(window=window):
                result = analyze_trace(sample_healthy_baseline(), config=ScannerConfig(state_window=window))
                self.assertEqual(result["hit_counts"], {})

    def test_no_match_does_not_mean_healthy(self):
        result = analyze_trace(trace_for((1, 1, -1, 0)), config=ScannerConfig(state_window=4))
        self.assertNotEqual(result["timeline"][-1]["sign"], [0, 0, 0, 0])
        self.assertEqual(result["status"], "no_match")

    def test_inputs_unmodified_and_reports_repeatable(self):
        ticks = sample_bottleneck()
        before = copy.deepcopy(ticks)
        first = analyze_trace(ticks)
        self.assertEqual(ticks, before)
        self.assertEqual(first, analyze_trace(ticks))
        self.assertEqual(first, json.loads(json.dumps(first, allow_nan=False)))

    def test_invalid_telemetry_rejected(self):
        bad_values = [
            ("self_calls", -1), ("self_calls", 11), ("self_calls", True),
            ("total_calls", 1.5), ("active_units", float("nan")),
            ("admitted_external", 11), ("attempted_external", -1),
            ("state_snapshot", ["unhashable"]), ("state_snapshot", None),
        ]
        for field, value in bad_values:
            tick = sample_sealed_component()[0]
            tick[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                analyze_trace([tick])
        for tick in ({}, [], dict(sample_sealed_component()[0], extra=1)):
            with self.assertRaises(ValueError):
                analyze_trace([tick])

    def test_invalid_config_rejected(self):
        for kwargs in (
            {"state_window": 0}, {"state_window": 1}, {"state_window": True},
            {"state_window": 4.0}, {"epsilon": -0.1}, {"epsilon": float("nan")},
            {"epsilon": True}, {"scale_reference": 0}, {"scale_reference": float("inf")},
            {"match_policy": "guess"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ScannerConfig(**kwargs)

    def test_zero_denominators_and_scale_saturation_are_visible(self):
        tick = dict(self_calls=0, total_calls=0, active_units=100,
                    admitted_external=0, attempted_external=0, state_snapshot="same")
        result = analyze_trace([tick] * 9)
        self.assertEqual(result["timeline"][-1]["rsfe"], [0.0, 1.0, 1.0, 1.0])

    def test_epsilon_boundary_is_strict(self):
        scanner = OperatorScanner(epsilon=0.02)
        self.assertEqual(scanner._sign(0.02), 0)
        self.assertEqual(scanner._sign(-0.02), 0)
        self.assertEqual(scanner._sign(0.021), 1)

    def test_dre_insufficient_history_is_reported(self):
        result = analyze_trace(sample_sealed_component())
        self.assertEqual(result["scope"]["iterations"], 2)
        self.assertFalse(result["scope"]["dre"]["history_sufficient"])
        self.assertFalse(result["scope"]["dre"]["drift_detected"])
        self.assertEqual(result["scope"]["dre"]["delta_h"], [-9, 0])

    def test_cli_json_file_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input.json", Path(directory) / "report.json"
            source.write_text(json.dumps(sample_sealed_component()), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["selected_labels"], ["Onion"])
            source.write_text("{}", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(["--input", str(source)])
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
