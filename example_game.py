#!/usr/bin/env python3
"""
Example: Initialize a Diplomacy Game

This script demonstrates how to:
1. Generate a map using the map generation pipeline
2. Initialize a game from the map
3. Export the game state as JSON
4. Export the game board as JPEG

This satisfies the initial success criteria for game implementation:
- A game board can be generated ready for the first turn
- Both JSON and JPEG are created representing it
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime


def generate_and_initialize_game(seed: int = 42, output_dir: str = None):
    """
    Generate a new map and initialize a game ready for the first turn.
    
    Args:
        seed: Random seed for reproducible map generation
        output_dir: Directory to save outputs (default: creates timestamped dir)
        
    Returns:
        Tuple of (game_manager, json_path, jpeg_path)
    """
    # Import the orchestrator for map generation
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
    from orchestrator import run_full_pipeline
    
    # Import game module
    from game import GameManager
    
    print("=" * 70)
    print(" DIPLOMACY GAME INITIALIZATION EXAMPLE")
    print("=" * 70)
    
    # Step 1: Generate a map
    print("\n[Step 1] Generating map...")
    
    config = {
        "num_cells": 80,
        "num_powers": 7,
        "territory_size": 3,
        "num_neutral_scs": 13,
        "land_ratio": 0.6,
        "seed": seed
    }
    
    # Generate the map (this also saves intermediate files)
    map_data = run_full_pipeline(
        config,
        output_dir=None,  # Use default
        save_intermediate=False  # Don't need intermediate files for game
    )
    
    print(f"  Map generated with {len(map_data.get('powers', {}))} powers")
    
    # Step 2: Initialize the game
    print("\n[Step 2] Initializing game...")
    
    gm = GameManager(map_data=map_data)
    state = gm.initialize_game()
    
    print(f"  Turn: {state.get_turn_string()}")
    print(f"  Phase: {state.phase.value}")
    print(f"  Powers: {len(state.powers)}")
    print(f"  Units placed: {len(state.units)}")
    print(f"  Supply centers: {len(state.sc_control)}")
    
    # Step 3: Prepare output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent / "game_output" / timestamp
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[Step 3] Output directory: {output_dir}")
    
    # Step 4: Export JSON
    print("\n[Step 4] Exporting game state to JSON...")
    json_path = output_dir / "game_state.json"
    gm.export_game_state_json(str(json_path))
    print(f"  Saved: {json_path}")
    print(f"  Size: {json_path.stat().st_size:,} bytes")
    
    # Step 5: Export JPEG
    print("\n[Step 5] Exporting game board to JPEG...")
    jpeg_path = output_dir / "game_board.jpeg"
    gm.export_board_image(str(jpeg_path), dpi=150)
    print(f"  Saved: {jpeg_path}")
    print(f"  Size: {jpeg_path.stat().st_size:,} bytes")
    
    # Step 6: Print game summary
    print("\n" + "=" * 70)
    print(" GAME SUMMARY")
    print("=" * 70)
    print(f"\nTurn: {state.get_turn_string()} ({state.phase.value.capitalize()} Phase)")
    print(f"\nPowers and their starting positions:")
    
    for power in sorted(state.powers):
        units = state.get_units_for_power(power)
        sc_count = state.get_sc_count(power)
        print(f"\n  {power}: {len(units)} units, {sc_count} supply centers")
        for unit in units:
            print(f"    - {unit}")
    
    print("\n" + "=" * 70)
    print(" SUCCESS: Game board generated and ready for first turn!")
    print("=" * 70)
    print(f"\nOutputs saved to: {output_dir}")
    print(f"  - {json_path.name}: Game state in JSON format")
    print(f"  - {jpeg_path.name}: Visual game board")
    
    return gm, str(json_path), str(jpeg_path)


def load_existing_game(json_path: str):
    """
    Load an existing game from a JSON file.
    
    Args:
        json_path: Path to the game state JSON file
        
    Returns:
        GameManager with loaded game
    """
    import json
    from game import GameManager
    
    print(f"Loading game from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Create game manager from saved map data
    gm = GameManager(map_data=data['map_data'])
    
    # Restore the game state
    from game.game_state import GameState
    gm.state = GameState.from_dict(data['game_state'], data['map_data'])
    gm.history = data.get('history', [])
    
    print(f"  Loaded: {gm.state.get_turn_string()} ({gm.state.phase.value})")
    print(f"  Units: {len(gm.state.units)}")
    
    return gm


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--load" and len(sys.argv) > 2:
            # Load an existing game
            gm = load_existing_game(sys.argv[2])
        else:
            # Use provided seed
            try:
                seed = int(sys.argv[1])
            except ValueError:
                print(f"Usage: {sys.argv[0]} [seed] or {sys.argv[0]} --load <json_path>")
                sys.exit(1)
            generate_and_initialize_game(seed=seed)
    else:
        # Generate new game with default seed
        generate_and_initialize_game(seed=42)
