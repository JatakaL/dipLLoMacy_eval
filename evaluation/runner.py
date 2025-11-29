"""
Game Runner for automated Diplomacy games.

This module provides the GameRunner class that manages
complete game execution with LLM or human players.
"""

import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.game_engine import GameEngine
from game.orders import Order
from game.game_state import Phase


class Player:
    """Base class for game players."""
    
    def get_orders(self, game_state: dict, power: str) -> List[Order]:
        """Get orders for the given game state."""
        raise NotImplementedError


class RandomPlayer(Player):
    """
    A random player that selects orders randomly.
    
    Useful as a baseline for LLM evaluation.
    """
    
    def __init__(self, seed: Optional[int] = None):
        import random
        self.rng = random.Random(seed)
    
    def get_orders(self, game_state: dict, power: str) -> List[Order]:
        """Get random valid orders for each unit."""
        from game.orders import Hold, Move, parse_order
        
        orders = []
        your_units = game_state.get("your_units", [])
        valid_orders = game_state.get("valid_orders", [])
        
        # Group valid orders by unit
        orders_by_unit = {}
        for order_info in valid_orders:
            unit_loc = order_info.get("unit_location")
            if unit_loc not in orders_by_unit:
                orders_by_unit[unit_loc] = []
            orders_by_unit[unit_loc].append(order_info)
        
        # Select random order for each unit
        for unit in your_units:
            unit_loc = unit.get("location")
            if unit_loc in orders_by_unit:
                unit_orders = orders_by_unit[unit_loc]
                if unit_orders:
                    selected = self.rng.choice(unit_orders)
                    order = parse_order(selected.get("description", ""), power)
                    if order:
                        orders.append(order)
                    else:
                        # Fall back to hold
                        orders.append(Hold(unit_loc, power))
        
        return orders


class HoldPlayer(Player):
    """
    A player that always issues hold orders.
    
    Useful as a simple baseline.
    """
    
    def get_orders(self, game_state: dict, power: str) -> List[Order]:
        """Issue hold orders for all units."""
        from game.orders import Hold
        
        orders = []
        for unit in game_state.get("your_units", []):
            unit_loc = unit.get("location")
            orders.append(Hold(unit_loc, power))
        return orders


class GameRunner:
    """
    Runs complete Diplomacy games with configurable players.
    
    Supports LLM players, random players, and human input.
    """
    
    def __init__(self, map_data: dict, players: Dict[str, Player]):
        """
        Initialize the game runner.
        
        Args:
            map_data: Map JSON from the generation pipeline
            players: Dictionary mapping power names to Player objects
        """
        self.map_data = map_data
        self.players = players
        self.engine = None
        self.game_log: List[dict] = []
        self.start_time = None
        self.end_time = None
    
    def setup_game(self):
        """Initialize the game engine and place starting units."""
        self.engine = GameEngine(self.map_data)
        self.engine.setup_starting_positions()
        self.game_log = []
        self.start_time = datetime.now()
    
    def run_game(self, max_turns: int = 50, verbose: bool = False) -> dict:
        """
        Run a complete game.
        
        Args:
            max_turns: Maximum number of game years to play
            verbose: Whether to print game progress
            
        Returns:
            Game result dictionary
        """
        self.setup_game()
        
        winner = None
        turn_count = 0
        
        while turn_count < max_turns and winner is None:
            # Run movement phases
            if self.engine.phase in (Phase.SPRING_MOVES, Phase.FALL_MOVES):
                if verbose:
                    print(f"\n=== {self.engine.year} {self.engine.phase.value} ===")
                
                # Collect orders from all players
                orders_by_power = {}
                for power, player in self.players.items():
                    if power in self.engine.state.eliminated_powers:
                        continue
                    
                    game_state = self.engine.get_game_state_for_llm(power)
                    orders = player.get_orders(game_state, power)
                    orders_by_power[power] = orders
                    
                    if verbose:
                        print(f"  {power}: {len(orders)} orders")
                
                # Resolve the turn
                result = self.engine.run_phase(orders_by_power)
                self.game_log.append({
                    "year": self.engine.year,
                    "phase": self.engine.phase.value,
                    "result": result
                })
                
                winner = result.get("winner")
            
            else:
                # Auto-resolve retreats and builds for now
                result = self.engine.resolve_turn()
                self.game_log.append({
                    "year": self.engine.year,
                    "phase": self.engine.phase.value,
                    "result": result
                })
                winner = result.get("winner")
            
            # Count years
            if self.engine.phase == Phase.SPRING_MOVES:
                turn_count += 1
        
        self.end_time = datetime.now()
        
        # Compile final results
        final_state = self.engine.state
        sc_counts = {}
        for power in self.engine.state.power_names:
            sc_counts[power] = len(final_state.get_power_supply_centers(power))
        
        return {
            "winner": winner,
            "final_year": final_state.year,
            "final_phase": final_state.phase.value,
            "supply_center_counts": sc_counts,
            "eliminated_powers": list(final_state.eliminated_powers),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "turn_count": turn_count,
            "log": self.game_log
        }
    
    def get_final_state(self) -> dict:
        """Get the final game state."""
        if self.engine is None:
            return {}
        return self.engine.state.to_dict()


class GameReplay:
    """
    Replay a game from its log.
    
    Useful for analyzing games after they've been played.
    """
    
    def __init__(self, map_data: dict, game_log: List[dict]):
        """
        Initialize game replay.
        
        Args:
            map_data: Map JSON
            game_log: Game log from a completed game
        """
        self.map_data = map_data
        self.game_log = game_log
        self.current_index = 0
    
    def get_state_at_turn(self, year: int, phase: str) -> Optional[dict]:
        """
        Get the game state at a specific turn.
        
        Args:
            year: Game year
            phase: Phase name
            
        Returns:
            Game state dictionary or None
        """
        for entry in self.game_log:
            if entry.get("year") == year and entry.get("phase") == phase:
                return entry.get("result", {})
        return None
    
    def get_all_turns(self) -> List[dict]:
        """Get all turn entries in the game log."""
        return self.game_log
