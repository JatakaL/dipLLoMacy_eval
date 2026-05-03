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

## LLM Agent Framework

The `llm/` module provides a modular adapter system for connecting any LLM (or non-LLM baseline) to the Diplomacy game engine. The design follows a plugin pattern: implement a small interface, register your adapter with the game moderator, and the framework handles the rest.

### Architecture overview

```
┌─────────────────────────┐
│     GameModerator        │  Drives the game loop: collects orders,
│  (llm/moderator.py)      │  feeds them to the engine, handles
└────────┬────────────────┘  retreats & winter adjustments.
         │ calls generate_orders() / generate_diplomacy_message()
         ▼
┌─────────────────────────┐
│   BaseLLMAdapter (ABC)   │  Abstract interface every adapter implements.
│  (llm/adapters/base.py)  │
└────────┬────────────────┘
         │ concrete implementations
    ┌────┴──────────┐
    ▼               ▼
MockLLMAdapter  RandomLLMAdapter   (future: OpenAI, Anthropic, local …)
```

### Key components

| File | Role |
|------|------|
| [`llm/adapters/base.py`](llm/adapters/base.py) | `BaseLLMAdapter` — abstract base class defining `generate_orders()` and `generate_diplomacy_message()` |
| [`llm/adapters/mock_adapter.py`](llm/adapters/mock_adapter.py) | `MockLLMAdapter` — deterministic hold-all adapter for unit tests (no API calls) |
| [`llm/adapters/random_adapter.py`](llm/adapters/random_adapter.py) | `RandomLLMAdapter` — random valid-move baseline for evaluation benchmarks |
| [`llm/moderator.py`](llm/moderator.py) | `GameModerator` — orchestrator that pairs adapters with powers and runs the game loop |

### Implementing a new adapter

1. Create a new file under `llm/adapters/` (e.g. `openai_adapter.py`).
2. Subclass `BaseLLMAdapter` and implement the two abstract methods:

```python
from llm.adapters.base import BaseLLMAdapter

class OpenAIAdapter(BaseLLMAdapter):
    def generate_orders(self, game_state_dict, power, board_image_path=None):
        # Call your LLM with the game state and return order strings
        # e.g. ["A {Paris} M {Burgundy}", "F {Brest} H"]
        ...

    def generate_diplomacy_message(self, game_state_dict, sender, recipient):
        # Return a natural-language message string
        ...
```

3. Register the adapter with the `GameModerator`:

```python
from game import GameManager
from llm import GameModerator

gm = GameManager(map_data=map_data)
gm.initialize_game()
agents = {power: OpenAIAdapter() for power in gm.state.powers}
moderator = GameModerator(gm, agents)
moderator.run_game(max_turns=20)
```

### How the moderator uses adapters

Each turn, `GameModerator.run_turn()`:

1. Calls `adapter.generate_orders(game_state_dict, power)` on every agent.
2. Parses returned order strings via `OrderParser`.
3. Submits all orders to `GameManager.process_turn()` for resolution.
4. Auto-disbands dislodged units with no retreat options.
5. Advances the game phase.

The higher-level `GameModerator.run_game()` repeats this cycle through ORDER → RETREAT → BUILD phases until a winner emerges or `max_turns` is reached.

### What's implemented vs. planned

- **Implemented:** `BaseLLMAdapter`, `MockLLMAdapter`, `RandomLLMAdapter`, `GameModerator`
- **Planned:** Provider-specific adapters (OpenAI, Anthropic, local models), diplomacy negotiation phase in the moderator, evaluation metrics and benchmarking (`evaluation/` module)

For the full integration roadmap see [docs/PLAN_LLM_INTEGRATION.md](docs/PLAN_LLM_INTEGRATION.md).

## Project Status

| Component | Status |
|-----------|--------|
| Map generation pipeline | ✅ Complete |
| Topology data model | ✅ Complete |
| Game engine (orders, resolution, retreats, builds) | ⚠️ Core functional — edge cases under review |
| LLM agent framework (moderator, adapter interface) | ✅ Core complete |
| Random & mock baseline agents | ✅ Complete |
| Visualization (map viewer, game viewer, order viewer) | ✅ Complete |
| Design decisions & architecture | ✅ See docs/DESIGN_DECISIONS.md |
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
