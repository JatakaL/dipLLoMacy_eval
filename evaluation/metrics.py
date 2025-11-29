"""
Metrics collection for Diplomacy game evaluation.

This module provides classes for collecting and analyzing
game metrics during LLM evaluation.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GameMetrics:
    """
    Metrics collected for a single game.
    
    Attributes:
        game_id: Unique identifier for this game
        winner: Power that won (or None if draw/timeout)
        final_year: Year the game ended
        duration_seconds: Game duration in seconds
        supply_center_counts: Final SC counts per power
        eliminated_powers: Powers that were eliminated
        order_validity: Per-power order validity rates
        order_counts: Per-power order counts
    """
    game_id: str
    winner: Optional[str] = None
    final_year: int = 0
    duration_seconds: float = 0.0
    supply_center_counts: Dict[str, int] = field(default_factory=dict)
    eliminated_powers: List[str] = field(default_factory=list)
    order_validity: Dict[str, float] = field(default_factory=dict)
    order_counts: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "game_id": self.game_id,
            "winner": self.winner,
            "final_year": self.final_year,
            "duration_seconds": self.duration_seconds,
            "supply_center_counts": self.supply_center_counts,
            "eliminated_powers": self.eliminated_powers,
            "order_validity": self.order_validity,
            "order_counts": self.order_counts
        }


@dataclass
class ExperimentMetrics:
    """
    Aggregated metrics across multiple games.
    
    Attributes:
        experiment_id: Unique identifier for this experiment
        num_games: Number of games played
        win_rates: Win rate per power/player
        avg_game_length: Average game length in years
        avg_duration: Average game duration in seconds
        elimination_rates: Elimination rate per power
    """
    experiment_id: str
    num_games: int = 0
    win_rates: Dict[str, float] = field(default_factory=dict)
    avg_game_length: float = 0.0
    avg_duration: float = 0.0
    elimination_rates: Dict[str, float] = field(default_factory=dict)
    games: List[GameMetrics] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "experiment_id": self.experiment_id,
            "num_games": self.num_games,
            "win_rates": self.win_rates,
            "avg_game_length": self.avg_game_length,
            "avg_duration": self.avg_duration,
            "elimination_rates": self.elimination_rates,
            "games": [g.to_dict() for g in self.games]
        }


class MetricsCollector:
    """
    Collects and analyzes metrics during game execution.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.games: List[GameMetrics] = []
        self.current_game: Optional[GameMetrics] = None
        self._order_tracking: Dict[str, Dict[str, int]] = {}
    
    def start_game(self, game_id: str):
        """Start collecting metrics for a new game."""
        self.current_game = GameMetrics(game_id=game_id)
        self._order_tracking = {}
    
    def record_orders(self, power: str, total_orders: int, valid_orders: int):
        """
        Record order validity for a power.
        
        Args:
            power: Power name
            total_orders: Total orders submitted
            valid_orders: Number of valid orders
        """
        if power not in self._order_tracking:
            self._order_tracking[power] = {"total": 0, "valid": 0}
        
        self._order_tracking[power]["total"] += total_orders
        self._order_tracking[power]["valid"] += valid_orders
    
    def end_game(self, result: dict):
        """
        Finalize metrics for the current game.
        
        Args:
            result: Game result dictionary from GameRunner
        """
        if self.current_game is None:
            return
        
        self.current_game.winner = result.get("winner")
        self.current_game.final_year = result.get("final_year", 0)
        self.current_game.duration_seconds = result.get("duration_seconds", 0.0)
        self.current_game.supply_center_counts = result.get("supply_center_counts", {})
        self.current_game.eliminated_powers = result.get("eliminated_powers", [])
        
        # Calculate order validity rates
        for power, tracking in self._order_tracking.items():
            if tracking["total"] > 0:
                self.current_game.order_validity[power] = (
                    tracking["valid"] / tracking["total"]
                )
            self.current_game.order_counts[power] = tracking["total"]
        
        self.games.append(self.current_game)
        self.current_game = None
    
    def get_aggregate_metrics(self, experiment_id: str = "default") -> ExperimentMetrics:
        """
        Calculate aggregate metrics across all games.
        
        Args:
            experiment_id: Identifier for the experiment
            
        Returns:
            ExperimentMetrics with aggregated data
        """
        if not self.games:
            return ExperimentMetrics(experiment_id=experiment_id)
        
        metrics = ExperimentMetrics(
            experiment_id=experiment_id,
            num_games=len(self.games),
            games=self.games
        )
        
        # Calculate win rates
        win_counts: Dict[str, int] = {}
        elimination_counts: Dict[str, int] = {}
        all_powers = set()
        
        total_years = 0
        total_duration = 0.0
        
        for game in self.games:
            total_years += game.final_year
            total_duration += game.duration_seconds
            
            # Track wins
            if game.winner:
                win_counts[game.winner] = win_counts.get(game.winner, 0) + 1
            
            # Track eliminations
            for power in game.eliminated_powers:
                elimination_counts[power] = elimination_counts.get(power, 0) + 1
            
            # Track all powers
            all_powers.update(game.supply_center_counts.keys())
            all_powers.update(game.eliminated_powers)
        
        # Calculate rates
        for power in all_powers:
            metrics.win_rates[power] = (
                win_counts.get(power, 0) / len(self.games)
            )
            metrics.elimination_rates[power] = (
                elimination_counts.get(power, 0) / len(self.games)
            )
        
        metrics.avg_game_length = total_years / len(self.games)
        metrics.avg_duration = total_duration / len(self.games)
        
        return metrics
    
    def generate_report(self) -> str:
        """
        Generate a human-readable report of the metrics.
        
        Returns:
            Report text
        """
        metrics = self.get_aggregate_metrics()
        
        lines = [
            "=" * 60,
            "DIPLOMACY EVALUATION REPORT",
            "=" * 60,
            "",
            f"Games Played: {metrics.num_games}",
            f"Average Game Length: {metrics.avg_game_length:.1f} years",
            f"Average Duration: {metrics.avg_duration:.1f} seconds",
            "",
            "WIN RATES:",
        ]
        
        for power, rate in sorted(metrics.win_rates.items(), 
                                   key=lambda x: x[1], reverse=True):
            lines.append(f"  {power}: {rate*100:.1f}%")
        
        lines.extend([
            "",
            "ELIMINATION RATES:",
        ])
        
        for power, rate in sorted(metrics.elimination_rates.items(),
                                   key=lambda x: x[1], reverse=True):
            lines.append(f"  {power}: {rate*100:.1f}%")
        
        lines.extend([
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)


class PerformanceTracker:
    """
    Tracks LLM-specific performance metrics.
    
    Collects data on:
    - Order quality
    - Response times
    - Token usage
    - Error rates
    """
    
    def __init__(self):
        """Initialize the performance tracker."""
        self.response_times: List[float] = []
        self.token_counts: List[int] = []
        self.error_count: int = 0
        self.total_requests: int = 0
    
    def record_request(self, response_time: float, tokens: int = 0, 
                      error: bool = False):
        """
        Record an LLM request.
        
        Args:
            response_time: Time in seconds
            tokens: Token count (if available)
            error: Whether the request resulted in an error
        """
        self.total_requests += 1
        self.response_times.append(response_time)
        if tokens > 0:
            self.token_counts.append(tokens)
        if error:
            self.error_count += 1
    
    def get_summary(self) -> dict:
        """Get summary statistics."""
        if not self.response_times:
            return {}
        
        return {
            "total_requests": self.total_requests,
            "avg_response_time": sum(self.response_times) / len(self.response_times),
            "max_response_time": max(self.response_times),
            "min_response_time": min(self.response_times),
            "avg_tokens": (
                sum(self.token_counts) / len(self.token_counts) 
                if self.token_counts else 0
            ),
            "error_rate": self.error_count / self.total_requests if self.total_requests else 0
        }
