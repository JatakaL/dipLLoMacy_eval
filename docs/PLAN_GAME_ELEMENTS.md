# Plan: Adding Game Elements

## Overview

This document outlines the plan for implementing Diplomacy game mechanics on top of the generated maps. The goal is to create a functional game engine that can process orders, resolve conflicts, and track game state.

## Game Elements to Implement

### Phase 1: Core Data Structures ✅

#### 1.1 Game State

Create a `GameState` class that tracks:

- [x] **Turn Number**: Current game turn (Spring 1901, Fall 1901, etc.)
- [x] **Phase**: Current game phase (Order, Retreat, Build)
- [x] **Unit Positions**: Map of province → unit
- [x] **Province Ownership**: Map of province → power (for supply centers)
- [x] **Supply Center Control**: Which power controls each SC
- [x] **Unit Counts**: Number of units per power

```python
# Implemented in game_state.py
class GameState:
    def __init__(self, map_data):
        self.turn = 1
        self.year = 1901
        self.season = "spring"  # spring, fall, winter
        self.phase = "order"     # order, retreat, build
        self.units = {}          # province_id -> Unit
        self.ownership = {}      # province_id -> power_id
        self.sc_control = {}     # sc_province_id -> power_id
```

#### 1.2 Unit Types

- [x] **Army**: Moves on land, can be convoyed across water
- [x] **Fleet**: Moves on water and coastal provinces

```python
# Implemented in units.py
class Unit:
    def __init__(self, unit_type, power, location):
        self.type = unit_type    # "army" or "fleet"
        self.power = power       # Power ID
        self.location = location # Province ID
        self.dislodged = False   # Set during retreat phase
```

#### 1.3 Order Types

- [x] **Hold**: Unit stays in place
- [x] **Move**: Unit attempts to move to adjacent province
- [x] **Support**: Unit supports another unit's hold or move
- [x] **Convoy**: Fleet transports army across water
- [x] **Build**: Create new unit at home SC (winter only)
- [x] **Disband**: Remove unit (winter or retreat phase)
- [x] **Retreat**: Move dislodged unit to valid province

```python
# Implemented in orders.py
class Order:
    def __init__(self, unit, order_type, target=None, support_target=None):
        self.unit = unit
        self.type = order_type
        self.target = target          # For move/convoy
        self.support_target = support_target  # For support orders
```

### Phase 2: Movement Rules ✅

#### 2.1 Adjacency Validation

- [x] Validate moves based on map adjacency
- [x] Handle coastal province restrictions (fleets can only access via coast)
- [x] Validate convoy paths (continuous chain of fleets)

#### 2.2 Conflict Resolution

Implement the standard Diplomacy conflict resolution algorithm:

- [x] **Strength Calculation**: Base strength + support count
- [x] **Cut Support**: Attacks on supporting units cut support
- [x] **Standoffs**: Equal strength results in no movement
- [x] **Dislodgement**: Successful attacks dislodge defenders
- [x] **Convoy Disruption**: Attacked fleets may break convoy chains
- [x] **Self-Dislodgement Prevention**: Cannot dislodge own units
- [x] **Head-to-Head Battles**: Special rules for units attacking each other

```python
# Implemented in resolver.py
class OrderResolver:
    def __init__(self, game_state, orders):
        self.state = game_state
        self.orders = orders
        
    def resolve(self):
        # 1. Validate all orders
        # 2. Calculate support
        # 3. Resolve conflicts
        # 4. Apply successful moves
        # 5. Mark dislodged units
        # 6. Return new game state
        pass
```

### Phase 3: Turn Processing (Partial ✅)

#### 3.1 Spring/Fall Movement Turns

- [x] Accept orders from all powers (via order files)
- [x] Resolve all orders simultaneously
- [x] Process retreats for dislodged units
- [ ] Update supply center control (fall only) - partially implemented

#### 3.2 Winter Adjustment Phase

- [ ] Calculate supply center counts per power
- [ ] Allow builds if SC count > unit count
- [ ] Force disbands if unit count > SC count
- [ ] Validate builds occur at unoccupied home SCs

#### 3.3 Victory Conditions

- [x] Track SC control per power
- [x] Check for victory (18+ SCs in standard game)
- [x] Detect elimination (0 SCs)

### Phase 4: Game Engine API ✅

#### 4.1 Game Manager

- [x] Initialize game from map JSON
- [x] Accept orders from players/AI (via order files)
- [x] Process turns
- [x] Provide game state queries
- [x] Export game history

```python
# Implemented in game_manager.py
class GameManager:
    def __init__(self, map_path):
        self.map_data = load_map(map_path)
        self.state = GameState(self.map_data)
        self.history = []
        
    def submit_orders(self, power, orders):
        """Submit orders for a power"""
        pass
        
    def process_turn(self):
        """Resolve all orders and advance game state"""
        pass
        
    def get_game_state(self):
        """Return current game state (JSON-serializable)"""
        pass
        
    def export_board_image(self, output_path):
        """Export current board state as JPEG with units and ownership"""
        pass
```

#### 4.2 Order Parser ✅

- [x] Parse order strings (e.g., "A {Territory} M {Target}", "F {Sea} C A {From} M {To}")
- [x] Validate order syntax
- [x] Map province names to IDs

#### 4.3 State Serialization ✅

- [x] Export game state to JSON
- [x] Import game state from JSON
- [x] Export game history for replay
- [x] **Export board image (JPEG)**: Render current game state as image with units and ownership

## File Structure

```
dipLLoMacy_eval/
├── game/
│   ├── __init__.py           # ✅ Module exports
│   ├── game_state.py         # ✅ GameState class
│   ├── units.py              # ✅ Unit classes (Army, Fleet)
│   ├── orders.py             # ✅ Order classes and parser
│   ├── resolver.py           # ✅ Order resolution logic
│   ├── game_manager.py       # ✅ Main game engine API
│   └── validators.py         # ✅ Move validation utilities
├── tests/
│   ├── test_game.py          # ✅ Game module tests
│   └── test_orders.py        # ✅ Order parsing tests
└── examples/
    ├── example_game.py       # ✅ Example game initialization
    └── example_turn_processing.py  # ✅ Turn processing demo
```

## Implementation Order

1. **Week 1**: Core Data Structures
   - GameState, Unit, Order classes
   - Basic map loading and initialization
   - Unit tests for data structures

2. **Week 2**: Movement Validation
   - Adjacency-based move validation
   - Fleet coastal restrictions
   - Convoy path validation
   - Unit tests for validation

3. **Week 3**: Conflict Resolution
   - Support calculation
   - Conflict resolution algorithm
   - Dislodgement handling
   - Comprehensive unit tests

4. **Week 4**: Turn Processing
   - Full turn cycle implementation
   - Winter adjustment phase
   - Victory/elimination detection
   - Integration tests

5. **Week 5**: API and Polish
   - Game Manager API
   - Order parser
   - State serialization
   - Documentation and examples

## Dependencies

### Required
- `json` (built-in): Game state serialization
- `typing` (built-in): Type hints
- `dataclasses` (built-in): Data structure definitions
- `enum` (built-in): Order types, seasons, phases

### Optional
- `pytest`: Testing framework
- `pydantic`: Data validation (consider for complex state)

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Cover edge cases in conflict resolution
- Test order parsing and validation

### Integration Tests
- Test full turn cycles
- Test multi-turn games
- Test standard Diplomacy scenarios

### Regression Tests
- Test known Diplomacy edge cases
- Compare results with reference implementations
- Test with various map configurations

## Success Criteria

- [x] Can initialize a game from any generated map
- [x] Can process all standard Diplomacy order types
- [x] Correctly resolves complex multi-unit conflicts
- [x] Handles retreat and build phases (retreat phase complete, build phase pending)
- [x] Detects victory and elimination conditions
- [x] Exports game state for LLM consumption (JSON and JPEG image)

## Integration with LLM Evaluation

The game engine must provide:

1. **State Description**: JSON representation of current game state ✅
2. **Board Image**: JPEG rendering of the board with units, ownership, and supply centers ✅
3. **Order Submission**: Accept orders as strings ✅
4. **Result Reporting**: Outcome of each order (succeeded/failed/cut) ✅

**Note**: LLMs must determine valid orders themselves from the JSON or board image - the engine does not provide a pre-computed list of valid moves.

This forms the foundation for the LLM evaluation framework described in `PLAN_LLM_INTEGRATION.md`.

## Order Format

Orders use the following format (territory names must be enclosed in braces `{}`):

```
A {Territory} H                    - Hold
A {Territory} M {Target}           - Move
A {Territory} S A {Unit} M {To}    - Support move
A {Territory} S A {Unit} H         - Support hold
F {Territory} C A {From} M {To}    - Convoy
```

Example orders:
- `A {Karwyn} M {Falmere}` - Army in Karwyn moves to Falmere
- `F {Dark Narrows} H` - Fleet in Dark Narrows holds
- `A {Harell} S A {Karwyn} M {Falmere}` - Army in Harell supports army in Karwyn moving to Falmere
- `F {Narrow Passage} C A {Derpeak} M {Karwyn}` - Fleet in Narrow Passage convoys army in Derpeak to Karwyn

## Usage Example

See `example_turn_processing.py` for a complete demonstration of:
1. Generating a game board and exporting JPEG
2. Writing order files for each power
3. Processing a turn using the order files
4. Handling retreats
5. Generating resolution logs
