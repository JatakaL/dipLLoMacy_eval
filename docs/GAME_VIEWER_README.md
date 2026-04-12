# Game Viewer & Standardized Game Output

## Overview

The **Game Viewer** provides a unified interface for replaying and exploring
Diplomacy games. Together with the **standardized game output format**, it
enables users to:

1. Run a game and have all artifacts (map, orders, board images, summaries)
   written to a single, well-structured folder.
2. Launch the Game Viewer and click through turns to see the board state,
   orders, and summaries for every phase.

---

## Quick Start

### 1. Run a game and export output

```bash
# From the project root:
python examples/run_random_game.py --output both
```

This generates a timestamped output folder under `outputs/`:

```
outputs/game_20260408_224500/
```

### 2. View the game

**GUI mode** (requires tkinter + matplotlib):

```bash
python game_viewer.py outputs/game_20260408_224500
```

**Text-only mode** (headless / CI):

```bash
python game_viewer.py --text outputs/game_20260408_224500
```

---

## Output Directory Layout

Every game produces a single folder with the following structure:

```
outputs/game_YYYYMMDD_HHMMSS/
├── game_metadata.json        # Powers, config, map summary
├── map.json                  # Full map data used for the game
├── turns/
│   ├── turn_01_Spring_1901/
│   │   ├── orders.json       # Resolved orders for this turn
│   │   ├── orders_view.png   # Map with order overlays (primary replay image)
│   │   ├── state.json        # Game state after resolution
│   │   ├── summary.txt       # Human-readable turn summary
│   │   └── board.jpeg        # Board image (state only, no orders)
│   ├── turn_02_Fall_1901/
│   │   └── ...
│   ├── turn_03_Winter_1901/
│   │   └── ...
│   └── ...
└── result.json               # Final game result (winner, SC counts)
```

### File descriptions

| File | Description |
|------|-------------|
| `game_metadata.json` | Game setup: power names, home SCs, total provinces/SCs, generation config |
| `map.json` | Complete map data (topology, faces, edges, vertices, etc.) |
| `turns/turn_NN_Label/orders.json` | Resolved orders, dislodged units, winter log |
| `turns/turn_NN_Label/orders_view.png` | Map with order overlays — arrows, hold rings, build/disband markers (primary replay image) |
| `turns/turn_NN_Label/state.json` | Serialized `GameState` after resolution |
| `turns/turn_NN_Label/summary.txt` | Human-readable turn summary |
| `turns/turn_NN_Label/board.jpeg` | Board image — state only, no order arrows (best-effort; may be absent on minimal maps) |
| `result.json` | Game outcome: winner, turns played, final SC counts |

### Naming conventions

- **Turn directories** follow the pattern `turn_{NN}_{Label}` where `NN` is
  a zero-padded step number and `Label` is the turn string with spaces
  replaced by underscores (e.g., `Spring_1901`, `Winter_1901`).
- Step numbers are sequential across all phases (ORDER, BUILD), starting
  at `01`.

---

## Game Viewer Interface

### GUI Mode — Unified Map-Centric View

The Game Viewer presents a **single unified view** focused on the map:

- **Map with order overlays** (centre, dominant) — the focal point of the
  viewer. Shows territories colored by owner, units, and order arrows/markers
  (move arrows, hold rings, support dashes, build stars, etc.) all rendered
  directly on the map. Uses `orders_view.png` when available; falls back to
  live rendering from map + state data.
- **Turn list** (left sidebar) — click any turn to jump to it instantly.
- **Navigation buttons** (top bar) — Previous / Next to step through turns.
- **Collapsible text panel** (right side) — shows text orders grouped by
  power and the turn summary. Can be hidden via "Hide Panel" to give the
  map maximum screen space, or shown again with "Show Panel".
- **Result info** (top bar) — game outcome displayed at a glance.

### Text Mode (`--text`)

Prints a structured summary to stdout showing powers, turn list,
winner, and final supply-center counts. No GUI dependencies required.

---

## Programmatic Usage

### Exporting a game

```python
from game import GameManager
from game.game_export import create_game_output_dir, export_full_game
from llm import GameModerator, RandomLLMAdapter

# Set up game
gm = GameManager(map_data=map_data)
gm.initialize_game()
agents = {p: RandomLLMAdapter() for p in gm.state.powers}
moderator = GameModerator(gm, agents)

# Export
output_dir = create_game_output_dir()  # outputs/game_YYYYMMDD_HHMMSS/
summary = export_full_game(
    output_dir=output_dir,
    game_manager=gm,
    moderator=moderator,
    max_turns=10,
    console=True,       # also print to stdout
    config={"seed": 42},
)
```

### Loading a game for analysis

```python
from game.game_export import load_game_output

data = load_game_output("outputs/game_20260408_224500")
print(data["metadata"])       # Powers, config
print(data["result"])         # Winner, final SC counts
for turn in data["turns"]:
    print(turn["label"], turn["orders"])
```

### Individual export functions

The module provides granular functions if you want more control:

```python
from game.game_export import (
    create_game_output_dir,
    write_game_metadata,
    write_map_data,
    write_turn_data,
    write_game_result,
    build_turn_callback,
)
```

---

## Design Decisions

1. **One folder per turn** rather than flat files — makes it trivial to
   enumerate turns and keeps related artifacts together.

2. **Step numbers across all phases** — ORDER and BUILD phases share a
   single counter so the turn list is unambiguous.

3. **Board images are best-effort** — if `export_board_image` fails
   (e.g., on minimal test maps), the turn folder is still valid. The
   viewer gracefully shows "No board image available."

4. **`result.json` excludes history** — the full order history is already
   in per-turn `orders.json` files. Keeping `result.json` lightweight
   makes it easy to scan many games quickly.

5. **`game_metadata.json` at the top level** — enables the viewer (and
   downstream tools) to display power names and map info before loading
   any turn data.

6. **GUI and text modes** — the viewer supports both interactive replay
   and headless text output for CI/scripting environments.
