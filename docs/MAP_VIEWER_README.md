# Map Viewer for Diplomacy Map Generator

This directory contains two map viewer applications that can visualize JSON outputs from any phase of the map generation pipeline.

## Overview

The map generation system produces JSON files at each of 7 phases. These viewers can load and display any of these files, automatically detecting the phase and rendering appropriately.

### Supported Phases

1. **Phase 1: Mesh Generation** - Voronoi cells with center points
2. **Phase 2: Terrain Assignment** - Land (green) vs Sea (blue)
3. **Phase 3: Province Definition** - Coastlines, oceans, impassable zones
4. **Phase 4: Kingdom Generation** - Player territories (colored by power)
5. **Phase 5: Supply Centers** - Supply center markers (gold circles)
6. **Phase 6: Graph Optimization** - Same as Phase 5 with analysis data
7. **Phase 7: Final Map** - Complete map with names and all features

## Map Viewer CLI (Recommended for Headless/Batch Processing)

A command-line tool that renders JSON files to PNG images.

### Usage

```bash
# Render a single file (auto-generates output.png)
python map_viewer_cli.py path/to/map.json

# Render with custom output path
python map_viewer_cli.py input.json output.png

# Render all JSON files in a directory
python map_viewer_cli.py --directory output/

# High-resolution rendering
python map_viewer_cli.py input.json output.png --dpi 300
```

### Examples

```bash
# Generate a map and visualize all phases
cd map_gen/phases
python orchestrator.py --output-dir ../../test_output
cd ../..
python map_viewer_cli.py --directory test_output/

# Quick visualization of final map
python map_viewer_cli.py test_output/final_map.json
```

### Output

PNG images are saved with the same name as the input JSON file. Each image includes:
- Phase name in title
- Statistics (for phases 4+)
- Legend for power colors (phases 4+)
- Province names (phase 7)
- Supply center markers (phases 5+)

## Map Viewer GUI (Interactive Application)

An interactive desktop application with tabbed interface for viewing multiple maps.

### Requirements

- Python 3.7+
- tkinter (usually included with Python)
- For Ubuntu/Debian: `sudo apt-get install python3-tk`

### Usage

```bash
# Launch the GUI
python map_viewer.py

# Or load files directly
python map_viewer.py file1.json file2.json file3.json
```

### Features

- **Tabbed Interface**: Load multiple JSON files as separate tabs
- **Auto-Detection**: Automatically detects phase from JSON metadata or filename
- **Interactive Controls**: Pan, zoom, and explore maps
- **Keyboard Shortcuts**:
  - `Ctrl+O`: Open file(s)
  - `Ctrl+D`: Open directory
  - `Ctrl+W`: Close current tab
  - `F5`: Refresh current tab
  - `Ctrl+Q`: Quit

### Menu Options

- **File Menu**:
  - Open File(s): Load one or more JSON files
  - Open Directory: Load all JSON files from a folder
  - Close Tab / Close All: Manage open tabs
  
- **View Menu**:
  - Refresh: Reload current visualization
  - Zoom to Fit: Reset zoom level

## Visualization Features

### Phase-Specific Rendering

- **Phase 1**: Gray cells with black borders, red center points, cell IDs
- **Phase 2**: Green land cells, blue sea cells
- **Phase 3**: Yellow coastal cells, gray impassable zones
- **Phase 4-7**: 
  - Power territories colored distinctly
  - Gold circles for supply centers
  - Province names (phase 7)
  - Power legend

### Colors

- **Terrain**:
  - Land: Light green (#C5E0B4)
  - Sea: Light blue (#BDD7EE)
  - Coastal: Yellow (#FFE699)
  - Impassable: Gray (#A6A6A6)

- **Powers**: Uses matplotlib's TABLEAU_COLORS palette
  - Power1: Blue
  - Power2: Orange
  - Power3: Green
  - Power4: Red
  - Power5: Purple
  - Power6: Brown
  - Power7: Pink

- **Supply Centers**: Gold markers with black outline

## Installation

### Quick Setup

```bash
# Install dependencies
pip install numpy scipy shapely scikit-learn matplotlib

# For GUI version, install tkinter
sudo apt-get install python3-tk  # Ubuntu/Debian
# or
brew install python-tk  # macOS

# Make executable (optional)
chmod +x map_viewer.py map_viewer_cli.py
```

### Virtual Environment (Recommended)

```bash
python3 -m venv map_viewer_env
source map_viewer_env/bin/activate
pip install numpy scipy shapely scikit-learn matplotlib
```

## Examples

### Example 1: Generate and Visualize

```bash
# Generate a map
cd map_gen/phases
python orchestrator.py --num-cells 80 --output-dir my_map

# Visualize all phases
cd ../..
python map_viewer_cli.py --directory map_gen/phases/my_map/
```

### Example 2: Compare Different Seeds

```bash
# Generate maps with different seeds
cd map_gen/phases
python orchestrator.py --seed 42 --output-dir seed42
python orchestrator.py --seed 123 --output-dir seed123
python orchestrator.py --seed 999 --output-dir seed999

# View them all in the GUI
cd ../..
python map_viewer.py \
  map_gen/phases/seed42/final_map.json \
  map_gen/phases/seed123/final_map.json \
  map_gen/phases/seed999/final_map.json
```

### Example 3: High-Resolution Export

```bash
# Generate publication-quality images
python map_viewer_cli.py \
  output/final_map.json \
  final_map_hires.png \
  --dpi 300
```

### Example 4: Debug a Specific Phase

```bash
# Generate phases individually
cd map_gen/phases
python phase1_mesh.py --num-cells 100 --output debug_mesh.json
python phase2_terrain.py --input debug_mesh.json --threshold 0.3 --output debug_terrain_v1.json
python phase2_terrain.py --input debug_mesh.json --threshold 0.2 --output debug_terrain_v2.json

# Compare terrain thresholds
cd ../..
python map_viewer.py \
  map_gen/phases/debug_terrain_v1.json \
  map_gen/phases/debug_terrain_v2.json
```

## Troubleshooting

### "No module named 'tkinter'"

Install the tkinter package for your system:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# macOS
brew install python-tk
```

Alternatively, use the CLI version which doesn't require tkinter.

### "Cannot connect to X server"

You're in a headless environment. Use the CLI version:
```bash
python map_viewer_cli.py --directory output/
```

### Images look pixelated

Increase the DPI:
```bash
python map_viewer_cli.py input.json output.png --dpi 300
```

### Too many labels overlap

The viewers automatically adjust label density based on the number of cells. For very detailed maps (>100 cells), labels are hidden to prevent clutter. To see all details, use the GUI version and zoom in.

## Technical Details

### Phase Detection

The viewer automatically detects the phase using:
1. `metadata.phases_completed` field (most reliable)
2. Filename pattern matching (phase1, phase2, etc.)
3. Data content inspection (presence of names, powers, terrain, etc.)

### JSON Structure Expected

All phases should have:
```json
{
  "config": { /* configuration parameters */ },
  "cells": {
    "C1": {
      "id": "C1",
      "center": [x, y],
      "vertices": [[x1, y1], [x2, y2], ...],
      "type": "land|sea|impassable",  // Phase 2+
      "owner": "Power1",               // Phase 4+
      "is_supply_center": true,        // Phase 5+
      "name": "Province Name"          // Phase 7
    }
  }
}
```

Optional fields for later phases:
- `metadata`: Version and phase info
- `powers`: Power definitions
- `supply_centers`: Lists of SCs
- `adjacency`: Neighbor relationships
- `analysis`: Quality metrics (Phase 6)

## Contributing

To add new visualization features:

1. Edit `map_viewer_cli.py` (simpler, no GUI complexity)
2. Add phase-specific rendering in the `visualize_map()` function
3. Test with sample data from all phases
4. Update the GUI version (`map_viewer.py`) if needed

## License

Same license as the parent dipLLoMacy_eval project.
