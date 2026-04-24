"""
Tests for the evaluation module skeleton.

Verifies that all evaluation classes import cleanly, initialise
correctly, and produce expected stub output.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation import (
    BenchmarkRunner,
    DiplomaticMetrics,
    EvaluationScenario,
    PerformanceMetrics,
    ScenarioRunner,
    StrategicMetrics,
)


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics collection and summary."""

    def test_initial_state(self):
        """Freshly created metrics have zero counts."""
        pm = PerformanceMetrics()
        assert pm.games_played == 0
        assert pm.wins == 0
        assert pm.survivals == 0
        assert pm.sc_counts == []
        assert pm.turns_survived == []

    def test_compute_summary_no_games(self):
        """Summary returns zeroes when no games recorded."""
        pm = PerformanceMetrics()
        summary = pm.compute_summary()
        assert summary["games_played"] == 0
        assert summary["win_rate"] == 0.0
        assert summary["survival_rate"] == 0.0
        assert summary["avg_sc_count"] == 0.0

    def test_add_game_result(self):
        """Adding a game result updates internal counters."""
        pm = PerformanceMetrics()
        pm.add_game_result({
            "won": True,
            "survived": True,
            "final_sc_count": 18,
            "turns": 30,
        })
        assert pm.games_played == 1
        assert pm.wins == 1
        assert pm.survivals == 1
        assert pm.sc_counts == [18]
        assert pm.turns_survived == [30]

    def test_compute_summary_after_games(self):
        """Summary computes correct aggregates after multiple games."""
        pm = PerformanceMetrics()
        pm.add_game_result({"won": True, "survived": True, "final_sc_count": 18, "turns": 30})
        pm.add_game_result({"won": False, "survived": True, "final_sc_count": 6, "turns": 40})
        summary = pm.compute_summary()
        assert summary["games_played"] == 2
        assert summary["win_rate"] == 0.5
        assert summary["survival_rate"] == 1.0
        assert summary["avg_sc_count"] == 12.0
        assert summary["avg_turns_survived"] == 35.0


class TestStrategicMetrics:
    """Tests for StrategicMetrics collection and summary."""

    def test_initial_state(self):
        """Freshly created metrics have zero counts."""
        sm = StrategicMetrics()
        assert sm.total_orders == 0
        assert sm.valid_orders == 0

    def test_compute_summary_no_data(self):
        """Summary returns zeroes when no orders recorded."""
        sm = StrategicMetrics()
        summary = sm.compute_summary()
        assert summary["total_orders"] == 0
        assert summary["order_validity_rate"] == 0.0
        assert summary["support_success_rate"] == 0.0
        assert summary["attack_success_rate"] == 0.0

    def test_record_orders(self):
        """Recording orders updates counters correctly."""
        sm = StrategicMetrics()
        sm.record_orders([
            {"valid": True, "type": "move", "success": True},
            {"valid": True, "type": "support", "success": False},
            {"valid": False, "type": "move", "success": False},
        ])
        assert sm.total_orders == 3
        assert sm.valid_orders == 2
        assert sm.attacks == 2
        assert sm.successful_attacks == 1
        assert sm.support_orders == 1
        assert sm.successful_supports == 0

    def test_compute_summary_after_orders(self):
        """Summary reflects recorded order data."""
        sm = StrategicMetrics()
        sm.record_orders([
            {"valid": True, "type": "move", "success": True},
            {"valid": True, "type": "support", "success": True},
        ])
        summary = sm.compute_summary()
        assert summary["order_validity_rate"] == 1.0
        assert summary["support_success_rate"] == 1.0
        assert summary["attack_success_rate"] == 1.0


class TestDiplomaticMetrics:
    """Tests for DiplomaticMetrics collection and summary."""

    def test_initial_state(self):
        """Freshly created metrics have zero counts."""
        dm = DiplomaticMetrics()
        assert dm.messages_sent == 0
        assert dm.alliances_proposed == 0

    def test_compute_summary_no_data(self):
        """Summary returns zeroes when no messages recorded."""
        dm = DiplomaticMetrics()
        summary = dm.compute_summary()
        assert summary["messages_sent"] == 0
        assert summary["alliance_formation_rate"] == 0.0
        assert summary["promise_keeping_rate"] == 0.0

    def test_record_message(self):
        """Recording a message updates counters correctly."""
        dm = DiplomaticMetrics()
        dm.record_message({
            "alliance_proposed": True,
            "alliance_formed": True,
            "promise_made": True,
            "promise_kept": False,
        })
        assert dm.messages_sent == 1
        assert dm.alliances_proposed == 1
        assert dm.alliances_formed == 1
        assert dm.promises_made == 1
        assert dm.promises_kept == 0


class TestEvaluationScenario:
    """Tests for EvaluationScenario dataclass."""

    def test_defaults(self):
        """Scenario has sensible defaults."""
        scenario = EvaluationScenario(name="test")
        assert scenario.name == "test"
        assert scenario.description == ""
        assert scenario.num_games == 1
        assert scenario.max_turns == 50
        assert scenario.powers == []
        assert scenario.tags == []

    def test_custom_values(self):
        """Scenario accepts custom values."""
        scenario = EvaluationScenario(
            name="opening",
            description="First 3 turns evaluation",
            num_games=10,
            max_turns=3,
            powers=["Avalon", "Borealis"],
            tags=["opening", "tactical"],
        )
        assert scenario.name == "opening"
        assert scenario.num_games == 10
        assert len(scenario.powers) == 2


class TestScenarioRunner:
    """Tests for ScenarioRunner stub."""

    def test_run_scenario_returns_dict(self):
        """run_scenario returns a dictionary with expected keys."""
        runner = ScenarioRunner()
        scenario = EvaluationScenario(name="test_scenario", num_games=5)
        result = runner.run_scenario(scenario)
        assert isinstance(result, dict)
        assert result["scenario"] == "test_scenario"
        assert result["num_games"] == 5
        assert result["results"] == []


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner stub."""

    def test_initial_state(self):
        """BenchmarkRunner starts with empty scenario list."""
        br = BenchmarkRunner()
        assert br.scenarios == []

    def test_add_scenario(self):
        """Adding a scenario grows the queue."""
        br = BenchmarkRunner()
        br.add_scenario(EvaluationScenario(name="s1"))
        br.add_scenario(EvaluationScenario(name="s2"))
        assert len(br.scenarios) == 2

    def test_run_all_empty(self):
        """run_all with no scenarios returns valid structure."""
        br = BenchmarkRunner()
        report = br.run_all()
        assert report["scenarios_run"] == 0
        assert isinstance(report["aggregate_performance"], dict)
        assert isinstance(report["aggregate_strategic"], dict)
        assert isinstance(report["aggregate_diplomatic"], dict)

    def test_run_all_with_scenarios(self):
        """run_all processes queued scenarios."""
        br = BenchmarkRunner()
        br.add_scenario(EvaluationScenario(name="s1"))
        br.add_scenario(EvaluationScenario(name="s2"))
        report = br.run_all()
        assert report["scenarios_run"] == 2
        assert len(report["scenario_results"]) == 2

    def test_export_results(self, tmp_path):
        """export_results writes a valid JSON file."""
        br = BenchmarkRunner()
        br.add_scenario(EvaluationScenario(name="export_test"))
        output_path = br.export_results(tmp_path / "results")
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["scenarios_run"] == 1

    def test_export_results_uses_cached_report(self, tmp_path):
        """export_results reuses the last run_all() report without re-running."""
        br = BenchmarkRunner()
        br.add_scenario(EvaluationScenario(name="cached"))
        report = br.run_all()
        output_path = br.export_results(tmp_path / "results")
        data = json.loads(output_path.read_text())
        assert data == report

    def test_export_results_accepts_precomputed_report(self, tmp_path):
        """export_results writes a provided report dict directly."""
        br = BenchmarkRunner()
        custom_report = {"custom": True, "scenarios_run": 99}
        output_path = br.export_results(tmp_path / "results", report=custom_report)
        data = json.loads(output_path.read_text())
        assert data == custom_report
