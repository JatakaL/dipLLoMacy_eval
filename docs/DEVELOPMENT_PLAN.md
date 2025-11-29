# dipLLoMacy_eval Development Plan

This document outlines the roadmap for completing the Diplomacy evaluation system, including game elements and LLM integration.

## Current Status

### Map Generation (Complete ✓)

The map generation system is fully implemented with 7 phases:

1. **Phase 1: Mesh Generation** - Voronoi tessellation with Poisson disk sampling
2. **Phase 2: Terrain Assignment** - Land/sea classification with noise-based generation
3. **Phase 3: Province Definition** - Coastline identification and ocean grouping
4. **Phase 4: Kingdom Generation** - Balanced starting positions for players
5. **Phase 5: Supply Center Distribution** - Strategic SC placement
6. **Phase 6: Graph Analysis** - Map quality validation
7. **Phase 7: Naming and Visualization** - Province naming and fractal edge subdivision

### What's Missing

1. **Game Engine** - No game mechanics (units, orders, resolution)
2. **Turn Structure** - No turn phases or game flow
3. **LLM Integration** - No LLM interfaces for evaluation

---

## Development Phases

### Phase 1: Game Engine Core (Priority: High)

Create the core Diplomacy game engine that can:

#### 1.1 Unit System
```
game/
├── __init__.py
├── units.py          # Unit types and placement
├── orders.py         # Order types and validation
├── resolution.py     # Order resolution algorithm
├── game_state.py     # Game state management
└── rules.py          # Diplomacy rules engine
```

**Unit Types:**
- `Army` - Can move on land, can be convoyed across sea
- `Fleet` - Can move on sea and coastal provinces

**Unit Data Structure:**
```python
{
    "id": "unit_001",
    "type": "army",          # "army" or "fleet"
    "power": "Power1",       # Owning power
    "location": "C23",       # Province ID
    "coast": null            # For fleets on coasts with multiple coasts
}
```

#### 1.2 Order System

**Order Types:**
1. **Hold** - Unit stays in place
2. **Move** - Unit attempts to move to adjacent province
3. **Support** - Unit supports another unit's move or hold
4. **Convoy** - Fleet convoys an army across sea

**Order Data Structure:**
```python
{
    "unit_id": "unit_001",
    "order_type": "move",    # "hold", "move", "support", "convoy"
    "target": "C24",         # Destination for move
    "support_target": null,  # Unit being supported
    "support_destination": null,  # Where support is going
    "convoy_army": null,     # Army being convoyed
    "convoy_via": null       # Sea province for convoy
}
```

#### 1.3 Resolution Algorithm

Implement the standard Diplomacy resolution rules:
- Equal strength units bounce
- Support adds strength
- Convoys require continuous sea path
- Retreats when dislodged
- Builds/disbands based on SC count

### Phase 2: Turn Structure (Priority: High)

#### 2.1 Turn Phases
```
Spring Movement → Spring Retreat → Fall Movement → Fall Retreat → Winter Builds
```

#### 2.2 Game Flow
```python
class GameEngine:
    def __init__(self, map_data):
        self.map = map_data
        self.units = {}
        self.turn = 1
        self.phase = "spring_movement"
        
    def submit_orders(self, power, orders):
        """Submit orders for a power."""
        
    def resolve_turn(self):
        """Resolve all orders and advance phase."""
        
    def get_valid_orders(self, power):
        """Get all valid orders for a power's units."""
```

### Phase 3: LLM Integration (Priority: High)

#### 3.1 Abstract LLM Interface
```python
# llm/
├── __init__.py
├── base.py           # Abstract LLM interface
├── openai_adapter.py # OpenAI API adapter
├── anthropic_adapter.py  # Anthropic API adapter
├── prompts.py        # Prompt templates
└── evaluator.py      # Evaluation harness
```

**Base Interface:**
```python
class LLMInterface(ABC):
    @abstractmethod
    def get_orders(self, game_state: dict, power: str) -> list:
        """Get orders from LLM for a power."""
        
    @abstractmethod
    def get_diplomacy_message(self, game_state: dict, power: str, recipient: str) -> str:
        """Get diplomatic message from LLM."""
```

#### 3.2 Prompt Templates

**Game State Prompt:**
```
You are playing as {power} in a game of Diplomacy.

Current Turn: {turn}
Phase: {phase}

Your Units:
{unit_list}

Your Supply Centers:
{sc_list}

Adjacent Provinces:
{adjacency_info}

Other Powers' Visible Units:
{visible_units}

Provide your orders in the following format:
UNIT_LOCATION: ORDER_TYPE [TARGET]
```

#### 3.3 Evaluation Metrics

Track LLM performance on:
- **Order Validity** - % of valid orders submitted
- **Tactical Soundness** - Quality of tactical decisions
- **Strategic Planning** - Long-term planning effectiveness
- **Diplomatic Skill** - Negotiation and alliance management
- **Win Rate** - Games won vs random/baseline opponents

### Phase 4: Evaluation Harness (Priority: Medium)

#### 4.1 Game Runner
```python
class GameRunner:
    def __init__(self, map_data, players: dict):
        """
        Initialize a game with LLM or human players.
        
        Args:
            map_data: Map JSON from generation
            players: Dict mapping power names to player types
                     {"Power1": LLMPlayer(...), "Power2": HumanPlayer(...)}
        """
        
    def run_game(self, max_turns=50) -> GameResult:
        """Run a complete game and return results."""
```

#### 4.2 Experiment Framework
```python
class Experiment:
    def run_experiment(self, 
                       num_games: int,
                       map_config: dict,
                       player_configs: dict) -> ExperimentResults:
        """Run multiple games and aggregate results."""
```

---

## Implementation Order

### Week 1: Game Engine Basics
1. ✓ Create `game/` module structure
2. ✓ Implement Unit and Order classes
3. ✓ Implement basic order validation
4. ✓ Add unit tests

### Week 2: Order Resolution
1. Implement resolution algorithm
2. Handle bounces, supports, convoys
3. Implement retreat logic
4. Add unit tests

### Week 3: Turn Structure & Builds
1. Implement complete turn flow
2. Handle winter builds/disbands
3. Victory condition checking
4. Add integration tests

### Week 4: LLM Integration
1. Create LLM interface abstraction
2. Implement OpenAI adapter
3. Create prompt templates
4. Add evaluation metrics

### Week 5: Evaluation Harness
1. Create game runner
2. Implement experiment framework
3. Add result analysis tools
4. Documentation

---

## Testing Strategy

### Unit Tests
- Each module has corresponding test file
- Test order validation thoroughly
- Test resolution edge cases

### Integration Tests
- Full game simulations
- LLM response parsing
- End-to-end workflows

### Evaluation Tests
- Baseline comparisons
- Reproducibility checks
- Performance benchmarks

---

## Dependencies to Add

```
# Core game engine
# No additional dependencies needed (uses stdlib)

# LLM Integration
openai>=1.0.0      # OpenAI API
anthropic>=0.10.0  # Anthropic API

# Testing/Evaluation
pytest>=7.0.0      # Testing framework (already installed)
```

---

## File Structure (Proposed)

```
dipLLoMacy_eval/
├── map_gen/                    # Existing map generation
│   └── phases/
├── game/                       # NEW: Game engine
│   ├── __init__.py
│   ├── units.py
│   ├── orders.py
│   ├── resolution.py
│   ├── game_state.py
│   └── game_engine.py
├── llm/                        # NEW: LLM integration
│   ├── __init__.py
│   ├── base.py
│   ├── openai_adapter.py
│   ├── anthropic_adapter.py
│   ├── prompts.py
│   └── evaluator.py
├── evaluation/                 # NEW: Evaluation harness
│   ├── __init__.py
│   ├── runner.py
│   ├── experiment.py
│   ├── metrics.py
│   └── analysis.py
├── tests/                      # NEW: Organized tests
│   ├── test_game/
│   ├── test_llm/
│   └── test_evaluation/
└── docs/
    ├── DEVELOPMENT_PLAN.md     # This file
    ├── GAME_ENGINE.md          # Game engine documentation
    └── LLM_INTEGRATION.md      # LLM integration guide
```

---

## Success Criteria

1. **Game Engine**
   - Can initialize a game from any generated map
   - Correctly validates all order types
   - Resolves orders according to standard rules
   - Handles complete game flow from start to victory

2. **LLM Integration**
   - Can query any supported LLM provider
   - Parses LLM responses into valid orders
   - Handles errors gracefully

3. **Evaluation**
   - Can run automated games between LLMs
   - Collects meaningful performance metrics
   - Produces reproducible results

---

## Getting Started

To begin development:

```bash
# 1. Create game module
mkdir -p game
touch game/__init__.py

# 2. Run existing tests to ensure nothing breaks
python -m pytest test_topology.py -v

# 3. Generate a test map
cd map_gen/phases && python orchestrator.py --seed 42

# 4. Start implementing game engine
# See game/units.py for first implementation
```
