# Map Output Structure Changes

## Summary

This document describes the changes made to the map generation output structure to organize files better and prevent cluttering the git repository.

## What Changed

### 1. Default Output Location
- **Before:** Files saved to `output/` directory within the repository
- **After:** Files saved to `../map_output/` (one level above the git repository)
- **Benefit:** Keeps generated maps separate from the codebase and version control

### 2. Datetime-Stamped Subdirectories
All output files are now organized in datetime-stamped subdirectories using the format `YYYYMMDD_HHMMSS`.

Example structure:
```
map_output/
├── 20251122_143052/
│   ├── phase1_mesh_output_20251122_143052.json
│   ├── phase2_terrain_output_20251122_143052.json
│   ├── ...
│   ├── final_map_20251122_143052.json
│   └── map_summary_20251122_143052.txt
└── 20251122_150321/
    ├── final_map_20251122_150321.json
    └── map_summary_20251122_150321.txt
```

### 3. Datetime-Stamped Filenames
All output files now include a datetime stamp in their filenames.

**Format:** `<basename>_<YYYYMMDD_HHMMSS>.<extension>`

Examples:
- `phase1_mesh_output_20251122_143052.json`
- `final_map_20251122_143052.json`
- `map_summary_20251122_143052.txt`

### 4. Smart Path Management for Different Execution Modes

#### Orchestrator Mode
When running the complete pipeline via `orchestrator.py`:
- Creates a single datetime subdirectory
- All output files use the same datetime stamp
- Example: All files in `map_output/20251122_143052/` have `_20251122_143052` in their names

#### Phase 1 Standalone
When running `phase1_mesh.py` independently:
- Creates a new datetime subdirectory in the base output directory
- Output saved as `<base_dir>/<datetime>/phase1_mesh_output_<datetime>.json`

#### Phase 2-7 Standalone
When running phases 2-7 independently:
- Saves output to the **same directory as the input file**
- Uses a **new datetime** for the filename
- Example: Input from `map_output/20251122_143052/phase1_mesh_output_20251122_143052.json`
- Output saved to `map_output/20251122_143052/phase2_terrain_output_20251122_150515.json`

This allows you to track when each phase was executed while keeping related files together.

## Usage Examples

### Using Orchestrator (Default Output)
```bash
cd map_gen/phases
python orchestrator.py --num-cells 80
# Output: ../map_output/20251122_143052/
```

### Using Orchestrator (Custom Output)
```bash
python orchestrator.py --num-cells 80 --output-dir /custom/path
# Output: /custom/path/20251122_143052/
```

### Running Individual Phases
```bash
# Phase 1: Creates new datetime subdirectory
python phase1_mesh.py --num-cells 50
# Output: ../map_output/20251122_143052/phase1_mesh_output_20251122_143052.json

# Phase 2: Uses same directory as input
python phase2_terrain.py --input ../map_output/20251122_143052/phase1_mesh_output_20251122_143052.json
# Output: ../map_output/20251122_143052/phase2_terrain_output_20251122_143330.json

# Phase 3: Also uses same directory
python phase3_provinces.py --input ../map_output/20251122_143052/phase2_terrain_output_20251122_143330.json
# Output: ../map_output/20251122_143052/phase3_provinces_output_20251122_143445.json
```

### Specifying Custom Paths
You can still specify exact output paths for any phase:
```bash
python phase1_mesh.py --num-cells 50 --output /exact/path/my_mesh.json
python phase2_terrain.py --input /exact/path/my_mesh.json --output /exact/path/my_terrain.json
```

## Implementation Details

### New Module: `output_utils.py`
A new utility module provides helper functions for path management:

- `get_default_output_base()`: Returns the default base output directory
- `create_datetime_subdir()`: Creates a datetime-stamped subdirectory
- `get_datetime_filename()`: Generates filenames with datetime stamps
- `get_output_path_for_phase()`: Smart path resolution based on execution mode

### Modified Files
- `orchestrator.py`: Updated to use datetime subdirectories and filenames
- `phase1_mesh.py`: Creates datetime subdirectories when run standalone
- `phase2_terrain.py` through `phase7_naming.py`: Save to input file's directory
- `example_usage_phased.py`: Updated examples to use new default
- `PHASED_MAP_GENERATION.md`: Updated documentation

## Benefits

1. **Better Organization**: All outputs from a single run are grouped together
2. **No Git Pollution**: Output files stay outside the repository by default
3. **Easy Tracking**: Datetime stamps show when each phase/map was generated
4. **Flexible**: Can still override paths when needed
5. **Automatic**: Works automatically without requiring user configuration
6. **Compatible**: Individual phases can still be chained together easily

## Migration Notes

If you have existing code that uses the old `output/` directory:

1. **For orchestrator**: Change `output_dir="output"` to `output_dir=None` (uses new default)
2. **For custom paths**: Specify your preferred `output_dir` parameter
3. **No breaking changes**: All command-line arguments still work as before

The system is backward-compatible - you can still specify any custom path you want using the `--output` or `--output-dir` flags.
