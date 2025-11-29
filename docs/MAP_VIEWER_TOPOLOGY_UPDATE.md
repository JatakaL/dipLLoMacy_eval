# Map Viewer Topology Support

## Overview

The map viewer applications (`map_viewer.py` and `map_viewer_cli.py`) have been updated to support the new Face-Edge-Vertex topology data structure while maintaining full backward compatibility with legacy cell-centric format.

## Changes Made

### 1. Topology Data Loading

Both viewers now load the `topology` field from JSON files:

```python
self.topology = self.data.get('topology', None)
```

### 2. Topology-Based Visualization

When topology data is present, the viewers now render using the edge-based approach:

**Features:**
- **Face fill colors** - Territories filled with terrain-appropriate colors (land=green, sea=blue)
- **Edge type styling** - Different colors and widths for different edge types:
  - **Land borders** (dark green, medium width): Borders between land territories
  - **Coastlines** (orange, thick): Borders between land and sea
  - **Sea borders** (light blue, thin): Borders between sea territories  
  - **Map boundaries** (dark gray, extra thick): Outer edges of the map

- **Legend** - Automatic legend showing edge types
- **Labels** - Optional cell ID labels for small maps (Phase 1)

### 3. Backward Compatibility

If `topology` is not present in the JSON, the viewers automatically fall back to legacy polygon rendering from cell vertices. This ensures:
- Old maps without topology continue to work
- Gradual migration path for existing datasets
- No breaking changes to existing workflows

## Usage Examples

### CLI Viewer

```bash
# View a map with topology (phases 1-3+)
python map_viewer_cli.py phase2_terrain_output.json

# View legacy map without topology (still works)
python map_viewer_cli.py old_map.json

# Batch process directory
python map_viewer_cli.py --directory map_output/
```

### GUI Viewer

```bash
# Launch with topology-enabled map
python map_viewer.py phase2_terrain_output.json

# Open multiple maps (mix of topology and legacy)
python map_viewer.py phase1.json phase2.json old_legacy_map.json

# Launch and use File > Open Directory
python map_viewer.py
```

## Visual Differences

### With Topology (New)
- Edges drawn with type-specific styling
- Coastlines clearly highlighted in orange
- Map boundaries emphasized with thick borders
- Consistent edge representation across all adjacent territories
- Legend showing edge classification

### Without Topology (Legacy)
- Simple polygon outlines
- All borders same style
- Less visual distinction between edge types
- Backward compatible appearance

## Technical Details

### Topology Rendering Implementation

The topology visualization follows these steps:

1. **Load topology data** - Extract vertices, edges, and faces
2. **Create vertex lookup** - Map vertex IDs to coordinates
3. **Render faces** - Fill territories using legacy cell vertices (for now)
4. **Render edges** - Draw edges with type-based styling
5. **Add labels** - Optionally show cell/face IDs
6. **Add legend** - Show edge type classification

### Edge Type Classification

Edge types are determined by adjacent face types:
- `land`: Both adjacent faces are land
- `sea`: Both adjacent faces are sea
- `coast`: One land face, one sea face
- `map-edge`: Only one adjacent face (boundary)

### Performance

Topology rendering has similar performance to legacy rendering:
- Small maps (<50 cells): Instant
- Medium maps (50-150 cells): <1 second
- Large maps (150+ cells): 1-3 seconds

## Benefits

1. **Visual Clarity**: Edge type styling makes map features immediately recognizable
2. **Correctness**: Topology guarantees consistent edge representation
3. **Flexibility**: Can render from either topology or legacy format
4. **Future-Ready**: Foundation for advanced features (edge editing, topology manipulation)
5. **Backward Compatible**: No breaking changes to existing workflows

## Phase Support

| Phase | Topology Available | Rendering Mode |
|-------|-------------------|----------------|
| Phase 1 | ✓ (after update) | Topology with labels |
| Phase 2 | ✓ (after update) | Topology with edge types |
| Phase 3 | ✓ (after update) | Topology with edge types |
| Phase 4+ | Planned | Legacy (will be updated) |
| Legacy maps | ✗ | Legacy polygons |

## Testing

The map viewer updates have been tested with:
- ✓ Phase 1 output with topology
- ✓ Phase 2 output with topology (land/sea/coastlines)
- ✓ Legacy maps without topology
- ✓ Small maps (25 cells)
- ✓ Edge type classification and styling
- ✓ Legend generation

## Future Enhancements

Potential improvements:
1. Interactive edge highlighting on hover
2. Edge-based region selection
3. Topology editing capabilities
4. Export to different formats (SVG with topology metadata)
5. 3D visualization using topology structure
