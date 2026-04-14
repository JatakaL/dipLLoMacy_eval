# Diplomacy Map Generator - Phased System

This directory contains the phased map generation system, where map creation is divided into 7 distinct phases. Each phase can be run independently and produces inspectable JSON output.

## Overview

The map generation follows the algorithm described in the Diplomacy map generation document, structured into logical phases:

1. **Phase 1: Mesh Generation (Voronoi Tesselation)**
2. **Phase 2: Terrain Assignment (Land vs. Sea)**
3. **Phase 3: Province Definition**
4. **Phase 4: Kingdom Generation (Player Starts)**
5. **Phase 5: Supply Center Distribution**
6. **Phase 6: Graph Optimization**
7. **Phase 7: Naming and Visualization**

## Quick Start

### Run Complete Pipeline

The easiest way to generate a map is using the orchestrator:

```bash
cd map_gen/phases
python orchestrator.py
```

This will generate a complete map with default settings and save all outputs to the `output/` directory.

### Custom Configuration

```bash
python orchestrator.py \
  --num-cells 100 \
  --num-powers 7 \
  --num-neutral-scs 15 \
  --land-ratio 0.65 \
  --seed 42 \
  --output-dir my_custom_map
```

### Run Individual Phases

Each phase can be run independently:

```bash
# Phase 1: Generate mesh
python phase1_mesh.py --num-cells 80 --output mesh.json

# Phase 2: Assign terrain
python phase2_terrain.py --input mesh.json --output terrain.json

# Phase 3: Define provinces
python phase3_provinces.py --input terrain.json --output provinces.json

# Phase 4: Generate kingdoms
python phase4_kingdoms.py --input provinces.json --output kingdoms.json

# Phase 5: Place supply centers
python phase5_supply_centers.py --input kingdoms.json --output scs.json

# Phase 6: Optimize graph
python phase6_optimization.py --input scs.json --output optimized.json

# Phase 7: Name and finalize
python phase7_naming.py --input optimized.json --output final_map.json
```

## Phase Details

### Phase 1: Mesh Generation

**Script:** `phase1_mesh.py`

Generates the base mesh structure using Voronoi tesselation.

**Techniques:**
- Poisson disk sampling for point distribution
- Voronoi diagram generation
- Optional Lloyd's relaxation for more uniform cells

**Key Parameters:**
- `--num-cells`: Target number of cells (default: 80)
- `--min-distance`: Minimum distance between points (default: 0.05)
- `--lloyd-iterations`: Number of relaxation iterations (default: 0)

**Output:** `mesh_output.json` containing cell polygons and adjacency

### Phase 2: Terrain Assignment

**Script:** `phase2_terrain.py`

Assigns land or sea to each cell based on procedural noise.

**Techniques:**
- Perlin noise generation
- Radial gradient masking (land in center, sea at edges)
- Single-cell island/lake culling

**Key Parameters:**
- `--threshold`: Land/sea threshold (default: 0.4)
- `--land-ratio`: Target land ratio (default: 0.6)
- `--octaves`: Noise detail level (default: 4)
- `--radial-falloff`: How tightly land clusters in center (default: 0.8)

**Output:** `terrain_output.json` with land/sea assignments

### Phase 3: Province Definition

**Script:** `phase3_provinces.py`

Defines mechanical properties of provinces.

**Techniques:**
- Coastal vs. inland classification
- Ocean grouping (contiguous sea regions)
- Impassable zone creation (e.g. impassable peaks)

**Key Parameters:**
- `--num-impassable-zones`: Number of impassable zones (default: 1)

**Output:** `provinces_output.json` with province classifications

### Phase 4: Kingdom Generation

**Script:** `phase4_kingdoms.py`

Creates balanced starting positions for players.

**Techniques:**
- Equidistant seed placement on coasts
- Simultaneous BFS territory growth
- Contiguity verification

**Key Parameters:**
- `--num-powers`: Number of player powers (default: 7)
- `--territory-size`: Home territory size (default: 3)
- `--max-retries`: Retry attempts for balanced placement (default: 10)

**Output:** `kingdoms_output.json` with player territories

### Phase 5: Supply Center Distribution

**Script:** `phase5_supply_centers.py`

Places supply centers across the map.

**Techniques:**
- All home territories marked as SCs
- Strategic neutral SC placement (equidistant from powers)
- Avoidance of adjacent neutral SCs

**Key Parameters:**
- `--num-neutral-scs`: Number of neutral supply centers (default: 13)

**Output:** `supply_centers_output.json` with SC placements

### Phase 6: Graph Optimization

**Script:** `phase6_optimization.py`

Analyzes and optimizes the map graph for gameplay quality.

**Analysis:**
- Node degree analysis (bottleneck detection)
- Sea connectivity verification
- Triangle density calculation (for support mechanics)
- Corner vs. central power identification
- Belgium factor analysis (contested neutral SCs)

**Output:** `optimized_graph_output.json` with analysis and recommendations

### Phase 7: Naming and Visualization

**Script:** `phase7_naming.py`

Generates names and creates final output.

**Features:**
- Markov-style name generation for provinces
- Adjacency list creation
- Power territory mapping
- Human-readable summary generation

**Output:** 
- `final_map.json`: Complete map data
- `map_summary.txt`: Human-readable summary

## Output Format

Each phase produces a JSON file that can be inspected and modified. The final output (`final_map.json`) contains:

```json
{
  "config": { /* All configuration parameters */ },
  "metadata": { /* Version and generator info */ },
  "cells": { /* All cells with properties */ },
  "adjacency": { /* Graph adjacency list */ },
  "powers": { /* Power territories and info */ },
  "supply_centers": { /* SC locations */ },
  "analysis": { /* Quality metrics */ },
  "recommendations": [ /* Improvement suggestions */ ],
  "statistics": { /* Map statistics */ }
}
```

## Configuration Parameters

### Complete Parameter List

| Parameter | Default | Phase | Description |
|-----------|---------|-------|-------------|
| `num_cells` | 80 | 1 | Target number of Voronoi cells |
| `width` | 1.0 | 1 | Map width |
| `height` | 1.0 | 1 | Map height |
| `min_distance` | 0.05 | 1 | Minimum distance for Poisson sampling |
| `lloyd_iterations` | 0 | 1 | Lloyd relaxation iterations |
| `threshold` | 0.4 | 2 | Land/sea threshold |
| `land_ratio` | 0.6 | 2 | Target land ratio |
| `octaves` | 4 | 2 | Noise octaves |
| `radial_falloff` | 0.8 | 2 | Radial mask falloff |
| `cull_iterations` | 2 | 2 | Island/lake culling iterations |
| `num_impassable_zones` | 1 | 3 | Number of impassable zones |
| `num_powers` | 7 | 4 | Number of player powers |
| `territory_size` | 3 | 4 | Home territory size |
| `max_retries` | 10 | 4 | Max retries for seed placement |
| `num_neutral_scs` | 13 | 5 | Number of neutral supply centers |
| `seed` | 42 | All | Random seed for reproducibility |

## Examples

See `example_usage_phased.py` in the parent directory for complete examples.

### Example 1: Default Map

```bash
python orchestrator.py
```

### Example 2: Large Map

```bash
python orchestrator.py --num-cells 120 --num-neutral-scs 18
```

### Example 3: Small Map for 4 Players

```bash
python orchestrator.py --num-cells 50 --num-powers 4 --num-neutral-scs 8
```

### Example 4: High Detail Map

```bash
python orchestrator.py --num-cells 100 --octaves 6 --radial-falloff 0.7
```

## Debugging and Iteration

The phased approach allows you to:

1. **Inspect intermediate outputs**: Each phase saves JSON that you can examine
2. **Modify and replay**: Edit a phase output and continue from there
3. **Adjust single phases**: Re-run just one phase with different parameters
4. **Compare variations**: Generate multiple versions and compare quality metrics

### Example: Iterating on Terrain

```bash
# Generate mesh once
python phase1_mesh.py --num-cells 80 --output mesh.json

# Try different terrain parameters
python phase2_terrain.py --input mesh.json --threshold 0.35 --output terrain_v1.json
python phase2_terrain.py --input mesh.json --threshold 0.45 --output terrain_v2.json

# Continue with the better version
python phase3_provinces.py --input terrain_v1.json --output provinces.json
# ... continue pipeline
```

## Quality Metrics

Phase 6 provides several quality metrics:

- **Average Degree**: How well connected the graph is (target: 4-6)
- **Triangle Density**: Support for Diplomacy mechanics (target: >30%)
- **Sea Connectivity**: All seas should be connected
- **Power Balance**: Mix of corner and central powers
- **Belgium Factor**: Contested neutral SCs (should have at least 1-2)

## Troubleshooting

### Not Enough Coastal Cells

If Phase 4 fails with "not enough coastal cells":
- Increase `land_ratio` in Phase 2
- Decrease `radial_falloff` for more spread-out land
- Increase `num_cells` in Phase 1

### Disconnected Seas

If Phase 6 reports disconnected seas:
- Decrease `land_ratio` in Phase 2
- Increase `radial_falloff` to push more land to center

### Poor Triangle Density

If triangle density is low:
- Increase `num_cells` in Phase 1 (creates smaller provinces)
- The mesh naturally forms triangles with Voronoi cells

## Contributing

When adding new features:

1. Keep phases independent
2. Document new parameters
3. Update this README
4. Ensure JSON compatibility between phases
