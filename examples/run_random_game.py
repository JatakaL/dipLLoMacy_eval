#!/usr/bin/env python3
"""
Example: Run a Diplomacy game with random-order agents.

Generates a map, initializes a game, assigns a RandomLLMAdapter to every
power, runs GameModerator.run_game(max_turns=10), and prints the summary.

Turn-by-turn output (orders, board state) can be directed to the console,
to files in an output directory, or both, via the ``--output`` flag.
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
from llm import GameModerator, RandomLLMAdapter, format_turn_summary


def _build_turn_callback(output_mode: str, output_dir: Path | None):
    """Return a callback suitable for ``GameModerator.run_game(turn_callback=...)``.

    The callback prints turn-by-turn summaries and/or writes per-turn
    log files and board images depending on *output_mode*.

    Args:
        output_mode: One of ``"console"``, ``"file"``, or ``"both"``.
        output_dir: Directory for file output (required when
            *output_mode* is ``"file"`` or ``"both"``).
    """

    def _callback(turn_result: dict, moderator: GameModerator,
                  step_number: int) -> None:
        gm = moderator.game_manager
        state = gm.state
        summary_text = format_turn_summary(turn_result, state, gm)

        # --- Console output ---
        if output_mode in ("console", "both"):
            print(summary_text)

        # --- File output ---
        if output_mode in ("file", "both") and output_dir is not None:
            turn_label = turn_result["turn"].replace(" ", "_")
            prefix = f"{step_number:02d}"

            # Write text log
            log_path = output_dir / f"{prefix}_{turn_label}_orders.txt"
            with open(log_path, "w") as f:
                f.write(summary_text + "\n")

            # Write board image
            img_path = output_dir / f"{prefix}_{turn_label}_board.jpeg"
            try:
                gm.export_board_image(str(img_path), dpi=150)
            except (OSError, ValueError, KeyError):
                pass  # Image export may fail on minimal maps

    return _callback


def main(seed: int = 42, max_turns: int = 10, output: str = "console",
         output_dir: str | None = None) -> dict:
    """Generate a map, run a full random game, and print the summary.

    Args:
        seed: Random seed used for both map generation and the adapters.
        max_turns: Maximum number of ORDER-phase turns to play.
        output: Output mode — ``"console"``, ``"file"``, or ``"both"``.
        output_dir: Directory for file output (auto-created if needed).
            Required when *output* is ``"file"`` or ``"both"``.

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

    # --- Prepare output directory if needed ---
    resolved_output_dir: Path | None = None
    if output in ("file", "both"):
        if output_dir is None:
            resolved_output_dir = Path("game_output") / f"random_game_seed{seed}"
        else:
            resolved_output_dir = Path(output_dir)
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n    File output directory: {resolved_output_dir}")

    # --- Step 4: Run the game ---
    print(f"\n[4] Running game (max {max_turns} turns) ...")
    turn_cb = _build_turn_callback(output, resolved_output_dir)
    summary = moderator.run_game(max_turns=max_turns, turn_callback=turn_cb)

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
        print(f"\n  Turn-by-turn files saved to: {resolved_output_dir}")

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
        "--output", choices=["console", "file", "both"], default="console",
        help="Where to send turn-by-turn output (default: console)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Directory for file output (auto-created; required for 'file'/'both')",
    )
    args = parser.parse_args()
    main(
        seed=args.seed,
        max_turns=args.max_turns,
        output=args.output,
        output_dir=args.output_dir,
    )
