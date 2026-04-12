# Copilot Instructions

## Project Overview

dipLLoMacy_eval evaluates Large Language Models on strategic reasoning, negotiation, and long-term planning by having them play the board game Diplomacy. Randomized maps (generated via a 7-phase pipeline) prevent memorization and force genuine reasoning. The framework includes a full game engine with turn processing and order resolution, and a modular LLM agent interface for running evaluations.

## Architecture

### Map Generation Pipeline (`map_gen/phases/`)

Seven sequential phases, each reading the previous phase's JSON output:

1. **Mesh** (`phase1_mesh.py`) — Poisson-disk sampling → Voronoi diagram → optional Lloyd relaxation
2. **Terrain** (`phase2_terrain.py`) — Perlin noise + radial gradient → land/sea classification → island/lake culling
3. **Provinces** (`phase3_provinces.py`) — Coastal/inland classification, ocean grouping, impassable zones
4. **Kingdoms** (`phase4_kingdoms.py`) — Equidistant coastal seeds → simultaneous BFS territory growth → balance verification
5. **Supply Centers** (`phase5_supply_centers.py`) — Home SC marking, strategic neutral placement
6. **Optimization** (`phase6_optimization.py`) — Quality metrics: node degree, sea connectivity, triangle density, Belgium factor
7. **Naming** (`phase7_naming.py`) — Markov name generation, adjacency lists, final `map.json` output

The orchestrator (`map_gen/phases/orchestrator.py`) runs all phases end-to-end.

### Topology Module (`map_gen/topology.py`, `map_gen/topology_utils.py`)

Core data model uses a face-edge-vertex topological structure:

- **Vertex** — geometric point `(x, y)`
- **Edge** — connects two vertices; references `left_face` / `right_face`; typed as land, sea, coast, or map-edge
- **Border** — ordered list of edges forming a boundary between two faces
- **Face** — territory with a type (land / sea / impassable) and a list of borders

### Game Engine (`game/`)

Fully implemented Diplomacy game mechanics:

- `game_state.py` — GameState class tracking turn, season, phase, units, ownership, and supply center control
- `units.py` — Unit and UnitType (Army / Fleet)
- `orders.py` — Order, OrderType (Hold, Move, Support, Convoy, Retreat, Build, Disband), OrderResult, and OrderParser
- `resolver.py` — OrderResolver implementing standard Diplomacy adjudication (support cutting, standoffs, dislodgement, head-to-head battles)
- `validators.py` — OrderValidator for territory existence, adjacency, unit type constraints, and convoy path validation
- `game_manager.py` — GameManager providing initialization, turn processing (spring/fall), retreat handling, winter adjustments (build/disband), state export (JSON and JPEG)
- `game_export.py` — standardized output directory creation, full game export, and game loading

### LLM Agent Framework (`llm/`)

Modular adapter system for connecting LLM agents to the game engine:

- `adapters/base.py` — BaseLLMAdapter ABC defining `generate_orders()` and `generate_diplomacy_message()`
- `adapters/random_adapter.py` — RandomLLMAdapter for baseline evaluation (random valid moves)
- `adapters/mock_adapter.py` — MockAdapter for testing without API calls
- `moderator.py` — GameModerator connecting adapters to the game engine, orchestrating turn collection and result distribution

Provider-specific adapters (OpenAI, Anthropic, local models) are not yet implemented; the framework is designed for them to be added as plugins.

### Visualization

- `map_viewer.py` — interactive map GUI (matplotlib + tkinter) with tab interface and phase auto-detection
- `map_viewer_cli.py` — CLI batch renderer for terminal output
- `game_viewer.py` — game replay viewer with map-centric order overlays and turn navigation
- `order_viewer.py` — order visualization library rendering arrows, hold shields, support dashes, and build/disband markers

### Planned Modules (not yet implemented)

- **Evaluation** (`evaluation/`) — performance metrics, strategic quality, diplomatic quality, batch benchmarking
- **LLM Provider Adapters** — OpenAI, Anthropic, and local model adapters for `llm/adapters/`

## Tech Stack

- **Language:** Python 3.12+
- **Key libraries:** NumPy, SciPy (`spatial.Voronoi`), Shapely, Matplotlib
- **Package manager:** Always use `uv` — never use `pip`, `pip install`, or `pip freeze`
- **Data interchange:** JSON between all pipeline phases
- **GUI framework:** tkinter (standard library) with matplotlib TkAgg backend

## Coding Conventions

- Snake_case for functions, methods, variables, and module filenames
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- Type hints on function signatures
- Module-level docstrings describing purpose and overview
- Imports grouped: stdlib first, then third-party
- Prefer `pathlib.Path` over `os.path`
- Tests live in the project root as `test_*.py` files and in the `tests/` subdirectory, using plain `assert` statements
- Documentation in `docs/` as Markdown files with UPPER_SNAKE_CASE names

## Domain Concepts

- **Diplomacy** — a strategy board game with simultaneous order resolution (all players submit orders before any resolve)
- **Provinces** — map territories; can be land, sea, or coastal
- **Supply Centers (SCs)** — key provinces that determine unit counts and victory
- **Kingdoms/Powers** — player-controlled territories grown via BFS from coastal seeds
- **Belgium Factor** — metric for contested neutral provinces between powers (named after the famously fought-over Belgium in classic Diplomacy)
- **Negotiation Phases** — periods where players communicate before submitting orders (critical for LLM agent evaluation)

## Key Documentation

- `docs/README.md` — documentation index and quick-start commands
- `docs/PHASED_MAP_GENERATION.md` — complete pipeline guide with parameters and examples
- `docs/TOPOLOGY_STRUCTURE.md` — face-edge-vertex data structure specification
- `docs/PLAN_GAME_ELEMENTS.md` — game mechanics implementation status
- `docs/PLAN_LLM_INTEGRATION.md` — LLM agent integration and evaluation framework roadmap
- `docs/REFACTORING_SUMMARY.md` — architecture evolution from monolithic to phased design
- `docs/GAME_VIEWER_README.md` — game replay viewer and standardized output format
- `docs/MAP_VIEWER_README.md` — GUI and CLI map viewer user guide
- `docs/MERGE_SPLIT_IMPLEMENTATION.md` — face merging and splitting for topology manipulation
- `docs/OUTPUT_STRUCTURE_CHANGES.md` — output directory organization
- `docs/TOPOLOGY_MIGRATION_SUMMARY.md` — migration from cell-centric to topological data structure
- `docs/PLAN_MAP_COMPLETION.md` — map generation completion status and optional enhancements
