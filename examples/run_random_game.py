#!/usr/bin/env python3
"""
Example: Run a Diplomacy game with random-order agents.

Generates a map, initialises a game, assigns a RandomLLMAdapter to every
power, runs GameModerator.run_game(max_turns=10), and prints the summary.
"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.join(Path(__file__).parent.parent, "map_gen", "phases"))

from orchestrator import run_full_pipeline
from game import GameManager
from llm import GameModerator, RandomLLMAdapter


def main(seed: int = 42, max_turns: int = 10) -> dict:
    """Generate a map, run a full random game, and print the summary.

    Args:
        seed: Random seed used for both map generation and the adapters.
        max_turns: Maximum number of ORDER-phase turns to play.

    Returns:
        The summary dict produced by ``GameModerator.run_game``.
    """
    print("=" * 70)
    print(" RANDOM-AGENT DIPLOMACY GAME")
    print("=" * 70)

    # --- Step 1: Generate a map ---
    print("\n[1] Generating map …")
    config = {
        "num_cells": 80,
        "num_powers": 7,
        "territory_size": 3,
        "num_neutral_scs": 13,
        "land_ratio": 0.6,
        "seed": seed,
    }
    map_data = run_full_pipeline(config, output_dir=None, save_intermediate=False)
    print(f"    {len(map_data.get('powers', {}))} powers on the map")

    # --- Step 2: Initialise the game ---
    print("\n[2] Initialising game …")
    gm = GameManager(map_data=map_data)
    state = gm.initialize_game()
    print(f"    {state.get_turn_string()} | {len(state.units)} units")

    # --- Step 3: Assign random adapters ---
    print("\n[3] Assigning RandomLLMAdapter to every power …")
    agents = {power: RandomLLMAdapter(seed=seed) for power in state.powers}
    moderator = GameModerator(gm, agents)

    # --- Step 4: Run the game ---
    print(f"\n[4] Running game (max {max_turns} turns) …")
    summary = moderator.run_game(max_turns=max_turns)

    # --- Step 5: Print summary ---
    print("\n" + "=" * 70)
    print(" GAME SUMMARY")
    print("=" * 70)
    print(f"\n  Turns played : {summary['turns_played']}")
    print(f"  Winner       : {summary['winner'] or 'None (game ended by turn limit)'}")
    print("\n  Final supply-center counts:")
    for power, count in sorted(
        summary["final_sc_counts"].items(), key=lambda x: -x[1]
    ):
        print(f"    {power:20s} : {count}")

    return summary


if __name__ == "__main__":
    game_seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    main(seed=game_seed)
