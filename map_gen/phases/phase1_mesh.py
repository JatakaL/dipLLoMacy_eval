#!/usr/bin/env python3
"""
Phase 1: Mesh Generation (Voronoi Tesselation)

This phase generates the base mesh structure using:
1. Poisson Disk Sampling for point distribution
2. Domain Warping (optional) - distorts space using noise for organic shapes
3. Voronoi diagram generation
4. Lloyd's Relaxation (optional)

Input: Configuration parameters
Output: mesh_output.json with cell polygons and adjacency
"""

import json
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon as ShapelyPolygon
import argparse
import sys
import os

# Add parent directory to path for topology import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_utils import get_output_path_for_phase
from topology import convert_cells_to_topology


def generate_perlin_noise_2d(shape, res, seed=None):
    """
    Generate 2D Perlin noise for domain warping.
    
    Args:
        shape: Shape of the output array (height, width)
        res: Resolution/frequency of the noise tuple (res_y, res_x)
        seed: Random seed
        
    Returns:
        2D numpy array of noise values approximately in range [-1, 1]
    """
    if seed is not None:
        np.random.seed(seed)
    
    def smoothstep(t):
        return t * t * (3.0 - 2.0 * t)
    
    # Create coordinate grids
    noise_height, noise_width = shape
    y = np.linspace(0, res[0], noise_height, endpoint=False)
    x = np.linspace(0, res[1], noise_width, endpoint=False)
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


def sample_noise_at_point(noise_map, x, y, width, height):
    """
    Sample the noise map at a specific point using bilinear interpolation.
    
    Args:
        noise_map: 2D noise array
        x: X coordinate in [0, width] space
        y: Y coordinate in [0, height] space  
        width: Map width
        height: Map height
        
    Returns:
        Interpolated noise value at the point
    """
    h, w = noise_map.shape
    
    # Convert to noise map coordinates
    nx = (x / width) * (w - 1)
    ny = (y / height) * (h - 1)
    
    # Clamp to valid range
    nx = max(0, min(w - 1, nx))
    ny = max(0, min(h - 1, ny))
    
    # Bilinear interpolation
    x0 = int(np.floor(nx))
    y0 = int(np.floor(ny))
    x1 = min(x0 + 1, w - 1)
    y1 = min(y0 + 1, h - 1)
    
    fx = nx - x0
    fy = ny - y0
    
    v00 = noise_map[y0, x0]
    v10 = noise_map[y0, x1]
    v01 = noise_map[y1, x0]
    v11 = noise_map[y1, x1]
    
    v0 = v00 * (1 - fx) + v10 * fx
    v1 = v01 * (1 - fx) + v11 * fx
    
    return v0 * (1 - fy) + v1 * fy


def apply_domain_warp(points, width, height, warp_strength=0.1, warp_frequency=2, seed=None):
    """
    Apply domain warping to points using low-frequency Perlin noise.
    
    This creates stretched, organic shapes by distorting the space before
    Voronoi generation. The warping moves each point based on noise values,
    creating cells that look "squashed" or "stretched" rather than uniform.
    
    Args:
        points: Array of [x, y] coordinates
        width: Width of the sampling area
        height: Height of the sampling area
        warp_strength: How much to displace points (as fraction of dimensions)
        warp_frequency: Frequency of the noise (lower = larger features)
        seed: Random seed for reproducibility
        
    Returns:
        Array of warped [x, y] coordinates
    """
    if warp_strength <= 0:
        return points.copy()
    
    # Generate low-frequency noise maps for x and y displacement
    # Scale noise resolution with map size for consistent quality
    # Using 100 as base multiplier provides good quality for typical map sizes
    noise_resolution = max(100, int(max(width, height) * 100))
    noise_shape = (noise_resolution, noise_resolution)
    
    # Use different seeds for x and y noise to ensure independence
    # When seed is None, use explicit different values to ensure different patterns
    seed_x = seed if seed is not None else 12345
    seed_y = seed + 100 if seed is not None else 67890
    noise_x = generate_perlin_noise_2d(noise_shape, (warp_frequency, warp_frequency), seed=seed_x)
    noise_y = generate_perlin_noise_2d(noise_shape, (warp_frequency, warp_frequency), seed=seed_y)
    
    # Calculate maximum displacement based on strength
    max_displacement_x = width * warp_strength
    max_displacement_y = height * warp_strength
    
    # Apply warping to each point
    buffer = 0.05  # Keep points within bounds

    warped_points = np.array([
        [
            max(buffer, min(width - buffer, x + sample_noise_at_point(noise_x, x, y, width, height) * max_displacement_x)),
            max(buffer, min(height - buffer, y + sample_noise_at_point(noise_y, x, y, width, height) * max_displacement_y))
        ]
        for x, y in points
    ])

    return warped_points
def poisson_disk_sampling(width, height, min_distance, num_points, seed=None):
    """
    Generate points using Poisson disk sampling.
    
    Args:
        width: Width of the sampling area
        height: Height of the sampling area
        min_distance: Minimum distance between points
        num_points: Target number of points
        seed: Random seed for reproducibility
        
    Returns:
        Array of [x, y] coordinates
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Simple Poisson disk sampling implementation
    # Start with random points and reject those too close to existing ones
    points = []
    max_attempts = num_points * 50  # Prevent infinite loops
    
    buffer = 0.05  # 5% buffer from edges
    
    for _ in range(max_attempts):
        if len(points) >= num_points:
            break
            
        # Generate candidate point
        candidate = np.array([
            np.random.uniform(buffer, width - buffer),
            np.random.uniform(buffer, height - buffer)
        ])
        
        # Check distance to all existing points
        if not points:
            points.append(candidate)
            continue
            
        distances = np.linalg.norm(np.array(points) - candidate, axis=1)
        if np.min(distances) >= min_distance:
            points.append(candidate)
    
    return np.array(points)


def generate_voronoi_cells(points, width=1.0, height=1.0):
    """
    Generate Voronoi diagram from points.
    
    Args:
        points: Array of [x, y] coordinates
        width: Width of the bounding box
        height: Height of the bounding box
        
    Returns:
        Dictionary of cells with polygon data
    """
    # Add corner points to ensure full coverage
    corner_points = np.array([
        [-0.1, -0.1], [width/2, -0.1], [width+0.1, -0.1],
        [-0.1, height/2], [width+0.1, height/2],
        [-0.1, height+0.1], [width/2, height+0.1], [width+0.1, height+0.1]
    ])
    all_points = np.vstack([points, corner_points])
    
    # Generate Voronoi diagram
    vor = Voronoi(all_points)
    
    # Define boundary polygon
    boundary = ShapelyPolygon([
        (0, 0), (width, 0), (width, height), (0, height)
    ])
    
    cells = {}
    num_original_points = len(points)
    
    for i in range(num_original_points):
        cell_id = f"C{i+1}"
        region_idx = vor.point_region[i]
        region_vertices = vor.regions[region_idx]
        
        # Skip unbounded regions
        if -1 in region_vertices or not region_vertices:
            continue
        
        # Get polygon vertices
        polygon_vertices = vor.vertices[region_vertices]
        
        # Create Shapely polygon
        try:
            shapely_poly = ShapelyPolygon(polygon_vertices)
            
            # Clip to boundary
            clipped_poly = shapely_poly.intersection(boundary)
            
            if clipped_poly.is_empty or clipped_poly.geom_type not in ['Polygon', 'MultiPolygon']:
                continue
            
            # Extract coordinates
            if clipped_poly.geom_type == 'Polygon':
                clipped_vertices = list(clipped_poly.exterior.coords)
            else:  # MultiPolygon - use largest part
                largest = max(clipped_poly.geoms, key=lambda p: p.area)
                clipped_vertices = list(largest.exterior.coords)
            
            cells[cell_id] = {
                "id": cell_id,
                "center": points[i].tolist(),
                "vertices": clipped_vertices,
                "area": clipped_poly.area,
                "neighbors": []
            }
        except Exception as e:
            print(f"Warning: Failed to create cell {cell_id}: {e}")
            continue
    
    return cells


def build_adjacency(cells):
    """
    Build adjacency relationships between cells.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Updated cells dictionary with neighbor information
    """
    cell_ids = list(cells.keys())
    
    # Create Shapely polygons for efficient intersection testing
    cell_polygons = {
        cell_id: ShapelyPolygon(cells[cell_id]["vertices"])
        for cell_id in cell_ids
    }
    
    # Check each pair for adjacency
    for i, cell1 in enumerate(cell_ids):
        poly1 = cell_polygons[cell1]
        
        for cell2 in cell_ids[i+1:]:
            poly2 = cell_polygons[cell2]
            
            # Check if polygons share a border
            if poly1.touches(poly2) or poly1.intersects(poly2):
                cells[cell1]["neighbors"].append(cell2)
                cells[cell2]["neighbors"].append(cell1)
    
    return cells


def lloyds_relaxation(cells, iterations=1, width=1.0, height=1.0):
    """
    Apply Lloyd's relaxation to make cells more uniform.
    
    Lloyd's algorithm iteratively improves cell uniformity by:
    1. Computing the centroid of each Voronoi cell
    2. Moving each point to its cell's centroid
    3. Regenerating the Voronoi diagram
    4. Repeating for the specified number of iterations
    
    Args:
        cells: Dictionary of cell data
        iterations: Number of relaxation iterations
        width: Width of the bounding box
        height: Height of the bounding box
        
    Returns:
        Relaxed cells dictionary
    """
    print(f"Applying Lloyd's relaxation ({iterations} iterations)...")
    
    # Extract initial points from cells
    points = np.array([cell["center"] for cell in cells.values()])
    
    for iteration in range(iterations):
        # Generate Voronoi diagram for current points
        cells = generate_voronoi_cells(points, width, height)
        
        # Calculate the true geometric centroid of each Voronoi cell
        # Note: The order of cells.values() matches the order of points used to generate them
        new_points = []
        for cell in cells.values():
            try:
                # Use Shapely to calculate the proper area-weighted centroid
                poly = ShapelyPolygon(cell["vertices"])
                if poly.is_valid:
                    centroid = poly.centroid
                    new_points.append([centroid.x, centroid.y])
                else:
                    # If polygon is invalid, keep the original center
                    new_points.append(cell["center"])
            except Exception as e:
                # If centroid calculation fails, keep the original center
                print(f"    Warning: Failed to calculate centroid for cell {cell['id']}, using original center")
                new_points.append(cell["center"])
        
        points = np.array(new_points)
        print(f"  Iteration {iteration + 1}/{iterations} complete")
    
    # Generate final cells with relaxed points
    cells = generate_voronoi_cells(points, width, height)
    cells = build_adjacency(cells)
    
    return cells


def run_phase1(config):
    """
    Run Phase 1: Mesh Generation.
    
    Args:
        config: Dictionary with configuration parameters
        
    Returns:
        Dictionary with mesh data
    """
    print("=" * 60)
    print("PHASE 1: MESH GENERATION (Voronoi Tesselation)")
    print("=" * 60)
    
    # Extract configuration
    num_cells = config.get("num_cells", 80)
    width = config.get("width", 1.0)
    height = config.get("height", 1.0)
    min_distance = config.get("min_distance", 0.05)
    lloyd_iterations = config.get("lloyd_iterations", 0)
    seed = config.get("seed", 42)
    
    # Domain warping configuration
    warp_enabled = config.get("warp_enabled", False)
    warp_strength = config.get("warp_strength", 0.1)
    warp_frequency = config.get("warp_frequency", 2)
    
    print(f"\nConfiguration:")
    print(f"  Target cells: {num_cells}")
    print(f"  Dimensions: {width} x {height}")
    print(f"  Min distance: {min_distance}")
    print(f"  Lloyd iterations: {lloyd_iterations}")
    print(f"  Random seed: {seed}")
    if warp_enabled:
        print(f"  Domain warping: enabled")
        print(f"    - Warp strength: {warp_strength}")
        print(f"    - Warp frequency: {warp_frequency}")
    else:
        print(f"  Domain warping: disabled")
    
    # Step 1: Point scattering with Poisson disk sampling
    print(f"\nStep 1: Generating {num_cells} points with Poisson disk sampling...")
    points = poisson_disk_sampling(width, height, min_distance, num_cells, seed)
    print(f"  Generated {len(points)} points")
    
    # Step 2: Apply domain warping (optional)
    if warp_enabled:
        print("\nStep 2: Applying domain warping...")
        points = apply_domain_warp(points, width, height, warp_strength, warp_frequency, seed)
        print(f"  Warped {len(points)} points with strength={warp_strength}, frequency={warp_frequency}")
    
    # Step 3: Generate Voronoi diagram
    step_num = 3 if warp_enabled else 2
    print(f"\nStep {step_num}: Generating Voronoi diagram...")
    cells = generate_voronoi_cells(points, width, height)
    print(f"  Created {len(cells)} valid cells")
    
    # Step 4: Build adjacency relationships
    step_num += 1
    print(f"\nStep {step_num}: Building cell adjacency...")
    cells = build_adjacency(cells)
    total_neighbors = sum(len(cell["neighbors"]) for cell in cells.values())
    avg_neighbors = total_neighbors / len(cells) if cells else 0
    print(f"  Average neighbors per cell: {avg_neighbors:.2f}")
    
    # Step 5: Lloyd's relaxation (optional)
    if lloyd_iterations > 0:
        step_num += 1
        print(f"\nStep {step_num}: Applying Lloyd's relaxation...")
        cells = lloyds_relaxation(cells, lloyd_iterations, width, height)
    
    # Step 6: Convert to topological representation
    step_num += 1
    print(f"\nStep {step_num}: Converting to topological representation (Face-Edge-Vertex)...")
    topology = convert_cells_to_topology(cells)
    
    # Verify topology integrity
    print(f"  Topology verification:")
    print(f"    - {len(topology['vertices'])} unique vertices")
    print(f"    - {len(topology['edges'])} edges")
    print(f"    - {len(topology['faces'])} faces")
    
    output = {
        "config": config,
        "topology": topology,
        "statistics": {
            "total_faces": len(topology['faces']),
            "average_neighbors": avg_neighbors,
            "topology_vertices": len(topology['vertices']),
            "topology_edges": len(topology['edges'])
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 1 COMPLETE: Generated {len(topology['faces'])} faces with topology")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 1."""
    parser = argparse.ArgumentParser(description="Phase 1: Mesh Generation")
    parser.add_argument("--num-cells", type=int, default=80, help="Target number of cells")
    parser.add_argument("--width", type=float, default=1.0, help="Map width")
    parser.add_argument("--height", type=float, default=1.0, help="Map height")
    parser.add_argument("--min-distance", type=float, default=0.05, help="Minimum distance between points")
    parser.add_argument("--lloyd-iterations", type=int, default=0, help="Number of Lloyd relaxation iterations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--warp-enabled", action="store_true", help="Enable domain warping for organic shapes")
    parser.add_argument("--warp-strength", type=float, default=0.1, help="Domain warp strength (0-1, as fraction of map dimensions)")
    parser.add_argument("--warp-frequency", type=int, default=2, help="Domain warp noise frequency (lower = larger features)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in datetime subdirectory)")
    parser.add_argument("--output-dir", type=str, default=None, help="Base output directory (default: ../map_output)")
    
    args = parser.parse_args()
    
    config = {
        "num_cells": args.num_cells,
        "width": args.width,
        "height": args.height,
        "min_distance": args.min_distance,
        "lloyd_iterations": args.lloyd_iterations,
        "seed": args.seed,
        "warp_enabled": args.warp_enabled,
        "warp_strength": args.warp_strength,
        "warp_frequency": args.warp_frequency
    }
    
    # Run phase 1
    output = run_phase1(config)
    
    # Determine output path
    if args.output:
        # User specified a custom output path
        output_path = args.output
    else:
        # Use automatic path generation
        _, _, output_path = get_output_path_for_phase(
            "phase1_mesh_output",
            input_file=None,
            base_dir=args.output_dir,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
