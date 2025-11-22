#!/usr/bin/env python3
"""
Phase 2: Terrain Assignment (Land vs. Sea)

This phase assigns terrain types to cells and optimizes the graph structure:
1. Generate noise map (Perlin/Simplex noise)
2. Apply radial gradient mask
3. Calculate threshold based on target land ratio
4. Assign land/sea based on calculated threshold
5. Cull single-cell islands and lakes
6. Check and fix ocean connectivity (connects disconnected seas)
7. Optimize graph structure (merge dead-ends, split highly-connected nodes)

The threshold is dynamically calculated from the noise value distribution
to achieve the target land ratio specified in the configuration.

Ocean connectivity and graph optimizations are done at this stage (before
supply centers and powers are assigned) to prevent breaking the map later.

Input: mesh_output.json from Phase 1
Output: terrain_output.json with land/sea assignments and optimized structure
"""

import json
import numpy as np
import argparse
from collections import deque

from output_utils import get_output_path_for_phase


def generate_perlin_noise_2d(shape, res, seed=None):
    """
    Generate 2D Perlin noise using a simpler approach.
    
    Args:
        shape: Shape of the output array (height, width)
        res: Resolution/frequency of the noise tuple (res_y, res_x)
        seed: Random seed
        
    Returns:
        2D numpy array of noise values
    """
    if seed is not None:
        np.random.seed(seed)
    
    def smoothstep(t):
        return t * t * (3.0 - 2.0 * t)
    
    # Create coordinate grids
    height, width = shape
    y = np.linspace(0, res[0], height, endpoint=False)
    x = np.linspace(0, res[1], width, endpoint=False)
    x_grid, y_grid = np.meshgrid(x, y)
    
    # Integer parts
    x0 = np.floor(x_grid).astype(int)
    y0 = np.floor(y_grid).astype(int)
    
    # Fractional parts
    fx = x_grid - x0
    fy = y_grid - y0
    
    # Wrap around
    x0 = x0 % res[1]
    y0 = y0 % res[0]
    x1 = (x0 + 1) % res[1]
    y1 = (y0 + 1) % res[0]
    
    # Generate random gradients for grid points
    grad_size = (res[0] + 1, res[1] + 1)
    angles = 2 * np.pi * np.random.rand(*grad_size)
    grad_x = np.cos(angles)
    grad_y = np.sin(angles)
    
    # Get gradients at corners
    g00_x = grad_x[y0, x0]
    g00_y = grad_y[y0, x0]
    g10_x = grad_x[y0, x1]
    g10_y = grad_y[y0, x1]
    g01_x = grad_x[y1, x0]
    g01_y = grad_y[y1, x0]
    g11_x = grad_x[y1, x1]
    g11_y = grad_y[y1, x1]
    
    # Dot products with distance vectors
    n00 = g00_x * fx + g00_y * fy
    n10 = g10_x * (fx - 1) + g10_y * fy
    n01 = g01_x * fx + g01_y * (fy - 1)
    n11 = g11_x * (fx - 1) + g11_y * (fy - 1)
    
    # Interpolate
    sx = smoothstep(fx)
    sy = smoothstep(fy)
    
    n0 = n00 * (1 - sx) + n10 * sx
    n1 = n01 * (1 - sx) + n11 * sx
    
    return n0 * (1 - sy) + n1 * sy


def generate_noise_map(width, height, octaves=4, seed=None):
    """
    Generate a multi-octave Perlin noise map.
    
    Args:
        width: Width of the noise map
        height: Height of the noise map
        octaves: Number of octaves for the noise
        seed: Random seed
        
    Returns:
        2D numpy array normalized to [0, 1]
    """
    shape = (int(height * 100), int(width * 100))  # Higher resolution for sampling
    noise = np.zeros(shape)
    
    for octave in range(octaves):
        freq = 2 ** octave
        amplitude = 1.0 / (2 ** octave)
        
        res = (4 * freq, 4 * freq)
        octave_noise = generate_perlin_noise_2d(shape, res, seed=seed + octave if seed else None)
        noise += octave_noise * amplitude
    
    # Normalize to [0, 1]
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    
    return noise


def apply_radial_mask(noise_map, center=(0.5, 0.5), falloff=0.5):
    """
    Apply a radial gradient mask to force land in center, water at edges.
    
    Args:
        noise_map: 2D noise array
        center: Center point (x, y) in [0, 1] coordinates
        falloff: How quickly the mask falls off from center
        
    Returns:
        Modified noise map
    """
    height, width = noise_map.shape
    
    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    x = x / width
    y = y / height
    
    # Calculate distance from center
    dx = x - center[0]
    dy = y - center[1]
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create radial mask (1 at center, 0 at edges)
    max_distance = np.sqrt(2) / 2  # Maximum distance to corner
    mask = 1.0 - (distance / max_distance) ** falloff
    mask = np.clip(mask, 0, 1)
    
    # Apply mask to noise
    masked_noise = noise_map * mask
    
    return masked_noise


def sample_noise_for_cell(noise_map, cell_center, width, height):
    """
    Sample the noise map at a cell's center.
    
    Args:
        noise_map: 2D noise array
        cell_center: [x, y] coordinates in [0, 1] space
        width: Map width
        height: Map height
        
    Returns:
        Noise value at cell center
    """
    h, w = noise_map.shape
    
    # Convert cell center to noise map coordinates
    x = int(cell_center[0] * w)
    y = int(cell_center[1] * h)
    
    # Clamp to valid range
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    
    return noise_map[y, x]


def assign_terrain(cells, noise_map, threshold, width, height, land_ratio_target=None):
    """
    Assign land or sea to each cell based on noise value.
    
    Args:
        cells: Dictionary of cell data
        noise_map: 2D noise array
        threshold: Threshold for land (value > threshold = land). 
                   If land_ratio_target is provided, this will be recalculated.
        width: Map width
        height: Map height
        land_ratio_target: Optional target land ratio (0-1). If provided, 
                          threshold will be calculated to achieve this ratio.
        
    Returns:
        Updated cells with terrain type and the actual threshold used
    """
    # Validate land_ratio_target if provided
    if land_ratio_target is not None:
        if not 0 <= land_ratio_target <= 1:
            raise ValueError(f"land_ratio_target must be between 0 and 1, got {land_ratio_target}")
    
    # Sample all noise values for the cells
    noise_values = []
    for cell_id, cell in cells.items():
        noise_value = sample_noise_for_cell(noise_map, cell["center"], width, height)
        cell["noise_value"] = float(noise_value)
        noise_values.append(noise_value)
    
    # If land_ratio_target is provided, calculate threshold from the distribution
    if land_ratio_target is not None:
        # We want the top land_ratio_target percent to be land
        # So we need the (1 - land_ratio_target) percentile as the threshold
        sea_percentile = (1 - land_ratio_target) * 100
        threshold = np.percentile(noise_values, sea_percentile)
    
    # Now assign terrain types based on the threshold
    land_count = 0
    sea_count = 0
    
    for cell_id, cell in cells.items():
        noise_value = cell["noise_value"]
        
        if noise_value > threshold:
            cell["type"] = "land"
            land_count += 1
        else:
            cell["type"] = "sea"
            sea_count += 1
    
    return cells, land_count, sea_count, threshold


def cull_single_cells(cells):
    """
    Remove single-cell islands and lakes by flipping them to match neighbors.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Updated cells with culled single cells
    """
    changes = 0
    
    for cell_id, cell in cells.items():
        if not cell.get("neighbors"):
            continue
        
        # Count neighbor types
        neighbor_types = [cells[n]["type"] for n in cell["neighbors"] if n in cells]
        
        if not neighbor_types:
            continue
        
        # If all neighbors are the opposite type, flip this cell
        neighbor_land = sum(1 for t in neighbor_types if t == "land")
        neighbor_sea = sum(1 for t in neighbor_types if t == "sea")
        
        # If isolated (all neighbors are opposite type), flip
        if cell["type"] == "land" and neighbor_sea > neighbor_land * 2:
            cell["type"] = "sea"
            changes += 1
        elif cell["type"] == "sea" and neighbor_land > neighbor_sea * 2:
            cell["type"] = "land"
            changes += 1
    
    return cells, changes


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
    # Highly connected: >7 neighbors
    highly_connected = [cell_id for cell_id, deg in degrees.items() if deg > 7]
    # Dead ends: <3 neighbors
    dead_ends = [cell_id for cell_id, deg in degrees.items() if deg < 3]
    
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


def merge_dead_end_node(cell_id, cells):
    """
    Merge a dead-end node by removing it and connecting its neighbors directly.
    Only merges if it doesn't create invalid connections (e.g., land-to-sea).
    
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
    cell_type = cell["type"]
    
    # Handle nodes with 0 neighbors (completely isolated)
    if len(neighbors) == 0:
        cell["type"] = "impassable"
        cell["neighbors"] = []
        return True
    
    # Handle nodes with 1 neighbor (isolated dead-end)
    if len(neighbors) == 1:
        neighbor_id = neighbors[0]
        if neighbor_id in cells:
            # Remove this node from its neighbor's list
            if cell_id in cells[neighbor_id]["neighbors"]:
                cells[neighbor_id]["neighbors"].remove(cell_id)
        
        # Mark the cell as impassable
        cell["type"] = "impassable"
        cell["neighbors"] = []
        return True
    
    # Handle nodes with 2 neighbors (connect them directly)
    if len(neighbors) == 2:
        neighbor1_id, neighbor2_id = neighbors[0], neighbors[1]
        
        # Check both neighbors exist
        if neighbor1_id not in cells or neighbor2_id not in cells:
            return False
        
        neighbor1 = cells[neighbor1_id]
        neighbor2 = cells[neighbor2_id]
        
        # IMPORTANT: Only merge if both neighbors are the same type as this cell
        # This prevents connecting land to sea or other invalid connections
        if neighbor1["type"] != cell_type or neighbor2["type"] != cell_type:
            return False
        
        # Connect the two neighbors directly (if not already connected)
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
        cell["type"] = "impassable"
        cell["neighbors"] = []
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
    
    This is done in Phase 2 before any supply centers or powers are assigned,
    so we don't need to worry about breaking the map by removing important cells.
    
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
            
            # Trace back path and convert only the first cell in the path
            # (We prefer converting fewer cells in Phase 2)
            bridge_id = found_bridge
        
        # Convert the bridge cell to sea
        if bridge_id and bridge_id in cells:
            cells[bridge_id]["type"] = "sea"
            cells[bridge_id]["coastal"] = False
            converted += 1
            largest_component.add(bridge_id)
    
    return converted


def run_phase2(phase1_output, config):
    """
    Run Phase 2: Terrain Assignment.
    
    Args:
        phase1_output: Output from Phase 1
        config: Configuration parameters
        
    Returns:
        Dictionary with terrain data
    """
    print("=" * 60)
    print("PHASE 2: TERRAIN ASSIGNMENT (Land vs. Sea)")
    print("=" * 60)
    
    cells = phase1_output["cells"]
    
    # Extract configuration
    width = phase1_output["config"].get("width", 1.0)
    height = phase1_output["config"].get("height", 1.0)
    threshold = config.get("threshold", 0.25)
    land_ratio_target = config.get("land_ratio", 0.6)
    octaves = config.get("octaves", 4)
    radial_falloff = config.get("radial_falloff", 0.8)
    cull_iterations = config.get("cull_iterations", 2)
    seed = config.get("seed", 42)
    
    print(f"\nConfiguration:")
    print(f"  Target land ratio: {land_ratio_target}")
    print(f"  Threshold: {threshold}")
    print(f"  Octaves: {octaves}")
    print(f"  Radial falloff: {radial_falloff}")
    print(f"  Cull iterations: {cull_iterations}")
    
    # Step 1: Generate noise map
    print("\nStep 1: Generating Perlin noise map...")
    noise_map = generate_noise_map(width, height, octaves, seed)
    print(f"  Noise map shape: {noise_map.shape}")
    print(f"  Noise range: [{noise_map.min():.3f}, {noise_map.max():.3f}]")
    
    # Step 2: Apply radial mask
    print("\nStep 2: Applying radial gradient mask...")
    masked_noise = apply_radial_mask(noise_map, center=(0.5, 0.5), falloff=radial_falloff)
    print(f"  Masked noise range: [{masked_noise.min():.3f}, {masked_noise.max():.3f}]")
    
    # Step 3: Assign terrain
    print("\nStep 3: Assigning terrain types...")
    cells, land_count, sea_count, actual_threshold = assign_terrain(
        cells, masked_noise, threshold, width, height, land_ratio_target=land_ratio_target
    )
    total = land_count + sea_count
    land_ratio = land_count / total if total > 0 else 0
    print(f"  Calculated threshold: {actual_threshold:.3f} (target land ratio: {land_ratio_target})")
    print(f"  Land cells: {land_count} ({land_ratio:.1%})")
    print(f"  Sea cells: {sea_count} ({1-land_ratio:.1%})")
    
    # Step 4: Cull single-cell islands/lakes
    print("\nStep 4: Culling single-cell islands and lakes...")
    for i in range(cull_iterations):
        cells, changes = cull_single_cells(cells)
        print(f"  Iteration {i+1}: {changes} cells flipped")
        if changes == 0:
            break
    
    # Step 5: Check and fix sea connectivity
    print("\nStep 5: Checking sea connectivity...")
    sea_connectivity = check_sea_connectivity(cells)
    print(f"  All seas connected: {sea_connectivity['connected']}")
    print(f"  Number of sea components: {sea_connectivity['components']}")
    
    if not sea_connectivity['connected']:
        print(f"  Component sizes: {sea_connectivity['component_sizes']}")
        print(f"  Connecting {sea_connectivity['components']} sea components...")
        
        total_converted = 0
        max_attempts = 10
        attempts = 0
        
        while attempts < max_attempts:
            current_connectivity = check_sea_connectivity(cells)
            if current_connectivity['connected']:
                break
            
            converted = connect_sea_components(cells, current_connectivity)
            if converted == 0:
                break
            
            total_converted += converted
            attempts += 1
        
        if total_converted > 0:
            print(f"  Converted {total_converted} land cells to sea to connect oceans")
        
        # Re-check connectivity
        final_connectivity = check_sea_connectivity(cells)
        print(f"  Final connectivity: {final_connectivity['connected']}")
    
    # Step 6: Optimize graph structure (merge dead-ends and split highly-connected nodes)
    print("\nStep 6: Optimizing graph structure...")
    initial_analysis = analyze_node_degrees(cells)
    print(f"  Initial: avg degree {initial_analysis['average']:.2f}, "
          f"{len(initial_analysis['highly_connected'])} highly connected, "
          f"{len(initial_analysis['dead_ends'])} dead ends")
    
    # Merge dead-end nodes (iterative, as merging can create new dead-ends)
    if initial_analysis['dead_ends']:
        print(f"  Merging dead-end nodes...")
        total_merged = 0
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            current_analysis = analyze_node_degrees(cells)
            if not current_analysis['dead_ends']:
                break
            
            merged_this_iteration = 0
            for dead_end_id in current_analysis['dead_ends']:
                if merge_dead_end_node(dead_end_id, cells):
                    merged_this_iteration += 1
                    total_merged += 1
            
            if merged_this_iteration == 0:
                break
            
            iteration += 1
        
        if total_merged > 0:
            print(f"    Merged {total_merged} dead-end nodes")
    
    # Split highly connected nodes
    if initial_analysis['highly_connected']:
        print(f"  Splitting highly connected nodes...")
        total_edges_removed = 0
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            current_analysis = analyze_node_degrees(cells)
            if not current_analysis['highly_connected']:
                break
            
            edges_removed_this_iteration = 0
            for high_conn_id in current_analysis['highly_connected']:
                edges_removed = split_highly_connected_node(high_conn_id, cells)
                edges_removed_this_iteration += edges_removed
                total_edges_removed += edges_removed
            
            if edges_removed_this_iteration == 0:
                break
            
            iteration += 1
        
        if total_edges_removed > 0:
            print(f"    Removed {total_edges_removed} edges from highly connected nodes")
    
    # Show final analysis
    final_analysis = analyze_node_degrees(cells)
    print(f"  Final: avg degree {final_analysis['average']:.2f}, "
          f"{len(final_analysis['highly_connected'])} highly connected, "
          f"{len(final_analysis['dead_ends'])} dead ends")
    
    # Recalculate statistics
    land_count = sum(1 for c in cells.values() if c["type"] == "land")
    sea_count = sum(1 for c in cells.values() if c["type"] == "sea")
    land_ratio = land_count / (land_count + sea_count) if (land_count + sea_count) > 0 else 0
    
    output = {
        "config": {**phase1_output["config"], **config},
        "cells": cells,
        "statistics": {
            "total_cells": len(cells),
            "land_cells": land_count,
            "sea_cells": sea_count,
            "land_ratio": land_ratio,
            "sea_connectivity": check_sea_connectivity(cells)
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 2 COMPLETE: {land_count} land, {sea_count} sea ({land_ratio:.1%} land)")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 2."""
    parser = argparse.ArgumentParser(description="Phase 2: Terrain Assignment")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 1")
    parser.add_argument("--threshold", type=float, default=0.25, help="Terrain threshold")
    parser.add_argument("--land-ratio", type=float, default=0.6, help="Target land ratio")
    parser.add_argument("--octaves", type=int, default=4, help="Noise octaves")
    parser.add_argument("--radial-falloff", type=float, default=0.8, help="Radial mask falloff")
    parser.add_argument("--cull-iterations", type=int, default=2, help="Culling iterations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 1 output
    with open(args.input, 'r') as f:
        phase1_output = json.load(f)
    
    config = {
        "threshold": args.threshold,
        "land_ratio": args.land_ratio,
        "octaves": args.octaves,
        "radial_falloff": args.radial_falloff,
        "cull_iterations": args.cull_iterations,
        "seed": args.seed
    }
    
    # Run phase 2
    output = run_phase2(phase1_output, config)
    
    # Determine output path
    if args.output:
        # User specified a custom output path
        output_path = args.output
    else:
        # Use automatic path generation (same directory as input)
        _, _, output_path = get_output_path_for_phase(
            "phase2_terrain_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
