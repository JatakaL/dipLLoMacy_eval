"""
Fractal Edge Subdivision Module

This module implements fractal subdivision for map edges using midpoint displacement.
It creates organic-looking coastlines and borders by recursively displacing edge midpoints.

The Algorithm:
1. Take an Edge E connecting Vertex A and Vertex B
2. Find the midpoint M
3. Move M slightly perpendicular to the direction of the edge by a random amount
4. Recursively repeat for segments A -> M and M -> B
5. Store these new points in a visual_path array inside the Edge

Refinement Strategy:
- Coastlines (land-sea boundaries): Heavy displacement for jagged coastlines
- Land borders (political lines/rivers): Gentle displacement for smoother borders
- Sea borders: Very gentle displacement
- Map edges: No displacement (remain straight)
"""

import math
import random
from typing import Dict, List, Tuple, Optional

# Tolerance for detecting degenerate edges (near-zero length)
EDGE_LENGTH_EPSILON = 1e-9


def midpoint_displacement(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
    displacement: float,
    roughness: float,
    depth: int,
    max_depth: int,
    rng: random.Random
) -> List[Tuple[float, float]]:
    """
    Recursively subdivide a line segment using midpoint displacement.
    
    Args:
        point_a: Starting point (x, y)
        point_b: Ending point (x, y)
        displacement: Current displacement magnitude
        roughness: How much displacement decreases each level (0.0 - 1.0)
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        rng: Random number generator for reproducibility
        
    Returns:
        List of points forming the subdivided path from A to B (inclusive)
    """
    if depth >= max_depth:
        return [point_a, point_b]
    
    # Calculate midpoint
    mid_x = (point_a[0] + point_b[0]) / 2.0
    mid_y = (point_a[1] + point_b[1]) / 2.0
    
    # Calculate perpendicular direction
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    length = math.sqrt(dx * dx + dy * dy)
    
    if length < EDGE_LENGTH_EPSILON:
        return [point_a, point_b]
    
    # Perpendicular unit vector (rotate 90 degrees)
    perp_x = -dy / length
    perp_y = dx / length
    
    # Random displacement along perpendicular
    offset = (rng.random() * 2.0 - 1.0) * displacement
    
    # Displaced midpoint
    mid_displaced = (
        mid_x + perp_x * offset,
        mid_y + perp_y * offset
    )
    
    # Reduce displacement for next level
    new_displacement = displacement * roughness
    
    # Recurse on both halves
    left_path = midpoint_displacement(
        point_a, mid_displaced, new_displacement, roughness,
        depth + 1, max_depth, rng
    )
    right_path = midpoint_displacement(
        mid_displaced, point_b, new_displacement, roughness,
        depth + 1, max_depth, rng
    )
    
    # Combine paths (remove duplicate midpoint)
    return left_path[:-1] + right_path


def get_edge_displacement_params(edge_type: str) -> Tuple[float, float, int]:
    """
    Get displacement parameters based on edge type.
    
    Args:
        edge_type: Type of edge ("coast", "land", "sea", "map-edge")
        
    Returns:
        Tuple of (initial_displacement, roughness, max_depth)
        - initial_displacement: Starting displacement magnitude (fraction of edge length)
        - roughness: How quickly displacement decreases (0.0 - 1.0)
        - max_depth: Maximum recursion depth
    """
    if edge_type == "coast":
        # Heavy displacement for coastlines - creates jagged, natural-looking shores
        return (0.08, 0.65, 4)
    elif edge_type == "land":
        # Gentle displacement for land borders - smoother political boundaries
        return (0.03, 0.5, 3)
    elif edge_type == "sea":
        # Very gentle displacement for sea borders
        return (0.02, 0.5, 2)
    elif edge_type == "map-edge":
        # No displacement for map boundaries - stay straight
        return (0.0, 0.5, 0)
    else:
        # Default: gentle displacement
        return (0.02, 0.5, 2)


def generate_visual_path(
    v1_coords: Tuple[float, float],
    v2_coords: Tuple[float, float],
    edge_type: str,
    seed: Optional[int] = None
) -> List[List[float]]:
    """
    Generate a visual path for an edge using fractal subdivision.
    
    Args:
        v1_coords: Coordinates of first vertex (x, y)
        v2_coords: Coordinates of second vertex (x, y)
        edge_type: Type of edge ("coast", "land", "sea", "map-edge")
        seed: Random seed for reproducibility
        
    Returns:
        List of [x, y] points forming the visual path
    """
    # Get displacement parameters for this edge type
    initial_displacement, roughness, max_depth = get_edge_displacement_params(edge_type)
    
    # If no displacement, return simple line
    if initial_displacement == 0.0 or max_depth == 0:
        return [list(v1_coords), list(v2_coords)]
    
    # Calculate edge length-based displacement
    dx = v2_coords[0] - v1_coords[0]
    dy = v2_coords[1] - v1_coords[1]
    edge_length = math.sqrt(dx * dx + dy * dy)
    
    # Scale displacement by edge length
    displacement = initial_displacement * edge_length
    
    # Create reproducible random generator
    rng = random.Random(seed)
    
    # Generate the subdivided path
    path = midpoint_displacement(
        v1_coords, v2_coords,
        displacement, roughness,
        0, max_depth, rng
    )
    
    # Convert to list format
    return [list(point) for point in path]


def generate_all_visual_paths(
    topology: Dict,
    seed: int = 42
) -> Dict:
    """
    Generate visual paths for all edges in a topology.
    
    Args:
        topology: Topology dictionary with vertices, edges, and faces
        seed: Base random seed for reproducibility
        
    Returns:
        Updated topology with visual_path added to each edge
    """
    vertices = topology.get("vertices", [])
    edges = topology.get("edges", {})
    
    # Create vertex coordinate lookup
    vertex_coords = {v["id"]: tuple(v["coords"]) for v in vertices}
    
    # Generate visual paths for each edge
    for edge_id, edge_data in edges.items():
        v1_id = edge_data.get("v1")
        v2_id = edge_data.get("v2")
        edge_type = edge_data.get("type", "land")
        
        if v1_id not in vertex_coords or v2_id not in vertex_coords:
            continue
        
        v1_coords = vertex_coords[v1_id]
        v2_coords = vertex_coords[v2_id]
        
        # Create edge-specific seed for reproducibility
        # Use edge vertex IDs to make seed deterministic per edge
        # Use bitwise AND with 0x7FFFFFFF to ensure positive value
        edge_seed = seed + (hash((v1_id, v2_id)) & 0x7FFFFFFF) % 10000
        
        # Generate visual path
        visual_path = generate_visual_path(
            v1_coords, v2_coords, edge_type, edge_seed
        )
        
        # Store in edge data
        edge_data["visual_path"] = visual_path
    
    return topology
