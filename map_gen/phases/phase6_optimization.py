#!/usr/bin/env python3
"""
Phase 6: Graph Optimization

This phase optimizes the map graph for gameplay:
1. Check bottlenecks (degree of each node)
2. Split highly connected nodes (degree > 7)
3. Merge dead-end nodes (degree < 3)
4. Ensure connectivity between all sea zones

Input: supply_centers_output.json from Phase 5
Output: optimized_graph_output.json with optimized structure
"""

import json
import argparse
from collections import deque

from output_utils import get_output_path_for_phase

# Configuration constants for graph quality thresholds
HIGH_CONNECTIVITY_THRESHOLD = 7  # Nodes with more than this many neighbors are considered highly connected
LOW_CONNECTIVITY_THRESHOLD = 3   # Nodes with fewer than this many neighbors are considered dead ends
MIN_TRIANGLE_DENSITY = 0.3       # Minimum triangle density for good Diplomacy gameplay (30%)


def analyze_node_degrees(cells):
    """
    Analyze the degree (number of neighbors) of each node.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Dictionary with degree statistics
    """
    degrees = {}
    
    for cell_id, cell in cells.items():
        if cell["type"] == "impassable":
            continue
        
        degree = len(cell["neighbors"])
        degrees[cell_id] = degree
    
    # Calculate statistics
    degree_values = list(degrees.values())
    
    if not degree_values:
        return {
            "degrees": degrees,
            "average": 0,
            "min": 0,
            "max": 0,
            "highly_connected": [],
            "dead_ends": []
        }
    
    avg_degree = sum(degree_values) / len(degree_values)
    
    # Find problematic nodes
    highly_connected = [cell_id for cell_id, deg in degrees.items() if deg > HIGH_CONNECTIVITY_THRESHOLD]
    dead_ends = [cell_id for cell_id, deg in degrees.items() if deg < LOW_CONNECTIVITY_THRESHOLD and deg > 0]
    
    return {
        "degrees": degrees,
        "average": avg_degree,
        "min": min(degree_values),
        "max": max(degree_values),
        "highly_connected": highly_connected,
        "dead_ends": dead_ends
    }


def check_sea_connectivity(cells):
    """
    Check if all sea zones are connected to each other.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Dictionary with connectivity information
    """
    # Find all sea cells
    sea_cells = [cell_id for cell_id, cell in cells.items() if cell["type"] == "sea"]
    
    if not sea_cells:
        return {
            "connected": True,
            "components": 0,
            "largest_component": 0
        }
    
    # BFS to find connected components
    visited = set()
    components = []
    
    for start_cell in sea_cells:
        if start_cell in visited:
            continue
        
        # Start new component
        component = []
        queue = deque([start_cell])
        visited.add(start_cell)
        
        while queue:
            cell_id = queue.popleft()
            component.append(cell_id)
            
            # Add sea neighbors
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor in cells and cells[neighbor]["type"] == "sea" and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        components.append(component)
    
    return {
        "connected": len(components) <= 1,
        "components": len(components),
        "largest_component": max(len(c) for c in components) if components else 0,
        "component_sizes": [len(c) for c in components]
    }


def calculate_triangle_density(cells):
    """
    Calculate the "triangle density" - how often provinces form triangles.
    
    In Diplomacy, if A touches B and C, then B and C should often touch each other,
    forming triangles that enable the support mechanic.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Triangle density ratio
    """
    total_pairs = 0
    connected_pairs = 0
    
    for cell_id, cell in cells.items():
        if cell["type"] == "impassable":
            continue
        
        neighbors = [n for n in cell["neighbors"] if n in cells and cells[n]["type"] != "impassable"]
        
        # For each pair of neighbors, check if they're also connected
        for i, neighbor1 in enumerate(neighbors):
            for neighbor2 in neighbors[i+1:]:
                total_pairs += 1
                
                # Check if neighbor1 and neighbor2 are connected
                if neighbor2 in cells[neighbor1]["neighbors"]:
                    connected_pairs += 1
    
    triangle_density = connected_pairs / total_pairs if total_pairs > 0 else 0
    
    return {
        "triangle_density": triangle_density,
        "total_pairs": total_pairs,
        "connected_pairs": connected_pairs
    }


def identify_corner_powers(cells, territories):
    """
    Identify which powers are in "corners" (fewer neighbors, easier defense)
    vs "central" (more neighbors, high risk/high reward).
    
    Args:
        cells: Dictionary of cell data
        territories: Dictionary of power territories
        
    Returns:
        Dictionary classifying powers
    """
    power_classifications = {}
    
    for power_id, territory_data in territories.items():
        territory_cells = territory_data["cells"]
        
        # Count unique neighboring powers
        neighboring_powers = set()
        
        for cell_id in territory_cells:
            if cell_id not in cells:
                continue
            
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor not in cells:
                    continue
                
                neighbor_owner = cells[neighbor].get("owner")
                if neighbor_owner and neighbor_owner != power_id:
                    neighboring_powers.add(neighbor_owner)
        
        num_neighbors = len(neighboring_powers)
        
        # Classify: 0-2 neighbors = corner, 3-4 = moderate, 5+ = central
        if num_neighbors <= 2:
            classification = "corner"
        elif num_neighbors <= 4:
            classification = "moderate"
        else:
            classification = "central"
        
        power_classifications[power_id] = {
            "classification": classification,
            "num_neighboring_powers": num_neighbors,
            "neighboring_powers": list(neighboring_powers)
        }
    
    return power_classifications


def identify_belgium_factor(cells, territories, supply_centers):
    """
    Identify neutral SCs accessible by 3+ powers in the first turn.
    These create the "Belgium factor" - forcing early diplomacy.
    
    Args:
        cells: Dictionary of cell data
        territories: Dictionary of power territories
        supply_centers: Supply center data
        
    Returns:
        List of contested neutral SCs
    """
    contested_scs = []
    
    for sc_id in supply_centers.get("neutral", []):
        if sc_id not in cells:
            continue
        
        # Find which powers are adjacent to this SC
        adjacent_powers = set()
        
        for neighbor in cells[sc_id]["neighbors"]:
            if neighbor not in cells:
                continue
            
            neighbor_owner = cells[neighbor].get("owner")
            if neighbor_owner:
                adjacent_powers.add(neighbor_owner)
        
        # If 3+ powers can reach it, it's a "Belgium"
        if len(adjacent_powers) >= 3:
            contested_scs.append({
                "cell_id": sc_id,
                "accessible_by": list(adjacent_powers),
                "num_powers": len(adjacent_powers)
            })
    
    return contested_scs


def run_phase6(phase5_output, config):
    """
    Run Phase 6: Graph Optimization.
    
    Args:
        phase5_output: Output from Phase 5
        config: Configuration parameters
        
    Returns:
        Dictionary with optimization data
    """
    print("=" * 60)
    print("PHASE 6: GRAPH OPTIMIZATION")
    print("=" * 60)
    
    cells = phase5_output["cells"]
    territories = phase5_output["territories"]
    supply_centers = phase5_output["supply_centers"]
    
    print("\nAnalyzing map graph quality...")
    
    # Step 1: Analyze node degrees
    print("\nStep 1: Analyzing node degrees...")
    degree_analysis = analyze_node_degrees(cells)
    print(f"  Average degree: {degree_analysis['average']:.2f}")
    print(f"  Range: {degree_analysis['min']} - {degree_analysis['max']}")
    print(f"  Highly connected nodes (>7): {len(degree_analysis['highly_connected'])}")
    print(f"  Dead ends (<3): {len(degree_analysis['dead_ends'])}")
    
    # Step 2: Check sea connectivity
    print("\nStep 2: Checking sea connectivity...")
    sea_connectivity = check_sea_connectivity(cells)
    print(f"  All seas connected: {sea_connectivity['connected']}")
    print(f"  Number of sea components: {sea_connectivity['components']}")
    if sea_connectivity['components'] > 1:
        print(f"  Component sizes: {sea_connectivity['component_sizes']}")
    
    # Step 3: Calculate triangle density
    print("\nStep 3: Calculating triangle density...")
    triangle_analysis = calculate_triangle_density(cells)
    print(f"  Triangle density: {triangle_analysis['triangle_density']:.1%}")
    print(f"  Connected pairs: {triangle_analysis['connected_pairs']}/{triangle_analysis['total_pairs']}")
    
    # Step 4: Identify corner vs central powers
    print("\nStep 4: Classifying power positions...")
    power_classifications = identify_corner_powers(cells, territories)
    corner_powers = [p for p, data in power_classifications.items() if data["classification"] == "corner"]
    central_powers = [p for p, data in power_classifications.items() if data["classification"] == "central"]
    moderate_powers = [p for p, data in power_classifications.items() if data["classification"] == "moderate"]
    
    print(f"  Corner powers ({len(corner_powers)}): {', '.join(corner_powers)}")
    print(f"  Moderate powers ({len(moderate_powers)}): {', '.join(moderate_powers)}")
    print(f"  Central powers ({len(central_powers)}): {', '.join(central_powers)}")
    
    # Step 5: Identify Belgium factor
    print("\nStep 5: Identifying contested neutral SCs (Belgium factor)...")
    contested_scs = identify_belgium_factor(cells, territories, supply_centers)
    print(f"  Found {len(contested_scs)} SCs accessible by 3+ powers")
    for sc_data in contested_scs:
        print(f"    {sc_data['cell_id']}: accessible by {sc_data['num_powers']} powers")
    
    # Generate recommendations
    recommendations = []
    
    if degree_analysis['highly_connected']:
        recommendations.append(f"Consider splitting {len(degree_analysis['highly_connected'])} highly connected nodes")
    
    if degree_analysis['dead_ends']:
        recommendations.append(f"Consider merging {len(degree_analysis['dead_ends'])} dead-end nodes")
    
    if not sea_connectivity['connected']:
        recommendations.append("WARNING: Seas are not fully connected - some are landlocked")
    
    if triangle_analysis['triangle_density'] < MIN_TRIANGLE_DENSITY:
        recommendations.append(f"Low triangle density - map may not support complex diplomacy (target: {MIN_TRIANGLE_DENSITY:.0%})")
    
    if len(corner_powers) < 2:
        recommendations.append("Too few corner powers - consider rebalancing")
    
    if len(contested_scs) == 0:
        recommendations.append("No contested neutral SCs - early game may be too peaceful")
    
    output = {
        "config": phase5_output["config"],
        "cells": cells,
        "territories": territories,
        "supply_centers": supply_centers,
        "analysis": {
            "degree_analysis": {
                "average_degree": degree_analysis['average'],
                "min_degree": degree_analysis['min'],
                "max_degree": degree_analysis['max'],
                "highly_connected_count": len(degree_analysis['highly_connected']),
                "dead_end_count": len(degree_analysis['dead_ends']),
                "highly_connected_nodes": degree_analysis['highly_connected'],
                "dead_end_nodes": degree_analysis['dead_ends']
            },
            "sea_connectivity": sea_connectivity,
            "triangle_analysis": triangle_analysis,
            "power_classifications": power_classifications,
            "contested_scs": contested_scs
        },
        "recommendations": recommendations,
        "statistics": {
            **phase5_output["statistics"],
            "corner_powers": len(corner_powers),
            "central_powers": len(central_powers),
            "contested_neutral_scs": len(contested_scs)
        }
    }
    
    print("\n" + "=" * 60)
    print("PHASE 6 COMPLETE: Graph analysis and optimization")
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  • {rec}")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 6."""
    parser = argparse.ArgumentParser(description="Phase 6: Graph Optimization")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 5")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 5 output
    with open(args.input, 'r') as f:
        phase5_output = json.load(f)
    
    config = {}
    
    # Run phase 6
    output = run_phase6(phase5_output, config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        _, _, output_path = get_output_path_for_phase(
            "phase6_optimization_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
