#!/usr/bin/env python3
"""
Example: Run a Diplomacy game with random-order agents.

Generates a map, initializes a game, assigns a RandomLLMAdapter to every
power, runs GameModerator.run_game(max_turns=10), and prints the summary.

Turn-by-turn output is written to a standardized game output folder
(see ``game/game_export.py`` for the directory layout) that can be
opened directly by the Game Viewer::

    python game_viewer.py outputs/game_20260408_224500

Use ``--output`` to control whether summaries are also printed to the
console, and ``--output-dir`` to override the output location.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.join(Path(__file__).parent.parent, "map_gen", "phases"))

from orchestrator import run_full_pipeline
from game import GameManager
from game.game_export import (
    create_game_output_dir,
    export_full_game,
)
from llm import GameModerator, RandomLLMAdapter


def main(seed: int = 42, max_turns: int = 10, output: str = "both",
         output_dir: str | None = None) -> dict:
    """Generate a map, run a full random game, and print the summary.

    All game artifacts (map, per-turn state/orders/images, result) are
    written to a single output folder using the standardized export
    format so the Game Viewer can load and replay the game.

    Args:
        seed: Random seed used for both map generation and the adapters.
        max_turns: Maximum number of ORDER-phase turns to play.
        output: Output mode — ``"console"`` (print only), ``"file"``
            (write only), or ``"both"`` (default).
        output_dir: Directory for file output (auto-created if needed).
            When *None*, a timestamped directory is created under
            ``outputs/``.

    Returns:
        The summary dict produced by ``GameModerator.run_game``.
    """
    print("=" * 70)
    print(" RANDOM-AGENT DIPLOMACY GAME")
    print("=" * 70)

    # --- Step 1: Generate a map ---
    print("\n[1] Generating map ...")
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
    print("\n[2] Initializing game ...")
    gm = GameManager(map_data=map_data)
    state = gm.initialize_game()
    print(f"    {state.get_turn_string()} | {len(state.units)} units")

    # --- Step 3: Assign random adapters ---
    print("\n[3] Assigning RandomLLMAdapter to every power ...")
    agents = {power: RandomLLMAdapter(seed=seed) for power in state.powers}
    moderator = GameModerator(gm, agents)

    # --- Prepare output directory ---
    console = output in ("console", "both")
    write_files = output in ("file", "both")

    if write_files:
        if output_dir is not None:
            resolved_output_dir = Path(output_dir)
            resolved_output_dir.mkdir(parents=True, exist_ok=True)
            (resolved_output_dir / "turns").mkdir(exist_ok=True)
        else:
            resolved_output_dir = create_game_output_dir(base_dir="outputs")
        print(f"\n    Output directory: {resolved_output_dir}")
    else:
        resolved_output_dir = None

    # --- Step 4: Run the game ---
    print(f"\n[4] Running game (max {max_turns} turns) ...")

    if write_files and resolved_output_dir is not None:
        summary = export_full_game(
            output_dir=resolved_output_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=max_turns,
            console=console,
            config=config,
        )
    else:
        # Console-only: use the old callback approach
        from llm import format_turn_summary

        def _console_cb(turn_result, mod, step):
            text = format_turn_summary(turn_result, mod.game_manager.state,
                                       mod.game_manager)
            print(text)

        summary = moderator.run_game(
            max_turns=max_turns,
            turn_callback=_console_cb if console else None,
        )

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

    if resolved_output_dir is not None:
        print(f"\n  Game output saved to: {resolved_output_dir}")
        print(f"  View with:  python game_viewer.py {resolved_output_dir}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a Diplomacy game with random-order agents.",
    )
    parser.add_argument(
        "seed", nargs="?", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--max-turns", type=int, default=10,
        help="Maximum ORDER-phase turns to play (default: 10)",
    )
    parser.add_argument(
        "--output", choices=["console", "file", "both"], default="both",
        help="Where to send turn-by-turn output (default: both)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Directory for file output (auto-created; default: outputs/game_TIMESTAMP/)",
    )
    args = parser.parse_args()
    main(
        seed=args.seed,
        max_turns=args.max_turns,
        output=args.output,
        output_dir=args.output_dir,
    )
