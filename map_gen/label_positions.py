"""
Label Position Calculator Module

This module calculates optimal positions for placing labels, supply center markers,
and unit markers within territory polygons. The positions are pre-determined during
map generation (Phase 7) to avoid overlaps during game rendering.

The algorithm uses Shapely to:
1. Find the maximum inscribed circle within each territory polygon
2. Use the center of this circle as the primary placement point
3. Designate positions for (in order of priority):
   - Territory name label (at the center - largest element)
   - Unit marker position (below the name - second largest)
   - Supply center marker (above the name if room, else find alternate position)

The positions are stored in the topology data structure and used during rendering
to ensure text and markers don't overlap.
"""

import math
from typing import Dict, List, Tuple, Optional

# Try to import Shapely for geometric operations
try:
    from shapely.geometry import Polygon, Point, MultiPoint
    from shapely.ops import polylabel
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

# Try to import maximum_inscribed_circle (Shapely 2.0+)
try:
    from shapely import maximum_inscribed_circle
    MIC_AVAILABLE = True
except ImportError:
    MIC_AVAILABLE = False


# Default spacing between elements (as fraction of map dimensions)
DEFAULT_ELEMENT_SPACING = 0.025

# Minimum polygon area for label placement calculations (below this, use centroid)
MIN_POLYGON_AREA = 0.0001

# Minimum inscribed circle radius for valid label placement
# If the max inscribed circle is smaller than this, the territory may be too small
MIN_INSCRIBED_RADIUS = 0.015


def calculate_label_positions(
    polygon_vertices: List[List[float]],
    has_supply_center: bool = False,
    element_spacing: float = DEFAULT_ELEMENT_SPACING
) -> Dict[str, List[float]]:
    """
    Calculate optimal positions for name label, SC marker, and unit marker.
    
    Uses the maximum inscribed circle approach:
    1. Name goes at the center of the maximum inscribed circle (largest element)
    2. Unit goes below the name, within the inscribed circle if possible
    3. SC goes above the name if there's room, otherwise finds alternate position
    
    Args:
        polygon_vertices: List of [x, y] coordinates forming the territory polygon
        has_supply_center: Whether this territory has a supply center
        element_spacing: Spacing between elements (fraction of map dimensions)
        
    Returns:
        Dictionary with position keys:
        - 'name_position': [x, y] for territory name label
        - 'sc_position': [x, y] for supply center marker (if has_supply_center)
        - 'unit_position': [x, y] for unit marker
    """
    if not polygon_vertices or len(polygon_vertices) < 3:
        return _fallback_positions([0.5, 0.5], has_supply_center, element_spacing)
    
    # Calculate centroid as fallback
    centroid = _calculate_centroid(polygon_vertices)
    
    if not SHAPELY_AVAILABLE:
        return _fallback_positions(centroid, has_supply_center, element_spacing)
    
    try:
        # Create Shapely polygon
        polygon = Polygon(polygon_vertices)
        
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
            if not polygon.is_valid or polygon.is_empty:
                return _fallback_positions(centroid, has_supply_center, element_spacing)
        
        if polygon.area < MIN_POLYGON_AREA:
            return _fallback_positions(centroid, has_supply_center, element_spacing)
        
        # Find the maximum inscribed circle
        center, radius = _get_max_inscribed_circle(polygon)
        
        if center is None or radius < MIN_INSCRIBED_RADIUS:
            # Territory too small for good placement - use fallback
            return _fallback_positions(centroid, has_supply_center, element_spacing)
        
        # Arrange elements using the inscribed circle
        return _arrange_in_inscribed_circle(center, radius, polygon, has_supply_center, element_spacing)
        
    except Exception:
        return _fallback_positions(centroid, has_supply_center, element_spacing)


def _get_max_inscribed_circle(polygon: 'Polygon') -> Tuple[Optional[List[float]], float]:
    """
    Get the center and radius of the maximum inscribed circle.
    
    Returns:
        Tuple of (center [x, y], radius) or (None, 0) if not available
    """
    if not MIC_AVAILABLE:
        # Fall back to polylabel
        try:
            poi = polylabel(polygon, tolerance=0.001)
            center = [poi.x, poi.y]
            # Approximate radius as distance to nearest boundary
            radius = polygon.exterior.distance(poi)
            return center, radius
        except Exception:
            return None, 0
    
    try:
        mic = maximum_inscribed_circle(polygon, tolerance=0.001)
        coords = list(mic.coords)
        if len(coords) < 2:
            return None, 0
        center = [coords[0][0], coords[0][1]]
        radius_point = coords[1]
        radius = math.sqrt((radius_point[0] - center[0])**2 + (radius_point[1] - center[1])**2)
        return center, radius
    except Exception:
        return None, 0


def _arrange_in_inscribed_circle(
    center: List[float],
    radius: float,
    polygon: 'Polygon',
    has_supply_center: bool,
    element_spacing: float
) -> Dict[str, List[float]]:
    """
    Arrange elements within the maximum inscribed circle.
    
    Priority order:
    1. Name at center (largest element)
    2. Unit below name  
    3. SC above name (if has_supply_center and there's room)
    
    All positions are validated to be inside the polygon.
    """
    positions = {}
    
    # Helper function for Euclidean distance from center
    def dist_from_center(pos):
        return math.sqrt((pos[0] - center[0])**2 + (pos[1] - center[1])**2)
    
    # 1. Name goes at the center of the inscribed circle
    positions['name_position'] = list(center)
    
    # Calculate vertical spacing based on radius (but not exceeding element_spacing)
    # Use about 40% of radius for spacing, capped at element_spacing
    vertical_spacing = min(radius * 0.4, element_spacing)
    
    # 2. Unit goes below the name
    unit_pos = [center[0], center[1] - vertical_spacing * 1.5]
    
    # Check if unit position is inside the inscribed circle using Euclidean distance
    if dist_from_center(unit_pos) > radius * 0.9:
        # Outside circle, try smaller offset
        unit_pos = [center[0], center[1] - radius * 0.6]
    
    # Validate inside polygon
    if not _is_inside_polygon(unit_pos, polygon):
        # Try smaller offset
        unit_pos = [center[0], center[1] - radius * 0.3]
        if not _is_inside_polygon(unit_pos, polygon):
            # Fall back to center
            unit_pos = list(center)
    
    positions['unit_position'] = unit_pos
    
    # 3. SC goes above the name (if applicable)
    if has_supply_center:
        sc_pos = [center[0], center[1] + vertical_spacing * 1.5]
        
        # Check if SC position is inside the inscribed circle using Euclidean distance
        if dist_from_center(sc_pos) > radius * 0.9:
            # Outside circle, try smaller offset
            sc_pos = [center[0], center[1] + radius * 0.6]
        
        # Validate inside polygon
        if not _is_inside_polygon(sc_pos, polygon):
            # Try to find alternate position - to the side
            for dx in [radius * 0.7, -radius * 0.7, radius * 0.5, -radius * 0.5]:
                alt_pos = [center[0] + dx, center[1]]
                if _is_inside_polygon(alt_pos, polygon) and dist_from_center(alt_pos) <= radius * 0.95:
                    sc_pos = alt_pos
                    break
            else:
                # Try smaller offset above
                sc_pos = [center[0], center[1] + radius * 0.3]
                if not _is_inside_polygon(sc_pos, polygon):
                    # Last resort - just above center
                    sc_pos = [center[0], center[1] + radius * 0.1]
                    if not _is_inside_polygon(sc_pos, polygon):
                        sc_pos = list(center)
        
        positions['sc_position'] = sc_pos
    
    return positions


def _calculate_centroid(vertices: List[List[float]]) -> List[float]:
    """Calculate the centroid of a polygon."""
    if not vertices:
        return [0.5, 0.5]
    
    x_sum = sum(v[0] for v in vertices)
    y_sum = sum(v[1] for v in vertices)
    n = len(vertices)
    
    return [x_sum / n, y_sum / n]


def _fallback_positions(
    center: List[float],
    has_supply_center: bool,
    element_spacing: float
) -> Dict[str, List[float]]:
    """
    Generate positions using simple offset from center point.
    
    This is used when Shapely is not available or polygon is invalid/too small.
    
    Layout (when SC present):
        [SC]    (above center)
        [Name]  (at center)
        [Unit]  (below center)
        
    Layout (no SC):
        [Name]  (at center)
        [Unit]  (below center)
    
    Note: unit_position is ALWAYS included since any territory can have a unit.
    """
    positions = {}
    
    # Name always at center
    positions['name_position'] = list(center)
    
    # Unit below center
    positions['unit_position'] = [center[0], center[1] - element_spacing * 1.2]
    
    if has_supply_center:
        # SC above center
        positions['sc_position'] = [center[0], center[1] + element_spacing * 1.2]
    
    return positions


def _is_inside_polygon(point: List[float], polygon: 'Polygon') -> bool:
    """Check if a point is inside a polygon (or MultiPolygon)."""
    try:
        return polygon.contains(Point(point[0], point[1]))
    except Exception:
        return False


def calculate_all_label_positions(
    faces: Dict[str, dict],
    topology: dict,
    element_spacing: float = DEFAULT_ELEMENT_SPACING
) -> Dict[str, dict]:
    """
    Calculate label positions for all faces in a topology.
    
    This function reconstructs the polygon for each face and calculates
    optimal positions for labels and markers.
    
    Args:
        faces: Dictionary of face data from topology
        topology: Full topology dictionary (needed to reconstruct polygons)
        element_spacing: Spacing between elements
        
    Returns:
        Updated faces dictionary with 'label_positions' added to each face
    """
    # Create vertex coordinate lookup
    vertices_list = topology.get('vertices', [])
    vertex_coords = {v['id']: v['coords'] for v in vertices_list}
    
    edges = topology.get('edges', {})
    borders = topology.get('borders', {})
    
    for face_id, face_data in faces.items():
        # Reconstruct polygon vertices
        polygon_vertices = _reconstruct_face_polygon(
            face_data, edges, borders, vertex_coords
        )
        
        # Check if this face has a supply center
        has_sc = face_data.get('is_supply_center', False)
        
        # Calculate positions
        positions = calculate_label_positions(
            polygon_vertices, has_sc, element_spacing
        )
        
        # Store positions in face data
        face_data['label_positions'] = positions
    
    return faces


def _reconstruct_face_polygon(
    face_data: dict,
    edges: Dict[str, dict],
    borders: Dict[str, dict],
    vertex_coords: Dict[int, List[float]]
) -> List[List[float]]:
    """
    Reconstruct polygon vertices for a face from topology data.
    
    This handles both direct edge references and border-based edge references.
    """
    # Get edge IDs through borders
    edge_ids = []
    for border_id in face_data.get('borders', []):
        if border_id in borders:
            border = borders[border_id]
            edge_ids.extend(border.get('edges', []))
    
    if not edge_ids:
        # Try direct edges (legacy support)
        edge_ids = face_data.get('edges', [])
    
    if not edge_ids:
        return []
    
    # Build vertex graph from edges
    vertex_graph = {}
    for edge_id in edge_ids:
        if edge_id not in edges:
            continue
        edge = edges[edge_id]
        v1, v2 = edge['v1'], edge['v2']
        
        if v1 not in vertex_graph:
            vertex_graph[v1] = []
        if v2 not in vertex_graph:
            vertex_graph[v2] = []
        vertex_graph[v1].append(v2)
        vertex_graph[v2].append(v1)
    
    if not vertex_graph:
        return []
    
    # Trace polygon boundary
    start_vertex = next(iter(vertex_graph.keys()))
    polygon = []
    current = start_vertex
    visited = set()
    
    max_iterations = len(vertex_graph) + 1
    for _ in range(max_iterations):
        if current in visited:
            break
        
        visited.add(current)
        if current in vertex_coords:
            polygon.append(vertex_coords[current])
        
        # Find next unvisited neighbor
        neighbors = vertex_graph.get(current, [])
        next_vertex = None
        for neighbor in neighbors:
            if neighbor not in visited:
                next_vertex = neighbor
                break
            elif neighbor == start_vertex and len(visited) == len(vertex_graph):
                next_vertex = neighbor
                break
        
        if next_vertex is None:
            break
        current = next_vertex
    
    return polygon
