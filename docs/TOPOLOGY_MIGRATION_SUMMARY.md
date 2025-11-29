# Topology Migration Summary

## Overview

This document summarizes the migration from cell-centric to Face-Edge-Vertex topological data structure.

## Problem Addressed

### Before: Cell-Centric Structure

```json
{
  "C1": {
    "id": "C1",
    "type": "land",
    "center": [0.25, 0.5],
    "vertices": [
      [0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]
    ],
    "neighbors": ["C2", "C3"]  // Calculated by distance heuristics
  },
  "C2": {
    "id": "C2",
    "type": "land",
    "center": [0.75, 0.5],
    "vertices": [
      [0.5, 0.0], [1.0, 0.0], [1.0, 1.0], [0.5, 1.0]  // Shared vertices duplicated!
    ],
    "neighbors": ["C1"]
  }
}
```

**Problems**:
1. Shared border stored twice (in both C1 and C2)
2. Floating point drift could create visual gaps
3. Neighbors determined by geometric distance, not topology
4. Changing one cell requires updating multiple cells

### After: Topological Structure

```json
{
  "vertices": [
    {"id": 0, "coords": [0.0, 0.0]},
    {"id": 1, "coords": [0.5, 0.0]},
    {"id": 2, "coords": [1.0, 0.0]},
    {"id": 3, "coords": [1.0, 1.0]},
    {"id": 4, "coords": [0.5, 1.0]},
    {"id": 5, "coords": [0.0, 1.0]}
  ],
  "edges": {
    "E_0_1": {"v1": 0, "v2": 1, "left_face": "C1", "type": "map-edge"},
    "E_1_2": {"v1": 1, "v2": 2, "left_face": "C2", "type": "map-edge"},
    "E_1_4": {"v1": 1, "v2": 4, "left_face": "C1", "right_face": "C2", "type": "land"},
    "E_2_3": {"v1": 2, "v2": 3, "left_face": "C2", "type": "map-edge"},
    "E_3_4": {"v1": 3, "v2": 4, "left_face": "C2", "type": "map-edge"},
    "E_0_5": {"v1": 0, "v2": 5, "left_face": "C1", "type": "map-edge"},
    "E_4_5": {"v1": 4, "v2": 5, "left_face": "C1", "type": "map-edge"}
  },
  "borders": {
    "B_0_1": {"edges": ["E_0_1"], "left_face": "C1", "type": "map-edge", "start_vertex": 0, "end_vertex": 1},
    "B_1_2": {"edges": ["E_1_2"], "left_face": "C2", "type": "map-edge", "start_vertex": 1, "end_vertex": 2},
    "B_2_3": {"edges": ["E_2_3"], "left_face": "C2", "type": "map-edge", "start_vertex": 2, "end_vertex": 3},
    "B_3_4": {"edges": ["E_3_4"], "left_face": "C2", "type": "map-edge", "start_vertex": 3, "end_vertex": 4},
    "B_1_4": {"edges": ["E_1_4"], "left_face": "C1", "right_face": "C2", "type": "land", "start_vertex": 1, "end_vertex": 4},
    "B_4_5": {"edges": ["E_4_5"], "left_face": "C1", "type": "map-edge", "start_vertex": 4, "end_vertex": 5},
    "B_0_5": {"edges": ["E_0_5"], "left_face": "C1", "type": "map-edge", "start_vertex": 0, "end_vertex": 5}
  },
  "faces": {
    "C1": {
      "type": "land",
      "borders": ["B_0_1", "B_1_4", "B_4_5", "B_0_5"],
      "center": [0.25, 0.5]
    },
    "C2": {
      "type": "land",
      "borders": ["B_1_2", "B_2_3", "B_3_4", "B_1_4"],
      "center": [0.75, 0.5]
    }
  }
}
```

**Benefits**:
1. Shared border (B_1_4) stored exactly once
2. No vertex duplication (vertex 1 and 4 shared)
3. Adjacency explicit: C1 and C2 both reference B_1_4
4. Changing a border only updates one border object
5. Borders provide an abstraction layer between faces and edges

## Implementation Details

### Vertex Deduplication

Vertices are deduplicated by rounding coordinates to 9 decimal places:

```python
def _round_coords(self, coords):
    return (round(coords[0], 9), round(coords[1], 9))
```

This ensures that vertices that are "close enough" are treated as identical.

### Edge Creation

Edges use canonical IDs based on vertex IDs:

```python
def _create_edge_id(self, v1, v2):
    min_v = min(v1, v2)
    max_v = max(v1, v2)
    return f"E_{min_v}_{max_v}"
```

This ensures that edge A→B has the same ID as edge B→A.

### Face-Edge Assignment

When converting cells to topology:
1. First face to reference an edge sets `left_face`
2. Second face to reference the same edge sets `right_face`
3. Map boundary edges have only `left_face` set

### Edge Type Classification

After all faces are processed, edges are classified:

```python
if edge.right_face is None:
    edge.type = "map-edge"
elif left_face.type != right_face.type:
    edge.type = "coast"
else:
    edge.type = left_face.type  # "land" or "sea"
```

## Usage Examples

### Deriving Adjacency

The preferred way to derive adjacency is through borders:

```python
from topology import get_adjacency_from_borders, get_adjacency_from_topology

# Preferred: Use borders (works correctly with subdivided edges)
adjacency = get_adjacency_from_borders(borders)
# Returns: {"C1": ["C2"], "C2": ["C1"]}

# Alternative: get_adjacency_from_topology uses borders when available, falls back to edges
adjacency = get_adjacency_from_topology(edges, borders)
```

### Finding Coastlines

```python
# Find coastal borders (preferred)
coastal_borders = [
    border_id for border_id, border in borders.items()
    if border.get("type") == "coast"
]

# Or find coastal edges
coastlines = [
    edge_id for edge_id, edge in edges.items()
    if edge.get("type") == "coast"
]
```

### Counting Neighbors

```python
def count_neighbors(face_id, edges):
    count = 0
    for edge in edges.values():
        if face_id in [edge.get("left_face"), edge.get("right_face")]:
            if edge.get("right_face") is not None:  # Not a map boundary
                count += 1
    return count
```

## Migration Path

### Phases 1-3: Topology Generated

All phases now include topology in their output:
- Phase 1: Base topology from Voronoi diagram
- Phase 2: Updated with terrain types, coastlines identified
- Phase 3: Updated with province designations

### Backward Compatibility

Legacy cell format is maintained alongside topology:
- `cells` key contains original cell-centric data
- `topology` key contains new topological data
- Existing code using `cells` continues to work

### Future Phases

Later phases (4-7) can be updated to use topology:
- Region merging can preserve topology
- Adjacency checks can use `get_adjacency_from_topology()`
- Geometry operations can manipulate edges directly

## Validation

### Integration Test Results

```
✓ Phase 1: 102 edges generated from 30 cells
✓ Phase 2: 102 edges maintained, 20 coastlines identified
✓ Phase 3: 102 edges maintained, provinces assigned
✓ All adjacencies match between topology and legacy format
✓ All edges reference valid faces
✓ All faces reference valid edges
✓ No duplicate vertices found
```

### Performance Impact

- Vertex deduplication: O(V) where V is number of unique vertices
- Edge creation: O(E) where E is number of edges
- Adjacency derivation: O(E) instead of O(F²) where F is number of faces
- **Overall**: Slightly more memory but much faster adjacency checks

### Memory Comparison

For a map with 100 cells averaging 6 vertices each:

**Before**:
- 100 cells × 6 vertices × 2 coords = 1200 coordinate pairs stored

**After**:
- ~200 unique vertices (shared) × 2 coords = 400 coordinate pairs stored
- ~300 edges × 4 references = 1200 references
- ~300 borders (grouping edges by face adjacency)
- **Total**: Similar memory, but with explicit topology and the border abstraction layer

## Visualizations

### Topology-Based Rendering

The new `visualize_topology()` method renders directly from edges:

- **Land borders**: Dark green, medium width
- **Coastlines**: Orange, thick width  
- **Sea borders**: Light blue, thin width
- **Map boundaries**: Gray, extra thick

This demonstrates that topology correctly preserves geometry while adding semantic information.

## Future Enhancements

1. **Edge-Preserving Region Merging**: When merging regions, update face references in edges rather than regenerating topology

2. **Half-Edge Structure**: For more complex operations (e.g., splitting territories), upgrade to a half-edge data structure

3. **Incremental Updates**: Add methods to add/remove/split edges without full regeneration

4. **Territory Splitting**: Use topology to split territories along existing edges:
   ```python
   def split_face(face_id, split_edge_ids):
       # Create new face
       # Reassign edges to new face
       # Create new edge connecting split points
   ```

5. **Border Smoothing**: Manipulate vertex positions while preserving topology

## Conclusion

The Face-Edge-Vertex topology refactoring successfully:
- ✅ Eliminates data redundancy
- ✅ Makes adjacency explicit and reliable
- ✅ Enables automatic feature detection (coastlines)
- ✅ Sets foundation for advanced geometry operations
- ✅ Maintains backward compatibility
- ✅ Passes all tests and security scans

The topology is now the authoritative source for spatial relationships in the map generation pipeline.
