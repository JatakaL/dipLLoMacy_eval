# Phased Map Generation System

This repository now includes a completely refactored map generation system that follows a phased approach, as described in the Diplomacy map generation algorithm document.

## Overview

The new system divides map generation into **7 independent phases**, each producing inspectable JSON output. This allows for:

- **Independent Development**: Work on individual phases without affecting others
- **Debugging**: Inspect intermediate outputs to understand what's happening
- **Experimentation**: Try different parameters for specific phases
- **Reproducibility**: Use seeds for consistent results

## Quick Start

### Generate a Map with Default Settings

```bash
cd map_gen/phases
source ../../env-dipllm/bin/activate  # Activate the Python environment
python orchestrator.py
```

This creates a map with:
- 80 Voronoi cells
- 7 player powers
- ~30 land provinces, ~50 sea regions
- 21 home supply centers (3 per power)
- 13 neutral supply centers

**Output location:** `../map_output/<datetime>/` (one level above the repository)
- All output files are saved in a datetime-stamped subdirectory
- Filenames include the datetime stamp (e.g., `final_map_20231122_153045.json`)

### Run with Custom Parameters

```bash
python orchestrator.py \
  --num-cells 100 \
  --num-powers 7 \
  --num-neutral-scs 15 \
  --land-ratio 0.65 \
  --seed 12345 \
  --output-dir /custom/path
```

The `--output-dir` specifies the base directory. A datetime subdirectory will be created inside it.

### Run from Python

```python
from map_gen.phases.orchestrator import run_full_pipeline

config = {
    "num_cells": 80,
    "num_powers": 7,
    "land_ratio": 0.6,
    "seed": 42
}

# Uses default output directory (../map_output)
output = run_full_pipeline(config)

# Or specify a custom base directory
output = run_full_pipeline(config, output_dir="/custom/path")
```

## The 7 Phases

### Phase 1: Mesh Generation (Voronoi Tesselation)

Creates the base mesh structure using Voronoi diagrams.

**Algorithm:**
1. Poisson disk sampling for point distribution (prevents points too close together)
2. Voronoi diagram generation
3. Optional Lloyd's relaxation for more uniform cells

**Key Parameters:**
- `--num-cells`: Target number of cells (default: 80)
- `--min-distance`: Minimum distance between points (default: 0.05)

**Output:** `phase1_mesh_output.json`

### Phase 2: Terrain Assignment (Land vs. Sea)

Assigns land or sea to each cell using procedural noise and ensures ocean connectivity.

**Algorithm:**
1. Generate Perlin noise map for organic terrain
2. Apply radial gradient mask (forces land to center, sea to edges)
3. Threshold to assign land/sea
4. Cull single-cell islands and lakes
5. **Check and fix ocean connectivity** (converts land bridges to sea if needed)

**Key Parameters:**
- `--threshold`: Land/sea cutoff (default: 0.25)
- `--land-ratio`: Target land percentage (default: 0.6)
- `--radial-falloff`: How tightly land clusters (default: 0.8)

**Important:** Ocean connectivity is fixed in Phase 2 (before any supply centers or powers are assigned), preventing Phase 6 from breaking the map by removing important cells. The ocean connectivity fix actually changes cell types (land to sea), which is reflected in visualizations.

**Output:** `phase2_terrain_output.json`

### Phase 3: Province Definition

Classifies provinces and identifies special features.

**Algorithm:**
1. Identify coastlines (land touching water)
2. Group contiguous water into ocean regions
3. Create impassable zones (Switzerland-style neutrals)

**Key Parameters:**
- `--num-impassable-zones`: Number of impassable regions (default: 1)

**Output:** `phase3_provinces_output.json`

### Phase 4: Kingdom Generation (Player Starts)

Creates balanced starting positions for players.

**Algorithm:**
1. Select equidistant coastal cells as seeds
2. Simultaneous BFS to grow territories (3 provinces each)
3. Verify contiguity of territories
4. Retry if necessary for better balance

**Key Parameters:**
- `--num-powers`: Number of player powers (default: 7)
- `--territory-size`: Home territory size (default: 3)

**Output:** `phase4_kingdoms_output.json`

### Phase 5: Supply Center Distribution

Places supply centers strategically across the map.

**Algorithm:**
1. Mark all home territories as supply centers
2. Find neutral candidates (land not owned, preferably coastal)
3. Select neutral SCs equidistant from multiple powers
4. Avoid placing neutral SCs adjacent to each other

**Key Parameters:**
- `--num-neutral-scs`: Number of neutral supply centers (default: 13)

**Output:** `phase5_supply_centers_output.json`

### Phase 6: Graph Analysis and Validation

Analyzes map quality for Diplomacy gameplay and validates map integrity. **This phase is analysis-only and does NOT modify the map.**

**Metrics:**
- **Node Degree**: Average connectivity (target: 4-6)
- **Triangle Density**: Support for complex diplomacy (target: >30%)
- **Sea Connectivity**: Validates that all seas are connected (fixed in Phase 2)
- **Power Balance**: Mix of corner and central powers
- **Belgium Factor**: Contested neutral SCs (should have 1-2)
- **Map Integrity**: Validates that all powers have correct number of SCs

**Important:** Phase 6 no longer modifies the map to prevent breaking supply centers and power territories. Ocean connectivity is now fixed in Phase 2 before any important assignments are made.

**Output:** `phase6_analysis_output.json` with analysis and recommendations

### Phase 7: Naming and Visualization

Generates names and creates final output.

**Features:**
- Markov-style province name generation
- Sea region naming
- Complete adjacency list
- Human-readable summary

**Output:** 
- `final_map.json`: Complete map data
- `map_summary.txt`: Human-readable summary

## Output Format

Each phase produces a JSON file that includes:
- Configuration from all previous phases
- Cell data with updated properties
- Statistics about the current state
- Additional phase-specific data

### Final Map JSON Structure

```json
{
  "config": { /* All configuration parameters */ },
  "metadata": {
    "version": "1.0",
    "generator": "Diplomacy Map Generator - Phased Pipeline",
    "phases_completed": 7
  },
  "cells": {
    "C1": {
      "id": "C1",
      "center": [0.5, 0.5],
      "vertices": [[x1, y1], [x2, y2], ...],
      "type": "land|sea|impassable",
      "name": "Ardonia",
      "coastal": true|false,
      "is_supply_center": true|false,
      "owner": "Power1|null",
      "neighbors": ["C2", "C3", ...]
    },
    ...
  },
  "adjacency": {
    "Ardonia": ["Belforge", "Corellis", ...],
    ...
  },
  "powers": {
    "Power1": {
      "home_territories": [...],
      "seed": "C23",
      "size": 3
    },
    ...
  },
  "supply_centers": {
    "home": [...],
    "neutral": [...]
  },
  "analysis": { /* Quality metrics */ },
  "statistics": { /* Map statistics */ }
}
```

## Running Individual Phases

Each phase can be run independently for debugging or experimentation.

### Automatic Output Path Management

By default, phases use datetime-stamped paths:

```bash
cd map_gen/phases

# Phase 1: Generate mesh (creates new datetime subdirectory)
python phase1_mesh.py --num-cells 100
# Output: ../map_output/20231122_153045/phase1_mesh_output_20231122_153045.json

# Phase 2-7: Use same directory as input, with new datetime in filename
python phase2_terrain.py --input ../map_output/20231122_153045/phase1_mesh_output_20231122_153045.json
# Output: ../map_output/20231122_153045/phase2_terrain_output_20231122_153512.json
```

**Key behaviors:**
- **Phase 1 standalone:** Creates a new datetime subdirectory in `../map_output/`
- **Phase 2+ standalone:** Saves output in the same directory as the input file, with a new datetime in the filename
- **Orchestrator:** All files use the same datetime and are saved together

### Custom Output Paths

You can also specify custom paths:

```bash
# Phase 1: Generate mesh
python phase1_mesh.py --num-cells 100 --output /custom/path/mesh.json

# Phase 2: Assign terrain
python phase2_terrain.py --input /custom/path/mesh.json --threshold 0.3 --output /custom/path/terrain.json

# And so on for remaining phases...
```

## Configuration Parameters

### Complete Reference

| Parameter | Default | Phase | Description |
|-----------|---------|-------|-------------|
| `num_cells` | 80 | 1 | Target number of Voronoi cells |
| `width` | 1.0 | 1 | Map width in normalized coordinates |
| `height` | 1.0 | 1 | Map height in normalized coordinates |
| `min_distance` | 0.05 | 1 | Minimum distance for Poisson sampling |
| `lloyd_iterations` | 0 | 1 | Lloyd relaxation iterations (0 = disabled) |
| `threshold` | 0.25 | 2 | Land/sea threshold (lower = more land) |
| `land_ratio` | 0.6 | 2 | Target land ratio (0.0-1.0) |
| `octaves` | 4 | 2 | Perlin noise octaves (detail level) |
| `radial_falloff` | 0.8 | 2 | Radial mask falloff (higher = tighter clustering) |
| `cull_iterations` | 2 | 2 | Island/lake culling iterations |
| `num_impassable_zones` | 1 | 3 | Number of impassable zones |
| `num_powers` | 7 | 4 | Number of player powers |
| `territory_size` | 3 | 4 | Home territory size (provinces per power) |
| `max_retries` | 10 | 4 | Max retries for seed placement |
| `num_neutral_scs` | 13 | 5 | Number of neutral supply centers |
| `seed` | 42 | All | Random seed for reproducibility |

## Example Configurations

### Large Detailed Map

```bash
python orchestrator.py \
  --num-cells 120 \
  --num-powers 7 \
  --num-neutral-scs 18 \
  --octaves 6 \
  --land-ratio 0.65 \
  --output-dir large_map
```

### Small 4-Player Map

```bash
python orchestrator.py \
  --num-cells 50 \
  --num-powers 4 \
  --num-neutral-scs 8 \
  --territory-size 3 \
  --output-dir small_4p
```

### High Land Ratio (Continental)

```bash
python orchestrator.py \
  --num-cells 80 \
  --land-ratio 0.8 \
  --threshold 0.2 \
  --radial-falloff 0.6 \
  --output-dir continental
```

### Island Chains Map

```bash
python orchestrator.py \
  --num-cells 100 \
  --land-ratio 0.4 \
  --threshold 0.35 \
  --radial-falloff 1.0 \
  --cull-iterations 0 \
  --output-dir islands
```

## Quality Metrics Explained

### Average Degree
- **What it is**: Average number of neighbors per province
- **Target**: 4-6
- **Too low**: Sparse, linear paths (like Risk)
- **Too high**: Too densely connected, overwhelming

### Triangle Density
- **What it is**: Percentage of neighbor pairs that are also connected
- **Target**: >30%
- **Importance**: Enables the "support" mechanic in Diplomacy
- **Example**: If A touches B and C, can B support A into C?

### Power Classifications
- **Corner Powers**: 0-2 neighbors, easier to defend
- **Central Powers**: 5+ neighbors, high risk/reward
- **Target**: Mix of both types for balance

### Belgium Factor
- **What it is**: Neutral SCs accessible by 3+ powers
- **Target**: At least 1-2
- **Importance**: Forces early diplomatic conversation

## Troubleshooting

### Problem: Not enough land

**Solution:**
- Lower `--threshold` (try 0.2)
- Increase `--land-ratio` (try 0.7)
- Lower `--radial-falloff` (try 0.6)

### Problem: Not enough coastal cells

**Solution:**
- Increase `--land-ratio`
- Lower `--radial-falloff` (spreads land more)
- Reduce `--cull-iterations` (keeps some islands)

### Problem: Disconnected seas

**Solution:**
- Lower `--land-ratio`
- Increase `--radial-falloff` (more compact land)
- Check Phase 6 analysis for details

### Problem: Poor triangle density

**Solution:**
- Increase `--num-cells` (creates more, smaller provinces)
- Voronoi naturally creates triangles, so more cells = better

## Dependencies

Required Python packages (installed in `env-dipllm`):
- `numpy` - Numerical computations
- `scipy` - Voronoi diagram generation
- `shapely` - Geometric operations
- `scikit-learn` - Clustering algorithms

Install with:
```bash
pip install numpy scipy shapely scikit-learn
```

## File Structure

```
dipLLoMacy_eval/
├── map_gen/
│   └── phases/
│       ├── __init__.py
│       ├── README.md                  # Detailed phase documentation
│       ├── orchestrator.py            # Main pipeline runner
│       ├── phase1_mesh.py            # Voronoi generation
│       ├── phase2_terrain.py         # Land/sea assignment
│       ├── phase3_provinces.py       # Province classification
│       ├── phase4_kingdoms.py        # Player territories
│       ├── phase5_supply_centers.py  # SC placement
│       ├── phase6_optimization.py    # Quality analysis
│       └── phase7_naming.py          # Naming and finalization
├── example_usage_phased.py           # Usage examples
├── PHASED_MAP_GENERATION.md         # This file
└── env-dipllm/                       # Python virtual environment
```

## Design Principles

1. **Independence**: Each phase can run separately
2. **Inspectability**: JSON output at every stage
3. **Reproducibility**: Seed-based random generation
4. **Configurability**: All parameters exposed
5. **Quality First**: Analysis and recommendations built-in

## Next Steps

### For Users
1. Run `python orchestrator.py` to generate your first map
2. Experiment with different parameters
3. Inspect intermediate JSON files to understand the process
4. Use Phase 6 recommendations to improve maps

### For Developers
1. Each phase is independent - improve one without breaking others
2. Add new features to specific phases
3. Create visualizations using the JSON data
4. Implement the recommendations from Phase 6 (node splitting/merging)

## Credits

Based on the Diplomacy map generation algorithm document, implementing:
- Voronoi tesselation for organic province shapes
- Perlin noise for natural terrain
- Graph analysis for gameplay quality
- Strategic SC placement for balanced gameplay
