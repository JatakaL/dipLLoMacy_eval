"""
Evaluation Module for Diplomacy LLM Testing

This module provides:
- GameRunner for running complete games
- Experiment framework for multiple game trials
- Metrics collection and analysis
- Result storage and reporting

Usage:
    from evaluation import GameRunner, Experiment
    
    # Run a single game
    runner = GameRunner(map_data, players)
    result = runner.run_game(max_turns=50)
    
    # Run an experiment
    experiment = Experiment(map_config, player_configs)
    results = experiment.run(num_games=10)
"""

from .runner import GameRunner
from .experiment import Experiment
from .metrics import MetricsCollector, GameMetrics

__all__ = [
    'GameRunner',
    'Experiment',
    'MetricsCollector',
    'GameMetrics',
]
