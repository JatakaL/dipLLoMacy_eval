"""
Shared utilities for fractal edge visualization.

This module provides common functions for drawing edges and
reconstructing face polygons from the topology.

Two Visualization Approaches:
1. Legacy (visual_path): Each edge stores a visual_path array with
   displaced coordinates for display purposes only.
   
2. New (subdivided topology): Edges are actually subdivided in the
   topology, creating new vertices and edges. The visual appearance
   comes from drawing the many small edges that form a border.

These utilities support both approaches for backward compatibility.
The draw_fractal_edges function will use visual_path if present,
otherwise it draws the actual edge vertices (which may be subdivided).
"""

import numpy as np


def _get_face_edges(face_data, borders):
    """
    Get the list of edge IDs for a face by looking up its borders.
    
    Args:
        face_data: Face dictionary with 'borders' list
        borders: Dictionary of border data with 'edges' list
        
    Returns:
        List of edge IDs forming the face perimeter
    """
    edge_ids = []
    for border_id in face_data.get('borders', []):
        if border_id in borders:
            border = borders[border_id]
            edge_ids.extend(border.get('edges', []))
    return edge_ids


# Default edge styling configurations
EDGE_COLORS = {
    'land': '#4A7C59',      # Dark green for land-land borders
    'sea': '#5B9BD5',       # Blue for sea-sea borders
    'coast': '#C55A11',     # Orange for coastlines
    'map-edge': '#2F2F2F'   # Dark gray for map boundaries
}

EDGE_WIDTHS = {
    'land': 1.0,
    'sea': 0.8,
    'coast': 1.8,
    'map-edge': 2.0
}

# Default tolerance for point comparison in coordinate space
DEFAULT_POINT_TOLERANCE = 1e-6


def _points_are_close(point1, point2, tolerance=DEFAULT_POINT_TOLERANCE):
    """Check if two points are within tolerance of each other.
    
    Args:
        point1: First point as [x, y]
        point2: Second point as [x, y]
        tolerance: Maximum distance for points to be considered close
        
    Returns:
        True if points are within tolerance, False otherwise
    """
    return (abs(point1[0] - point2[0]) < tolerance and 
            abs(point1[1] - point2[1]) < tolerance)


def draw_fractal_edges(ax, topology, edge_colors=None, edge_widths=None):
    """Draw edges from topology with type-based styling.
    
    This function supports two modes:
    1. If edges have visual_path data, it draws the path (legacy mode)
    2. Otherwise, it draws straight lines between edge vertices
       (works with subdivided topology where many small edges create fractal appearance)
    
    Args:
        ax: Matplotlib axis
        topology: Topology dictionary with vertices and edges
        edge_colors: Optional dict mapping edge types to colors (uses defaults if None)
        edge_widths: Optional dict mapping edge types to line widths (uses defaults if None)
    """
    if not topology:
        return
    
    if edge_colors is None:
        edge_colors = EDGE_COLORS
    if edge_widths is None:
        edge_widths = EDGE_WIDTHS
    
    vertices_list = topology.get('vertices', [])
    edges = topology.get('edges', {})
    
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in vertices_list}
    
    # Draw edges with type-based styling
    for edge_id, edge_data in edges.items():
        v1_id = edge_data.get('v1')
        v2_id = edge_data.get('v2')
        edge_type = edge_data.get('type', 'land')
        
        if v1_id not in vertex_coords or v2_id not in vertex_coords:
            continue
        
        v1_coords = vertex_coords[v1_id]
        v2_coords = vertex_coords[v2_id]
        
        # Get color and width based on edge type
        color = edge_colors.get(edge_type, '#000000')
        linewidth = edge_widths.get(edge_type, 1.0)
        
        # Check if visual_path is available (fractal subdivision)
        visual_path = edge_data.get('visual_path')
        if visual_path and len(visual_path) >= 2:
            # Draw the fractal edge using visual_path
            path_array = np.array(visual_path)
            ax.plot(path_array[:, 0], path_array[:, 1], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')
        else:
            # Draw simple straight line
            ax.plot([v1_coords[0], v2_coords[0]], 
                    [v1_coords[1], v2_coords[1]], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')


def get_fractal_face_polygon(topology, face_id):
    """Reconstruct a face polygon from its edges.
    
    This function works with both:
    1. Legacy mode: Uses visual_path arrays from edges
    2. Subdivided mode: Uses actual edge vertices (many small edges)
    
    Args:
        topology: Topology dictionary with vertices, edges, borders, and faces
        face_id: ID of the face to reconstruct
        
    Returns:
        List of [x, y] points forming the polygon, or None if not available
    """
    if not topology:
        return None
    
    faces = topology.get('faces', {})
    edges = topology.get('edges', {})
    borders = topology.get('borders', {})
    vertices_list = topology.get('vertices', [])
    
    if face_id not in faces:
        return None
    
    face = faces[face_id]
    edge_ids = _get_face_edges(face, borders)
    
    if not edge_ids:
        return None
    
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in vertices_list}
    
    # Build ordered polygon from edges using visual_path
    polygon_points = []
    
    # We need to trace the edges in order, connecting end-to-end
    remaining_edges = list(edge_ids)
    if not remaining_edges:
        return None
    
    # Start with the first edge
    first_edge_id = remaining_edges.pop(0)
    if first_edge_id not in edges:
        return None
    
    first_edge = edges[first_edge_id]
    visual_path = first_edge.get('visual_path')
    
    if visual_path and len(visual_path) >= 2:
        polygon_points.extend(visual_path[:-1])  # Don't include last point (will be first of next edge)
        current_end = visual_path[-1]
    else:
        v1_id, v2_id = first_edge.get('v1'), first_edge.get('v2')
        if v1_id in vertex_coords and v2_id in vertex_coords:
            polygon_points.append(vertex_coords[v1_id])
            current_end = vertex_coords[v2_id]
        else:
            return None
    
    # Continue with remaining edges
    max_iterations = len(edge_ids) + 1
    for _ in range(max_iterations):
        if not remaining_edges:
            break
        
        # Find edge that connects to current_end
        found = False
        for i, edge_id in enumerate(remaining_edges):
            if edge_id not in edges:
                continue
            edge = edges[edge_id]
            visual_path = edge.get('visual_path')
            v1_id, v2_id = edge.get('v1'), edge.get('v2')
            
            if visual_path and len(visual_path) >= 2:
                start_point = visual_path[0]
                end_point = visual_path[-1]
            else:
                if v1_id in vertex_coords and v2_id in vertex_coords:
                    start_point = vertex_coords[v1_id]
                    end_point = vertex_coords[v2_id]
                else:
                    continue
            
            # Check if this edge connects to current_end (within tolerance)
            if _points_are_close(start_point, current_end):
                # Edge connects in forward direction
                if visual_path and len(visual_path) >= 2:
                    polygon_points.extend(visual_path[:-1])
                    current_end = visual_path[-1]
                else:
                    polygon_points.append(start_point)
                    current_end = end_point
                remaining_edges.pop(i)
                found = True
                break
            elif _points_are_close(end_point, current_end):
                # Edge connects in reverse direction
                if visual_path and len(visual_path) >= 2:
                    reversed_path = list(reversed(visual_path))
                    polygon_points.extend(reversed_path[:-1])
                    current_end = reversed_path[-1]
                else:
                    polygon_points.append(end_point)
                    current_end = start_point
                remaining_edges.pop(i)
                found = True
                break
        
        if not found:
            # Could not find connecting edge, polygon is incomplete
            break
    
    if len(polygon_points) < 3:
        return None
    
    return polygon_points
