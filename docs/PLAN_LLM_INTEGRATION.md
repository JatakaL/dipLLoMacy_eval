# Plan: LLM Integration for Evaluation

## Overview

This document outlines the plan for integrating Large Language Models (LLMs) into the Diplomacy game framework for evaluation purposes. The goal is to create a system that can assess LLM capabilities in strategic reasoning, negotiation, and gameplay.

## Objectives

1. **Strategic Reasoning**: Evaluate LLMs' ability to make sound tactical decisions
2. **Negotiation Skills**: Assess communication and alliance-building capabilities
3. **Long-term Planning**: Measure ability to plan multiple turns ahead
4. **Adaptability**: Test response to changing game situations
5. **Diplomatic Communication**: Evaluate natural language diplomacy messages

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Evaluation Framework                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  LLM Agent  │  │  LLM Agent  │  │  LLM Agent  │  ...         │
│  │  (Power 1)  │  │  (Power 2)  │  │  (Power 3)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│                 ┌────────▼────────┐                              │
│                 │  Game Moderator  │                             │
│                 │  (Coordinator)   │                             │
│                 └────────┬────────┘                              │
│                          │                                       │
│                 ┌────────▼────────┐                              │
│                 │   Game Engine    │                             │
│                 │ (from PLAN_GAME_ELEMENTS) │                    │
│                 └────────┬────────┘                              │
│                          │                                       │
│                 ┌────────▼────────┐                              │
│                 │    Map Data      │                             │
│                 └──────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Components to Implement

### Phase 1: LLM Interface Layer

#### 1.1 LLM Adapter Interface

Create an abstract interface for LLM communication:

- [ ] Define base LLM adapter class
- [ ] Support multiple LLM providers (OpenAI, Anthropic, local models)
- [ ] Handle rate limiting and retries
- [ ] Log all prompts and responses

```python
# Proposed structure (llm_adapters/base.py)
from abc import ABC, abstractmethod

class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate_orders(self, game_state, power, board_image_path=None):
        """Generate orders for a power given game state and optional board image"""
        pass
    
    @abstractmethod
    def generate_diplomacy_message(self, game_state, sender, recipient):
        """Generate a diplomacy message to another power"""
        pass
    
    @abstractmethod
    def evaluate_position(self, game_state, power):
        """Generate strategic analysis of current position"""
        pass
```

#### 1.2 Provider-Specific Adapters

- [ ] **OpenAI Adapter**: GPT-4, GPT-4-turbo, GPT-3.5
- [ ] **Anthropic Adapter**: Claude 3, Claude 2
- [ ] **Local Model Adapter**: LLaMA, Mistral via API
- [ ] **Mock Adapter**: For testing without API calls

```python
# Proposed structure (llm_adapters/openai_adapter.py)
class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, model="gpt-4", api_key=None):
        self.model = model
        self.client = OpenAI(api_key=api_key)
    
    def generate_orders(self, game_state, power, board_image_path=None):
        prompt = self._build_order_prompt(game_state, power)
        # Attach board_image_path for multimodal models (GPT-4V, etc.)
        response = self.client.chat.completions.create(...)
        return self._parse_orders(response)
```

### Phase 2: Prompt Engineering

#### 2.1 State Representation Prompts

Design prompts that effectively communicate game state:

- [ ] **Map Description**: Province names, adjacencies, terrain types
- [ ] **Unit Positions**: All units on the board with owners
- [ ] **Supply Centers**: Control status of all SCs
- [ ] **Board Image**: JPEG rendering of current game state
- [ ] **Game History**: Recent moves and outcomes

**Note**: LLMs must infer valid orders from the game state (JSON or image) - no pre-computed list is provided.

```python
# Proposed structure (prompts/state_prompt.py)
def build_state_prompt(game_state, power, board_image_path=None):
    prompt = f"""
You are playing as {power} in a game of Diplomacy.

Current Turn: {game_state.season} {game_state.year}

Your Units:
{format_units(game_state, power)}

All Units on the Board:
{format_all_units(game_state)}

Supply Centers:
{format_supply_centers(game_state)}

Based on the game state (and board image if provided), determine your valid moves and submit orders for all your units.
"""
    return prompt, board_image_path  # Image attached separately for multimodal LLMs
```

#### 2.2 Strategic Prompts

- [ ] **Position Analysis**: Assess strengths and weaknesses
- [ ] **Threat Assessment**: Identify potential enemies
- [ ] **Alliance Strategy**: Suggest diplomatic approaches
- [ ] **Multi-Turn Planning**: Plan ahead for future turns

#### 2.3 Diplomacy Prompts

- [ ] **Alliance Proposals**: Suggest specific alliances
- [ ] **Threat Detection**: Analyze messages for lies/threats
- [ ] **Negotiation**: Make and evaluate deals
- [ ] **Message Generation**: Write diplomatic messages

### Phase 3: Game Moderator

#### 3.1 Turn Orchestration

- [ ] Initialize game with LLM agents
- [ ] Collect orders from all agents
- [ ] Process diplomacy phase
- [ ] Submit orders to game engine
- [ ] Distribute results to agents

```python
# Proposed structure (moderator.py)
class GameModerator:
    def __init__(self, game_manager, agents):
        self.game = game_manager
        self.agents = agents  # power -> LLMAdapter
        
    async def run_game(self, max_turns=50):
        while not self.game.is_over() and self.game.turn < max_turns:
            # Diplomacy phase
            await self.diplomacy_phase()
            # Order collection phase
            orders = await self.collect_orders()
            # Process turn
            self.game.submit_all_orders(orders)
            results = self.game.process_turn()
            # Inform agents
            await self.broadcast_results(results)
            
        return self.game.get_final_results()
```

#### 3.2 Agent Communication

- [ ] Manage message passing between agents
- [ ] Enforce press rules (no-press, white press, full press)
- [ ] Log all communications

### Phase 4: Evaluation Metrics

#### 4.1 Performance Metrics

- [ ] **Win Rate**: Games won / games played
- [ ] **Survival Rate**: Games survived to end / games played
- [ ] **Average SC Count**: Mean SCs at end of game
- [ ] **Time to Victory**: Average turns to win
- [ ] **Expansion Rate**: SC gain per turn

#### 4.2 Strategic Quality Metrics

- [ ] **Order Validity**: % of valid orders submitted
- [ ] **Tactical Soundness**: % of orders that match expert moves
- [ ] **Support Utilization**: How often support orders are used effectively
- [ ] **Defense Quality**: How well units protect supply centers
- [ ] **Attack Efficiency**: Success rate of offensive moves

#### 4.3 Diplomatic Quality Metrics (for press games)

- [ ] **Alliance Formation**: Successfully formed alliances
- [ ] **Promise Keeping**: % of promises honored
- [ ] **Deception Detection**: % of lies detected
- [ ] **Communication Quality**: Message clarity and relevance

```python
# Proposed structure (evaluation/metrics.py)
class EvaluationMetrics:
    def __init__(self):
        self.games_played = 0
        self.wins = 0
        self.survivals = 0
        self.sc_counts = []
        self.order_validity = []
        
    def add_game_result(self, result):
        """Record results from a completed game"""
        pass
        
    def compute_summary(self):
        """Calculate aggregate metrics"""
        return {
            "win_rate": self.wins / self.games_played,
            "survival_rate": self.survivals / self.games_played,
            "avg_sc_count": sum(self.sc_counts) / len(self.sc_counts),
            "avg_order_validity": sum(self.order_validity) / len(self.order_validity),
        }
```

### Phase 5: Evaluation Scenarios

#### 5.1 Single-Agent Evaluation

- [ ] LLM vs Random agents
- [ ] LLM vs Simple heuristic agents
- [ ] LLM vs Expert rule-based agents

#### 5.2 Multi-Agent Evaluation

- [ ] Same LLM playing all powers
- [ ] Different LLMs competing against each other
- [ ] LLM population dynamics (same model variants)

#### 5.3 Benchmark Scenarios

- [ ] **Opening Theory**: Evaluate first 3 moves
- [ ] **Mid-Game Tactics**: Complex tactical situations
- [ ] **End-Game**: 2-3 powers remaining
- [ ] **Defense Scenarios**: Respond to coordinated attack

## File Structure

```
dipLLoMacy_eval/
├── llm/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py          # BaseLLMAdapter
│   │   ├── openai_adapter.py
│   │   ├── anthropic_adapter.py
│   │   └── mock_adapter.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── state_prompt.py
│   │   ├── order_prompt.py
│   │   └── diplomacy_prompt.py
│   ├── moderator.py         # GameModerator
│   └── agent.py             # LLMAgent wrapper
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py           # EvaluationMetrics
│   ├── scenarios.py         # Benchmark scenarios
│   └── runner.py            # Evaluation orchestrator
├── config/
│   ├── llm_config.yaml      # LLM provider configs
│   └── eval_config.yaml     # Evaluation parameters
└── examples/
    ├── run_single_game.py
    ├── run_evaluation.py
    └── compare_models.py
```

## Implementation Order

1. **Week 1**: LLM Interface Layer
   - Base adapter interface
   - OpenAI adapter implementation
   - Mock adapter for testing
   - Basic prompt templates

2. **Week 2**: Prompt Engineering
   - State representation prompts
   - Order generation prompts
   - Response parsing
   - Unit tests for prompts

3. **Week 3**: Game Moderator
   - Turn orchestration
   - Order collection and submission
   - Result broadcasting
   - Single-agent game support

4. **Week 4**: Evaluation Framework
   - Performance metrics
   - Strategic quality metrics
   - Evaluation runner
   - Basic benchmark scenarios

5. **Week 5**: Multi-Agent and Polish
   - Multi-agent games
   - Diplomacy message support
   - Documentation
   - Example scripts

## Dependencies

### Required
- `openai`: OpenAI API client
- `anthropic`: Anthropic API client (optional)
- `aiohttp`: Async HTTP for API calls
- `pyyaml`: Configuration files
- `tiktoken`: Token counting for prompts

### Optional
- `wandb`: Experiment tracking
- `pandas`: Results analysis
- `matplotlib`: Results visualization

## Configuration

### LLM Configuration

```yaml
# config/llm_config.yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    models:
      - gpt-4-turbo-preview
      - gpt-4
      - gpt-3.5-turbo
    default_model: gpt-4-turbo-preview
    
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    models:
      - claude-3-opus
      - claude-3-sonnet
    default_model: claude-3-opus
```

### Evaluation Configuration

```yaml
# config/eval_config.yaml
evaluation:
  games_per_matchup: 10
  max_turns: 50
  timeout_per_turn: 60  # seconds
  
scenarios:
  - name: "vs_random"
    llm_powers: 1
    random_powers: 6
    
  - name: "all_same_llm"
    llm_powers: 7
    random_powers: 0
```

## Success Criteria

- [ ] Can run games with LLM agents controlling powers
- [ ] Generates valid orders from LLM responses
- [ ] Collects and reports evaluation metrics
- [ ] Supports multiple LLM providers
- [ ] Handles API errors gracefully
- [ ] Logs all prompts and responses for analysis
- [ ] Can run batch evaluations automatically
- [ ] Produces meaningful comparison between models

## Security Considerations

- [ ] API keys stored in environment variables, not code
- [ ] Rate limiting to prevent excessive API costs
- [ ] Input sanitization to prevent prompt injection
- [ ] Output validation before processing

## Future Enhancements

1. **Human-in-the-Loop**: Allow human players to join games
2. **Training Data Generation**: Export games for fine-tuning
3. **Tournament System**: Structured competition between models
4. **Analysis Tools**: Deep analysis of LLM decision patterns
5. **Press Rules Enforcement**: Implement full Diplomacy press variants
6. **ELO Rating System**: Track model performance over time
