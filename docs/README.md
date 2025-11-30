# dipLLoMacy_eval Documentation

Welcome to the dipLLoMacy_eval documentation. This directory contains comprehensive documentation for the Diplomacy map generation and evaluation system.

## Getting Started

For new developers, we recommend starting with the **Phased Map Generation** guide to understand the core map generation pipeline.

## Documentation Index

### Core System Documentation

| Document | Description |
|----------|-------------|
| [Phased Map Generation](PHASED_MAP_GENERATION.md) | Complete guide to the 7-phase map generation system, including quick start, configuration parameters, and examples |
| [Refactoring Summary](REFACTORING_SUMMARY.md) | Overview of the architecture refactoring from monolithic to phased pipeline |
| [Output Structure Changes](OUTPUT_STRUCTURE_CHANGES.md) | Details on how map outputs are organized with datetime-stamped directories |

### Topology System

| Document | Description |
|----------|-------------|
| [Topology Structure](TOPOLOGY_STRUCTURE.md) | Face-Edge-Vertex topological data structure specification, including the border abstraction layer between faces and edges |
| [Topology Migration Summary](TOPOLOGY_MIGRATION_SUMMARY.md) | Summary of the migration from cell-centric to topological data structure |
| [Merge/Split Implementation](MERGE_SPLIT_IMPLEMENTATION.md) | Face merging and splitting functionality for topology manipulation |

### Map Viewer

| Document | Description |
|----------|-------------|
| [Map Viewer README](MAP_VIEWER_README.md) | User guide for the GUI and CLI map viewer applications |
| [Map Viewer Topology Update](MAP_VIEWER_TOPOLOGY_UPDATE.md) | Topology support additions to the map viewers |
| [Viewer Implementation Summary](VIEWER_IMPLEMENTATION_SUMMARY.md) | Technical details of the map viewer implementation |

### Project Roadmap

| Document | Description |
|----------|-------------|
| [Map Completion Plan](PLAN_MAP_COMPLETION.md) | Status of map generation and remaining optional enhancements |
| [Game Elements Plan](PLAN_GAME_ELEMENTS.md) | Plan for implementing Diplomacy game mechanics (units, orders, movement, combat) |
| [LLM Integration Plan](PLAN_LLM_INTEGRATION.md) | Plan for hooking up LLMs for game evaluation and benchmarking |

## Additional Resources

- **Phase-specific documentation**: See [map_gen/phases/README.md](../map_gen/phases/README.md) for detailed information about each generation phase
- **Example usage**: See [example_usage_phased.py](../example_usage_phased.py) for code examples
- **Map viewer examples**: See [example_map_viewer.py](../example_map_viewer.py) for visualization examples

## Quick Links

### Generate a Map
```bash
cd map_gen/phases
python orchestrator.py
```

### View a Map
```bash
python map_viewer_cli.py path/to/map.json
# or for GUI:
python map_viewer.py path/to/map.json
```

## Contributing

When adding new documentation:
1. Place the document in this `docs/` directory
2. Update this index with a link and description
3. Follow the existing naming conventions (UPPERCASE_WITH_UNDERSCORES.md)
