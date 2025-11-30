"""
Game module for Diplomacy game mechanics.

This module provides the core game functionality including:
- GameState: Tracks the current state of a game
- Unit: Represents armies and fleets
- GameManager: High-level API for game management
"""

from .game_state import GameState
from .units import Unit, UnitType
from .game_manager import GameManager

__all__ = ['GameState', 'Unit', 'UnitType', 'GameManager']
