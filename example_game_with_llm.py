#!/usr/bin/env python3
"""
Example: Running a Diplomacy Game with LLM Players

This script demonstrates how to:
1. Generate a map
2. Set up a game with different player types
3. Run a complete game
4. Collect and analyze metrics

Usage:
    python example_game_with_llm.py
    
For real LLM evaluation, set environment variables:
    export OPENAI_API_KEY="your-key-here"
    export ANTHROPIC_API_KEY="your-key-here"
"""

import sys
import os
import json

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map_gen', 'phases'))


def example_random_game():
    """
    Run a game with random players.
    
    Good for testing the game engine without LLM costs.
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Random Player Game")
    print("="*60 + "\n")
    
    from orchestrator import run_full_pipeline
    from evaluation.runner import GameRunner, RandomPlayer
    
    # Generate a map
    print("Generating map...")
    map_data = run_full_pipeline(
        {"num_cells": 60, "num_powers": 4, "seed": 42},
        output_dir="/tmp/example_games",
        save_intermediate=False
    )
    
    # Get power names
    powers = list(map_data.get("powers", {}).keys())
    print(f"Powers: {powers}")
    
    # Create random players
    players = {power: RandomPlayer(seed=i) for i, power in enumerate(powers)}
    
    # Run game
    print("\nRunning game...")
    runner = GameRunner(map_data, players)
    result = runner.run_game(max_turns=10, verbose=True)
    
    # Print results
    print("\n" + "-"*40)
    print("GAME RESULTS:")
    print(f"  Winner: {result.get('winner', 'No winner (max turns reached)')}")
    print(f"  Final Year: {result.get('final_year')}")
    print(f"  Supply Centers:")
    for power, count in result.get('supply_center_counts', {}).items():
        print(f"    {power}: {count}")


def example_mock_llm_game():
    """
    Run a game with mock LLM players.
    
    Uses mock adapters that don't make real API calls.
    Good for testing the LLM integration without costs.
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Mock LLM Player Game")
    print("="*60 + "\n")
    
    from orchestrator import run_full_pipeline
    from evaluation.runner import GameRunner
    from llm.openai_adapter import MockOpenAIAdapter
    
    # Generate a smaller map for faster testing
    print("Generating map...")
    map_data = run_full_pipeline(
        {"num_cells": 50, "num_powers": 3, "seed": 123},
        output_dir="/tmp/example_games",
        save_intermediate=False
    )
    
    powers = list(map_data.get("powers", {}).keys())
    print(f"Powers: {powers}")
    
    # Create mock LLM players
    players = {power: MockOpenAIAdapter() for power in powers}
    
    # Run game
    print("\nRunning game with mock LLM players...")
    runner = GameRunner(map_data, players)
    result = runner.run_game(max_turns=5, verbose=True)
    
    print("\n" + "-"*40)
    print("GAME RESULTS:")
    print(f"  Winner: {result.get('winner', 'No winner')}")
    print(f"  Final Year: {result.get('final_year')}")


def example_experiment():
    """
    Run a multi-game experiment.
    
    Demonstrates the experiment framework for systematic evaluation.
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Multi-Game Experiment")
    print("="*60 + "\n")
    
    from evaluation.experiment import Experiment
    
    # Configure experiment
    map_config = {
        "num_cells": 50,
        "num_powers": 4,
        "seed": 42
    }
    
    # All random players for this example
    player_configs = {
        "Power1": {"type": "random", "seed": 1},
        "Power2": {"type": "random", "seed": 2},
        "Power3": {"type": "random", "seed": 3},
        "Power4": {"type": "random", "seed": 4},
    }
    
    # Run experiment
    experiment = Experiment(map_config, player_configs, "demo_experiment")
    
    print("Running 3 games...")
    metrics = experiment.run(num_games=3, max_turns=10, verbose=True)
    
    # Print summary
    print("\n" + "-"*40)
    print("EXPERIMENT SUMMARY:")
    print(f"  Games played: {metrics.num_games}")
    print(f"  Average game length: {metrics.avg_game_length:.1f} years")
    print("\nWin rates:")
    for power, rate in sorted(metrics.win_rates.items(), 
                               key=lambda x: x[1], reverse=True):
        print(f"  {power}: {rate*100:.1f}%")


def example_game_state_for_llm():
    """
    Demonstrate how game state is formatted for LLM consumption.
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Game State for LLM")
    print("="*60 + "\n")
    
    from orchestrator import run_full_pipeline
    from game.game_engine import GameEngine
    from llm.prompts import GameStateFormatter
    
    # Generate a map
    print("Generating map...")
    map_data = run_full_pipeline(
        {"num_cells": 50, "num_powers": 3, "seed": 456},
        output_dir="/tmp/example_games",
        save_intermediate=False
    )
    
    # Create game and set up starting positions
    engine = GameEngine(map_data)
    engine.setup_starting_positions()
    
    # Get state for one power
    power = list(map_data.get("powers", {}).keys())[0]
    state = engine.get_game_state_for_llm(power)
    
    # Format for LLM
    formatter = GameStateFormatter()
    formatted = formatter.format_game_state(state)
    
    print(f"Game state for {power}:")
    print("-"*40)
    print(formatted)
    print("-"*40)
    
    # Show valid orders
    print(f"\nValid orders for {power}:")
    for order in state.get("valid_orders", [])[:5]:  # Show first 5
        print(f"  - {order.get('description')}")
    if len(state.get("valid_orders", [])) > 5:
        print(f"  ... and {len(state['valid_orders']) - 5} more")


def main():
    """Run all examples."""
    print("="*60)
    print("DIPLOMACY LLM EVALUATION - EXAMPLES")
    print("="*60)
    
    try:
        # Example 1: Random players
        example_random_game()
        
        # Example 2: Mock LLM players
        example_mock_llm_game()
        
        # Example 3: Multi-game experiment
        example_experiment()
        
        # Example 4: Show game state formatting
        example_game_state_for_llm()
        
        print("\n" + "="*60)
        print("ALL EXAMPLES COMPLETED")
        print("="*60)
        print("""
Next steps for real LLM evaluation:
1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable
2. Change player_configs to use "llm" type:
   {"type": "llm", "provider": "openai", "model": "gpt-4"}
3. Run experiments with larger num_games for statistical significance
""")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
