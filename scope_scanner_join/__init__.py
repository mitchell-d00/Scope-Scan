"""Auditable telemetry classification joined to executable SCOPE pruning."""

from .model import ScannerConfig, analyze_trace

__all__ = ["ScannerConfig", "analyze_trace"]
__version__ = "0.1.0"
