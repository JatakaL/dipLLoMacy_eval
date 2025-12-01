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
    'build_adjacency_from_map'
]
