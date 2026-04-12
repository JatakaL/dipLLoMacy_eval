# dipLLoMacy_eval

**Evaluate LLM strategic reasoning, negotiation, and long-term planning by having them play Diplomacy on procedurally generated maps.**

dipLLoMacy_eval is a framework for benchmarking Large Language Models on the complex, multi-agent challenges that Diplomacy presents: simultaneous decision-making, alliance formation, deception detection, and multi-turn planning. Randomized maps prevent memorization of known openings and force genuine strategic reasoning.

## How It Works

1. **Generate a map** — A 7-phase pipeline produces a unique, balanced Diplomacy map with provinces, supply centers, and kingdoms.
2. **Play a game** — LLM agents (or baselines) control powers, submit orders each turn, and optionally negotiate via diplomacy messages. A game moderator coordinates the agents and the rule engine.
3. **Evaluate** — Collect metrics on strategic quality, order validity, negotiation skill, and win/survival rates across games.

## Quick Start

```bash
# Generate a random map
cd map_gen/phases && python orchestrator.py

# Run a game with random baseline agents
python examples/run_random_game.py --output both

# Replay the game
python game_viewer.py outputs/game_YYYYMMDD_HHMMSS
```

## Project Status

| Component | Status |
|-----------|--------|
| Map generation pipeline | ✅ Complete |
| Topology data model | ✅ Complete |
| Game engine (orders, resolution, retreats, builds) | ✅ Complete |
| LLM agent framework (moderator, adapter interface) | ✅ Core complete |
| Random & mock baseline agents | ✅ Complete |
| Visualization (map viewer, game viewer, order viewer) | ✅ Complete |
| LLM provider adapters (OpenAI, Anthropic, local) | 🔲 Planned |
| Evaluation metrics & benchmarking | 🔲 Planned |

## Documentation

See [docs/README.md](docs/README.md) for the full documentation index, including:

- [LLM Integration Plan](docs/PLAN_LLM_INTEGRATION.md) — evaluation objectives, adapter architecture, metrics, and scenarios
- [Phased Map Generation](docs/PHASED_MAP_GENERATION.md) — the 7-phase pipeline that produces randomized maps
- [Game Elements Plan](docs/PLAN_GAME_ELEMENTS.md) — game engine design and implementation status
- [Game Viewer README](docs/GAME_VIEWER_README.md) — replaying and inspecting completed games

## Tech Stack

- **Language:** Python 3.12+
- **Key libraries:** NumPy, SciPy, Shapely, Matplotlib
- **Package manager:** [uv](https://github.com/astral-sh/uv)

## License

[Unlicense](LICENSE)
