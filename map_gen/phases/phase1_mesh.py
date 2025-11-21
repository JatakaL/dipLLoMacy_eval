#!/usr/bin/env python3
"""
Phase 1: Mesh Generation (Voronoi Tesselation)

This phase generates the base mesh structure using:
1. Poisson Disk Sampling for point distribution
2. Voronoi diagram generation
3. Lloyd's Relaxation (optional)

Input: Configuration parameters
Output: mesh_output.json with cell polygons and adjacency
"""

import json
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon as ShapelyPolygon
import argparse


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


def lloyds_relaxation(cells, iterations=1):
    """
    Apply Lloyd's relaxation to make cells more uniform.
    
    Args:
        cells: Dictionary of cell data
        iterations: Number of relaxation iterations
        
    Returns:
        Relaxed cells dictionary
    """
    # Lloyd's relaxation moves each point to the centroid of its Voronoi cell
    # For now, we'll skip this as it requires regenerating the Voronoi diagram
    # This is a placeholder that can be implemented if needed
    print(f"Lloyd's relaxation ({iterations} iterations) - skipped for now")
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
    
    print(f"\nConfiguration:")
    print(f"  Target cells: {num_cells}")
    print(f"  Dimensions: {width} x {height}")
    print(f"  Min distance: {min_distance}")
    print(f"  Lloyd iterations: {lloyd_iterations}")
    print(f"  Random seed: {seed}")
    
    # Step 1: Point scattering with Poisson disk sampling
    print(f"\nStep 1: Generating {num_cells} points with Poisson disk sampling...")
    points = poisson_disk_sampling(width, height, min_distance, num_cells, seed)
    print(f"  Generated {len(points)} points")
    
    # Step 2: Generate Voronoi diagram
    print("\nStep 2: Generating Voronoi diagram...")
    cells = generate_voronoi_cells(points, width, height)
    print(f"  Created {len(cells)} valid cells")
    
    # Step 3: Build adjacency relationships
    print("\nStep 3: Building cell adjacency...")
    cells = build_adjacency(cells)
    total_neighbors = sum(len(cell["neighbors"]) for cell in cells.values())
    avg_neighbors = total_neighbors / len(cells) if cells else 0
    print(f"  Average neighbors per cell: {avg_neighbors:.2f}")
    
    # Step 4: Lloyd's relaxation (optional)
    if lloyd_iterations > 0:
        print(f"\nStep 4: Applying Lloyd's relaxation...")
        cells = lloyds_relaxation(cells, lloyd_iterations)
    
    output = {
        "config": config,
        "cells": cells,
        "statistics": {
            "total_cells": len(cells),
            "average_neighbors": avg_neighbors
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 1 COMPLETE: Generated {len(cells)} cells")
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
    parser.add_argument("--output", type=str, default="mesh_output.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    config = {
        "num_cells": args.num_cells,
        "width": args.width,
        "height": args.height,
        "min_distance": args.min_distance,
        "lloyd_iterations": args.lloyd_iterations,
        "seed": args.seed
    }
    
    # Run phase 1
    output = run_phase1(config)
    
    # Save output
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
