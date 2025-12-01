# Topology Data Structure

## Overview

This document describes the Face-Edge-Vertex topological data structure used in the map generation pipeline. This structure replaces the previous cell-centric (GeoJSON-style) format with an explicit topological representation that eliminates data redundancy and makes adjacency relationships explicit.

## Benefits

1. **No Data Redundancy**: Shared boundaries are stored exactly once, not duplicated in both adjacent cells
2. **Explicit Adjacency**: Two territories are neighbors if and only if they share a border
3. **Coastline Detection**: Coastlines are borders where adjacent faces have different types (land vs. sea)
4. **Easy Geometry Operations**: Splitting or merging territories only requires updating border and face references
5. **Border Abstraction**: Borders group edges that share the same adjacent faces, providing a clean abstraction layer between faces and edges that supports edge subdivision for jagged coastlines

## Data Structure

The topology is stored in the `topology` key of phase outputs, with four main components:

### 1. Vertices (Points)

**Format**: Array of vertex objects

```json
[
  {
    "id": 0,
    "coords": [0.15, 0.33]
  },
  {
    "id": 1,
    "coords": [0.18, 0.40]
  }
]
```

**Properties**:
- `id` (integer): Unique identifier for the vertex
- `coords` (array of 2 floats): [x, y] coordinates in map space (0.0 to 1.0)

**Deduplication**: Vertices are deduplicated during conversion - identical coordinates (within tolerance) share the same vertex ID.

### 2. Edges (Connections)

**Format**: Dictionary mapping edge IDs to edge objects

```json
{
  "E_0_1": {
    "v1": 0,
    "v2": 1,
    "left_face": "C4",
    "right_face": "C21",
    "type": "land"
  },
  "E_1_2": {
    "v1": 1,
    "v2": 2,
    "left_face": "C4",
    "right_face": "C5",
    "type": "coast"
  }
}
```

**Properties**:
- `v1` (integer): ID of the first vertex (always the smaller ID)
- `v2` (integer): ID of the second vertex (always the larger ID)
- `left_face` (string, optional): ID of the face on one side of the edge
- `right_face` (string, optional): ID of the face on the other side of the edge
- `type` (string): Type of edge
  - `"land"`: Both adjacent faces are land
  - `"sea"`: Both adjacent faces are sea
  - `"coast"`: Adjacent faces have different types (land-sea boundary)
  - `"map-edge"`: Only one adjacent face (boundary of the map)

**Edge IDs**: Edges are named `E_{min_vertex}_{max_vertex}` to ensure that edge A→B has the same ID as edge B→A.

**Face Assignment**: When an edge is first created during Voronoi conversion, its `left_face` is set. When the same edge is encountered from the adjacent face, `right_face` is set. Map boundary edges have only `left_face` set.

### 3. Faces (Territories)

**Format**: Dictionary mapping face IDs to face objects

```json
{
  "C4": {
    "type": "land",
    "borders": ["B_0_1", "B_1_5", "B_5_9", "B_9_0"],
    "center": [0.16, 0.35],
    "is_supply_center": true,
    "label_positions": {
      "name_position": [0.16, 0.38],
      "sc_position": [0.16, 0.35],
      "unit_position": [0.16, 0.32]
    }
  },
  "C5": {
    "type": "sea",
    "borders": ["B_1_2", "B_2_6", "B_6_1"],
    "center": [0.25, 0.42],
    "label_positions": {
      "name_position": [0.25, 0.44],
      "unit_position": [0.25, 0.40]
    }
  }
}
```

**Properties**:
- `type` (string): Type of face - `"land"`, `"sea"`, or `"impassable"`
- `borders` (array of strings): Ordered list of border IDs forming the perimeter
- `center` (array of 2 floats): Centroid coordinates [x, y]
- `is_supply_center` (boolean, optional): Whether this face is a supply center
- `label_positions` (object, optional): Pre-determined positions for rendering elements:
  - `name_position` (array of 2 floats): [x, y] position for territory name label
  - `sc_position` (array of 2 floats): [x, y] position for supply center marker (only if `is_supply_center` is true)
  - `unit_position` (array of 2 floats): [x, y] position for unit marker (army/fleet)

**No Geometric Data or Direct Edge References**: Faces reference borders, not edges directly. This eliminates redundancy and ensures edges are only referenced in one place (borders).

**Label Positions**: The `label_positions` field is calculated during Phase 7 using the Shapely library to find optimal positions within the polygon that avoid overlap. The algorithm finds the "pole of inaccessibility" (the point furthest from edges) and arranges elements around it. This pre-calculation ensures consistent, non-overlapping placement of names, supply center markers, and units during game rendering.

### 4. Borders (Edge Groups)

**Format**: Dictionary mapping border IDs to border objects

```json
{
  "B_0_1": {
    "edges": ["E_0_2", "E_2_3", "E_3_1"],
    "left_face": "C4",
    "right_face": "C5",
    "type": "coast",
    "start_vertex": 0,
    "end_vertex": 1
  }
}
```

**Properties**:
- `edges` (array of strings): Ordered list of edge IDs that form this border
- `left_face` (string, optional): ID of the face on the left side
- `right_face` (string, optional): ID of the face on the right side
- `type` (string): Type of border (same values as edge types)
- `start_vertex` (integer): ID of the first vertex in the border chain
- `end_vertex` (integer): ID of the last vertex in the border chain

**Border IDs**: Borders are named `B_{min_vertex}_{max_vertex}` based on their original vertices before subdivision.

**Purpose**: Borders group edges that share the same adjacent faces. Before edge subdivision, each border contains a single edge. After subdivision (to create jagged coastlines/borders), a border contains multiple edges that together represent the original boundary.

**Consistency Guarantee**: By subdividing edges within the topology (creating new vertices and edges) rather than using visual-only paths, the visual representation and the topological data remain consistent. This is a key design principle of the data structure.

## Usage Examples

### Deriving Adjacency

Two faces are neighbors if they share a border. The recommended approach uses borders (the abstraction layer between faces and edges):

```python
from topology import get_adjacency_from_borders, get_adjacency_from_topology

# Preferred: Use borders directly (works correctly with subdivided edges)
adjacency = get_adjacency_from_borders(borders)
# Returns: {"C4": ["C5", "C21"], "C5": ["C4", "C6"], ...}

# Alternative: get_adjacency_from_topology uses borders when available
adjacency = get_adjacency_from_topology(edges, borders)
```

### Finding Coastlines

Coastlines are borders (or edges) where the adjacent faces have different types. Using borders is preferred:

```python
# Preferred: Use borders
coastal_borders = [
    border_id for border_id, border_data in borders.items()
    if border_data.get("type") == "coast"
]

# Alternative: Use edges directly
coastline_edges = [
    edge_id for edge_id, edge_data in edges.items()
    if edge_data.get("type") == "coast"
]
```

### Reconstructing Polygon Geometry

To get the polygon vertices for a face, use the `get_face_edges()` helper to retrieve edges through borders:

```python
from topology import get_face_edges

def get_face_polygon(face_id, faces, edges, borders, vertices):
    face = faces[face_id]
    # Get edges through borders (the proper abstraction layer)
    edge_ids = get_face_edges(face, borders)
    
    # Build ordered polygon from edges
    # (Implementation details depend on edge ordering)
    vertex_coords = []
    for edge_id in edge_ids:
        edge = edges[edge_id]
        v1_coords = vertices[edge["v1"]]["coords"]
        vertex_coords.append(v1_coords)
    
    return vertex_coords
```

Note: Faces reference borders, not edges directly. Use `get_face_edges()` to retrieve the underlying edges when needed.

## Pipeline Integration

### Phase 1: Mesh Generation
- Generates Voronoi diagram from random points
- Converts cells to topology using `convert_cells_to_topology()`
- All edges are classified as `"land"` (no terrain assigned yet)

### Phase 2: Terrain Assignment
- Assigns land/sea types to cells
- Regenerates topology with updated face types
- Edges are reclassified based on adjacent face types
- Coastline edges (`type="coast"`) are now identified

### Phase 3: Province Definition
- Marks coastal vs. inland cells
- Groups sea cells into ocean regions
- Creates impassable zones
- Regenerates topology with updated face types

### Later Phases
The topology can be carried forward through region merging and other operations. When regions are merged, edges and vertices can be preserved and reassigned to the merged region faces.

### Phase 7: Naming and Fractal Subdivision
- Assigns names to all provinces using procedural generation
- **Fractal Edge Subdivision**: Subdivides edges topologically to create jagged borders:
  - Creates new vertices at displaced midpoints
  - Replaces original edges with multiple smaller edges
  - Updates borders to contain the subdivided edges
  - Ensures visual representation matches topological data
- **Label Position Calculation**: Pre-determines positions for rendering elements:
  - Uses Shapely's "pole of inaccessibility" algorithm to find optimal center points
  - Calculates non-overlapping positions for: territory name, SC marker, and unit marker
  - Stores positions in `label_positions` field of each face
  - Ensures consistent rendering across different viewers and game states
- Exports final map with subdivision and label positions applied

## Validation

The integration test (`test_topology_integration.py`) verifies:

1. **Topology Presence**: All phases include topology in their output
2. **Adjacency Consistency**: Adjacency derived from topology matches legacy neighbor lists
3. **Reference Integrity**: All edges reference valid faces, all faces reference valid edges
4. **Vertex Uniqueness**: No duplicate vertices exist

## Recent Enhancements

### Border Data Type and Topological Edge Subdivision

The border data type has been implemented to address concerns about jagged border visualization. Previously, fractal edges were stored as `visual_path` arrays on each edge, creating a disconnect between the visual representation and the topological data.

**New Approach**:
1. **Border Class**: A border is an ordered list of edges that share the same adjacent faces
2. **Topological Subdivision**: When creating jagged borders, edges are actually subdivided:
   - New vertices are created at displaced midpoints
   - New edges are created connecting the vertices
   - The border is updated to contain all the new edges
   - Faces are updated to reference the new edges
3. **Visual-Data Consistency**: The visual representation now matches the topological data

**Benefits**:
- No inconsistency between what the software sees and what players see
- Edge operations (split, merge) work correctly on subdivided edges
- Better support for future features like pathfinding along borders

## Future Enhancements

Potential improvements to the topology system:

1. **Edge-Only Region Merging**: When merging regions, preserve edges and update face references rather than regenerating topology
2. **Geometry-Free Operations**: Implement splitting and merging operations that only manipulate edge-vertex topology
3. **Half-Edge Structure**: For more complex operations, consider upgrading to a half-edge data structure
4. **Persistent Vertex IDs**: Maintain stable vertex IDs across topology regenerations for better change tracking

## References

- Original issue: "Refactor Map Data Structure to Face-Edge-Vertex Topology"
- Border implementation issue: "Re-examine implementation of jagged borders"
- Label positions issue: "Pre-determine SC, Name, and Unit positions"
- Implementation: `map_gen/topology.py`, `map_gen/fractal_subdivision.py`, `map_gen/label_positions.py`
- Tests: `test_topology.py`, `test_topology_integration.py`, `test_fractal_subdivision.py`, `tests/test_label_positions.py`
- Visualization: `map_viewer.py` and `map_viewer_cli.py` (interactive viewer and CLI renderer)
