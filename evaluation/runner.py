"""
Batch benchmarking runner for LLM Diplomacy evaluation.

Orchestrates running multiple evaluation scenarios, collecting
metrics, and producing aggregate benchmark reports.

Designed to be the top-level entry point for automated evaluation
campaigns once LLM provider adapters are implemented.
"""

from __future__ import annotations

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

        return {
            "scenarios_run": len(scenario_results),
            "scenario_results": scenario_results,
            "aggregate_performance": self.performance.compute_summary(),
            "aggregate_strategic": self.strategic.compute_summary(),
            "aggregate_diplomatic": self.diplomatic.compute_summary(),
        }

    def export_results(self, output_dir: Path) -> Path:
        """Export benchmark results to a JSON file.

        Args:
            output_dir: Directory to write results into.

        Returns:
            Path to the written results file.
        """
        import json

        output_dir.mkdir(parents=True, exist_ok=True)
        results_path = output_dir / "benchmark_results.json"
        report = self.run_all()
        results_path.write_text(json.dumps(report, indent=2))
        return results_path
