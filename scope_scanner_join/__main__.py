"""Command-line entry point for synthetic demos and JSON telemetry."""

import argparse
import json
from pathlib import Path
import sys

from operator_scanner import (
    sample_bottleneck, sample_healthy_baseline,
    sample_sealed_component, sample_self_reference_collapse,
)
from .model import ScannerConfig, analyze_trace


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="analyze the four synthetic traces")
    source.add_argument("--input", type=Path, help="JSON array of telemetry ticks")
    parser.add_argument("--output", type=Path, help="write JSON report; default is stdout")
    parser.add_argument("--state-window", type=int, default=8)
    parser.add_argument("--scale-reference", type=float, default=10.0)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--match-policy", choices=("exact", "upstream"), default="exact")
    args = parser.parse_args(argv)
    try:
        config = ScannerConfig(args.scale_reference, args.state_window, args.epsilon, args.match_policy)
        if args.demo:
            cases = [
                ("Sealed component", sample_sealed_component()),
                ("Bottleneck", sample_bottleneck()),
                ("Self-reference collapse", sample_self_reference_collapse()),
                ("Healthy baseline", sample_healthy_baseline()),
            ]
            report = {"cases": [analyze_trace(ticks, title=title, config=config) for title, ticks in cases]}
        else:
            ticks = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(ticks, list):
                raise ValueError("input must be a JSON array of telemetry ticks")
            report = analyze_trace(ticks, title=args.input.stem, config=config)
        output = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
