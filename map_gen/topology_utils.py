"""
Topology Utilities Module

This module implements utility functions for topology manipulation including:
- Calculating edge lengths using shapely LineString
- Calculating face sizes (areas) using shapely Polygon
- Merging adjacent faces (works at border level, then affects edges)
- Splitting faces (works at border level, then affects edges)

Architecture:
    All face-level operations work through BORDERS as the intermediary layer.
    Face → Border → Edge hierarchy is maintained.
    
    When splitting a face:
    1. Find two borders to split between (longest and opposite)
    2. Split each border at its midpoint using split_border()
    3. Create a new border connecting the split points
    4. Assign borders to the two new faces
    
    Border operations (split_border, etc.) handle the edge-level details.
"""

import math
from typing import Dict, List, Tuple, Optional
from shapely.geometry import Polygon, LineString
from shapely.errors import GEOSException
from topology import get_adjacency_from_topology, get_face_edges


def _get_vertex_coords_lookup(topology: dict) -> Dict[int, List[float]]:
    """
    Create a lookup dictionary for vertex coordinates.
    
    Args:
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Dictionary mapping vertex ID to coordinates [x, y]
    """
    return {v["id"]: v["coords"] for v in topology.get("vertices", [])}


def _trace_face_polygon_vertices(face_id: str, topology: dict) -> List[List[float]]:
    """
    Trace the polygon boundary of a face and return ordered vertices.
    
    This function builds a graph from the face's edges and traces the boundary
    to get an ordered list of vertex coordinates forming the polygon.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        List of [x, y] coordinates forming the polygon boundary
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    if face_id not in faces:
        return []
    
    face = faces[face_id]
    edge_ids = get_face_edges(face, borders)
    
    if not edge_ids:
        return []
    
    # Build a graph of vertex connections from the face's edges
    vertex_graph = {}
    for edge_id in edge_ids:
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        v1, v2 = edge["v1"], edge["v2"]
        
        if v1 not in vertex_graph:
            vertex_graph[v1] = []
        if v2 not in vertex_graph:
            vertex_graph[v2] = []
        vertex_graph[v1].append(v2)
        vertex_graph[v2].append(v1)
    
    if not vertex_graph:
        return []
    
    # Trace the polygon boundary to get ordered vertices
    polygon_vertices = []
    start_vertex = next(iter(vertex_graph.keys()))
    current = start_vertex
    visited = set()
    
    for _ in range(len(vertex_graph) + 1):
        if current in visited and current == start_vertex and len(visited) > 0:
            break
        if current in visited:
            break
        
        visited.add(current)
        if current in vertex_coords:
            polygon_vertices.append(vertex_coords[current])
        
        # Find next unvisited vertex
        neighbors = vertex_graph.get(current, [])
        next_vertex = None
        for neighbor in neighbors:
            if neighbor not in visited or (neighbor == start_vertex and len(visited) == len(vertex_graph)):
                next_vertex = neighbor
                break
        
        if next_vertex is None:
            break
        current = next_vertex
    
    return polygon_vertices


def _get_face_polygon(face_id: str, topology: dict) -> Optional[Polygon]:
    """
    Get a shapely Polygon object for a face.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Shapely Polygon object, or None if the polygon cannot be created
    """
    vertices = _trace_face_polygon_vertices(face_id, topology)
    
    if len(vertices) < 3:
        return None
    
    try:
        return Polygon(vertices)
    except (ValueError, GEOSException):
        return None


def calculate_edge_length(edge_id: str, topology: dict) -> float:
    """
    Calculate the length of an edge using shapely LineString.
    
    Args:
        edge_id: ID of the edge (e.g., "E_0_1")
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Length of the edge in map units
    """
    edges = topology.get("edges", {})
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    if edge_id not in edges:
        raise ValueError(f"Edge {edge_id} not found in topology")
    
    edge = edges[edge_id]
    v1_id = edge["v1"]
    v2_id = edge["v2"]
    
    v1_coords = vertex_coords.get(v1_id)
    v2_coords = vertex_coords.get(v2_id)
    
    if v1_coords is None or v2_coords is None:
        raise ValueError(f"Vertices for edge {edge_id} not found")
    
    # Use shapely LineString for length calculation
    line = LineString([v1_coords, v2_coords])
    return line.length


def calculate_face_size(face_id: str, topology: dict) -> float:
    """
    Calculate the area of a face using shapely Polygon.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Area of the face in square map units
    """
    faces = topology.get("faces", {})
    
    if face_id not in faces:
        raise ValueError(f"Face {face_id} not found in topology")
    
    polygon = _get_face_polygon(face_id, topology)
    
    if polygon is None:
        return 0.0
    
    return polygon.area


# =============================================================================
# BORDER-LEVEL OPERATIONS
# =============================================================================
# These functions operate at the border level, providing the intermediary
# layer between faces and edges. Face operations call these functions
# rather than manipulating edges directly.
# =============================================================================

def calculate_border_length(border_id: str, topology: dict) -> float:
    """
    Calculate the total length of a border (sum of all its edge lengths).
    
    Args:
        border_id: ID of the border
        topology: Dictionary with topology data
        
    Returns:
        Total length of the border in map units
    """
    borders = topology.get("borders", {})
    
    if border_id not in borders:
        raise ValueError(f"Border {border_id} not found in topology")
    
    border = borders[border_id]
    total_length = 0.0
    
    for edge_id in border.get("edges", []):
        try:
            total_length += calculate_edge_length(edge_id, topology)
        except ValueError:
            continue
    
    return total_length


def get_border_midpoint(border_id: str, topology: dict) -> Optional[Tuple[float, float]]:
    """
    Get the midpoint of a border.
    
    For a border with a single edge, this is the edge midpoint.
    For multi-edge borders, this is the point at half the total length.
    
    Args:
        border_id: ID of the border
        topology: Dictionary with topology data
        
    Returns:
        (x, y) coordinates of the midpoint, or None if cannot be calculated
    """
    borders = topology.get("borders", {})
    edges = topology.get("edges", {})
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    if border_id not in borders:
        return None
    
    border = borders[border_id]
    edge_ids = border.get("edges", [])
    
    if not edge_ids:
        return None
    
    # For single-edge borders (most common case before subdivision)
    if len(edge_ids) == 1:
        edge_id = edge_ids[0]
        if edge_id not in edges:
            return None
        edge = edges[edge_id]
        v1_coords = vertex_coords.get(edge["v1"])
        v2_coords = vertex_coords.get(edge["v2"])
        if v1_coords is None or v2_coords is None:
            return None
        line = LineString([v1_coords, v2_coords])
        midpoint = line.interpolate(0.5, normalized=True)
        return (midpoint.x, midpoint.y)
    
    # For multi-edge borders, find point at half total length
    total_length = calculate_border_length(border_id, topology)
    if total_length <= 0:
        return None
    
    target_length = total_length / 2.0
    accumulated = 0.0
    
    for edge_id in edge_ids:
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        v1_coords = vertex_coords.get(edge["v1"])
        v2_coords = vertex_coords.get(edge["v2"])
        if v1_coords is None or v2_coords is None:
            continue
        
        line = LineString([v1_coords, v2_coords])
        edge_length = line.length
        
        if accumulated + edge_length >= target_length:
            # Midpoint is on this edge
            remaining = target_length - accumulated
            fraction = remaining / edge_length if edge_length > 0 else 0.5
            midpoint = line.interpolate(fraction, normalized=True)
            return (midpoint.x, midpoint.y)
        
        accumulated += edge_length
    
    return None


def get_border_endpoints(border_id: str, topology: dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Get the start and end vertex IDs of a border.
    
    Args:
        border_id: ID of the border
        topology: Dictionary with topology data
        
    Returns:
        Tuple of (start_vertex_id, end_vertex_id)
    """
    borders = topology.get("borders", {})
    
    if border_id not in borders:
        return None, None
    
    border = borders[border_id]
    return border.get("start_vertex"), border.get("end_vertex")


def split_border(border_id: str, topology: dict) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
    """
    Split a border at its midpoint into two borders.
    
    For single-edge borders, this creates:
    - A new vertex at the border's midpoint
    - Two new edges (splitting the edge at midpoint)
    - Two new borders (each containing one of the new edges)
    
    For multi-edge borders (e.g., after fractal subdivision), this:
    - Finds the edge containing the midpoint along the chain
    - Splits that edge at the midpoint
    - Creates two new borders, each containing a subset of the original edges
      plus one half of the split edge
    
    The original border and the split edge are removed.
    
    Args:
        border_id: ID of the border to split
        topology: Dictionary with topology data (vertices, edges, faces, borders)
        
    Returns:
        Tuple of (success, border1_id, border2_id, midpoint_vertex_id)
        border1_id connects to start_vertex, border2_id connects to end_vertex
    """
    borders = topology.get("borders", {})
    edges = topology.get("edges", {})
    vertices = topology.get("vertices", [])
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    if border_id not in borders:
        return False, None, None, None
    
    border = borders[border_id]
    edge_ids = border.get("edges", [])
    
    if not edge_ids:
        return False, None, None, None
    
    # Get the midpoint of the border
    midpoint = get_border_midpoint(border_id, topology)
    if midpoint is None:
        return False, None, None, None
    
    # Create new vertex at midpoint
    max_vertex_id = max(v["id"] for v in vertices) if vertices else -1
    new_vertex_id = max_vertex_id + 1
    vertices.append({"id": new_vertex_id, "coords": list(midpoint)})
    
    # For single-edge borders (most common case before subdivision)
    if len(edge_ids) == 1:
        edge_id = edge_ids[0]
        if edge_id not in edges:
            return False, None, None, None
        
        edge = edges[edge_id]
        v1_id = edge["v1"]
        v2_id = edge["v2"]
        
        # Create two new edges
        edge1_id = f"E_{min(v1_id, new_vertex_id)}_{max(v1_id, new_vertex_id)}"
        edge2_id = f"E_{min(new_vertex_id, v2_id)}_{max(new_vertex_id, v2_id)}"
        
        edges[edge1_id] = {
            "v1": min(v1_id, new_vertex_id),
            "v2": max(v1_id, new_vertex_id),
            "left_face": edge.get("left_face"),
            "right_face": edge.get("right_face"),
            "type": edge.get("type")
        }
        edges[edge2_id] = {
            "v1": min(new_vertex_id, v2_id),
            "v2": max(new_vertex_id, v2_id),
            "left_face": edge.get("left_face"),
            "right_face": edge.get("right_face"),
            "type": edge.get("type")
        }
        
        # Create two new borders using border's start/end vertices
        start_vertex = border.get("start_vertex", v1_id)
        end_vertex = border.get("end_vertex", v2_id)
        
        border1_id = f"B_{min(start_vertex, new_vertex_id)}_{max(start_vertex, new_vertex_id)}"
        border2_id = f"B_{min(new_vertex_id, end_vertex)}_{max(new_vertex_id, end_vertex)}"
        
        borders[border1_id] = {
            "edges": [edge1_id],
            "left_face": border.get("left_face"),
            "right_face": border.get("right_face"),
            "type": border.get("type"),
            "start_vertex": start_vertex,
            "end_vertex": new_vertex_id
        }
        borders[border2_id] = {
            "edges": [edge2_id],
            "left_face": border.get("left_face"),
            "right_face": border.get("right_face"),
            "type": border.get("type"),
            "start_vertex": new_vertex_id,
            "end_vertex": end_vertex
        }
        
        # Remove original edge and border
        del edges[edge_id]
        del borders[border_id]
        
        return True, border1_id, border2_id, new_vertex_id
    
    # For multi-edge borders, find which edge contains the midpoint
    total_length = calculate_border_length(border_id, topology)
    if total_length <= 0:
        return False, None, None, None
    
    target_length = total_length / 2.0
    accumulated = 0.0
    split_edge_index = -1
    split_edge_id = None
    
    for i, edge_id in enumerate(edge_ids):
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        v1_coords = vertex_coords.get(edge["v1"])
        v2_coords = vertex_coords.get(edge["v2"])
        if v1_coords is None or v2_coords is None:
            continue
        
        line = LineString([v1_coords, v2_coords])
        edge_length = line.length
        
        if accumulated + edge_length >= target_length:
            # Midpoint is on this edge
            split_edge_index = i
            split_edge_id = edge_id
            break
        
        accumulated += edge_length
    
    if split_edge_index < 0 or split_edge_id is None:
        return False, None, None, None
    
    split_edge = edges[split_edge_id]
    split_v1_id = split_edge["v1"]
    split_v2_id = split_edge["v2"]
    
    # Create two new edges from the split edge
    new_edge1_id = f"E_{min(split_v1_id, new_vertex_id)}_{max(split_v1_id, new_vertex_id)}"
    new_edge2_id = f"E_{min(new_vertex_id, split_v2_id)}_{max(new_vertex_id, split_v2_id)}"
    
    edges[new_edge1_id] = {
        "v1": min(split_v1_id, new_vertex_id),
        "v2": max(split_v1_id, new_vertex_id),
        "left_face": split_edge.get("left_face"),
        "right_face": split_edge.get("right_face"),
        "type": split_edge.get("type")
    }
    edges[new_edge2_id] = {
        "v1": min(new_vertex_id, split_v2_id),
        "v2": max(new_vertex_id, split_v2_id),
        "left_face": split_edge.get("left_face"),
        "right_face": split_edge.get("right_face"),
        "type": split_edge.get("type")
    }
    
    # Determine edge ordering - need to trace from start_vertex to midpoint to end_vertex
    # The edges before the split edge go to border1, after go to border2
    start_vertex = border.get("start_vertex")
    end_vertex = border.get("end_vertex")
    
    # Edges before the split point (plus the first half of split edge)
    border1_edges = list(edge_ids[:split_edge_index]) + [new_edge1_id]
    # Edges after the split point (plus the second half of split edge) 
    border2_edges = [new_edge2_id] + list(edge_ids[split_edge_index + 1:])
    
    # Create two new borders
    border1_id = f"B_{min(start_vertex, new_vertex_id)}_{max(start_vertex, new_vertex_id)}"
    border2_id = f"B_{min(new_vertex_id, end_vertex)}_{max(new_vertex_id, end_vertex)}"
    
    borders[border1_id] = {
        "edges": border1_edges,
        "left_face": border.get("left_face"),
        "right_face": border.get("right_face"),
        "type": border.get("type"),
        "start_vertex": start_vertex,
        "end_vertex": new_vertex_id
    }
    borders[border2_id] = {
        "edges": border2_edges,
        "left_face": border.get("left_face"),
        "right_face": border.get("right_face"),
        "type": border.get("type"),
        "start_vertex": new_vertex_id,
        "end_vertex": end_vertex
    }
    
    # Remove original split edge and border
    del edges[split_edge_id]
    del borders[border_id]
    
    return True, border1_id, border2_id, new_vertex_id


def create_border_between_vertices(v1_id: int, v2_id: int, left_face: str, right_face: str, 
                                    border_type: str, topology: dict) -> Optional[str]:
    """
    Create a new border (and its edge) connecting two vertices.
    
    Args:
        v1_id: First vertex ID
        v2_id: Second vertex ID
        left_face: ID of the left face
        right_face: ID of the right face
        border_type: Type of the border ("land", "sea", "coast", etc.)
        topology: Dictionary with topology data
        
    Returns:
        Border ID of the created border, or None on failure
    """
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    
    # Create edge
    edge_id = f"E_{min(v1_id, v2_id)}_{max(v1_id, v2_id)}"
    edges[edge_id] = {
        "v1": min(v1_id, v2_id),
        "v2": max(v1_id, v2_id),
        "left_face": left_face,
        "right_face": right_face,
        "type": border_type
    }
    
    # Create border
    border_id = f"B_{min(v1_id, v2_id)}_{max(v1_id, v2_id)}"
    borders[border_id] = {
        "edges": [edge_id],
        "left_face": left_face,
        "right_face": right_face,
        "type": border_type,
        "start_vertex": v1_id,
        "end_vertex": v2_id
    }
    
    return border_id


def get_face_borders(face_id: str, topology: dict) -> List[str]:
    """
    Get all border IDs for a face.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data
        
    Returns:
        List of border IDs
    """
    faces = topology.get("faces", {})
    
    if face_id not in faces:
        return []
    
    return faces[face_id].get("borders", [])


def find_longest_border(face_id: str, topology: dict) -> Optional[str]:
    """
    Find the longest border of a face.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data
        
    Returns:
        Border ID of the longest border, or None
    """
    border_ids = get_face_borders(face_id, topology)
    
    if not border_ids:
        return None
    
    longest_id = None
    longest_length = 0.0
    
    for border_id in border_ids:
        try:
            length = calculate_border_length(border_id, topology)
            if length > longest_length:
                longest_length = length
                longest_id = border_id
        except ValueError:
            continue
    
    return longest_id


def find_opposite_border(face_id: str, reference_border_id: str, topology: dict) -> Optional[str]:
    """
    Find the border most 'opposite' to a reference border.
    
    Uses perpendicular distance from the reference border's midpoint.
    
    Args:
        face_id: ID of the face
        reference_border_id: ID of the reference border
        topology: Dictionary with topology data
        
    Returns:
        Border ID of the opposite border, or None
    """
    borders = topology.get("borders", {})
    edges = topology.get("edges", {})
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    border_ids = get_face_borders(face_id, topology)
    
    if not border_ids or reference_border_id not in borders:
        return None
    
    # Get reference border info
    ref_border = borders[reference_border_id]
    ref_midpoint = get_border_midpoint(reference_border_id, topology)
    if ref_midpoint is None:
        return None
    
    # Get direction perpendicular to reference border
    ref_edge_ids = ref_border.get("edges", [])
    if not ref_edge_ids:
        return None
    
    ref_edge = edges.get(ref_edge_ids[0])
    if not ref_edge:
        return None
    
    v1_coords = vertex_coords.get(ref_edge["v1"])
    v2_coords = vertex_coords.get(ref_edge["v2"])
    if v1_coords is None or v2_coords is None:
        return None
    
    # Calculate perpendicular direction
    edge_vec = [v2_coords[0] - v1_coords[0], v2_coords[1] - v1_coords[1]]
    perpendicular = [-edge_vec[1], edge_vec[0]]
    perp_length = math.sqrt(perpendicular[0]**2 + perpendicular[1]**2)
    if perp_length < 1e-10:
        return None
    perpendicular = [perpendicular[0] / perp_length, perpendicular[1] / perp_length]
    
    # Find border with maximum projected distance in perpendicular direction
    opposite_id = None
    max_distance = 0.0
    
    for border_id in border_ids:
        if border_id == reference_border_id:
            continue
        
        border_midpoint = get_border_midpoint(border_id, topology)
        if border_midpoint is None:
            continue
        
        # Vector from reference midpoint to this border's midpoint
        to_border = [border_midpoint[0] - ref_midpoint[0], 
                     border_midpoint[1] - ref_midpoint[1]]
        
        # Project onto perpendicular direction
        projected = abs(to_border[0] * perpendicular[0] + to_border[1] * perpendicular[1])
        
        if projected > max_distance:
            max_distance = projected
            opposite_id = border_id
    
    return opposite_id


def update_border_face_references(border_id: str, old_face_id: str, new_face_id: str, topology: dict):
    """
    Update a border's face references and its edges' face references.
    
    Args:
        border_id: ID of the border
        old_face_id: The face ID to replace
        new_face_id: The new face ID
        topology: Dictionary with topology data
    """
    borders = topology.get("borders", {})
    edges = topology.get("edges", {})
    
    if border_id not in borders:
        return
    
    border = borders[border_id]
    
    # Update border's face references
    if border.get("left_face") == old_face_id:
        border["left_face"] = new_face_id
    if border.get("right_face") == old_face_id:
        border["right_face"] = new_face_id
    
    # Update edges' face references
    for edge_id in border.get("edges", []):
        if edge_id in edges:
            edge = edges[edge_id]
            if edge.get("left_face") == old_face_id:
                edge["left_face"] = new_face_id
            if edge.get("right_face") == old_face_id:
                edge["right_face"] = new_face_id


# =============================================================================
# END BORDER-LEVEL OPERATIONS
# =============================================================================


def merge_faces(face1_id: str, face2_id: str, topology: dict) -> Tuple[bool, Optional[str]]:
    """
    Merge two adjacent faces into one by removing the shared border between them.
    
    This operation works at the BORDER level:
    1. Find the shared border(s) between the two faces
    2. Combine borders from both faces, excluding shared borders
    3. Update remaining borders' face references
    4. Remove shared borders (and their edges)
    5. Remove face2 from topology
    
    Args:
        face1_id: ID of the first face (will be kept)
        face2_id: ID of the second face (will be removed)
        topology: Dictionary with topology data (vertices, edges, faces, borders)
        
    Returns:
        Tuple of (success: bool, merged_face_id: Optional[str])
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    
    if face1_id not in faces or face2_id not in faces:
        return False, None
    
    face1 = faces[face1_id]
    face2 = faces[face2_id]
    
    # Step 1: Find shared borders between the two faces (BORDER-LEVEL operation)
    shared_borders = []
    face1_border_ids = get_face_borders(face1_id, topology)
    
    for border_id in face1_border_ids:
        if border_id not in borders:
            continue
        border = borders[border_id]
        # Check if this border is shared between face1 and face2
        if (border.get("left_face") == face1_id and border.get("right_face") == face2_id) or \
           (border.get("left_face") == face2_id and border.get("right_face") == face1_id):
            shared_borders.append(border_id)
    
    if not shared_borders:
        # Faces are not adjacent, cannot merge
        return False, None
    
    # Step 2: Combine borders from both faces, excluding shared borders
    new_borders = []
    for border_id in face1.get("borders", []):
        if border_id not in shared_borders and border_id in borders:
            new_borders.append(border_id)
    
    for border_id in face2.get("borders", []):
        if border_id not in shared_borders and border_id not in new_borders and border_id in borders:
            new_borders.append(border_id)
    
    # Step 3: Update face1 with combined borders
    face1["borders"] = new_borders
    
    # Step 4: Update remaining borders' face references (using border-level function)
    for border_id in new_borders:
        update_border_face_references(border_id, face2_id, face1_id, topology)
    
    # Step 5: Remove shared borders and their edges
    for border_id in shared_borders:
        if border_id in borders:
            border = borders[border_id]
            # Remove the edges in this border
            for edge_id in border.get("edges", []):
                if edge_id in edges:
                    del edges[edge_id]
            # Remove the border
            del borders[border_id]
    
    # Step 6: Remove face2 from topology
    del faces[face2_id]
    
    return True, face1_id


def split_face(face_id: str, topology: dict, split_axis: str = "horizontal") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Split a face into two faces by finding the longest border and its opposite border,
    creating a split line (new border) between their midpoints.
    
    This operation works at the BORDER level:
    1. Find the face's longest border
    2. Find the opposite border (most perpendicular to longest)
    3. Split both borders at their midpoints using split_border()
    4. Create a new border connecting the two midpoint vertices
    5. Assign borders to the two new faces
    6. Update all border face references
    
    Args:
        face_id: ID of the face to split
        topology: Dictionary with topology data (vertices, edges, faces, borders)
        split_axis: Not used in this implementation (kept for API compatibility)
        
    Returns:
        Tuple of (success: bool, face1_id: Optional[str], face2_id: Optional[str])
        Returns (False, None, None) if the split cannot be performed.
    """
    faces = topology.get("faces", {})
    borders = topology.get("borders", {})
    vertices = topology.get("vertices", [])
    
    if face_id not in faces:
        return False, None, None
    
    face = faces[face_id]
    face_border_ids = get_face_borders(face_id, topology)
    
    if len(face_border_ids) < 4:
        # Need at least 4 borders to split meaningfully
        return False, None, None
    
    # Step 1: Find the longest border (BORDER-LEVEL operation)
    longest_border_id = find_longest_border(face_id, topology)
    if longest_border_id is None:
        return False, None, None
    
    # Step 2: Find the opposite border (BORDER-LEVEL operation)
    opposite_border_id = find_opposite_border(face_id, longest_border_id, topology)
    if opposite_border_id is None:
        return False, None, None
    
    # Step 3: Split both borders at their midpoints (BORDER-LEVEL operation)
    success1, border1a_id, border1b_id, midpoint1_id = split_border(longest_border_id, topology)
    if not success1:
        return False, None, None
    
    success2, border2a_id, border2b_id, midpoint2_id = split_border(opposite_border_id, topology)
    if not success2:
        # Rollback first split: merge the two borders back
        # This is simplified - in a production system we'd want proper transaction semantics
        # For now, we leave the partially split state as it doesn't corrupt face structure
        # The first border is just now two borders that can still be used
        return False, None, None
    
    # Step 4: Create names for new faces
    face1_id = f"{face_id}_a"
    face2_id = f"{face_id}_b"
    
    # Step 5: Create a new border connecting the midpoints
    split_border_type = "land" if face.get("type") == "land" else "sea"
    split_border_id = create_border_between_vertices(
        midpoint1_id, midpoint2_id, 
        face1_id, face2_id,
        split_border_type, topology
    )
    if split_border_id is None:
        return False, None, None
    
    # Step 6: Determine which borders belong to which new face
    # We need to partition the face's borders (now with the split ones)
    # Use vertex connectivity to determine sides
    
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    # Get the original border endpoints to understand the geometry
    longest_border = borders.get(longest_border_id)
    if longest_border is None:
        # The border was split, get info from the split pieces
        longest_start = borders[border1a_id].get("start_vertex")
        longest_end = borders[border1b_id].get("end_vertex")
    else:
        longest_start = longest_border.get("start_vertex")
        longest_end = longest_border.get("end_vertex")
    
    # Collect all borders that were part of this face
    # Replace the original split borders with their halves
    remaining_border_ids = []
    for bid in face_border_ids:
        if bid == longest_border_id:
            remaining_border_ids.extend([border1a_id, border1b_id])
        elif bid == opposite_border_id:
            remaining_border_ids.extend([border2a_id, border2b_id])
        else:
            remaining_border_ids.append(bid)
    
    # Use the split direction to partition borders
    midpoint1_coords = vertex_coords.get(midpoint1_id, [0, 0])
    midpoint2_coords = vertex_coords.get(midpoint2_id, [0, 0])
    
    split_vec = [midpoint2_coords[0] - midpoint1_coords[0], 
                 midpoint2_coords[1] - midpoint1_coords[1]]
    
    # Get vertex for border1a (start of original longest border) - this goes to face1
    border1a_start = borders[border1a_id].get("start_vertex")
    v1_coords = vertex_coords.get(border1a_start, [0, 0])
    
    # Vector from midpoint1 to this vertex
    v1_to_mid = [v1_coords[0] - midpoint1_coords[0], v1_coords[1] - midpoint1_coords[1]]
    # Cross product to determine side
    v1_cross = split_vec[0] * v1_to_mid[1] - split_vec[1] * v1_to_mid[0]
    v1_side_positive = v1_cross > 0
    
    # Partition borders based on which side their vertices are on
    face1_borders = [split_border_id]  # Split border is shared by both
    face2_borders = [split_border_id]
    
    # border1a connects to the "positive" side vertex
    face1_borders.append(border1a_id)
    face2_borders.append(border1b_id)
    
    # Determine which side of split the opposite border halves are on
    border2a_start = borders[border2a_id].get("start_vertex")
    ov1_coords = vertex_coords.get(border2a_start, [0, 0])
    ov1_to_mid = [ov1_coords[0] - midpoint1_coords[0], ov1_coords[1] - midpoint1_coords[1]]
    ov1_cross = split_vec[0] * ov1_to_mid[1] - split_vec[1] * ov1_to_mid[0]
    
    if (ov1_cross > 0) == v1_side_positive:
        face1_borders.append(border2a_id)
        face2_borders.append(border2b_id)
    else:
        face2_borders.append(border2a_id)
        face1_borders.append(border2b_id)
    
    # Assign remaining borders to faces based on their vertex positions
    assigned_borders = {border1a_id, border1b_id, border2a_id, border2b_id, split_border_id}
    
    for border_id in remaining_border_ids:
        if border_id in assigned_borders:
            continue
        
        if border_id not in borders:
            continue
        
        border = borders[border_id]
        b_start = border.get("start_vertex")
        b_end = border.get("end_vertex")
        
        # Check which side this border is on
        # Get coordinates, falling back to the other endpoint if one is missing
        b_coords = vertex_coords.get(b_start) or vertex_coords.get(b_end)
        if b_coords is None:
            # Skip borders with no valid vertex coordinates - assign to face1 as fallback
            face1_borders.append(border_id)
            continue
        
        b_to_mid = [b_coords[0] - midpoint1_coords[0], b_coords[1] - midpoint1_coords[1]]
        b_cross = split_vec[0] * b_to_mid[1] - split_vec[1] * b_to_mid[0]
        
        if (b_cross > 0) == v1_side_positive:
            face1_borders.append(border_id)
        else:
            face2_borders.append(border_id)
    
    # Step 7: Create the two new faces
    face1 = {
        "type": face.get("type"),
        "borders": face1_borders,
        "center": face.get("center", [0.5, 0.5])
    }
    
    face2 = {
        "type": face.get("type"),
        "borders": face2_borders,
        "center": face.get("center", [0.5, 0.5])
    }
    
    # Step 8: Check coastal property
    edges = topology.get("edges", {})
    for border_id in face1_borders:
        if border_id in borders:
            for edge_id in borders[border_id].get("edges", []):
                if edge_id in edges and edges[edge_id].get("type") == "coast":
                    face1["coastal"] = True
                    break
    
    for border_id in face2_borders:
        if border_id in borders:
            for edge_id in borders[border_id].get("edges", []):
                if edge_id in edges and edges[edge_id].get("type") == "coast":
                    face2["coastal"] = True
                    break
    
    # Step 9: Update all border face references
    for border_id in face1_borders:
        update_border_face_references(border_id, face_id, face1_id, topology)
    
    for border_id in face2_borders:
        update_border_face_references(border_id, face_id, face2_id, topology)
    
    # Step 10: Update neighboring faces that reference the old split borders
    for fid, fdata in faces.items():
        if fid == face_id:
            continue
        
        new_border_list = []
        changed = False
        
        for bid in fdata.get("borders", []):
            if bid == longest_border_id:
                # Replace with both split parts
                new_border_list.append(border1a_id)
                new_border_list.append(border1b_id)
                changed = True
            elif bid == opposite_border_id:
                new_border_list.append(border2a_id)
                new_border_list.append(border2b_id)
                changed = True
            else:
                new_border_list.append(bid)
        
        if changed:
            fdata["borders"] = new_border_list
    
    # Step 11: Add new faces and remove old face
    faces[face1_id] = face1
    faces[face2_id] = face2
    del faces[face_id]
    
    return True, face1_id, face2_id


def find_smallest_faces(topology: dict, face_type: str, count: int = 5) -> List[Tuple[str, float]]:
    """
    Find the smallest faces of a given type.
    
    Args:
        topology: Dictionary with topology data
        face_type: Type of face to find ("land", "sea", etc.)
        count: Number of faces to return
        
    Returns:
        List of (face_id, size) tuples, sorted by size (smallest first)
    """
    faces = topology.get("faces", {})
    face_sizes = []
    
    for face_id, face_data in faces.items():
        if face_data.get("type") == face_type:
            size = calculate_face_size(face_id, topology)
            face_sizes.append((face_id, size))
    
    # Sort by size (smallest first)
    face_sizes.sort(key=lambda x: x[1])
    
    return face_sizes[:count]


def find_largest_faces(topology: dict, face_type: str, count: int = 5) -> List[Tuple[str, float]]:
    """
    Find the largest faces of a given type.
    
    Args:
        topology: Dictionary with topology data
        face_type: Type of face to find ("land", "sea", etc.)
        count: Number of faces to return
        
    Returns:
        List of (face_id, size) tuples, sorted by size (largest first)
    """
    faces = topology.get("faces", {})
    face_sizes = []
    
    for face_id, face_data in faces.items():
        if face_data.get("type") == face_type:
            size = calculate_face_size(face_id, topology)
            face_sizes.append((face_id, size))
    
    # Sort by size (largest first)
    face_sizes.sort(key=lambda x: x[1], reverse=True)
    
    return face_sizes[:count]


def find_smallest_neighbor(face_id: str, topology: dict) -> Optional[Tuple[str, float]]:
    """
    Find the smallest neighbor of a face (same type only).
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data
        
    Returns:
        Tuple of (neighbor_face_id, size) or None if no neighbors found
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    
    if face_id not in faces:
        return None
    
    face = faces[face_id]
    face_type = face.get("type")
    
    # Get adjacency information
    adjacency = get_adjacency_from_topology(edges)
    neighbors = adjacency.get(face_id, [])
    
    # Find neighbors of the same type
    same_type_neighbors = []
    for neighbor_id in neighbors:
        if neighbor_id in faces and faces[neighbor_id].get("type") == face_type:
            size = calculate_face_size(neighbor_id, topology)
            same_type_neighbors.append((neighbor_id, size))
    
    if not same_type_neighbors:
        return None
    
    # Return the smallest neighbor
    same_type_neighbors.sort(key=lambda x: x[1])
    return same_type_neighbors[0]
