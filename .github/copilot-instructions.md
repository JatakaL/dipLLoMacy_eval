# Copilot Instructions

## Project Overview

dipLLoMacy_eval is a Diplomacy board game evaluation framework. It generates randomized Diplomacy maps via a 7-phase pipeline and will eventually support LLM-based agents playing the game with negotiation, strategic reasoning, and simultaneous order resolution.

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

### Visualization

- `map_viewer.py` — interactive GUI (matplotlib + tkinter)
- `map_viewer_cli.py` — CLI renderer for terminal output

### Planned Modules (not yet implemented)

- **Game Engine** (`game/`) — GameState, Unit, Order classes; movement rules; turn processing (spring/fall/winter); victory conditions
- **LLM Agents** (`llm/`) — adapters for OpenAI, Anthropic, and local models; prompt engineering for state representation and strategy
- **Evaluation** (`evaluation/`) — performance metrics, strategic quality, diplomatic quality, batch benchmarking

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
- Tests live in the project root as `test_*.py` files using plain `assert` statements
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
- `docs/PLAN_GAME_ELEMENTS.md` — roadmap for Diplomacy game mechanics implementation
- `docs/PLAN_LLM_INTEGRATION.md` — roadmap for LLM agent integration and evaluation framework
- `docs/REFACTORING_SUMMARY.md` — architecture evolution from monolithic to phased design
