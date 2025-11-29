"""
Game Module for Diplomacy

This module implements the core game mechanics for Diplomacy:
- Units (Army, Fleet)
- Orders (Hold, Move, Support, Convoy)
- Order Resolution
- Game State Management
- Turn Structure

Usage:
    from game import GameEngine
    
    # Load a map
    with open('map.json') as f:
        map_data = json.load(f)
    
    # Create game
    engine = GameEngine(map_data)
    
    # Place starting units
    engine.setup_starting_positions()
    
    # Submit orders
    engine.submit_orders("Power1", [
        {"unit": "C23", "order": "move", "target": "C24"},
        {"unit": "C25", "order": "hold"}
    ])
    
    # Resolve
    engine.resolve_turn()
"""

from .units import Unit, Army, Fleet, UnitType
from .orders import Order, OrderType, Hold, Move, Support, Convoy
from .game_state import GameState
from .game_engine import GameEngine

__all__ = [
    'Unit', 'Army', 'Fleet', 'UnitType',
    'Order', 'OrderType', 'Hold', 'Move', 'Support', 'Convoy',
    'GameState',
    'GameEngine'
]
