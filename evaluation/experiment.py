"""
Experiment framework for Diplomacy LLM evaluation.

This module provides the Experiment class for running
multiple game trials with configurable parameters.
"""

import os
import sys
import json
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .runner import GameRunner, Player, RandomPlayer, HoldPlayer
from .metrics import MetricsCollector, ExperimentMetrics


class Experiment:
    """
    Framework for running multiple Diplomacy game trials.
    
    Supports:
    - Multiple games with different seeds
    - Different player configurations
    - Metrics collection and analysis
    - Result persistence
    """
    
    def __init__(self, 
                 map_config: dict,
                 player_configs: Dict[str, dict],
                 experiment_id: Optional[str] = None):
        """
        Initialize an experiment.
        
        Args:
            map_config: Configuration for map generation
            player_configs: Configuration for each power's player
                           {"Power1": {"type": "random", "seed": 42}, ...}
            experiment_id: Unique identifier (auto-generated if not provided)
        """
        self.map_config = map_config
        self.player_configs = player_configs
        self.experiment_id = experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = MetricsCollector()
        self.results: List[dict] = []
    
    def _generate_map(self, seed: int) -> dict:
        """
        Generate a map with the given seed.
        
        Args:
            seed: Random seed for map generation
            
        Returns:
            Generated map data
        """
        # Import map generation
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'map_gen', 'phases'
        ))
        from orchestrator import run_full_pipeline
        
        config = dict(self.map_config)
        config["seed"] = seed
        
        # Generate map but don't save files
        return run_full_pipeline(config, output_dir="/tmp/experiment_maps",
                                save_intermediate=False)
    
    def _create_players(self, powers: List[str]) -> Dict[str, Player]:
        """
        Create player instances for each power.
        
        Args:
            powers: List of power names
            
        Returns:
            Dictionary mapping power names to Player instances
        """
        players = {}
        
        for power in powers:
            config = self.player_configs.get(power, {"type": "random"})
            player_type = config.get("type", "random").lower()
            
            if player_type == "random":
                players[power] = RandomPlayer(seed=config.get("seed"))
            elif player_type == "hold":
                players[power] = HoldPlayer()
            elif player_type == "llm":
                # Import LLM player
                provider = config.get("provider", "openai")
                if provider == "openai":
                    from llm.openai_adapter import OpenAIAdapter, MockOpenAIAdapter
                    if config.get("mock", False):
                        players[power] = MockOpenAIAdapter()
                    else:
                        players[power] = OpenAIAdapter(
                            model=config.get("model", "gpt-4"),
                            temperature=config.get("temperature", 0.7)
                        )
                elif provider == "anthropic":
                    from llm.anthropic_adapter import AnthropicAdapter, MockAnthropicAdapter
                    if config.get("mock", False):
                        players[power] = MockAnthropicAdapter()
                    else:
                        players[power] = AnthropicAdapter(
                            model=config.get("model", "claude-3-sonnet-20240229"),
                            temperature=config.get("temperature", 0.7)
                        )
            else:
                # Default to random
                players[power] = RandomPlayer()
        
        return players
    
    def run(self, num_games: int = 10, max_turns: int = 50,
            verbose: bool = False) -> ExperimentMetrics:
        """
        Run the experiment.
        
        Args:
            num_games: Number of games to play
            max_turns: Maximum turns per game
            verbose: Whether to print progress
            
        Returns:
            Aggregated experiment metrics
        """
        if verbose:
            print(f"\nStarting experiment {self.experiment_id}")
            print(f"Running {num_games} games, max {max_turns} turns each\n")
        
        for game_num in range(num_games):
            game_id = f"{self.experiment_id}_game_{game_num}"
            
            if verbose:
                print(f"Game {game_num + 1}/{num_games}...")
            
            try:
                # Generate map
                seed = self.map_config.get("seed", 42) + game_num
                map_data = self._generate_map(seed)
                
                # Get power names from map
                powers = list(map_data.get("powers", {}).keys())
                
                # Create players
                players = self._create_players(powers)
                
                # Run game
                self.metrics.start_game(game_id)
                runner = GameRunner(map_data, players)
                result = runner.run_game(max_turns=max_turns, verbose=False)
                
                # Record metrics
                self.metrics.end_game(result)
                self.results.append({
                    "game_id": game_id,
                    "seed": seed,
                    "result": result
                })
                
                if verbose:
                    winner = result.get("winner", "No winner")
                    years = result.get("final_year", 0)
                    print(f"  -> Winner: {winner} (Year {years})")
            
            except Exception as e:
                if verbose:
                    print(f"  -> Error: {e}")
                continue
        
        return self.metrics.get_aggregate_metrics(self.experiment_id)
    
    def save_results(self, output_dir: str):
        """
        Save experiment results to disk.
        
        Args:
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save metrics
        metrics = self.metrics.get_aggregate_metrics(self.experiment_id)
        metrics_path = output_path / f"{self.experiment_id}_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)
        
        # Save detailed results
        results_path = output_path / f"{self.experiment_id}_results.json"
        with open(results_path, 'w') as f:
            # Filter out non-serializable data from game logs
            serializable_results = []
            for r in self.results:
                result_copy = dict(r)
                if "result" in result_copy:
                    result_copy["result"] = {
                        k: v for k, v in result_copy["result"].items()
                        if k != "log"  # Exclude detailed log
                    }
                serializable_results.append(result_copy)
            json.dump(serializable_results, f, indent=2)
        
        # Save human-readable report
        report_path = output_path / f"{self.experiment_id}_report.txt"
        with open(report_path, 'w') as f:
            f.write(self.metrics.generate_report())
    
    @classmethod
    def load_results(cls, results_path: str) -> dict:
        """
        Load experiment results from disk.
        
        Args:
            results_path: Path to results JSON file
            
        Returns:
            Results dictionary
        """
        with open(results_path) as f:
            return json.load(f)


class ExperimentSuite:
    """
    Run multiple experiments with different configurations.
    
    Useful for comparing different LLM models or player strategies.
    """
    
    def __init__(self, experiments: List[Experiment]):
        """
        Initialize an experiment suite.
        
        Args:
            experiments: List of experiments to run
        """
        self.experiments = experiments
        self.results: Dict[str, ExperimentMetrics] = {}
    
    def run_all(self, num_games: int = 10, max_turns: int = 50,
                verbose: bool = False) -> Dict[str, ExperimentMetrics]:
        """
        Run all experiments in the suite.
        
        Args:
            num_games: Number of games per experiment
            max_turns: Maximum turns per game
            verbose: Whether to print progress
            
        Returns:
            Dictionary mapping experiment IDs to metrics
        """
        for experiment in self.experiments:
            if verbose:
                print(f"\n{'='*60}")
                print(f"Running experiment: {experiment.experiment_id}")
                print('='*60)
            
            metrics = experiment.run(
                num_games=num_games,
                max_turns=max_turns,
                verbose=verbose
            )
            self.results[experiment.experiment_id] = metrics
        
        return self.results
    
    def compare_results(self) -> str:
        """
        Generate a comparison report across experiments.
        
        Returns:
            Comparison report text
        """
        if not self.results:
            return "No results to compare."
        
        lines = [
            "=" * 60,
            "EXPERIMENT COMPARISON REPORT",
            "=" * 60,
            ""
        ]
        
        # Compare win rates
        lines.append("WIN RATES BY EXPERIMENT:")
        for exp_id, metrics in self.results.items():
            lines.append(f"\n{exp_id}:")
            for power, rate in sorted(metrics.win_rates.items(),
                                       key=lambda x: x[1], reverse=True):
                lines.append(f"  {power}: {rate*100:.1f}%")
        
        # Compare game lengths
        lines.extend([
            "",
            "AVERAGE GAME LENGTHS:",
        ])
        for exp_id, metrics in self.results.items():
            lines.append(f"  {exp_id}: {metrics.avg_game_length:.1f} years")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
