"""
Fractal Edge Subdivision Module

This module implements fractal subdivision for map edges using midpoint displacement.
It creates organic-looking coastlines and borders by recursively displacing edge midpoints.

The Algorithm:
1. Take an Edge E connecting Vertex A and Vertex B
2. Find the midpoint M
3. Move M slightly perpendicular to the direction of the edge by a random amount
4. Recursively repeat for segments A -> M and M -> B
5. Create new vertices and edges in the topology (topological subdivision)
6. Update borders to contain the new edges

Two Approaches:
1. generate_all_visual_paths(): Legacy approach - stores visual coordinates in visual_path
   array on each edge. Simple but creates inconsistency between visual and topological data.
   
2. subdivide_all_edges(): New approach - actually modifies the topology by creating new
   vertices and edges. This ensures visual representation matches topological data.

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


def subdivide_edge_topology(
    topology: Dict,
    edge_id: str,
    seed: Optional[int] = None
) -> Tuple[List[str], List[int]]:
    """
    Subdivide a single edge in the topology, creating new vertices and edges.
    
    This function:
    1. Uses the fractal midpoint displacement algorithm
    2. Creates new vertices at each displaced point
    3. Creates new edges connecting consecutive vertices
    4. Updates the border to contain the new edges
    5. Removes the original edge
    
    Args:
        topology: Topology dictionary (modified in place)
        edge_id: ID of the edge to subdivide
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (new_edge_ids, new_vertex_ids)
    """
    vertices = topology.get("vertices", [])
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    faces = topology.get("faces", {})
    
    if edge_id not in edges:
        return [], []
    
    edge = edges[edge_id]
    v1_id = edge.get("v1")
    v2_id = edge.get("v2")
    edge_type = edge.get("type", "land")
    left_face = edge.get("left_face")
    right_face = edge.get("right_face")
    
    # Create vertex coordinate lookup
    vertex_coords = {v["id"]: tuple(v["coords"]) for v in vertices}
    
    # If vertices are missing, return the original edge unchanged
    if v1_id not in vertex_coords or v2_id not in vertex_coords:
        return [edge_id], []
    
    v1_coords = vertex_coords[v1_id]
    v2_coords = vertex_coords[v2_id]
    
    # Get displacement parameters for this edge type
    initial_displacement, roughness, max_depth = get_edge_displacement_params(edge_type)
    
    # If no subdivision needed, return unchanged
    if initial_displacement == 0.0 or max_depth == 0:
        return [edge_id], []
    
    # Generate the subdivided path using midpoint displacement
    dx = v2_coords[0] - v1_coords[0]
    dy = v2_coords[1] - v1_coords[1]
    edge_length = math.sqrt(dx * dx + dy * dy)
    displacement = initial_displacement * edge_length
    
    rng = random.Random(seed)
    path = midpoint_displacement(
        v1_coords, v2_coords,
        displacement, roughness,
        0, max_depth, rng
    )
    
    # If path has only 2 points (start and end), no subdivision needed
    if len(path) <= 2:
        return [edge_id], []
    
    # Find the maximum vertex ID - handle empty list case
    if not vertices:
        return [edge_id], []  # Cannot subdivide without existing vertices
    max_vertex_id = max(v["id"] for v in vertices)
    
    # Create new vertices for intermediate points (skip first and last which are v1 and v2)
    new_vertex_ids = []
    for i, point in enumerate(path):
        if i == 0 or i == len(path) - 1:
            continue  # Skip start and end points
        
        max_vertex_id += 1
        new_vertex = {
            "id": max_vertex_id,
            "coords": list(point)
        }
        vertices.append(new_vertex)
        new_vertex_ids.append(max_vertex_id)
    
    # Create new edges connecting consecutive vertices
    new_edge_ids = []
    all_vertex_ids = [v1_id] + new_vertex_ids + [v2_id]
    
    for i in range(len(all_vertex_ids) - 1):
        from_v = all_vertex_ids[i]
        to_v = all_vertex_ids[i + 1]
        
        # Create canonical edge ID (smaller vertex ID first)
        min_v = min(from_v, to_v)
        max_v = max(from_v, to_v)
        new_edge_id = f"E_{min_v}_{max_v}"
        
        # Create the new edge with same properties as original
        new_edge = {
            "v1": min_v,
            "v2": max_v,
            "type": edge_type
        }
        if left_face:
            new_edge["left_face"] = left_face
        if right_face:
            new_edge["right_face"] = right_face
        
        edges[new_edge_id] = new_edge
        new_edge_ids.append(new_edge_id)
    
    # Find and update the border that contains this edge
    border_id = f"B_{min(v1_id, v2_id)}_{max(v1_id, v2_id)}"
    if border_id in borders:
        border = borders[border_id]
        # Replace the original edge with the new edges in the border's edge list
        if edge_id in border["edges"]:
            idx = border["edges"].index(edge_id)
            border["edges"] = border["edges"][:idx] + new_edge_ids + border["edges"][idx+1:]
        else:
            # Edge wasn't in the border's list - append new edges to preserve existing ones
            # This handles the case where the border was created with a different initial edge
            border["edges"].extend(new_edge_ids)
    
    # Note: Faces now only contain borders, not edges directly.
    # The border update above already handles the edge replacement.
    # No need to update faces since they reference borders, not edges.
    
    # Remove the original edge
    del edges[edge_id]
    
    return new_edge_ids, new_vertex_ids


def subdivide_all_edges(
    topology: Dict,
    seed: int = 42
) -> Dict:
    """
    Subdivide all edges in a topology to create jagged borders.
    
    This function modifies the topology in place by:
    1. Creating new vertices at displaced midpoints
    2. Replacing each edge with multiple smaller edges
    3. Updating borders to contain the new edges
    4. Updating faces to reference the new edges
    
    This approach ensures that the visual representation is based
    on the actual topological data, not a separate visual-only path.
    
    Args:
        topology: Topology dictionary with vertices, edges, faces, and borders
        seed: Base random seed for reproducibility
        
    Returns:
        Updated topology with subdivided edges
    """
    edges = topology.get("edges", {})
    
    # Get list of original edge IDs (copy since we'll modify the dict)
    original_edge_ids = list(edges.keys())
    
    total_new_edges = 0
    total_new_vertices = 0
    
    for edge_id in original_edge_ids:
        if edge_id not in edges:
            continue  # Edge may have been removed in a previous iteration
        
        # Create edge-specific seed for reproducibility
        edge = edges[edge_id]
        v1_id = edge.get("v1", 0)
        v2_id = edge.get("v2", 0)
        edge_seed = seed + (hash((v1_id, v2_id)) & 0x7FFFFFFF) % 10000
        
        new_edge_ids, new_vertex_ids = subdivide_edge_topology(
            topology, edge_id, edge_seed
        )
        
        if new_edge_ids and new_edge_ids != [edge_id]:
            total_new_edges += len(new_edge_ids)
            total_new_vertices += len(new_vertex_ids)
    
    return topology


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
