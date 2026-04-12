"""
Standardized game output export for Diplomacy games.

Writes all game artifacts (map data, per-turn state, orders, board images,
summaries) into a single well-structured folder so the Game Viewer (and
other downstream tools) can replay and analyze a complete game.

Output directory layout
-----------------------
::

    outputs/game_YYYYMMDD_HHMMSS/
    ├── game_metadata.json        # Powers, config, map summary
    ├── map.json                  # Full map data used for the game
    ├── turns/
    │   ├── turn_01_Spring_1901/
    │   │   ├── state.json        # Game state *after* resolution
    │   │   ├── orders.json       # Resolved orders for this turn
    │   │   ├── orders_view.png   # Map with order overlays (primary replay image)
    │   │   ├── summary.txt       # Human-readable turn summary
    │   │   └── board.jpeg        # Board image (state only, no orders)
    │   ├── turn_02_Fall_1901/
    │   │   └── ...
    │   ├── turn_03_Winter_1901/
    │   │   └── ...
    │   └── ...
    └── result.json               # Final game result summary

Design decisions
~~~~~~~~~~~~~~~~
* One folder per turn, named ``turn_{NN}_{label}`` where *NN* is the
  zero-padded step number and *label* is the turn string with spaces
  replaced by underscores (e.g. ``Spring_1901``).
* ``game_metadata.json`` is written once at game start so the viewer
  can display power names and map info before loading individual turns.
* ``result.json`` is written at game end with final SC counts, winner,
  turns played, etc.
* Board images are best-effort — if ``export_board_image`` fails (e.g.
  on a minimal test map) the turn folder is still valid without it.
* ``orders_view.png`` is the primary replay image, showing the map with
  order overlays (move arrows, hold rings, etc.).  The Game Viewer
  prefers this over ``board.jpeg`` when both are present.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .game_manager import GameManager
from .game_state import GameState


def create_game_output_dir(
    base_dir: str | Path = "outputs",
    timestamp: Optional[str] = None,
) -> Path:
    """Create and return a timestamped game output directory.

    Args:
        base_dir: Parent directory for all game outputs.
        timestamp: Optional explicit timestamp string (``YYYYMMDD_HHMMSS``).
            If *None*, the current UTC time is used.

    Returns:
        Absolute ``Path`` to the created directory, e.g.
        ``outputs/game_20260408_224500/``.
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / f"game_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "turns").mkdir(exist_ok=True)
    return output_dir


def write_game_metadata(
    output_dir: Path,
    game_manager: GameManager,
    config: Optional[dict] = None,
) -> Path:
    """Write ``game_metadata.json`` describing the game setup.

    Args:
        output_dir: Root game output directory.
        game_manager: Initialized game manager.
        config: Optional generation config that was used.

    Returns:
        Path to the written file.
    """
    state = game_manager.state
    powers_info = {}
    for power in sorted(state.powers):
        powers_info[power] = {
            "home_scs": state.get_home_scs(power),
            "initial_units": len(state.get_units_for_power(power)),
        }

    metadata = {
        "created": datetime.now(timezone.utc).isoformat() + "Z",
        "powers": powers_info,
        "total_provinces": len(
            game_manager.map_data.get("topology", {}).get("faces", {})
        ),
        "total_supply_centers": len(state.sc_control),
    }
    if config is not None:
        metadata["generation_config"] = config

    path = output_dir / "game_metadata.json"
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)
    return path


def write_map_data(output_dir: Path, game_manager: GameManager) -> Path:
    """Write the full map JSON used for the game.

    Args:
        output_dir: Root game output directory.
        game_manager: Initialized game manager.

    Returns:
        Path to ``map.json``.
    """
    path = output_dir / "map.json"
    with open(path, "w") as f:
        json.dump(game_manager.map_data, f, indent=2)
    return path


def write_turn_data(
    output_dir: Path,
    step_number: int,
    turn_result: dict,
    state: GameState,
    game_manager: GameManager,
    summary_text: str,
) -> Path:
    """Write all artifacts for a single turn into ``turns/turn_NN_Label/``.

    Args:
        output_dir: Root game output directory.
        step_number: 1-based sequential step counter.
        turn_result: Dict returned by ``GameModerator.run_turn`` or
            the winter-build dict.
        state: Game state *after* resolution.
        game_manager: Game manager (for board image export).
        summary_text: Pre-formatted human-readable summary string.

    Returns:
        Path to the turn sub-directory.
    """
    turn_label = turn_result["turn"].replace(" ", "_")
    turn_dir = output_dir / "turns" / f"turn_{step_number:02d}_{turn_label}"
    turn_dir.mkdir(parents=True, exist_ok=True)

    # orders.json — resolved orders + metadata
    orders_path = turn_dir / "orders.json"
    orders_data = {
        "turn": turn_result["turn"],
        "step_number": step_number,
        "resolved_orders": turn_result.get("resolved_orders", []),
        "dislodged": turn_result.get("dislodged", {}),
        "winter_log": turn_result.get("winter_log"),
    }
    with open(orders_path, "w") as f:
        json.dump(orders_data, f, indent=2)

    # state.json — game state after resolution
    state_path = turn_dir / "state.json"
    with open(state_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)

    # summary.txt — human-readable summary
    summary_path = turn_dir / "summary.txt"
    with open(summary_path, "w") as f:
        f.write(summary_text + "\n")

    # board.jpeg — best-effort board image (state only, no orders)
    try:
        img_path = turn_dir / "board.jpeg"
        game_manager.export_board_image(str(img_path), dpi=150)
    except (OSError, ValueError, KeyError, TypeError):
        pass  # Image export may fail on minimal/test maps

    # orders_view.png — board with order overlays (the primary replay image)
    try:
        from order_viewer import render_order_view
        resolved = turn_result.get("resolved_orders", [])
        if resolved:
            render_order_view(
                map_data=game_manager.map_data,
                orders=resolved,
                turn_label=turn_result.get("turn", ""),
                output_path=str(turn_dir / "orders_view.png"),
                dpi=150,
            )
    except (ImportError, OSError, ValueError, KeyError, TypeError):
        pass  # Order-view export is best-effort

    return turn_dir


def write_game_result(
    output_dir: Path,
    summary: dict,
) -> Path:
    """Write ``result.json`` at the end of the game.

    Args:
        output_dir: Root game output directory.
        summary: The dict returned by ``GameModerator.run_game``.

    Returns:
        Path to ``result.json``.
    """
    # Strip history from result.json (it's large and already in per-turn files)
    result_data = {
        "turns_played": summary["turns_played"],
        "winner": summary.get("winner"),
        "final_sc_counts": summary.get("final_sc_counts", {}),
    }
    path = output_dir / "result.json"
    with open(path, "w") as f:
        json.dump(result_data, f, indent=2)
    return path


def build_turn_callback(
    output_dir: Path,
    console: bool = False,
):
    """Return a turn-callback function that writes standardized output.

    The returned callable has the signature expected by
    ``GameModerator.run_game(turn_callback=...)``.

    Args:
        output_dir: Root game output directory (must already exist).
        console: If *True*, also print summaries to stdout.

    Returns:
        A callback ``(turn_result, moderator, step_number) -> None``.
    """
    # Import here to avoid circular imports at module level
    from llm.moderator import format_turn_summary

    def _callback(
        turn_result: dict,
        moderator,
        step_number: int,
    ) -> None:
        gm = moderator.game_manager
        state = gm.state
        summary_text = format_turn_summary(turn_result, state, gm)

        if console:
            print(summary_text)

        write_turn_data(
            output_dir=output_dir,
            step_number=step_number,
            turn_result=turn_result,
            state=state,
            game_manager=gm,
            summary_text=summary_text,
        )

    return _callback


def export_full_game(
    output_dir: Path,
    game_manager: GameManager,
    moderator,
    max_turns: int = 50,
    console: bool = False,
    config: Optional[dict] = None,
) -> dict:
    """Run a complete game and export all output to *output_dir*.

    Convenience wrapper that ties together metadata writing, the game
    loop (via ``moderator.run_game``), and result writing.

    Args:
        output_dir: Root game output directory (created if needed).
        game_manager: Initialized game manager.
        moderator: ``GameModerator`` instance ready to play.
        max_turns: Maximum ORDER-phase turns.
        console: Print turn summaries to stdout.
        config: Optional generation config dict to store in metadata.

    Returns:
        The summary dict from ``moderator.run_game``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "turns").mkdir(exist_ok=True)

    write_game_metadata(output_dir, game_manager, config=config)
    write_map_data(output_dir, game_manager)

    callback = build_turn_callback(output_dir, console=console)
    summary = moderator.run_game(max_turns=max_turns, turn_callback=callback)

    write_game_result(output_dir, summary)
    return summary


def load_game_output(game_dir: str | Path) -> dict:
    """Load a previously exported game for replay in the Game Viewer.

    Args:
        game_dir: Path to a game output directory
            (e.g. ``outputs/game_20260408_224500``).

    Returns:
        A dict with keys:

        * ``"metadata"`` — contents of ``game_metadata.json``
        * ``"map_data"`` — contents of ``map.json``
        * ``"turns"`` — list of turn dicts sorted by step number, each
          containing ``"step"``, ``"label"``, ``"orders"``, ``"state"``,
          ``"summary"``, and ``"dir"``
        * ``"result"`` — contents of ``result.json`` (or *None*)

    Raises:
        FileNotFoundError: If *game_dir* does not exist or required
            files are missing.
    """
    game_dir = Path(game_dir)
    if not game_dir.is_dir():
        raise FileNotFoundError(f"Game directory not found: {game_dir}")

    # -- metadata --
    meta_path = game_dir / "game_metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"game_metadata.json not found in {game_dir}. "
            "Is this a valid game output directory?"
        )
    with open(meta_path) as f:
        metadata = json.load(f)

    # -- map data --
    map_path = game_dir / "map.json"
    if not map_path.exists():
        raise FileNotFoundError(
            f"map.json not found in {game_dir}. "
            "Is this a valid game output directory?"
        )
    with open(map_path) as f:
        map_data = json.load(f)

    # -- turns --
    turns_dir = game_dir / "turns"
    turns: list[dict] = []
    if turns_dir.is_dir():
        for turn_path in sorted(turns_dir.iterdir()):
            if not turn_path.is_dir():
                continue
            turn_info: dict = {
                "dir": str(turn_path),
                "dir_name": turn_path.name,
            }

            # Parse step number and label from directory name
            # Format: turn_NN_Label
            parts = turn_path.name.split("_", 2)
            if len(parts) >= 3:
                try:
                    turn_info["step"] = int(parts[1])
                except ValueError:
                    turn_info["step"] = 0
                turn_info["label"] = parts[2].replace("_", " ")
            else:
                turn_info["step"] = 0
                turn_info["label"] = turn_path.name

            # Load orders.json
            orders_file = turn_path / "orders.json"
            if orders_file.exists():
                with open(orders_file) as f:
                    turn_info["orders"] = json.load(f)
            else:
                turn_info["orders"] = None

            # Load state.json
            state_file = turn_path / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    turn_info["state"] = json.load(f)
            else:
                turn_info["state"] = None

            # Load summary.txt
            summary_file = turn_path / "summary.txt"
            if summary_file.exists():
                with open(summary_file) as f:
                    turn_info["summary"] = f.read()
            else:
                turn_info["summary"] = None

            # Check for board image
            board_file = turn_path / "board.jpeg"
            turn_info["has_board_image"] = board_file.exists()
            turn_info["board_image_path"] = str(board_file) if board_file.exists() else None

            # Check for order-overlay image (preferred for replay)
            orders_view_file = turn_path / "orders_view.png"
            turn_info["has_orders_view"] = orders_view_file.exists()
            turn_info["orders_view_path"] = str(orders_view_file) if orders_view_file.exists() else None

            turns.append(turn_info)

        turns.sort(key=lambda t: t["step"])

    # -- result --
    result_path = game_dir / "result.json"
    result = None
    if result_path.exists():
        with open(result_path) as f:
            result = json.load(f)

    return {
        "metadata": metadata,
        "map_data": map_data,
        "turns": turns,
        "result": result,
        "game_dir": str(game_dir),
    }
