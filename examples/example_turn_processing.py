#!/usr/bin/env python3
"""
Example: Single Turn Processing

This script demonstrates the full workflow for processing a single turn:
1. Generate the game board and export JPEG
2. Write Spring 1901 order files for each power (with holds)
3. Wait for user to edit order files
4. Process the turn using order files
5. Handle retreats if necessary
6. Update the map and export Fall 1901 JPEG with logs

This implements the turn processing flow described in the issue.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_turn_processing_demo(seed: int = 42, output_dir: str = None):
    """
    Run a full turn processing demonstration.
    
    Args:
        seed: Random seed for reproducible map generation
        output_dir: Directory to save outputs
    """
    # Import the orchestrator for map generation
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'map_gen', 'phases'))
    from orchestrator import run_full_pipeline
    
    # Import game module
    from game import GameManager
    
    print("=" * 70)
    print(" DIPLOMACY TURN PROCESSING DEMO")
    print("=" * 70)
    
    # Step 1: Generate a map and initialize game
    print("\n[Step 1] Generating map and initializing game...")
    
    config = {
        "num_cells": 80,
        "num_powers": 7,
        "territory_size": 3,
        "num_neutral_scs": 13,
        "land_ratio": 0.6,
        "seed": seed
    }
    
    map_data = run_full_pipeline(
        config,
        output_dir=None,
        save_intermediate=False
    )
    
    gm = GameManager(map_data=map_data)
    state = gm.initialize_game()
    
    print(f"  Turn: {state.get_turn_string()}")
    print(f"  Powers: {len(state.powers)}")
    print(f"  Units: {len(state.units)}")
    
    # Set up output directory
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent / "game_output" / f"turn_demo_{timestamp}"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    orders_dir = output_dir / "orders"
    orders_dir.mkdir(exist_ok=True)
    
    print(f"\n[Step 2] Exporting initial game board...")
    initial_jpeg = output_dir / "01_spring_1901_initial.jpeg"
    gm.export_board_image(str(initial_jpeg), dpi=150)
    print(f"  Saved: {initial_jpeg}")
    
    # Step 3: Write order files
    print(f"\n[Step 3] Writing order files (all units holding)...")
    order_files = gm.write_order_files(str(orders_dir))
    
    for power, filepath in order_files.items():
        print(f"  {power}: {filepath}")
    
    # Print instructions
    print("\n" + "=" * 70)
    print(" ORDER FILES READY")
    print("=" * 70)
    print(f"\nOrder files have been written to: {orders_dir}")
    print("\nEach power has a file with all units set to HOLD by default.")
    print("\nTo test different orders, edit the order files using this format:")
    print("  A {Territory} H            - Hold")
    print("  A {Territory} M {Target}   - Move")
    print("  A {Territory} S A {Unit} M {To} - Support move")
    print("  A {Territory} S A {Unit} H     - Support hold")
    print("  F {Territory} C A {From} M {To} - Convoy")
    print("\nTerritory names must be enclosed in braces {} and match exactly.")
    print("\n" + "=" * 70)
    
    # Wait for user input
    input("\nPress Enter when you have finished editing the order files...")
    
    # Step 4: Read and process orders
    print("\n[Step 4] Reading order files...")
    orders = gm.read_order_files(order_files)
    
    total_orders = sum(len(o) for o in orders.values())
    print(f"  Read {total_orders} orders from {len(orders)} powers")
    
    # Step 5: Process the turn
    print("\n[Step 5] Processing turn...")
    resolved_orders, dislodged, log = gm.process_turn(orders)
    
    print(log)
    
    # Write log to file
    log_file = output_dir / "02_spring_1901_resolution.txt"
    with open(log_file, 'w') as f:
        f.write(f"Turn: {state.get_turn_string()}\n")
        f.write(log)
    print(f"\nLog saved to: {log_file}")
    
    # Step 6: Handle retreats if necessary
    if dislodged:
        print("\n" + "=" * 70)
        print(" RETREATS REQUIRED")
        print("=" * 70)
        
        for location, attacker_loc in dislodged.items():
            unit = gm.state.get_unit_at(location)
            if not unit:
                continue
            
            territory_name = gm.get_territory_name(location)
            attacker_name = gm.get_territory_name(attacker_loc)
            
            print(f"\n{unit} was dislodged by attack from {attacker_name}")
            
            # Get retreat options
            options = gm.get_retreat_options(location)
            
            if not options:
                print("  No valid retreat options - unit must disband.")
                gm.disband_unit(location)
                print(f"  {unit} disbanded.")
                continue
            
            print("  Valid retreat options:")
            for i, opt in enumerate(options):
                opt_name = gm.get_territory_name(opt)
                print(f"    {i + 1}. {opt_name} ({opt})")
            print(f"    {len(options) + 1}. Disband")
            
            while True:
                try:
                    choice = input(f"  Enter choice (1-{len(options) + 1}): ").strip()
                    choice_num = int(choice)
                    
                    if 1 <= choice_num <= len(options):
                        dest = options[choice_num - 1]
                        if gm.process_retreat(location, dest):
                            dest_name = gm.get_territory_name(dest)
                            print(f"  {unit} retreats to {dest_name}")
                            break
                        else:
                            print("  Retreat failed. Try again.")
                    elif choice_num == len(options) + 1:
                        gm.disband_unit(location)
                        print(f"  {unit} disbanded.")
                        break
                    else:
                        print(f"  Invalid choice. Enter 1-{len(options) + 1}")
                except ValueError:
                    print("  Please enter a number.")
        
        print("\nAll retreats processed.")
    
    # Step 7: Advance phase and export final board
    print("\n[Step 6] Advancing to next phase...")
    gm.advance_to_next_phase()
    print(f"  Now: {gm.state.get_turn_string()} - {gm.state.phase.value.capitalize()} Phase")
    
    # Export final board
    final_jpeg = output_dir / f"03_{gm.state.season.value}_{gm.state.year}_positions.jpeg"
    gm.export_board_image(str(final_jpeg), dpi=150)
    print(f"\n[Step 7] Exported final board: {final_jpeg}")
    
    # Save game state
    state_file = output_dir / "game_state.json"
    gm.export_game_state_json(str(state_file))
    print(f"  Game state saved: {state_file}")
    
    print("\n" + "=" * 70)
    print(" TURN PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nAll outputs saved to: {output_dir}")
    print(f"  - {initial_jpeg.name}: Initial board")
    print(f"  - {log_file.name}: Resolution log")
    print(f"  - {final_jpeg.name}: Final positions")
    print(f"  - {state_file.name}: Game state JSON")
    
    return gm


def run_automated_test(seed: int = 42):
    """
    Run an automated test without user input.
    
    This is useful for testing the turn processing logic.
    """
    import tempfile
    
    # Import the orchestrator for map generation
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'map_gen', 'phases'))
    from orchestrator import run_full_pipeline
    
    # Import game module
    from game import GameManager
    from game.orders import OrderParser
    
    print("=" * 70)
    print(" AUTOMATED TURN PROCESSING TEST")
    print("=" * 70)
    
    # Generate map
    config = {
        "num_cells": 80,
        "num_powers": 7,
        "territory_size": 3,
        "num_neutral_scs": 13,
        "land_ratio": 0.6,
        "seed": seed
    }
    
    print("\n[1] Generating map...")
    map_data = run_full_pipeline(
        config,
        output_dir=None,
        save_intermediate=False
    )
    
    # Initialize game
    print("\n[2] Initializing game...")
    gm = GameManager(map_data=map_data)
    state = gm.initialize_game()
    
    print(f"  Turn: {state.get_turn_string()}")
    print(f"  Powers: {list(state.powers)}")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        orders_dir = os.path.join(tmpdir, "orders")
        os.makedirs(orders_dir)
        
        # Write order files
        print("\n[3] Writing order files...")
        order_files = gm.write_order_files(orders_dir)
        
        # Modify some orders to test movement
        # Find a unit and its adjacencies to create a valid move
        print("\n[4] Modifying orders to test movement...")
        adjacency = gm.get_adjacency()
        
        # Track occupied locations
        occupied = set(state.units.keys())
        
        for power, filepath in order_files.items():
            units = state.get_units_for_power(power)
            if units:
                unit = units[0]
                adjacent = adjacency.get(unit.location, [])
                
                # Find a valid UNOCCUPIED target for army or coastal/sea for fleet
                target = None
                topology = map_data.get('topology', {})
                faces = topology.get('faces', {})
                
                for adj in adjacent:
                    # Skip occupied territories
                    if adj in occupied:
                        continue
                    
                    adj_data = faces.get(adj, {})
                    adj_type = adj_data.get('type', 'land')
                    is_coastal = adj_data.get('coastal', False)
                    
                    # Check if unit can move there
                    from game.units import UnitType
                    if unit.unit_type == UnitType.ARMY:
                        if adj_type != 'sea':
                            target = adj
                            break
                    else:  # Fleet
                        if adj_type == 'sea' or is_coastal:
                            target = adj
                            break
                
                if target:
                    # Rewrite order file with a move
                    unit_type = 'A' if unit.unit_type == UnitType.ARMY else 'F'
                    location_name = gm.get_territory_name(unit.location)
                    target_name = gm.get_territory_name(target)
                    
                    with open(filepath, 'w') as f:
                        f.write(f"# Test orders for {power}\n")
                        f.write(f"{unit_type} {{{location_name}}} M {{{target_name}}}\n")
                        
                        # Add holds for other units
                        for other_unit in units[1:]:
                            other_type = 'A' if other_unit.unit_type == UnitType.ARMY else 'F'
                            other_name = gm.get_territory_name(other_unit.location)
                            f.write(f"{other_type} {{{other_name}}} H\n")
                    
                    print(f"  {power}: {unit_type} {location_name} -> {target_name}")
                    break
        
        # Read orders
        print("\n[5] Reading orders...")
        orders = gm.read_order_files(order_files)
        
        # Process turn
        print("\n[6] Processing turn...")
        resolved_orders, dislodged, log = gm.process_turn(orders)
        
        print(log)
        
        # Check results
        successful = [o for o in resolved_orders if o.result.value == 'success']
        print(f"\n[7] Results: {len(successful)} successful orders")
        
        # Export final board
        jpeg_path = os.path.join(tmpdir, "test_board.jpeg")
        gm.export_board_image(jpeg_path)
        print(f"  Board exported to: {jpeg_path}")
        
        print("\n" + "=" * 70)
        print(" AUTOMATED TEST COMPLETE")
        print("=" * 70)
        
        return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # Run automated test
            run_automated_test(seed=42)
        else:
            try:
                seed = int(sys.argv[1])
                run_turn_processing_demo(seed=seed)
            except ValueError:
                print(f"Usage: {sys.argv[0]} [seed] or {sys.argv[0]} --test")
                sys.exit(1)
    else:
        # Interactive demo
        run_turn_processing_demo(seed=42)
