#!/usr/bin/env python3
"""
Phase 3: Province Definition

This phase defines the mechanical properties of regions:
1. Identify coastlines (land cells touching water)
2. Identify and group oceans (contiguous water cells)
3. Create impassable zones (Switzerland-style neutral zones)

Input: terrain_output.json from Phase 2
Output: provinces_output.json with province classifications
"""

import json
import random
import argparse
import sys
import os

# Add parent directory to path for topology import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_utils import get_output_path_for_phase
from topology import convert_cells_to_topology


def identify_coastlines(cells):
    """
    Mark land cells that border water as coastal.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Updated cells with coastal designation
    """
    coastal_count = 0
    inland_count = 0
    
    for cell_id, cell in cells.items():
        if cell["type"] != "land":
            cell["coastal"] = False
            continue
        
        # Check if any neighbor is water
        has_water_neighbor = any(
            cells[n]["type"] == "sea" 
            for n in cell["neighbors"] 
            if n in cells
        )
        
        if has_water_neighbor:
            cell["coastal"] = True
            coastal_count += 1
        else:
            cell["coastal"] = False
            inland_count += 1
    
    return cells, coastal_count, inland_count


def group_oceans(cells):
    """
    Group contiguous water cells into ocean regions.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Updated cells with ocean_id, list of ocean groups
    """
    # Find all sea cells
    sea_cells = {cell_id for cell_id, cell in cells.items() if cell["type"] == "sea"}
    
    oceans = []
    visited = set()
    
    # BFS to find connected components of sea
    for start_cell in sea_cells:
        if start_cell in visited:
            continue
        
        # Start a new ocean
        ocean = []
        queue = [start_cell]
        visited.add(start_cell)
        
        while queue:
            cell_id = queue.pop(0)
            ocean.append(cell_id)
            
            # Add sea neighbors to queue
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor in sea_cells and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        oceans.append(ocean)
    
    # Assign ocean IDs to cells
    for ocean_id, ocean in enumerate(oceans):
        for cell_id in ocean:
            cells[cell_id]["ocean_id"] = ocean_id
            cells[cell_id]["ocean_size"] = len(ocean)
    
    return cells, oceans


def create_impassable_zones(cells, num_zones=1):
    """
    Create impassable zones (like Switzerland) in central inland locations.
    
    Args:
        cells: Dictionary of cell data
        num_zones: Number of impassable zones to create
        
    Returns:
        Updated cells with impassable designation
    """
    # Find inland cells (not coastal, not sea)
    inland_cells = [
        cell_id for cell_id, cell in cells.items()
        if cell["type"] == "land" and not cell.get("coastal", False)
    ]
    
    if len(inland_cells) < num_zones:
        print(f"  Warning: Only {len(inland_cells)} inland cells, cannot create {num_zones} zones")
        num_zones = len(inland_cells)
    
    # Find central inland cells (those with most inland neighbors)
    cell_centrality = []
    for cell_id in inland_cells:
        inland_neighbor_count = sum(
            1 for n in cells[cell_id]["neighbors"]
            if n in cells and cells[n]["type"] == "land" and not cells[n].get("coastal", False)
        )
        cell_centrality.append((cell_id, inland_neighbor_count))
    
    # Sort by centrality and pick top candidates
    cell_centrality.sort(key=lambda x: x[1], reverse=True)
    
    # Select impassable zones from top candidates
    impassable_cells = []
    for i in range(min(num_zones, len(cell_centrality))):
        cell_id, _ = cell_centrality[i]
        cells[cell_id]["impassable"] = True
        cells[cell_id]["type"] = "impassable"
        impassable_cells.append(cell_id)
    
    # Mark all other cells as passable
    for cell_id in cells:
        if "impassable" not in cells[cell_id]:
            cells[cell_id]["impassable"] = False
    
    return cells, impassable_cells


def run_phase3(phase2_output, config):
    """
    Run Phase 3: Province Definition.
    
    Args:
        phase2_output: Output from Phase 2
        config: Configuration parameters
        
    Returns:
        Dictionary with province data
    """
    print("=" * 60)
    print("PHASE 3: PROVINCE DEFINITION")
    print("=" * 60)
    
    cells = phase2_output["cells"]
    
    # Extract configuration
    num_impassable = config.get("num_impassable_zones", 1)
    seed = config.get("seed", 42)
    
    random.seed(seed)
    
    print(f"\nConfiguration:")
    print(f"  Number of impassable zones: {num_impassable}")
    
    # Step 1: Identify coastlines
    print("\nStep 1: Identifying coastlines...")
    cells, coastal_count, inland_count = identify_coastlines(cells)
    land_total = coastal_count + inland_count
    print(f"  Coastal cells: {coastal_count} ({coastal_count/land_total:.1%} of land)" if land_total > 0 else "  No land cells")
    print(f"  Inland cells: {inland_count} ({inland_count/land_total:.1%} of land)" if land_total > 0 else "  No land cells")
    
    # Step 2: Group oceans
    print("\nStep 2: Grouping ocean regions...")
    cells, oceans = group_oceans(cells)
    print(f"  Found {len(oceans)} ocean region(s)")
    for i, ocean in enumerate(oceans):
        print(f"    Ocean {i}: {len(ocean)} cells")
    
    # Step 3: Create impassable zones
    print("\nStep 3: Creating impassable zones...")
    cells, impassable_cells = create_impassable_zones(cells, num_impassable)
    print(f"  Created {len(impassable_cells)} impassable zone(s)")
    for cell_id in impassable_cells:
        print(f"    {cell_id} marked as impassable")
    
    # Calculate statistics
    land_cells = sum(1 for c in cells.values() if c["type"] == "land")
    sea_cells = sum(1 for c in cells.values() if c["type"] == "sea")
    impassable = sum(1 for c in cells.values() if c["type"] == "impassable")
    
    # Step 4: Update topology with province designations
    print("\nStep 4: Updating topology with province designations...")
    topology = convert_cells_to_topology(cells)
    print(f"  Topology updated with {len(topology['vertices'])} vertices, {len(topology['edges'])} edges")
    
    output = {
        "config": {**phase2_output["config"], **config},
        "cells": cells,
        "topology": topology,
        "oceans": [
            {
                "ocean_id": i,
                "size": len(ocean),
                "cells": ocean
            }
            for i, ocean in enumerate(oceans)
        ],
        "statistics": {
            "total_cells": len(cells),
            "land_cells": land_cells,
            "sea_cells": sea_cells,
            "impassable_cells": impassable,
            "coastal_cells": coastal_count,
            "inland_cells": inland_count,
            "num_oceans": len(oceans),
            "topology_vertices": len(topology['vertices']),
            "topology_edges": len(topology['edges'])
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 3 COMPLETE: {coastal_count} coastal, {inland_count} inland, {len(oceans)} oceans")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 3."""
    parser = argparse.ArgumentParser(description="Phase 3: Province Definition")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 2")
    parser.add_argument("--num-impassable-zones", type=int, default=1, help="Number of impassable zones")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 2 output
    with open(args.input, 'r') as f:
        phase2_output = json.load(f)
    
    config = {
        "num_impassable_zones": args.num_impassable_zones,
        "seed": args.seed
    }
    
    # Run phase 3
    output = run_phase3(phase2_output, config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        _, _, output_path = get_output_path_for_phase(
            "phase3_provinces_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
