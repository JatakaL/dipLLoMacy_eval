#!/usr/bin/env python3
"""
Example Usage - Phased Map Generation

This script demonstrates how to use the new phased map generation system.
You can run the entire pipeline at once or run individual phases.
"""

import sys
import os

# Add the map_gen/phases directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'map_gen', 'phases'))

from orchestrator import run_full_pipeline


def example_full_pipeline():
    """Example: Run the complete pipeline with default settings."""
    print("Example 1: Full Pipeline with Default Settings")
    print("-" * 60)
    
    config = {
        "num_cells": 80,
        "num_powers": 7,
        "territory_size": 3,
        "num_neutral_scs": 13,
        "land_ratio": 0.6,
        "seed": 42
    }
    
    output = run_full_pipeline(
        config,
        output_dir=None,  # Uses default: ../map_output
        save_intermediate=True
    )
    
    print("\nMap generated successfully!")
    print(f"Total faces: {output['statistics']['total_faces']}")
    print(f"Powers: {output['statistics']['num_powers']}")
    print(f"Supply centers: {output['statistics']['total_supply_centers']}")


def example_custom_pipeline():
    """Example: Run pipeline with custom settings for a larger map."""
    print("\n\nExample 2: Custom Pipeline for Larger Map")
    print("-" * 60)
    
    config = {
        "num_cells": 120,           # More cells for a larger map
        "num_powers": 7,             # Standard 7 powers
        "territory_size": 3,         # 3 home provinces each
        "num_neutral_scs": 18,       # More neutral SCs for larger map
        "land_ratio": 0.65,          # Slightly more land
        "threshold": 0.38,           # Adjust terrain threshold
        "octaves": 5,                # More detailed terrain
        "radial_falloff": 0.75,      # Tighter land clustering
        "num_impassable_zones": 2,   # More impassable zones
        "seed": 12345                # Different seed
    }
    
    output = run_full_pipeline(
        config,
        output_dir=None,  # Uses default: ../map_output
        save_intermediate=True
    )
    
    print("\nLarge map generated successfully!")
    print(f"Total faces: {output['statistics']['total_faces']}")
    print(f"Powers: {output['statistics']['num_powers']}")
    print(f"Supply centers: {output['statistics']['total_supply_centers']}")


def example_small_game():
    """Example: Generate a smaller map for fewer players."""
    print("\n\nExample 3: Small Map for 4 Players")
    print("-" * 60)
    
    config = {
        "num_cells": 50,             # Fewer cells
        "num_powers": 4,             # Only 4 powers
        "territory_size": 3,         # 3 home provinces each
        "num_neutral_scs": 8,        # Fewer neutral SCs
        "land_ratio": 0.7,           # More land (less sea)
        "seed": 999
    }
    
    output = run_full_pipeline(
        config,
        output_dir=None,  # Uses default: ../map_output
        save_intermediate=False  # Don't save intermediate files for quick generation
    )
    
    print("\nSmall map generated successfully!")
    print(f"Total faces: {output['statistics']['total_faces']}")
    print(f"Powers: {output['statistics']['num_powers']}")
    print(f"Supply centers: {output['statistics']['total_supply_centers']}")


def example_run_individual_phases():
    """Example: Run individual phases for debugging or customization."""
    print("\n\nExample 4: Running Individual Phases")
    print("-" * 60)
    print("(This example shows how to run phases individually)")
    print("See the phase scripts (phase1_mesh.py, etc.) for details.")
    
    # You can run individual phases like this:
    # python map_gen/phases/phase1_mesh.py --num-cells 100 --output my_mesh.json
    # python map_gen/phases/phase2_terrain.py --input my_mesh.json --output my_terrain.json
    # ... and so on
    
    print("\nTo run individual phases (auto-generates datetime paths):")
    print("  cd map_gen/phases")
    print("  python phase1_mesh.py --num-cells 100")
    print("    # Creates ../map_output/<datetime>/phase1_mesh_output_<datetime>.json")
    print("  python phase2_terrain.py --input ../map_output/<datetime>/phase1_mesh_output_<datetime>.json")
    print("    # Saves in same directory as input with new datetime in filename")
    print("  ... and so on")
    print("\nOr specify custom output paths:")
    print("  python phase1_mesh.py --num-cells 100 --output /path/to/mesh.json")
    print("  python phase2_terrain.py --input /path/to/mesh.json --output /path/to/terrain.json")


def main():
    """Run all examples."""
    print("=" * 70)
    print(" DIPLOMACY MAP GENERATOR - PHASED SYSTEM EXAMPLES")
    print("=" * 70)
    print()
    
    # Run examples
    try:
        # Example 1: Default pipeline
        example_full_pipeline()
        
        # Example 2: Custom larger map
        # Uncomment to run:
        # example_custom_pipeline()
        
        # Example 3: Small map
        # Uncomment to run:
        # example_small_game()
        
        # Example 4: Individual phases info
        example_run_individual_phases()
        
        print("\n" + "=" * 70)
        print(" ALL EXAMPLES COMPLETED")
        print("=" * 70)
        print("\nCheck '../map_output/' directory for generated maps!")
        print("Each map is in a datetime-stamped subdirectory and includes:")
        print("  - final_map_<datetime>.json: Complete map data")
        print("  - map_summary_<datetime>.txt: Human-readable summary")
        print("  - phase*_output_<datetime>.json: Intermediate outputs (if enabled)")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
