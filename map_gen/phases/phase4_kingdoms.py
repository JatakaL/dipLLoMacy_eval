#!/usr/bin/env python3
"""
Phase 4: Kingdom Generation (Player Starts)

This phase creates balanced starting positions for players:
1. Seed placement (select equidistant coastal cells)
2. Flood fill territory growth (BFS from seeds)
3. Verify contiguity of territories

Input: provinces_output.json from Phase 3
Output: kingdoms_output.json with player territories
"""

import json
import numpy as np
import random
import argparse
from collections import deque

from output_utils import get_output_path_for_phase


def select_distant_seeds(coastal_cells, cells, num_powers=7, seed=None):
    """
    Select equidistant coastal cells as starting seeds for powers.
    
    Args:
        coastal_cells: List of coastal cell IDs
        cells: Dictionary of all cells
        num_powers: Number of powers to create
        seed: Random seed
        
    Returns:
        List of seed cell IDs
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
    
    if len(coastal_cells) < num_powers:
        print(f"  Warning: Only {len(coastal_cells)} coastal cells for {num_powers} powers")
        return coastal_cells
    
    # Use greedy selection to maximize minimum distance
    seeds = []
    
    # Pick first seed randomly
    first_seed = random.choice(coastal_cells)
    seeds.append(first_seed)
    
    # For each remaining seed, pick the cell farthest from all existing seeds
    available = set(coastal_cells) - {first_seed}
    
    for _ in range(num_powers - 1):
        if not available:
            break
        
        max_min_distance = -1
        best_candidate = None
        
        for candidate in available:
            candidate_pos = np.array(cells[candidate]["center"])
            
            # Calculate minimum distance to existing seeds
            min_distance = min(
                np.linalg.norm(candidate_pos - np.array(cells[seed]["center"]))
                for seed in seeds
            )
            
            if min_distance > max_min_distance:
                max_min_distance = min_distance
                best_candidate = candidate
        
        if best_candidate:
            seeds.append(best_candidate)
            available.remove(best_candidate)
    
    return seeds


def grow_territory_bfs(seeds, cells, territory_size=3):
    """
    Grow territories from seeds using simultaneous BFS.
    
    Args:
        seeds: List of seed cell IDs
        cells: Dictionary of all cells
        territory_size: Target size for each territory
        
    Returns:
        Dictionary mapping power ID to list of cell IDs
    """
    territories = {f"Power{i+1}": [seed] for i, seed in enumerate(seeds)}
    claimed = set(seeds)
    
    # Create queues for each power
    queues = {f"Power{i+1}": deque([seed]) for i, seed in enumerate(seeds)}
    
    # Grow territories simultaneously
    max_iterations = 1000
    iteration = 0
    
    while any(len(territory) < territory_size for territory in territories.values()) and iteration < max_iterations:
        iteration += 1
        
        # Each power takes a turn to expand
        for power_id in territories:
            if len(territories[power_id]) >= territory_size:
                continue
            
            if not queues[power_id]:
                continue
            
            # Try to expand from current frontier
            current_cell = queues[power_id].popleft()
            
            # Find unclaimed land neighbors
            for neighbor in cells[current_cell]["neighbors"]:
                if neighbor in claimed:
                    continue
                
                if neighbor not in cells:
                    continue
                
                neighbor_cell = cells[neighbor]
                
                # Only claim land cells
                if neighbor_cell["type"] != "land":
                    continue
                
                # Claim this neighbor
                territories[power_id].append(neighbor)
                claimed.add(neighbor)
                queues[power_id].append(neighbor)
                
                # Check if we've reached target size
                if len(territories[power_id]) >= territory_size:
                    break
    
    return territories


def verify_contiguity(territory, cells):
    """
    Verify that a territory is contiguous (all cells connected).
    
    Args:
        territory: List of cell IDs in the territory
        cells: Dictionary of all cells
        
    Returns:
        Boolean indicating if territory is contiguous
    """
    if not territory:
        return False
    
    # BFS to check if all cells are reachable from first cell
    start = territory[0]
    visited = {start}
    queue = deque([start])
    
    while queue:
        current = queue.popleft()
        
        for neighbor in cells[current]["neighbors"]:
            if neighbor in territory and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    
    return len(visited) == len(territory)


def run_phase4(phase3_output, config):
    """
    Run Phase 4: Kingdom Generation.
    
    Args:
        phase3_output: Output from Phase 3
        config: Configuration parameters
        
    Returns:
        Dictionary with kingdom data
    """
    print("=" * 60)
    print("PHASE 4: KINGDOM GENERATION (Player Starts)")
    print("=" * 60)
    
    cells = phase3_output["cells"]
    
    # Extract configuration
    num_powers = config.get("num_powers", 7)
    territory_size = config.get("territory_size", 3)
    seed = config.get("seed", 42)
    max_retries = config.get("max_retries", 10)
    
    print(f"\nConfiguration:")
    print(f"  Number of powers: {num_powers}")
    print(f"  Territory size: {territory_size}")
    print(f"  Max retries: {max_retries}")
    
    # Step 1: Find coastal cells
    print("\nStep 1: Finding coastal cells for seed placement...")
    coastal_cells = [
        cell_id for cell_id, cell in cells.items()
        if cell["type"] == "land" and cell.get("coastal", False)
    ]
    print(f"  Found {len(coastal_cells)} coastal cells")
    
    if len(coastal_cells) < num_powers:
        print(f"  ERROR: Not enough coastal cells ({len(coastal_cells)}) for {num_powers} powers")
        print("  Using all available coastal cells...")
        num_powers = len(coastal_cells)
    
    # Step 2: Select equidistant seeds
    print("\nStep 2: Selecting equidistant seeds...")
    
    best_territories = None
    best_contiguity = 0
    
    for attempt in range(max_retries):
        seeds = select_distant_seeds(coastal_cells, cells, num_powers, seed + attempt)
        
        # Calculate minimum distance between seeds
        min_distance = float('inf')
        for i, seed1 in enumerate(seeds):
            for seed2 in seeds[i+1:]:
                pos1 = np.array(cells[seed1]["center"])
                pos2 = np.array(cells[seed2]["center"])
                distance = np.linalg.norm(pos1 - pos2)
                min_distance = min(min_distance, distance)
        
        print(f"  Attempt {attempt+1}: {len(seeds)} seeds, min distance: {min_distance:.3f}")
        
        # Step 3: Grow territories
        territories = grow_territory_bfs(seeds, cells, territory_size)
        
        # Step 4: Verify contiguity
        contiguous_count = 0
        for power_id, territory in territories.items():
            is_contiguous = verify_contiguity(territory, cells)
            if is_contiguous:
                contiguous_count += 1
        
        print(f"    {contiguous_count}/{len(territories)} territories are contiguous")
        
        if contiguous_count > best_contiguity:
            best_contiguity = contiguous_count
            best_territories = territories
            best_seeds = seeds
        
        if contiguous_count == len(territories):
            print(f"  SUCCESS: All territories contiguous on attempt {attempt+1}")
            break
    
    territories = best_territories
    seeds = best_seeds
    
    # Assign ownership to cells
    for power_id, territory in territories.items():
        for cell_id in territory:
            cells[cell_id]["owner"] = power_id
            cells[cell_id]["is_home"] = True
    
    # Mark seeds as starting positions
    for i, seed in enumerate(seeds):
        cells[seed]["is_seed"] = True
    
    # Update topology faces with ownership information
    topology = phase3_output.get("topology", {})
    if topology and "faces" in topology:
        for power_id, territory in territories.items():
            for cell_id in territory:
                if cell_id in topology["faces"]:
                    topology["faces"][cell_id]["owner"] = power_id
                    topology["faces"][cell_id]["is_home"] = True
        
        # Mark seeds in topology
        for seed in seeds:
            if seed in topology["faces"]:
                topology["faces"][seed]["is_seed"] = True
    
    # Calculate statistics
    territory_sizes = {power_id: len(territory) for power_id, territory in territories.items()}
    
    output = {
        "config": {**phase3_output["config"], **config},
        "cells": cells,
        "topology": topology,
        "territories": {
            power_id: {
                "cells": territory,
                "seed": seeds[i],
                "size": len(territory),
                "contiguous": verify_contiguity(territory, cells)
            }
            for i, (power_id, territory) in enumerate(territories.items())
        },
        "statistics": {
            **phase3_output["statistics"],
            "num_powers": len(territories),
            "territory_sizes": territory_sizes,
            "all_contiguous": best_contiguity == len(territories)
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 4 COMPLETE: {len(territories)} powers with territories")
    print(f"Territory sizes: {territory_sizes}")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 4."""
    parser = argparse.ArgumentParser(description="Phase 4: Kingdom Generation")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 3")
    parser.add_argument("--num-powers", type=int, default=7, help="Number of powers")
    parser.add_argument("--territory-size", type=int, default=3, help="Home territory size")
    parser.add_argument("--max-retries", type=int, default=10, help="Maximum retries for seed placement")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 3 output
    with open(args.input, 'r') as f:
        phase3_output = json.load(f)
    
    config = {
        "num_powers": args.num_powers,
        "territory_size": args.territory_size,
        "max_retries": args.max_retries,
        "seed": args.seed
    }
    
    # Run phase 4
    output = run_phase4(phase3_output, config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        _, _, output_path = get_output_path_for_phase(
            "phase4_kingdoms_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
