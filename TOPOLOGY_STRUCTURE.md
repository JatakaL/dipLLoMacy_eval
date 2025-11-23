# Topology Data Structure

## Overview

This document describes the Face-Edge-Vertex topological data structure used in the map generation pipeline. This structure replaces the previous cell-centric (GeoJSON-style) format with an explicit topological representation that eliminates data redundancy and makes adjacency relationships explicit.

## Benefits

1. **No Data Redundancy**: Shared borders are stored exactly once as edges, not duplicated in both adjacent cells
2. **Explicit Adjacency**: Two territories are neighbors if and only if they share an edge
3. **Coastline Detection**: Coastlines are edges where adjacent faces have different types (land vs. sea)
4. **Easy Geometry Operations**: Splitting or merging territories only requires updating edge and face references

## Data Structure

The topology is stored in the `topology` key of phase outputs, with three main components:

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
    "edges": ["E_0_1", "E_1_5", "E_5_9", "E_9_0"],
    "center": [0.16, 0.35]
  },
  "C5": {
    "type": "sea",
    "edges": ["E_1_2", "E_2_6", "E_6_1"],
    "center": [0.25, 0.42]
  }
}
```

**Properties**:
- `type` (string): Type of face - `"land"`, `"sea"`, or `"impassable"`
- `edges` (array of strings): Ordered list of edge IDs forming the perimeter of this face
- `center` (array of 2 floats): Centroid coordinates [x, y]

**No Geometric Data**: Faces do not store vertex coordinates directly - they only reference edges, which in turn reference vertices.

## Usage Examples

### Deriving Adjacency

Two faces are neighbors if they share an edge:

```python
from topology import get_adjacency_from_topology

adjacency = get_adjacency_from_topology(edges)
# Returns: {"C4": ["C5", "C21"], "C5": ["C4", "C6"], ...}
```

### Finding Coastlines

Coastlines are edges where the adjacent faces have different types:

```python
coastline_edges = [
    edge_id for edge_id, edge_data in edges.items()
    if edge_data.get("type") == "coast"
]
```

### Reconstructing Polygon Geometry

To get the polygon vertices for a face:

```python
def get_face_polygon(face_id, faces, edges, vertices):
    face = faces[face_id]
    edge_ids = face["edges"]
    
    # Build ordered polygon from edges
    # (Implementation details depend on edge ordering)
    vertex_coords = []
    for edge_id in edge_ids:
        edge = edges[edge_id]
        v1_coords = vertices[edge["v1"]]["coords"]
        vertex_coords.append(v1_coords)
    
    return vertex_coords
```

Note: For visualization, it's often easier to use the legacy `vertices` array stored in the cell data during the transition period.

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

## Validation

The integration test (`test_topology_integration.py`) verifies:

1. **Topology Presence**: All phases include topology in their output
2. **Adjacency Consistency**: Adjacency derived from topology matches legacy neighbor lists
3. **Reference Integrity**: All edges reference valid faces, all faces reference valid edges
4. **Vertex Uniqueness**: No duplicate vertices exist

## Future Enhancements

Potential improvements to the topology system:

1. **Edge-Only Region Merging**: When merging regions, preserve edges and update face references rather than regenerating topology
2. **Geometry-Free Operations**: Implement splitting and merging operations that only manipulate edge-vertex topology
3. **Half-Edge Structure**: For more complex operations, consider upgrading to a half-edge data structure
4. **Persistent Vertex IDs**: Maintain stable vertex IDs across topology regenerations for better change tracking

## References

- Original issue: "Refactor Map Data Structure to Face-Edge-Vertex Topology"
- Implementation: `map_gen/topology.py`
- Tests: `test_topology.py`, `test_topology_integration.py`
- Visualization: `map_viewer.py` and `map_viewer_cli.py` (interactive viewer and CLI renderer)
