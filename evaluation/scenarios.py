"""
Evaluation scenario definitions for structured LLM benchmarking.

Provides dataclass-style scenario descriptors and a scenario runner
that pairs game configurations with evaluation criteria.

Planned scenario categories:
- Single-agent: LLM vs random / heuristic / expert agents
- Multi-agent: same or different LLMs competing
- Benchmark: opening theory, mid-game tactics, end-game, defense
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvaluationScenario:
    """Describes a single evaluation scenario configuration.

    Attributes:
        name: Human-readable scenario identifier.
        description: What the scenario tests.
        num_games: Number of games to run for statistical significance.
        max_turns: Maximum turns per game before forcing a draw.
        powers: List of power names involved (empty = use map default).
        tags: Freeform labels for filtering and grouping results.
    """

    name: str
    description: str = ""
    num_games: int = 1
    max_turns: int = 50
    powers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class ScenarioRunner:
    """Executes evaluation scenarios and collects results.

    Orchestrates running multiple games per scenario, feeding
    game results into the metrics collectors.  This is a stub
    that will be wired to GameModerator and LLM adapters once
    those integrations are complete.
    """

    def run_scenario(self, scenario: EvaluationScenario) -> dict:
        """Execute a scenario and return collected results.

        Args:
            scenario: The scenario configuration to run.

        Returns:
            Dictionary summarising the scenario run, including
            the scenario name and a placeholder results list.
        """
        # Placeholder — will integrate with GameModerator
        return {
            "scenario": scenario.name,
            "num_games": scenario.num_games,
            "results": [],
        }
