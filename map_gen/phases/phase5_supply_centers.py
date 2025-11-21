#!/usr/bin/env python3
"""
Phase 5: Supply Center Distribution

This phase places supply centers across the map:
1. Mark all home territories as supply centers (3 per power)
2. Place neutral supply centers in strategic locations
3. Ensure neutral SCs are equidistant between powers

Input: kingdoms_output.json from Phase 4
Output: supply_centers_output.json with SC placements
"""

import json
import numpy as np
import random
import argparse

# Configuration constants for SC placement
PREFERRED_NEUTRAL_SC_DISTANCE = 0.2  # Preferred average distance of neutral SCs from powers
BALANCE_WEIGHT = 0.4                 # Weight for balance score in SC selection
COASTAL_WEIGHT = 0.3                 # Weight for coastal preference in SC selection
DISTANCE_WEIGHT = 0.3                # Weight for distance score in SC selection


def mark_home_centers(cells, territories):
    """
    Mark all home territory cells as supply centers.
    
    Args:
        cells: Dictionary of all cells
        territories: Dictionary of power territories
        
    Returns:
        Updated cells, count of home supply centers
    """
    home_sc_count = 0
    
    for power_id, territory_data in territories.items():
        territory_cells = territory_data["cells"]
        
        for cell_id in territory_cells:
            if cell_id in cells:
                cells[cell_id]["is_supply_center"] = True
                cells[cell_id]["sc_type"] = "home"
                home_sc_count += 1
    
    return cells, home_sc_count


def find_neutral_candidates(cells, territories):
    """
    Find candidate cells for neutral supply centers.
    
    Args:
        cells: Dictionary of all cells
        territories: Dictionary of power territories
        
    Returns:
        List of candidate cell IDs
    """
    # Get all owned cells
    owned_cells = set()
    for territory_data in territories.values():
        owned_cells.update(territory_data["cells"])
    
    # Find neutral land cells (not owned, preferably coastal)
    coastal_neutral = []
    inland_neutral = []
    
    for cell_id, cell in cells.items():
        if cell["type"] != "land":
            continue
        
        if cell_id in owned_cells:
            continue
        
        if cell.get("impassable", False):
            continue
        
        if cell.get("coastal", False):
            coastal_neutral.append(cell_id)
        else:
            inland_neutral.append(cell_id)
    
    # Prefer coastal cells
    return coastal_neutral + inland_neutral


def calculate_power_distances(cell_id, cells, territories):
    """
    Calculate distances from a cell to all power territories.
    
    Args:
        cell_id: ID of the cell to check
        cells: Dictionary of all cells
        territories: Dictionary of power territories
        
    Returns:
        List of (power_id, distance) tuples
    """
    cell_pos = np.array(cells[cell_id]["center"])
    distances = []
    
    for power_id, territory_data in territories.items():
        # Find closest cell in this power's territory
        min_dist = float('inf')
        
        for territory_cell in territory_data["cells"]:
            if territory_cell not in cells:
                continue
            
            territory_pos = np.array(cells[territory_cell]["center"])
            dist = np.linalg.norm(cell_pos - territory_pos)
            min_dist = min(min_dist, dist)
        
        distances.append((power_id, min_dist))
    
    return distances


def select_neutral_scs(candidates, cells, territories, num_neutral, seed=None):
    """
    Select neutral supply centers from candidates.
    
    Priority:
    1. Cells equidistant between multiple powers
    2. Coastal cells
    3. Not adjacent to other neutral SCs
    
    Args:
        candidates: List of candidate cell IDs
        cells: Dictionary of all cells
        territories: Dictionary of power territories
        num_neutral: Number of neutral SCs to place
        seed: Random seed
        
    Returns:
        List of selected neutral SC cell IDs
    """
    if seed is not None:
        random.seed(seed)
    
    if not candidates:
        return []
    
    selected = []
    available = set(candidates)
    
    # Score each candidate
    candidate_scores = []
    
    for cell_id in available:
        # Calculate distances to all powers
        power_distances = calculate_power_distances(cell_id, cells, territories)
        
        # Score based on:
        # 1. Balance (how evenly distributed are the distances to powers)
        distances = [d for _, d in power_distances]
        if not distances:
            continue
        
        # Preference for cells that are roughly equidistant to multiple powers
        min_dist = min(distances)
        max_dist = max(distances)
        balance_score = 1.0 - (max_dist - min_dist) / (max_dist + 0.001)
        
        # 2. Coastal preference
        coastal_score = 1.0 if cells[cell_id].get("coastal", False) else 0.5
        
        # 3. Average distance to powers (prefer contested areas, not too far)
        avg_dist = np.mean(distances)
        distance_score = 1.0 / (1.0 + abs(avg_dist - PREFERRED_NEUTRAL_SC_DISTANCE))  # Prefer moderate distances
        
        # Combined score
        total_score = balance_score * BALANCE_WEIGHT + coastal_score * COASTAL_WEIGHT + distance_score * DISTANCE_WEIGHT
        
        candidate_scores.append((cell_id, total_score, power_distances))
    
    # Sort by score (descending)
    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select top candidates, avoiding adjacent placements
    for cell_id, score, _ in candidate_scores:
        if len(selected) >= num_neutral:
            break
        
        # Check if adjacent to any already selected SC
        is_adjacent = any(
            neighbor in selected
            for neighbor in cells[cell_id]["neighbors"]
        )
        
        if not is_adjacent:
            selected.append(cell_id)
    
    # If we couldn't find enough non-adjacent cells, just take top scoring ones
    if len(selected) < num_neutral:
        for cell_id, score, _ in candidate_scores:
            if cell_id not in selected:
                selected.append(cell_id)
                if len(selected) >= num_neutral:
                    break
    
    return selected


def run_phase5(phase4_output, config):
    """
    Run Phase 5: Supply Center Distribution.
    
    Args:
        phase4_output: Output from Phase 4
        config: Configuration parameters
        
    Returns:
        Dictionary with supply center data
    """
    print("=" * 60)
    print("PHASE 5: SUPPLY CENTER DISTRIBUTION")
    print("=" * 60)
    
    cells = phase4_output["cells"]
    territories = phase4_output["territories"]
    
    # Extract configuration
    num_neutral = config.get("num_neutral_scs", 13)
    seed = config.get("seed", 42)
    
    print(f"\nConfiguration:")
    print(f"  Target neutral SCs: {num_neutral}")
    
    # Step 1: Mark home centers
    print("\nStep 1: Marking home territory supply centers...")
    cells, home_sc_count = mark_home_centers(cells, territories)
    print(f"  Marked {home_sc_count} home supply centers")
    
    # Step 2: Find neutral candidates
    print("\nStep 2: Finding neutral supply center candidates...")
    candidates = find_neutral_candidates(cells, territories)
    print(f"  Found {len(candidates)} candidate cells")
    
    # Step 3: Select neutral SCs
    print("\nStep 3: Selecting neutral supply centers...")
    neutral_scs = select_neutral_scs(candidates, cells, territories, num_neutral, seed)
    print(f"  Selected {len(neutral_scs)} neutral supply centers")
    
    # Mark neutral SCs
    for cell_id in neutral_scs:
        cells[cell_id]["is_supply_center"] = True
        cells[cell_id]["sc_type"] = "neutral"
    
    # Compile all supply centers
    all_scs = {
        "home": [
            cell_id for cell_id, cell in cells.items()
            if cell.get("is_supply_center", False) and cell.get("sc_type") == "home"
        ],
        "neutral": neutral_scs
    }
    
    total_scs = len(all_scs["home"]) + len(all_scs["neutral"])
    
    output = {
        "config": {**phase4_output["config"], **config},
        "cells": cells,
        "territories": territories,
        "supply_centers": all_scs,
        "statistics": {
            **phase4_output["statistics"],
            "total_supply_centers": total_scs,
            "home_supply_centers": len(all_scs["home"]),
            "neutral_supply_centers": len(all_scs["neutral"])
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 5 COMPLETE: {total_scs} total SCs ({len(all_scs['home'])} home, {len(all_scs['neutral'])} neutral)")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 5."""
    parser = argparse.ArgumentParser(description="Phase 5: Supply Center Distribution")
    parser.add_argument("--input", type=str, default="kingdoms_output.json", help="Input JSON from Phase 4")
    parser.add_argument("--num-neutral-scs", type=int, default=13, help="Number of neutral supply centers")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="supply_centers_output.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    # Load Phase 4 output
    with open(args.input, 'r') as f:
        phase4_output = json.load(f)
    
    config = {
        "num_neutral_scs": args.num_neutral_scs,
        "seed": args.seed
    }
    
    # Run phase 5
    output = run_phase5(phase4_output, config)
    
    # Save output
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
