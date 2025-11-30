"""
Label Position Calculator Module

This module calculates optimal positions for placing labels, supply center markers,
and unit markers within territory polygons. The positions are pre-determined during
map generation (Phase 7) to avoid overlaps during game rendering.

The algorithm uses Shapely to:
1. Find a "writable" interior area within each territory polygon
2. Designate positions for:
   - Territory name label (primary position, typically the largest clear area)
   - Supply center marker (if applicable)
   - Unit marker position (for placing armies/fleets during gameplay)

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


# Default spacing between elements (as fraction of map dimensions)
# Increased from 0.015 to 0.025 for better readability
DEFAULT_ELEMENT_SPACING = 0.025

# Minimum polygon area for label placement calculations (below this, use centroid)
MIN_POLYGON_AREA = 0.0001

# Aspect ratio threshold for detecting horizontal vs vertical territories
# If width/height > this, consider it a horizontal territory
HORIZONTAL_ASPECT_RATIO = 1.8


def calculate_label_positions(
    polygon_vertices: List[List[float]],
    has_supply_center: bool = False,
    element_spacing: float = DEFAULT_ELEMENT_SPACING
) -> Dict[str, List[float]]:
    """
    Calculate optimal positions for name label, SC marker, and unit marker.
    
    The algorithm finds the "pole of inaccessibility" (point furthest from edges)
    and arranges elements around it to avoid overlaps.
    
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
        # Without Shapely, use centroid-based positioning
        return _fallback_positions(centroid, has_supply_center, element_spacing)
    
    try:
        # Create Shapely polygon
        polygon = Polygon(polygon_vertices)
        
        if not polygon.is_valid:
            # Try to fix invalid polygon using buffer(0) trick
            # This can fix self-intersecting polygons but may produce empty results
            # for degenerate geometries (e.g., bowtie shapes that collapse)
            polygon = polygon.buffer(0)
            if not polygon.is_valid or polygon.is_empty:
                return _fallback_positions(centroid, has_supply_center, element_spacing)
        
        if polygon.area < MIN_POLYGON_AREA:
            # Very small polygon - just use centroid
            return _fallback_positions(centroid, has_supply_center, element_spacing)
        
        # Find the "pole of inaccessibility" - the point furthest from edges
        # This gives us the best center point for placing labels
        try:
            poi = polylabel(polygon, tolerance=0.001)
            base_point = [poi.x, poi.y]
        except Exception:
            # polylabel can fail on some geometries - use centroid
            if polygon.centroid.is_empty:
                base_point = centroid
            else:
                base_point = [polygon.centroid.x, polygon.centroid.y]
        
        # Check if polygon is large enough to benefit from interior buffering
        # For small polygons, skip the expensive buffer operation
        buffer_distance = element_spacing * 0.5
        min_area_for_buffer = buffer_distance * buffer_distance * 4  # Rough estimate
        
        if polygon.area < min_area_for_buffer:
            # Polygon is too small for meaningful buffer - use simple positioning
            return _arrange_elements_simple(base_point, polygon, has_supply_center, element_spacing)
        
        # Calculate the interior buffer to find usable label area
        # This is the area that's at least some distance from edges
        interior_buffer = polygon.buffer(-buffer_distance)
        
        if interior_buffer.is_empty or interior_buffer.area < MIN_POLYGON_AREA:
            # Buffer result is too small - use simple positioning
            return _arrange_elements_simple(base_point, polygon, has_supply_center, element_spacing)
        
        # Arrange elements within the interior area
        return _arrange_elements(base_point, polygon, interior_buffer, has_supply_center, element_spacing)
        
    except Exception:
        # Any error - fall back to centroid-based positioning
        return _fallback_positions(centroid, has_supply_center, element_spacing)


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
    
    Layout (when SC present) - Name and SC in northern part, unit below:
        [Name]  (top/north)
        [SC]    (middle, with increased gap from name to avoid overlap)
        [Unit]  (bottom/south, with more spacing)
        
    Layout (no SC) - Name in northern part, unit below:
        [Name]  (top/north)
        [Unit]  (bottom/south)
    
    Note: unit_position is ALWAYS included since any territory can have a unit.
    """
    positions = {}
    
    if has_supply_center:
        # Three elements stacked vertically with name/SC in northern part
        # Name at top (highest Y), SC at center, Unit further below
        # Name is 1.5 spacing above center, SC at center, Unit 1.3 spacing below center
        # This gives 1.5 spacing between name and SC to prevent text/marker overlap
        positions['name_position'] = [center[0], center[1] + element_spacing * 1.5]
        positions['sc_position'] = [center[0], center[1]]
        positions['unit_position'] = [center[0], center[1] - element_spacing * 1.3]
    else:
        # Two elements - name in northern part, unit below
        positions['name_position'] = [center[0], center[1] + element_spacing * 0.7]
        positions['unit_position'] = [center[0], center[1] - element_spacing * 0.7]
    
    return positions


def _arrange_elements_simple(
    base_point: List[float],
    polygon: 'Polygon',
    has_supply_center: bool,
    element_spacing: float
) -> Dict[str, List[float]]:
    """
    Arrange elements using simple vertical stacking when polygon is too small for buffering.
    Ensures positions stay within the polygon boundary.
    Uses improved layout with name/SC in northern part and unit below.
    
    Note: unit_position is ALWAYS included since any territory can have a unit.
    """
    positions = _fallback_positions(base_point, has_supply_center, element_spacing)
    
    # Clamp positions to stay within polygon
    for key in positions:
        pos = positions[key]
        point = Point(pos[0], pos[1])
        if not polygon.contains(point):
            # Move to nearest point on polygon boundary, then slightly inside
            nearest = polygon.exterior.interpolate(polygon.exterior.project(point))
            # Move toward centroid to ensure we're inside
            cx, cy = polygon.centroid.x, polygon.centroid.y
            dx = cx - nearest.x
            dy = cy - nearest.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                # Move 30% of the way toward centroid for better positioning
                positions[key] = [
                    nearest.x + dx * 0.3,
                    nearest.y + dy * 0.3
                ]
    
    return positions


def _arrange_elements(
    base_point: List[float],
    polygon: 'Polygon',
    interior_buffer: 'Polygon',
    has_supply_center: bool,
    element_spacing: float
) -> Dict[str, List[float]]:
    """
    Arrange elements optimally within the polygon interior.
    
    Strategy:
    1. Detect if territory is horizontally oriented (wide and short)
    2. For vertical/normal territories:
       - Name goes at northern position (higher Y, above base point)
       - SC marker (if present) goes below name but still in upper portion
       - Unit marker goes in southern portion (lower Y)
    3. For horizontal territories:
       - Name and SC on one side, unit on the other side
    
    Note: unit_position is ALWAYS included since any territory can have a unit.
    """
    positions = {}
    
    # Get polygon bounds to detect orientation
    minx, miny, maxx, maxy = polygon.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Detect if territory is horizontally oriented
    # Use epsilon to avoid floating point precision issues with height
    is_horizontal = height > 1e-10 and (width / height) > HORIZONTAL_ASPECT_RATIO
    
    if is_horizontal:
        # Horizontal territory - arrange elements left to right
        # Name and SC on left/center, unit on right
        return _arrange_elements_horizontal(base_point, polygon, interior_buffer, has_supply_center, element_spacing)
    
    # Vertical/normal arrangement - name/SC in northern part, unit in southern part
    # Try to place name in northern part of polygon (higher Y)
    name_pos = [base_point[0], base_point[1] + element_spacing * 1.5]
    if not _is_inside_polygon(name_pos, interior_buffer):
        # Try at base point with smaller offset
        name_pos = [base_point[0], base_point[1] + element_spacing * 0.8]
        if not _is_inside_polygon(name_pos, interior_buffer):
            name_pos = list(base_point)
    positions['name_position'] = name_pos
    
    if has_supply_center:
        # SC goes below name with increased gap to prevent text overlap
        # Increased spacing from 0.9 to 1.5 to ensure name text doesn't overlap SC marker
        sc_pos = [name_pos[0], name_pos[1] - element_spacing * 1.5]
        if not _is_inside_polygon(sc_pos, interior_buffer):
            # Try at center
            sc_pos = [base_point[0], base_point[1]]
            if not _is_inside_polygon(sc_pos, interior_buffer):
                sc_pos = list(base_point)
        positions['sc_position'] = sc_pos
        
        # Unit goes in southern portion, below SC with good spacing
        unit_pos = [sc_pos[0], sc_pos[1] - element_spacing * 1.5]
        if not _is_inside_polygon(unit_pos, interior_buffer):
            # Try further below base point
            unit_pos = [base_point[0], base_point[1] - element_spacing * 1.8]
            if not _is_inside_polygon(unit_pos, interior_buffer):
                # Try to the side
                for dx in [element_spacing, -element_spacing]:
                    unit_pos = [sc_pos[0] + dx, sc_pos[1] - element_spacing * 0.8]
                    if _is_inside_polygon(unit_pos, interior_buffer):
                        break
                else:
                    # Fall back to below SC with smaller spacing
                    unit_pos = [sc_pos[0], sc_pos[1] - element_spacing * 1.0]
        positions['unit_position'] = unit_pos
    else:
        # No SC - unit goes in southern portion below name
        unit_pos = [name_pos[0], name_pos[1] - element_spacing * 1.5]
        if not _is_inside_polygon(unit_pos, interior_buffer):
            # Try at base point offset
            unit_pos = [base_point[0], base_point[1] - element_spacing * 0.8]
            if not _is_inside_polygon(unit_pos, interior_buffer):
                # Try to the side
                for dx in [element_spacing, -element_spacing]:
                    unit_pos = [base_point[0] + dx, base_point[1]]
                    if _is_inside_polygon(unit_pos, interior_buffer):
                        break
                else:
                    unit_pos = [base_point[0], base_point[1] - element_spacing * 0.5]
        positions['unit_position'] = unit_pos
    
    # Final validation - ensure all positions are inside polygon (at least the outer boundary)
    for key in positions:
        pos = positions[key]
        if not _is_inside_polygon(pos, polygon):
            # Move to centroid if outside
            positions[key] = [polygon.centroid.x, polygon.centroid.y]
    
    return positions


def _arrange_elements_horizontal(
    base_point: List[float],
    polygon: 'Polygon',
    interior_buffer: 'Polygon',
    has_supply_center: bool,
    element_spacing: float
) -> Dict[str, List[float]]:
    """
    Arrange elements for horizontally-oriented (wide) territories.
    
    Layout: Name and SC on left/center, Unit on right side
    This prevents vertical stacking from going outside narrow boundaries.
    """
    positions = {}
    
    # Get polygon center
    cx = polygon.centroid.x
    cy = polygon.centroid.y
    
    if has_supply_center:
        # Name slightly left and above center with more vertical spacing
        name_pos = [cx - element_spacing * 0.3, cy + element_spacing * 0.8]
        if not _is_inside_polygon(name_pos, interior_buffer):
            name_pos = [cx, cy + element_spacing * 0.5]
            if not _is_inside_polygon(name_pos, interior_buffer):
                name_pos = [cx, cy]
        positions['name_position'] = name_pos
        
        # SC below name with increased gap to prevent overlap
        sc_pos = [name_pos[0], name_pos[1] - element_spacing * 1.3]
        if not _is_inside_polygon(sc_pos, interior_buffer):
            sc_pos = [cx, cy - element_spacing * 0.5]
            if not _is_inside_polygon(sc_pos, interior_buffer):
                sc_pos = [cx, cy]
        positions['sc_position'] = sc_pos
        
        # Unit to the right side
        unit_pos = [cx + element_spacing * 1.5, cy]
        if not _is_inside_polygon(unit_pos, interior_buffer):
            # Try left side instead
            unit_pos = [cx - element_spacing * 1.5, cy]
            if not _is_inside_polygon(unit_pos, interior_buffer):
                # Fall back to below
                unit_pos = [cx, cy - element_spacing * 1.2]
                if not _is_inside_polygon(unit_pos, interior_buffer):
                    unit_pos = [cx, cy]
        positions['unit_position'] = unit_pos
    else:
        # Name on left side
        name_pos = [cx - element_spacing * 0.5, cy]
        if not _is_inside_polygon(name_pos, interior_buffer):
            name_pos = [cx, cy]
        positions['name_position'] = name_pos
        
        # Unit on right side
        unit_pos = [cx + element_spacing * 1.0, cy]
        if not _is_inside_polygon(unit_pos, interior_buffer):
            # Try left side
            unit_pos = [cx - element_spacing * 1.0, cy]
            if not _is_inside_polygon(unit_pos, interior_buffer):
                unit_pos = [cx, cy - element_spacing * 0.5]
                if not _is_inside_polygon(unit_pos, interior_buffer):
                    unit_pos = [cx, cy]
        positions['unit_position'] = unit_pos
    
    # Final validation
    for key in positions:
        pos = positions[key]
        if not _is_inside_polygon(pos, polygon):
            positions[key] = [polygon.centroid.x, polygon.centroid.y]
    
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
