"""
Topology Utilities Module

This module implements utility functions for topology manipulation including:
- Calculating edge lengths using Euclidean distance
- Calculating face sizes (areas) using the shoelace formula
- Merging adjacent faces (removes shared edges, fully implemented)
- Splitting faces (simplified implementation for demonstration/tracking)

Note on split_face():
    The split_face() function is a simplified implementation intended for
    demonstration and statistical tracking purposes. It divides a face's edges
    between two faces but does NOT create proper geometric splits with new
    vertices and connecting edges. For production use in complex scenarios,
    a full geometric splitting algorithm would be needed.
"""

import math
from typing import Dict, List, Tuple, Optional
from topology import get_adjacency_from_topology


def calculate_edge_length(edge_id: str, topology: dict) -> float:
    """
    Calculate the Euclidean length of an edge.
    
    Args:
        edge_id: ID of the edge (e.g., "E_0_1")
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Length of the edge in map units
    """
    edges = topology.get("edges", {})
    vertices = topology.get("vertices", [])
    
    if edge_id not in edges:
        raise ValueError(f"Edge {edge_id} not found in topology")
    
    edge = edges[edge_id]
    v1_id = edge["v1"]
    v2_id = edge["v2"]
    
    # Find vertex coordinates
    v1_coords = None
    v2_coords = None
    for vertex in vertices:
        if vertex["id"] == v1_id:
            v1_coords = vertex["coords"]
        if vertex["id"] == v2_id:
            v2_coords = vertex["coords"]
    
    if v1_coords is None or v2_coords is None:
        raise ValueError(f"Vertices for edge {edge_id} not found")
    
    # Calculate Euclidean distance
    dx = v2_coords[0] - v1_coords[0]
    dy = v2_coords[1] - v1_coords[1]
    length = math.sqrt(dx * dx + dy * dy)
    
    return length


def calculate_face_size(face_id: str, topology: dict) -> float:
    """
    Calculate the area of a face using the shoelace formula.
    
    Args:
        face_id: ID of the face
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Area of the face in square map units
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    vertices = topology.get("vertices", [])
    
    if face_id not in faces:
        raise ValueError(f"Face {face_id} not found in topology")
    
    face = faces[face_id]
    edge_ids = face.get("edges", [])
    
    if not edge_ids:
        return 0.0
    
    # Create vertex lookup for faster access
    vertex_coords = {v["id"]: v["coords"] for v in vertices}
    
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
        return 0.0
    
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
    
    # Calculate area using shoelace formula
    if len(polygon_vertices) < 3:
        return 0.0
    
    area = 0.0
    n = len(polygon_vertices)
    for i in range(n):
        j = (i + 1) % n
        area += polygon_vertices[i][0] * polygon_vertices[j][1]
        area -= polygon_vertices[j][0] * polygon_vertices[i][1]
    
    return abs(area) / 2.0


def merge_faces(face1_id: str, face2_id: str, topology: dict) -> Tuple[bool, Optional[str]]:
    """
    Merge two adjacent faces into one.
    
    This operation:
    1. Combines the two faces into a single face (keeping face1_id)
    2. Removes shared edges between the faces
    3. Updates edge references to point to the merged face
    4. Removes face2 from the topology
    
    Args:
        face1_id: ID of the first face (will be kept)
        face2_id: ID of the second face (will be removed)
        topology: Dictionary with topology data (vertices, edges, faces)
        
    Returns:
        Tuple of (success: bool, merged_face_id: Optional[str])
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    
    if face1_id not in faces or face2_id not in faces:
        return False, None
    
    face1 = faces[face1_id]
    face2 = faces[face2_id]
    
    # Find shared edges between the two faces
    shared_edges = []
    face1_edges = set(face1.get("edges", []))
    face2_edges = set(face2.get("edges", []))
    
    for edge_id in face1_edges:
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        left_face = edge.get("left_face")
        right_face = edge.get("right_face")
        
        # Check if this edge is shared between face1 and face2
        if (left_face == face1_id and right_face == face2_id) or \
           (left_face == face2_id and right_face == face1_id):
            shared_edges.append(edge_id)
    
    if not shared_edges:
        # Faces are not adjacent, cannot merge
        return False, None
    
    # Combine edges from both faces, excluding shared edges
    new_edges = []
    for edge_id in face1_edges:
        if edge_id not in shared_edges:
            new_edges.append(edge_id)
    
    for edge_id in face2_edges:
        if edge_id not in shared_edges and edge_id not in new_edges:
            new_edges.append(edge_id)
    
    # Update face1 with combined edges
    face1["edges"] = new_edges
    
    # Update face1's properties (use face1's type, but could be customized)
    # Keep face1's center for now (could be recalculated as average of both)
    
    # Update all edges that referenced face2 to now reference face1
    for edge_id in new_edges:
        if edge_id in edges:
            edge = edges[edge_id]
            if edge.get("left_face") == face2_id:
                edge["left_face"] = face1_id
            if edge.get("right_face") == face2_id:
                edge["right_face"] = face1_id
    
    # Remove shared edges from topology
    for edge_id in shared_edges:
        if edge_id in edges:
            del edges[edge_id]
    
    # Remove face2 from topology
    del faces[face2_id]
    
    return True, face1_id


def split_face(face_id: str, topology: dict, split_axis: str = "horizontal") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Split a face into two faces along a specified axis.
    
    **IMPORTANT: This is a simplified implementation for demonstration purposes.**
    
    This implementation divides a face's edges into two groups and creates two new faces.
    It does NOT:
    - Create new vertices at split points
    - Create proper connecting edges between the split halves
    - Maintain valid Voronoi properties
    - Ensure geometric validity of the resulting faces
    
    **Limitations:**
    - The resulting faces share the original edges but are not properly connected
    - The topology may become invalid for certain operations
    - This should primarily be used for statistical tracking (e.g., territory size tracking)
    - For production use, a proper geometric splitting algorithm is needed
    
    **Use Cases:**
    - Demonstrating the concept of face splitting
    - Tracking territory modifications in map generation
    - Testing topology manipulation logic
    
    Args:
        face_id: ID of the face to split
        topology: Dictionary with topology data (vertices, edges, faces)
        split_axis: "horizontal" or "vertical" split direction (currently unused)
        
    Returns:
        Tuple of (success: bool, face1_id: Optional[str], face2_id: Optional[str])
        Returns (False, None, None) if the split cannot be performed.
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    vertices = topology.get("vertices", [])
    
    if face_id not in faces:
        return False, None, None
    
    face = faces[face_id]
    
    edge_ids = face.get("edges", [])
    if len(edge_ids) < 4:
        # Need at least 4 edges to split meaningfully
        return False, None, None
    
    # Simple approach: divide edges roughly in half to create two sub-faces
    # This creates a "virtual" split for statistical tracking purposes
    split_point = len(edge_ids) // 2
    
    # Create new face ID with a counter to handle multiple splits
    counter = 1
    new_face_id = f"{face_id}_split"
    while new_face_id in faces:
        counter += 1
        new_face_id = f"{face_id}_split{counter}"
    
    # Create new face with second half of edges
    new_face = {
        "type": face["type"],
        "edges": edge_ids[split_point:],
        "center": face.get("center", [0.5, 0.5])
    }
    
    # Copy face properties if present
    if "coastal" in face:
        new_face["coastal"] = face["coastal"]
    
    # Update original face to only use first half of edges
    faces[face_id]["edges"] = edge_ids[:split_point]
    
    # Add new face to topology
    faces[new_face_id] = new_face
    
    return True, face_id, new_face_id


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
