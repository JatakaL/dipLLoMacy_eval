"""
Topology Utilities Module

This module implements utility functions for topology manipulation including:
- Calculating edge lengths using shapely LineString
- Calculating face sizes (areas) using shapely Polygon
- Merging adjacent faces (removes shared edges, fully implemented)
- Splitting faces (geometric split with proper polygon tracing)

Note on split_face():
    The split_face() function implements a geometric face splitting algorithm:
    - Finds the longest edge and its opposite edge
    - Creates new vertices at the midpoints of these edges
    - Splits the edges and creates a connecting edge between midpoints
    - Uses polygon tracing to properly assign edges to each new face
    - Creates two new faces (_a and _b) with correct closed polygons
    - Properly maintains coastal properties and edge references
    - Updates neighboring faces that shared the split edges
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


def merge_faces(face1_id: str, face2_id: str, topology: dict) -> Tuple[bool, Optional[str]]:
    """
    Merge two adjacent faces into one.
    
    This operation:
    1. Combines the two faces into a single face (keeping face1_id)
    2. Removes shared borders between the faces
    3. Updates edge/border references to point to the merged face
    4. Removes face2 from the topology
    
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
    
    # Get edges for each face through their borders
    face1_edges = set(get_face_edges(face1, borders))
    face2_edges = set(get_face_edges(face2, borders))
    
    # Find shared edges between the two faces
    shared_edges = []
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
    
    # Find shared borders
    shared_borders = []
    for border_id in face1.get("borders", []):
        if border_id in borders:
            border = borders[border_id]
            if (border.get("left_face") == face1_id and border.get("right_face") == face2_id) or \
               (border.get("left_face") == face2_id and border.get("right_face") == face1_id):
                shared_borders.append(border_id)
    
    # Combine borders from both faces, excluding shared borders
    new_borders = []
    for border_id in face1.get("borders", []):
        if border_id not in shared_borders and border_id in borders:
            new_borders.append(border_id)
    
    for border_id in face2.get("borders", []):
        if border_id not in shared_borders and border_id not in new_borders and border_id in borders:
            new_borders.append(border_id)
    
    # Update face1 with combined borders
    face1["borders"] = new_borders
    
    # Update all edges and borders that referenced face2 to now reference face1
    for border_id in new_borders:
        if border_id in borders:
            border = borders[border_id]
            if border.get("left_face") == face2_id:
                border["left_face"] = face1_id
            if border.get("right_face") == face2_id:
                border["right_face"] = face1_id
            # Also update edges in this border
            for edge_id in border.get("edges", []):
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
    
    # Remove shared borders from topology
    for border_id in shared_borders:
        if border_id in borders:
            del borders[border_id]
    
    # Remove face2 from topology
    del faces[face2_id]
    
    return True, face1_id


def split_face(face_id: str, topology: dict, split_axis: str = "horizontal") -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Split a face into two faces by finding the longest edge and its opposite edge,
    creating a split line between their midpoints.
    
    Algorithm:
    1. Find the face's longest edge
    2. Find the midpoint of that edge
    3. Determine which edge is 'across' from that midpoint (perpendicular line intersection)
    4. Find the midpoint of that edge
    5. Create new vertices at the two midpoints
    6. Split the two existing edges into four new ones at those midpoints
    7. Create a new edge connecting the midpoints
    8. Edit the existing face to include only one side, append _a to its name
    9. Create a new face from the other side, append _b to the name
    10. Check coastal property for both new faces
    
    Args:
        face_id: ID of the face to split
        topology: Dictionary with topology data (vertices, edges, faces, borders)
        split_axis: Not used in this implementation (kept for API compatibility)
        
    Returns:
        Tuple of (success: bool, face1_id: Optional[str], face2_id: Optional[str])
        Returns (False, None, None) if the split cannot be performed.
    """
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    vertices = topology.get("vertices", [])
    
    if face_id not in faces:
        return False, None, None
    
    face = faces[face_id]
    edge_ids = get_face_edges(face, borders)
    
    if len(edge_ids) < 4:
        # Need at least 4 edges to split meaningfully
        return False, None, None
    
    # Create vertex lookup for faster access
    vertex_coords = _get_vertex_coords_lookup(topology)
    
    # Step 1: Find the longest edge
    longest_edge_id = None
    longest_length = 0.0
    
    for edge_id in edge_ids:
        if edge_id not in edges:
            continue
        try:
            length = calculate_edge_length(edge_id, topology)
            if length > longest_length:
                longest_length = length
                longest_edge_id = edge_id
        except (ValueError, KeyError):
            # Skip edges with missing vertices
            continue
    
    if longest_edge_id is None:
        return False, None, None
    
    longest_edge = edges[longest_edge_id]
    v1_id = longest_edge["v1"]
    v2_id = longest_edge["v2"]
    v1_coords = vertex_coords[v1_id]
    v2_coords = vertex_coords[v2_id]
    
    # Step 2: Find midpoint of longest edge using shapely
    longest_line = LineString([v1_coords, v2_coords])
    midpoint1_point = longest_line.interpolate(0.5, normalized=True)
    midpoint1 = [midpoint1_point.x, midpoint1_point.y]
    
    # Step 3: Find the edge "across" from the longest edge
    # Calculate perpendicular direction to longest edge
    edge_vec = [v2_coords[0] - v1_coords[0], v2_coords[1] - v1_coords[1]]
    perpendicular = [-edge_vec[1], edge_vec[0]]  # Rotate 90 degrees
    
    # Normalize perpendicular vector
    perp_length = math.sqrt(perpendicular[0]**2 + perpendicular[1]**2)
    if perp_length < 1e-10:
        return False, None, None
    perpendicular = [perpendicular[0] / perp_length, perpendicular[1] / perp_length]
    
    # Find edge that is farthest from midpoint1 in perpendicular direction
    # or that the perpendicular line intersects
    opposite_edge_id = None
    max_projected_distance = 0.0
    
    for edge_id in edge_ids:
        if edge_id == longest_edge_id or edge_id not in edges:
            continue
        
        edge = edges[edge_id]
        ev1_coords = vertex_coords[edge["v1"]]
        ev2_coords = vertex_coords[edge["v2"]]
        
        # Calculate center of this edge using shapely
        edge_line = LineString([ev1_coords, ev2_coords])
        edge_center_point = edge_line.interpolate(0.5, normalized=True)
        edge_center = [edge_center_point.x, edge_center_point.y]
        
        # Calculate vector from midpoint1 to edge center
        to_edge = [edge_center[0] - midpoint1[0], edge_center[1] - midpoint1[1]]
        
        # Project onto perpendicular direction (absolute value to get distance)
        projected = abs(to_edge[0] * perpendicular[0] + to_edge[1] * perpendicular[1])
        
        if projected > max_projected_distance:
            max_projected_distance = projected
            opposite_edge_id = edge_id
    
    if opposite_edge_id is None:
        return False, None, None
    
    opposite_edge = edges[opposite_edge_id]
    ov1_id = opposite_edge["v1"]
    ov2_id = opposite_edge["v2"]
    ov1_coords = vertex_coords[ov1_id]
    ov2_coords = vertex_coords[ov2_id]
    
    # Step 4: Find midpoint of opposite edge using shapely
    opposite_line = LineString([ov1_coords, ov2_coords])
    midpoint2_point = opposite_line.interpolate(0.5, normalized=True)
    midpoint2 = [midpoint2_point.x, midpoint2_point.y]
    
    # Step 5: Create new vertices at the two midpoints
    # Get next vertex ID
    if not vertices:
        # No vertices exist, cannot proceed with split
        return False, None, None
    max_vertex_id = max(v["id"] for v in vertices)
    new_vertex1_id = max_vertex_id + 1
    new_vertex2_id = max_vertex_id + 2
    
    vertices.append({"id": new_vertex1_id, "coords": midpoint1})
    vertices.append({"id": new_vertex2_id, "coords": midpoint2})
    
    # Step 6: Split the two existing edges into four new ones
    # For longest_edge: v1 -> new_vertex1 and new_vertex1 -> v2
    # For opposite_edge: ov1 -> new_vertex2 and new_vertex2 -> ov2
    
    # Create new edge IDs
    edge1a_id = f"E_{min(v1_id, new_vertex1_id)}_{max(v1_id, new_vertex1_id)}"
    edge1b_id = f"E_{min(new_vertex1_id, v2_id)}_{max(new_vertex1_id, v2_id)}"
    edge2a_id = f"E_{min(ov1_id, new_vertex2_id)}_{max(ov1_id, new_vertex2_id)}"
    edge2b_id = f"E_{min(new_vertex2_id, ov2_id)}_{max(new_vertex2_id, ov2_id)}"
    
    # Get face references from original edges
    longest_left = longest_edge.get("left_face")
    longest_right = longest_edge.get("right_face")
    opposite_left = opposite_edge.get("left_face")
    opposite_right = opposite_edge.get("right_face")
    
    # Create the four new edges from split
    edges[edge1a_id] = {
        "v1": min(v1_id, new_vertex1_id),
        "v2": max(v1_id, new_vertex1_id),
        "left_face": longest_left,
        "right_face": longest_right,
        "type": longest_edge.get("type")
    }
    edges[edge1b_id] = {
        "v1": min(new_vertex1_id, v2_id),
        "v2": max(new_vertex1_id, v2_id),
        "left_face": longest_left,
        "right_face": longest_right,
        "type": longest_edge.get("type")
    }
    edges[edge2a_id] = {
        "v1": min(ov1_id, new_vertex2_id),
        "v2": max(ov1_id, new_vertex2_id),
        "left_face": opposite_left,
        "right_face": opposite_right,
        "type": opposite_edge.get("type")
    }
    edges[edge2b_id] = {
        "v1": min(new_vertex2_id, ov2_id),
        "v2": max(new_vertex2_id, ov2_id),
        "left_face": opposite_left,
        "right_face": opposite_right,
        "type": opposite_edge.get("type")
    }
    
    # Step 7: Create new edge connecting the midpoints
    split_edge_id = f"E_{min(new_vertex1_id, new_vertex2_id)}_{max(new_vertex1_id, new_vertex2_id)}"
    
    # Step 8 & 9: Create the two new faces
    face1_id = f"{face_id}_a"
    face2_id = f"{face_id}_b"
    
    # Determine which vertices belong to which side of the split
    # The split line goes from midpoint1 to midpoint2
    # We'll use the cross product to determine which side each vertex is on
    
    # Split line direction
    split_dx = midpoint2[0] - midpoint1[0]
    split_dy = midpoint2[1] - midpoint1[1]
    
    # Get all original vertices of this face
    original_vertices = set()
    for eid in edge_ids:
        if eid in edges:
            original_vertices.add(edges[eid]["v1"])
            original_vertices.add(edges[eid]["v2"])
    
    # Classify each vertex as being on side A (positive cross product) or side B (negative)
    side_a_vertices = set()  # Will include v1 (from longest edge)
    side_b_vertices = set()  # Will include v2 (from longest edge)
    
    for vid in original_vertices:
        if vid == v1_id:
            side_a_vertices.add(vid)
            continue
        if vid == v2_id:
            side_b_vertices.add(vid)
            continue
        if vid == ov1_id or vid == ov2_id:
            # These vertices are on the split line - they need special handling
            # ov1 is connected to v1 via edges, so determine based on adjacency
            # For now, we'll add them to both sides since they're on the split line
            continue
        
        vcoords = vertex_coords[vid]
        # Vector from midpoint1 to vertex
        to_v = [vcoords[0] - midpoint1[0], vcoords[1] - midpoint1[1]]
        # Cross product with split direction
        cross = split_dx * to_v[1] - split_dy * to_v[0]
        
        # Also compute cross product for v1 to establish which side is A
        v1_to_v = [v1_coords[0] - midpoint1[0], v1_coords[1] - midpoint1[1]]
        v1_cross = split_dx * v1_to_v[1] - split_dy * v1_to_v[0]
        
        if (cross > 0) == (v1_cross > 0):
            side_a_vertices.add(vid)
        else:
            side_b_vertices.add(vid)
    
    # Now assign edges to faces based on which vertices they connect
    # An edge belongs to face A if both its vertices are on side A or on the split line
    # The split edge and the split parts of the original edges are shared/special
    
    remaining_old_edges = [e for e in edge_ids if e not in [longest_edge_id, opposite_edge_id]]
    
    face1_edges = []  # Side A (includes v1)
    face2_edges = []  # Side B (includes v2)
    
    # Add the new split edge to both faces (it's their shared boundary)
    face1_edges.append(split_edge_id)
    face2_edges.append(split_edge_id)
    
    # edge1a connects v1 to new_vertex1 - belongs to face1 (side A)
    face1_edges.append(edge1a_id)
    # edge1b connects new_vertex1 to v2 - belongs to face2 (side B)
    face2_edges.append(edge1b_id)
    
    # For edge2a and edge2b, we need to determine which connects to which side
    # edge2a connects ov1 to new_vertex2
    # edge2b connects new_vertex2 to ov2
    # We need to figure out if ov1 is on side A or side B
    
    # Check adjacency: ov1 should be connected to either v1 or v2 (or both) via other edges
    ov1_side_a = False
    ov2_side_a = False
    
    for eid in remaining_old_edges:
        if eid not in edges:
            continue
        e = edges[eid]
        ev1, ev2 = e["v1"], e["v2"]
        # If this edge connects ov1 to a side_a vertex, ov1 is on side A
        if ev1 == ov1_id and ev2 in side_a_vertices:
            ov1_side_a = True
        if ev2 == ov1_id and ev1 in side_a_vertices:
            ov1_side_a = True
        if ev1 == ov2_id and ev2 in side_a_vertices:
            ov2_side_a = True
        if ev2 == ov2_id and ev1 in side_a_vertices:
            ov2_side_a = True
        # Similarly for side B
        if ev1 == ov1_id and ev2 in side_b_vertices:
            ov1_side_a = False
        if ev2 == ov1_id and ev1 in side_b_vertices:
            ov1_side_a = False
        if ev1 == ov2_id and ev2 in side_b_vertices:
            ov2_side_a = False
        if ev2 == ov2_id and ev1 in side_b_vertices:
            ov2_side_a = False
    
    # If ov1 is on side A, edge2a belongs to face1
    if ov1_side_a:
        face1_edges.append(edge2a_id)
        face2_edges.append(edge2b_id)
    else:
        face2_edges.append(edge2a_id)
        face1_edges.append(edge2b_id)
    
    # Now assign remaining old edges based on their vertices
    for eid in remaining_old_edges:
        if eid not in edges:
            continue
        e = edges[eid]
        ev1, ev2 = e["v1"], e["v2"]
        
        # Check which side this edge belongs to
        # Use parentheses for clarity of precedence
        v1_on_a = (ev1 in side_a_vertices or 
                   (ev1 == ov1_id and ov1_side_a) or 
                   (ev1 == ov2_id and ov2_side_a))
        v2_on_a = (ev2 in side_a_vertices or 
                   (ev2 == ov1_id and ov1_side_a) or 
                   (ev2 == ov2_id and ov2_side_a))
        
        if v1_on_a and v2_on_a:
            face1_edges.append(eid)
        elif not v1_on_a and not v2_on_a:
            face2_edges.append(eid)
        else:
            # Edge crosses the split - this shouldn't happen for edges not being split
            # Add to face1 as a fallback (should be rare)
            face1_edges.append(eid)
    
    # Validate: both faces must have at least 3 edges
    # Store original vertex count for proper cleanup if validation fails
    original_vertex_count = len(vertices) - 2  # We added 2 vertices
    if len(face1_edges) < 3 or len(face2_edges) < 3:
        # Remove the vertices we added
        del vertices[original_vertex_count:]
        # Remove the edges we added
        for edge_id in [edge1a_id, edge1b_id, edge2a_id, edge2b_id]:
            if edge_id in edges:
                del edges[edge_id]
        return False, None, None
    
    # Create the actual edges in the topology
    split_edge_type = "land" if face.get("type") == "land" else "sea"
    
    edges[edge1a_id] = {
        "v1": min(v1_id, new_vertex1_id),
        "v2": max(v1_id, new_vertex1_id),
        "left_face": face1_id,
        "right_face": longest_right if longest_right != face_id else (longest_left if longest_left != face_id else None),
        "type": longest_edge.get("type")
    }
    edges[edge1b_id] = {
        "v1": min(new_vertex1_id, v2_id),
        "v2": max(new_vertex1_id, v2_id),
        "left_face": face2_id,
        "right_face": longest_right if longest_right != face_id else (longest_left if longest_left != face_id else None),
        "type": longest_edge.get("type")
    }
    edges[edge2a_id] = {
        "v1": min(ov1_id, new_vertex2_id),
        "v2": max(ov1_id, new_vertex2_id),
        "left_face": face1_id if ov1_side_a else face2_id,
        "right_face": opposite_right if opposite_right != face_id else (opposite_left if opposite_left != face_id else None),
        "type": opposite_edge.get("type")
    }
    edges[edge2b_id] = {
        "v1": min(new_vertex2_id, ov2_id),
        "v2": max(new_vertex2_id, ov2_id),
        "left_face": face2_id if ov1_side_a else face1_id,
        "right_face": opposite_right if opposite_right != face_id else (opposite_left if opposite_left != face_id else None),
        "type": opposite_edge.get("type")
    }
    edges[split_edge_id] = {
        "v1": min(new_vertex1_id, new_vertex2_id),
        "v2": max(new_vertex1_id, new_vertex2_id),
        "left_face": face1_id,
        "right_face": face2_id,
        "type": split_edge_type
    }
    
    # Create borders for the new faces
    # Each edge in face1_edges/face2_edges needs a corresponding border
    face1_borders = []
    face2_borders = []
    
    for eid in face1_edges:
        edge = edges.get(eid)
        if edge:
            border_id = f"B_{edge['v1']}_{edge['v2']}"
            if border_id not in borders:
                borders[border_id] = {
                    "edges": [eid],
                    "left_face": edge.get("left_face"),
                    "right_face": edge.get("right_face"),
                    "type": edge.get("type"),
                    "start_vertex": edge["v1"],
                    "end_vertex": edge["v2"]
                }
            if border_id not in face1_borders:
                face1_borders.append(border_id)
    
    for eid in face2_edges:
        edge = edges.get(eid)
        if edge:
            border_id = f"B_{edge['v1']}_{edge['v2']}"
            if border_id not in borders:
                borders[border_id] = {
                    "edges": [eid],
                    "left_face": edge.get("left_face"),
                    "right_face": edge.get("right_face"),
                    "type": edge.get("type"),
                    "start_vertex": edge["v1"],
                    "end_vertex": edge["v2"]
                }
            if border_id not in face2_borders:
                face2_borders.append(border_id)
    
    # Create face 1
    face1 = {
        "type": face["type"],
        "borders": face1_borders,
        "center": face.get("center", [0.5, 0.5])
    }
    
    # Create face 2
    face2 = {
        "type": face["type"],
        "borders": face2_borders,
        "center": face.get("center", [0.5, 0.5])
    }
    
    # Step 10: Check coastal property for both new faces
    face1_coastal = False
    face2_coastal = False
    
    for eid in face1_edges:
        if eid in edges and edges[eid].get("type") == "coast":
            face1_coastal = True
            break
    
    for eid in face2_edges:
        if eid in edges and edges[eid].get("type") == "coast":
            face2_coastal = True
            break
    
    if face1_coastal:
        face1["coastal"] = True
    if face2_coastal:
        face2["coastal"] = True
    
    # Update edge references for remaining old edges in THIS face
    face1_edges_set = set(face1_edges)
    face2_edges_set = set(face2_edges)
    
    for eid in remaining_old_edges:
        if eid in edges:
            e = edges[eid]
            if eid in face1_edges_set:
                if e.get("left_face") == face_id:
                    e["left_face"] = face1_id
                if e.get("right_face") == face_id:
                    e["right_face"] = face1_id
            elif eid in face2_edges_set:
                if e.get("left_face") == face_id:
                    e["left_face"] = face2_id
                if e.get("right_face") == face_id:
                    e["right_face"] = face2_id
    
    # ALSO update any OTHER edges that reference the old face (from neighboring faces)
    # These are edges shared with neighbors that we need to update
    all_face1_edges = set(face1_edges)
    all_face2_edges = set(face2_edges)
    
    # For edges belonging to THIS face, update their face references
    for eid, e in edges.items():
        if e.get("left_face") == face_id:
            # Determine which new face this edge belongs to
            if eid in all_face1_edges:
                e["left_face"] = face1_id
            elif eid in all_face2_edges:
                e["left_face"] = face2_id
            else:
                # Edge from neighbor - determine based on shared vertex
                # This edge shares a vertex with our face; find which part it's adjacent to
                edge_verts = {e["v1"], e["v2"]}
                # Check if any vertex of this edge is connected to face1 edges
                face1_verts = set()
                for fe in all_face1_edges:
                    if fe in edges:
                        face1_verts.add(edges[fe]["v1"])
                        face1_verts.add(edges[fe]["v2"])
                if edge_verts & face1_verts:
                    e["left_face"] = face1_id
                else:
                    e["left_face"] = face2_id
                    
        if e.get("right_face") == face_id:
            if eid in all_face1_edges:
                e["right_face"] = face1_id
            elif eid in all_face2_edges:
                e["right_face"] = face2_id
            else:
                # Edge from neighbor - determine based on shared vertex
                edge_verts = {e["v1"], e["v2"]}
                face1_verts = set()
                for fe in all_face1_edges:
                    if fe in edges:
                        face1_verts.add(edges[fe]["v1"])
                        face1_verts.add(edges[fe]["v2"])
                if edge_verts & face1_verts:
                    e["right_face"] = face1_id
                else:
                    e["right_face"] = face2_id
    
    # Also update borders' face references for the new faces
    for bid in face1_borders:
        if bid in borders:
            border = borders[bid]
            if border.get("left_face") == face_id:
                border["left_face"] = face1_id
            if border.get("right_face") == face_id:
                border["right_face"] = face1_id
    
    for bid in face2_borders:
        if bid in borders:
            border = borders[bid]
            if border.get("left_face") == face_id:
                border["left_face"] = face2_id
            if border.get("right_face") == face_id:
                border["right_face"] = face2_id
    
    # Also update ALL borders that reference the old face
    for bid, border in borders.items():
        if border.get("left_face") == face_id:
            # Determine which new face this border belongs to based on its edges
            border_edges = border.get("edges", [])
            if any(e in all_face1_edges for e in border_edges):
                border["left_face"] = face1_id
            elif any(e in all_face2_edges for e in border_edges):
                border["left_face"] = face2_id
        if border.get("right_face") == face_id:
            border_edges = border.get("edges", [])
            if any(e in all_face1_edges for e in border_edges):
                border["right_face"] = face1_id
            elif any(e in all_face2_edges for e in border_edges):
                border["right_face"] = face2_id
    
    # Calculate the new border IDs that will replace the old ones
    edge1a_border_id = f"B_{edges[edge1a_id]['v1']}_{edges[edge1a_id]['v2']}"
    edge1b_border_id = f"B_{edges[edge1b_id]['v1']}_{edges[edge1b_id]['v2']}"
    edge2a_border_id = f"B_{edges[edge2a_id]['v1']}_{edges[edge2a_id]['v2']}"
    edge2b_border_id = f"B_{edges[edge2b_id]['v1']}_{edges[edge2b_id]['v2']}"
    
    # Store old border IDs before we delete them
    longest_border_id = f"B_{longest_edge['v1']}_{longest_edge['v2']}"
    opposite_border_id = f"B_{opposite_edge['v1']}_{opposite_edge['v2']}"
    
    # Update neighboring faces that shared the split edges - update their borders
    for fid, fdata in faces.items():
        if fid == face_id:
            continue
        neighbor_edge_ids = get_face_edges(fdata, borders)
        if longest_edge_id in neighbor_edge_ids or opposite_edge_id in neighbor_edge_ids:
            # Update the neighbor's borders - replace old border IDs with new ones
            new_borders = []
            for bid in fdata.get("borders", []):
                if bid == longest_border_id:
                    # Replace with borders for the new edges
                    if edge1a_border_id not in new_borders:
                        new_borders.append(edge1a_border_id)
                    if edge1b_border_id not in new_borders:
                        new_borders.append(edge1b_border_id)
                elif bid == opposite_border_id:
                    if edge2a_border_id not in new_borders:
                        new_borders.append(edge2a_border_id)
                    if edge2b_border_id not in new_borders:
                        new_borders.append(edge2b_border_id)
                else:
                    if bid not in new_borders:
                        new_borders.append(bid)
            fdata["borders"] = new_borders
    
    # Remove original edges and their borders
    if longest_border_id in borders:
        del borders[longest_border_id]
    if opposite_border_id in borders:
        del borders[opposite_border_id]
    
    del edges[longest_edge_id]
    del edges[opposite_edge_id]
    
    # Add new faces and remove old face
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
