"""
Evaluation module for LLM Diplomacy benchmarking.

Provides metrics collection, scenario management, and batch
benchmarking infrastructure for assessing LLM performance in
Diplomacy gameplay:

- metrics: Performance, strategic quality, and diplomatic quality metrics
- scenarios: Evaluation scenario definitions and execution
- runner: Batch benchmarking orchestration and result export
"""

from .metrics import DiplomaticMetrics, PerformanceMetrics, StrategicMetrics
from .runner import BenchmarkRunner
from .scenarios import EvaluationScenario, ScenarioRunner

__all__ = [
    'PerformanceMetrics',
    'StrategicMetrics',
    'DiplomaticMetrics',
    'EvaluationScenario',
    'ScenarioRunner',
    'BenchmarkRunner',
]
