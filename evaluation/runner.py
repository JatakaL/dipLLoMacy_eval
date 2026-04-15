"""
Batch benchmarking runner for LLM Diplomacy evaluation.

Orchestrates running multiple evaluation scenarios, collecting
metrics, and producing aggregate benchmark reports.

Designed to be the top-level entry point for automated evaluation
campaigns once LLM provider adapters are implemented.
"""

from __future__ import annotations

import json
from pathlib import Path

from .metrics import DiplomaticMetrics, PerformanceMetrics, StrategicMetrics
from .scenarios import EvaluationScenario, ScenarioRunner


class BenchmarkRunner:
    """Top-level runner for batch evaluation campaigns.

    Coordinates scenario execution, metric collection, and
    result aggregation across multiple evaluation runs.

    Attributes:
        scenarios: List of scenarios queued for execution.
        performance: Aggregate performance metrics collector.
        strategic: Aggregate strategic metrics collector.
        diplomatic: Aggregate diplomatic metrics collector.
    """

    def __init__(self) -> None:
        self.scenarios: list[EvaluationScenario] = []
        self.performance = PerformanceMetrics()
        self.strategic = StrategicMetrics()
        self.diplomatic = DiplomaticMetrics()
        self._scenario_runner = ScenarioRunner()
        self._last_report: dict | None = None

    def add_scenario(self, scenario: EvaluationScenario) -> None:
        """Queue a scenario for the next benchmark run.

        Args:
            scenario: Scenario configuration to add.
        """
        self.scenarios.append(scenario)

    def run_all(self) -> dict:
        """Execute all queued scenarios and return a benchmark report.

        Returns:
            Dictionary containing per-scenario results and
            aggregate metric summaries.
        """
        scenario_results = []
        for scenario in self.scenarios:
            result = self._scenario_runner.run_scenario(scenario)
            scenario_results.append(result)

        self._last_report = {
            "scenarios_run": len(scenario_results),
            "scenario_results": scenario_results,
            "aggregate_performance": self.performance.compute_summary(),
            "aggregate_strategic": self.strategic.compute_summary(),
            "aggregate_diplomatic": self.diplomatic.compute_summary(),
        }
        return self._last_report

    def export_results(self, output_dir: Path, report: dict | None = None) -> Path:
        """Export benchmark results to a JSON file.

        Uses the provided *report* if given, otherwise falls back to
        the cached report from the most recent ``run_all()`` call.
        If neither is available, executes ``run_all()`` first.

        Args:
            output_dir: Directory to write results into.
            report: Optional precomputed report dictionary.  When
                supplied, it is written directly without re-running
                any scenarios.

        Returns:
            Path to the written results file.
        """
        if report is None:
            report = self._last_report if self._last_report is not None else self.run_all()

        output_dir.mkdir(parents=True, exist_ok=True)
        results_path = output_dir / "benchmark_results.json"
        results_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return results_path
