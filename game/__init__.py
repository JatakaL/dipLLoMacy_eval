"""
Game module for Diplomacy game mechanics.

This module provides the core game functionality including:
- GameState: Tracks the current state of a game
- Unit: Represents armies and fleets
- GameManager: High-level API for game management
- Order: Represents orders given to units
- OrderParser: Parses order strings
- OrderResolver: Resolves orders for a turn
- OrderValidator: Validates orders against game state
"""

from .game_state import GameState
from .units import Unit, UnitType
from .game_manager import GameManager
from .orders import Order, OrderType, OrderResult, OrderParser
from .resolver import OrderResolver
from .validators import OrderValidator, build_adjacency_from_map
from .game_export import (
    create_game_output_dir,
    write_game_metadata,
    write_map_data,
    write_turn_data,
    write_game_result,
    build_turn_callback,
    export_full_game,
    load_game_output,
)

__all__ = [
    'GameState', 
    'Unit', 
    'UnitType', 
    'GameManager',
    'Order',
    'OrderType',
    'OrderResult',
    'OrderParser',
    'OrderResolver',
    'OrderValidator',
    'build_adjacency_from_map',
    'create_game_output_dir',
    'write_game_metadata',
    'write_map_data',
    'write_turn_data',
    'write_game_result',
    'build_turn_callback',
    'export_full_game',
    'load_game_output',
]
