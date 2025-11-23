#!/usr/bin/env python3
"""
Phase 6: Graph Analysis and Validation

This phase analyzes the map graph quality for gameplay and provides recommendations.
It performs analysis only and does NOT modify the map (to prevent breaking SCs and powers).

Analysis includes:
1. Check bottlenecks (degree of each node)
2. Analyze triangle density (support mechanic viability)
3. Verify connectivity between all sea zones
4. Classify power positions (corner vs central)
5. Identify contested neutral SCs (Belgium factor)

Note: Ocean connectivity is now fixed in Phase 2 (before SCs and powers are assigned).
Phase 6 only validates that the ocean is connected and warns if it's not.

Input: supply_centers_output.json from Phase 5
Output: analysis_output.json with quality metrics and recommendations
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
    # Include nodes with 0 neighbors as they are isolated and should be considered dead ends
    dead_ends = [cell_id for cell_id, deg in degrees.items() if deg < LOW_CONNECTIVITY_THRESHOLD]
    
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


def mark_cell_as_impassable(cell):
    """
    Mark a cell as impassable and remove game-relevant attributes.
    
    Args:
        cell: Cell dictionary to mark as impassable
    """
    cell["type"] = "impassable"
    cell["neighbors"] = []
    
    # Remove supply center status if present
    if cell.get("is_supply_center"):
        cell["is_supply_center"] = False
        cell["sc_type"] = None
    
    # Remove ownership if present
    if cell.get("owner"):
        cell["owner"] = None
    if cell.get("is_home"):
        cell["is_home"] = False


def merge_dead_end_node(cell_id, cells):
    """
    Merge a dead-end node by removing it and connecting its neighbors directly.
    
    Args:
        cell_id: ID of the dead-end node to merge
        cells: Dictionary of cell data
        
    Returns:
        True if merge was successful, False otherwise
    """
    if cell_id not in cells:
        return False
    
    cell = cells[cell_id]
    neighbors = cell["neighbors"]
    
    # Handle nodes with 0 neighbors (completely isolated)
    if len(neighbors) == 0:
        mark_cell_as_impassable(cell)
        return True
    
    # Handle nodes with 1 neighbor (isolated dead-end)
    if len(neighbors) == 1:
        neighbor_id = neighbors[0]
        if neighbor_id in cells:
            # Remove this node from its neighbor's list
            if cell_id in cells[neighbor_id]["neighbors"]:
                cells[neighbor_id]["neighbors"].remove(cell_id)
        
        # Mark the cell as impassable
        mark_cell_as_impassable(cell)
        return True
    
    # Handle nodes with 2 neighbors (connect them directly)
    if len(neighbors) == 2:
        neighbor1_id, neighbor2_id = neighbors[0], neighbors[1]
        
        # Check both neighbors exist
        if neighbor1_id not in cells or neighbor2_id not in cells:
            return False
        
        # Connect the two neighbors directly (if not already connected)
        neighbor1 = cells[neighbor1_id]
        neighbor2 = cells[neighbor2_id]
        
        if neighbor2_id not in neighbor1["neighbors"]:
            neighbor1["neighbors"].append(neighbor2_id)
        if neighbor1_id not in neighbor2["neighbors"]:
            neighbor2["neighbors"].append(neighbor1_id)
        
        # Remove the dead-end node from its neighbors' neighbor lists
        if cell_id in neighbor1["neighbors"]:
            neighbor1["neighbors"].remove(cell_id)
        if cell_id in neighbor2["neighbors"]:
            neighbor2["neighbors"].remove(cell_id)
        
        # Mark the cell as impassable
        mark_cell_as_impassable(cell)
        return True
    
    # Can't merge nodes with 3+ neighbors
    return False


def split_highly_connected_node(cell_id, cells):
    """
    Split a highly connected node by reducing its connectivity.
    
    Since we can't actually create new cells in the Voronoi mesh,
    we instead remove some edges to reduce connectivity.
    
    Args:
        cell_id: ID of the highly connected node
        cells: Dictionary of cell data
        
    Returns:
        Number of edges removed
    """
    if cell_id not in cells:
        return 0
    
    cell = cells[cell_id]
    neighbors = cell["neighbors"][:]  # Copy list
    
    # Target: reduce to about 6 neighbors (midpoint of good range)
    target_degree = 6
    edges_to_remove = len(neighbors) - target_degree
    
    if edges_to_remove <= 0:
        return 0
    
    # Strategy: Remove edges to neighbors that also have high degree
    # This helps balance the graph overall
    neighbor_degrees = []
    for neighbor_id in neighbors:
        if neighbor_id in cells:
            degree = len(cells[neighbor_id]["neighbors"])
            neighbor_degrees.append((neighbor_id, degree))
    
    # Sort by degree (highest first)
    neighbor_degrees.sort(key=lambda x: x[1], reverse=True)
    
    # Remove edges to highest-degree neighbors
    removed = 0
    for neighbor_id, _ in neighbor_degrees[:edges_to_remove]:
        # Remove bidirectional edge
        if neighbor_id in cell["neighbors"]:
            cell["neighbors"].remove(neighbor_id)
        if cell_id in cells[neighbor_id]["neighbors"]:
            cells[neighbor_id]["neighbors"].remove(cell_id)
        removed += 1
    
    return removed


def connect_sea_components(cells, sea_connectivity):
    """
    Connect disconnected sea components by converting land bridges to sea.
    
    Args:
        cells: Dictionary of cell data
        sea_connectivity: Sea connectivity analysis
        
    Returns:
        Number of land cells converted to sea
    """
    if sea_connectivity["connected"]:
        return 0
    
    # Find all sea components using BFS
    sea_cells = [cell_id for cell_id, cell in cells.items() if cell["type"] == "sea"]
    
    if len(sea_cells) < 2:
        return 0
    
    # Build components
    visited = set()
    components = []
    
    for start_cell in sea_cells:
        if start_cell in visited:
            continue
        
        component = []
        queue = deque([start_cell])
        visited.add(start_cell)
        
        while queue:
            cell_id = queue.popleft()
            component.append(cell_id)
            
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor in cells and cells[neighbor]["type"] == "sea" and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        components.append(component)
    
    if len(components) <= 1:
        return 0
    
    # Sort components by size (largest first)
    components.sort(key=len, reverse=True)
    
    # Strategy: Connect smaller components to the largest one
    # Find the shortest path through land cells between components
    largest_component = set(components[0])
    converted = 0
    
    for component in components[1:]:
        component_set = set(component)
        
        # Find land cells adjacent to this component
        adjacent_to_small = set()
        for cell_id in component:
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor in cells and cells[neighbor]["type"] == "land":
                    adjacent_to_small.add(neighbor)
        
        # Find land cells adjacent to the largest component
        adjacent_to_large = set()
        for cell_id in largest_component:
            for neighbor in cells[cell_id]["neighbors"]:
                if neighbor in cells and cells[neighbor]["type"] == "land":
                    adjacent_to_large.add(neighbor)
        
        # Check if any land cells are adjacent to both (direct bridge)
        direct_bridges = adjacent_to_small & adjacent_to_large
        
        if direct_bridges:
            # Use the first direct bridge
            bridge_id = list(direct_bridges)[0]
        else:
            # Find shortest path through land using BFS
            # Start from land cells adjacent to small component
            visited_land = set()
            parent = {}
            queue = deque()
            
            for start in adjacent_to_small:
                queue.append(start)
                visited_land.add(start)
                parent[start] = None
            
            found_bridge = None
            while queue and not found_bridge:
                current = queue.popleft()
                
                # Check if we reached a cell adjacent to the large component
                if current in adjacent_to_large:
                    found_bridge = current
                    break
                
                # Explore land neighbors
                for neighbor in cells[current]["neighbors"]:
                    if neighbor in cells and cells[neighbor]["type"] == "land" and neighbor not in visited_land:
                        visited_land.add(neighbor)
                        parent[neighbor] = current
                        queue.append(neighbor)
            
            if not found_bridge:
                continue  # Can't connect this component
            
            # Trace back path and convert cells
            path = []
            current = found_bridge
            while current is not None:
                path.append(current)
                current = parent[current]
            
            # Convert the shortest land cell in the path (preferably not a home territory or SC)
            bridge_id = None
            for cell_id in path:
                if not cells[cell_id].get("is_home") and not cells[cell_id].get("is_supply_center"):
                    bridge_id = cell_id
                    break
            
            # If all cells in path are important, use the first one
            if not bridge_id:
                bridge_id = path[0]
        
        # Convert the bridge cell to sea
        if bridge_id and bridge_id in cells:
            cells[bridge_id]["type"] = "sea"
            cells[bridge_id]["coastal"] = False
            
            # Remove land-specific attributes
            if cells[bridge_id].get("owner"):
                cells[bridge_id]["owner"] = None
            if cells[bridge_id].get("is_supply_center"):
                cells[bridge_id]["is_supply_center"] = False
                cells[bridge_id]["sc_type"] = None
            if cells[bridge_id].get("is_home"):
                cells[bridge_id]["is_home"] = False
            
            converted += 1
            largest_component.add(bridge_id)
    
    return converted


def run_phase6(phase5_output, config):
    """
    Run Phase 6: Graph Analysis and Validation (analysis only, no modifications).
    
    Args:
        phase5_output: Output from Phase 5
        config: Configuration parameters
        
    Returns:
        Dictionary with analysis data and recommendations
    """
    print("=" * 60)
    print("PHASE 6: GRAPH ANALYSIS AND VALIDATION")
    print("=" * 60)
    print("\nNOTE: This phase performs analysis only and does NOT modify the map.")
    print("Ocean connectivity is now fixed in Phase 2 (before SCs/powers are assigned).")
    
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
    
    # Step 2: Check sea connectivity (validation only)
    print("\nStep 2: Validating sea connectivity...")
    sea_connectivity = check_sea_connectivity(cells)
    print(f"  All seas connected: {sea_connectivity['connected']}")
    print(f"  Number of sea components: {sea_connectivity['components']}")
    if sea_connectivity['components'] > 1:
        print(f"  Component sizes: {sea_connectivity['component_sizes']}")
        print(f"  WARNING: Seas are not connected. This should have been fixed in Phase 2.")
    
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
    
    # Step 6: Verify map integrity
    print("\nStep 6: Verifying map integrity...")
    integrity_issues = []
    
    # Check that all powers have exactly 3 SCs
    for power_id, territory_data in territories.items():
        power_sc_count = sum(1 for cell_id in territory_data["cells"] 
                            if cells[cell_id].get("is_supply_center", False))
        if power_sc_count != 3:
            integrity_issues.append(f"Power {power_id} has {power_sc_count} SCs (expected 3)")
    
    # Count total SCs
    total_scs = sum(1 for cell in cells.values() if cell.get("is_supply_center", False))
    expected_scs = len(territories) * 3 + len(supply_centers.get("neutral", []))
    if total_scs != expected_scs:
        integrity_issues.append(f"Total SC count mismatch: {total_scs} (expected {expected_scs})")
    
    if integrity_issues:
        print("  INTEGRITY ISSUES FOUND:")
        for issue in integrity_issues:
            print(f"    ✗ {issue}")
    else:
        print("  ✓ All integrity checks passed")
    
    # Generate recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    recommendations = []
    
    if degree_analysis['highly_connected']:
        recommendations.append(f"Found {len(degree_analysis['highly_connected'])} highly connected nodes (>7 neighbors) - consider regenerating with different parameters")
    
    if degree_analysis['dead_ends']:
        recommendations.append(f"Found {len(degree_analysis['dead_ends'])} dead-end nodes (<3 neighbors) - consider regenerating with different parameters")
    
    if not sea_connectivity['connected']:
        recommendations.append("CRITICAL: Seas not fully connected - Phase 2 ocean connectivity fix may have failed")
    
    if triangle_analysis['triangle_density'] < MIN_TRIANGLE_DENSITY:
        recommendations.append(f"Low triangle density ({triangle_analysis['triangle_density']:.1%}) - map may not support complex diplomacy (target: {MIN_TRIANGLE_DENSITY:.0%})")
    
    if len(corner_powers) < 2:
        recommendations.append("Too few corner powers - map may be unbalanced")
    
    if len(central_powers) == 0:
        recommendations.append("No central powers - map may lack strategic tension")
    
    if len(contested_scs) == 0:
        recommendations.append("No contested neutral SCs - early game may be too peaceful")
    
    if integrity_issues:
        recommendations.append("CRITICAL: Map integrity issues found - regeneration recommended")
    
    if not recommendations:
        print("\n  ✓ No issues found - map quality is acceptable!")
    else:
        print("\nIssues found:")
        for rec in recommendations:
            print(f"  • {rec}")
    
    output = {
        "config": phase5_output["config"],
        "cells": cells,
        "topology": phase5_output.get("topology", {}),
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
            "contested_scs": contested_scs,
            "integrity_issues": integrity_issues
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
    print("PHASE 6 COMPLETE: Graph analysis and validation")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 6."""
    parser = argparse.ArgumentParser(description="Phase 6: Graph Analysis and Validation")
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
            "phase6_analysis_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
