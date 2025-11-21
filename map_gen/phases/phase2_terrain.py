#!/usr/bin/env python3
"""
Phase 2: Terrain Assignment (Land vs. Sea)

This phase assigns terrain types to cells:
1. Generate noise map (Perlin/Simplex noise)
2. Apply radial gradient mask
3. Assign land/sea based on threshold
4. Cull single-cell islands and lakes

Input: mesh_output.json from Phase 1
Output: terrain_output.json with land/sea assignments
"""

import json
import numpy as np
import argparse


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


def assign_terrain(cells, noise_map, threshold, width, height):
    """
    Assign land or sea to each cell based on noise value.
    
    Args:
        cells: Dictionary of cell data
        noise_map: 2D noise array
        threshold: Threshold for land (value > threshold = land)
        width: Map width
        height: Map height
        
    Returns:
        Updated cells with terrain type
    """
    land_count = 0
    sea_count = 0
    
    for cell_id, cell in cells.items():
        noise_value = sample_noise_for_cell(noise_map, cell["center"], width, height)
        
        if noise_value > threshold:
            cell["type"] = "land"
            land_count += 1
        else:
            cell["type"] = "sea"
            sea_count += 1
        
        cell["noise_value"] = float(noise_value)
    
    return cells, land_count, sea_count


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
    cells, land_count, sea_count = assign_terrain(cells, masked_noise, threshold, width, height)
    total = land_count + sea_count
    land_ratio = land_count / total if total > 0 else 0
    print(f"  Land cells: {land_count} ({land_ratio:.1%})")
    print(f"  Sea cells: {sea_count} ({1-land_ratio:.1%})")
    
    # Step 4: Cull single-cell islands/lakes
    print("\nStep 4: Culling single-cell islands and lakes...")
    for i in range(cull_iterations):
        cells, changes = cull_single_cells(cells)
        print(f"  Iteration {i+1}: {changes} cells flipped")
        if changes == 0:
            break
    
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
            "land_ratio": land_ratio
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 2 COMPLETE: {land_count} land, {sea_count} sea ({land_ratio:.1%} land)")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 2."""
    parser = argparse.ArgumentParser(description="Phase 2: Terrain Assignment")
    parser.add_argument("--input", type=str, default="mesh_output.json", help="Input JSON from Phase 1")
    parser.add_argument("--threshold", type=float, default=0.25, help="Terrain threshold")
    parser.add_argument("--land-ratio", type=float, default=0.6, help="Target land ratio")
    parser.add_argument("--octaves", type=int, default=4, help="Noise octaves")
    parser.add_argument("--radial-falloff", type=float, default=0.8, help="Radial mask falloff")
    parser.add_argument("--cull-iterations", type=int, default=2, help="Culling iterations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="terrain_output.json", help="Output JSON file")
    
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
    
    # Save output
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
