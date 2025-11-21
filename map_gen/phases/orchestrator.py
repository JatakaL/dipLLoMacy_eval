#!/usr/bin/env python3
"""
Orchestrator - Run All Map Generation Phases

This script orchestrates the complete map generation pipeline,
running all 7 phases in sequence and managing intermediate outputs.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Import all phases
from phase1_mesh import run_phase1
from phase2_terrain import run_phase2
from phase3_provinces import run_phase3
from phase4_kingdoms import run_phase4
from phase5_supply_centers import run_phase5
from phase6_optimization import run_phase6
from phase7_naming import run_phase7


def create_output_directory(output_dir):
    """Create output directory if it doesn't exist."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)


def run_full_pipeline(config, output_dir="output", save_intermediate=True):
    """
    Run the complete 7-phase map generation pipeline.
    
    Args:
        config: Configuration dictionary with all parameters
        output_dir: Directory to save outputs
        save_intermediate: Whether to save intermediate phase outputs
        
    Returns:
        Final map data
    """
    create_output_directory(output_dir)
    
    print("\n" + "=" * 70)
    print(" DIPLOMACY MAP GENERATOR - FULL PIPELINE")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print(f"Save intermediate files: {save_intermediate}")
    print("\n")
    
    # Phase 1: Mesh Generation
    phase1_config = {
        "num_cells": config.get("num_cells", 80),
        "width": config.get("width", 1.0),
        "height": config.get("height", 1.0),
        "min_distance": config.get("min_distance", 0.05),
        "lloyd_iterations": config.get("lloyd_iterations", 0),
        "seed": config.get("seed", 42)
    }
    
    phase1_output = run_phase1(phase1_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase1_mesh_output.json"), 'w') as f:
            json.dump(phase1_output, f, indent=2)
    
    # Phase 2: Terrain Assignment
    phase2_config = {
        "threshold": config.get("threshold", 0.4),
        "land_ratio": config.get("land_ratio", 0.6),
        "octaves": config.get("octaves", 4),
        "radial_falloff": config.get("radial_falloff", 0.8),
        "cull_iterations": config.get("cull_iterations", 2),
        "seed": config.get("seed", 42)
    }
    
    phase2_output = run_phase2(phase1_output, phase2_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase2_terrain_output.json"), 'w') as f:
            json.dump(phase2_output, f, indent=2)
    
    # Phase 3: Province Definition
    phase3_config = {
        "num_impassable_zones": config.get("num_impassable_zones", 1),
        "seed": config.get("seed", 42)
    }
    
    phase3_output = run_phase3(phase2_output, phase3_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase3_provinces_output.json"), 'w') as f:
            json.dump(phase3_output, f, indent=2)
    
    # Phase 4: Kingdom Generation
    phase4_config = {
        "num_powers": config.get("num_powers", 7),
        "territory_size": config.get("territory_size", 3),
        "max_retries": config.get("max_retries", 10),
        "seed": config.get("seed", 42)
    }
    
    phase4_output = run_phase4(phase3_output, phase4_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase4_kingdoms_output.json"), 'w') as f:
            json.dump(phase4_output, f, indent=2)
    
    # Phase 5: Supply Center Distribution
    phase5_config = {
        "num_neutral_scs": config.get("num_neutral_scs", 13),
        "seed": config.get("seed", 42)
    }
    
    phase5_output = run_phase5(phase4_output, phase5_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase5_supply_centers_output.json"), 'w') as f:
            json.dump(phase5_output, f, indent=2)
    
    # Phase 6: Graph Optimization
    phase6_config = {}
    
    phase6_output = run_phase6(phase5_output, phase6_config)
    
    if save_intermediate:
        with open(os.path.join(output_dir, "phase6_optimization_output.json"), 'w') as f:
            json.dump(phase6_output, f, indent=2)
    
    # Phase 7: Naming and Visualization
    phase7_config = {
        "seed": config.get("seed", 42)
    }
    
    final_output = run_phase7(phase6_output, phase7_config)
    
    # Always save final output
    final_path = os.path.join(output_dir, "final_map.json")
    with open(final_path, 'w') as f:
        json.dump(final_output, f, indent=2)
    
    # Save summary
    from phase7_naming import generate_map_summary
    summary = generate_map_summary(final_output)
    summary_path = os.path.join(output_dir, "map_summary.txt")
    with open(summary_path, 'w') as f:
        f.write(summary)
    
    print("\n" + "=" * 70)
    print(" PIPELINE COMPLETE!")
    print("=" * 70)
    print(f"\nFinal map: {final_path}")
    print(f"Summary: {summary_path}")
    
    if save_intermediate:
        print(f"\nIntermediate outputs saved in: {output_dir}/")
    
    print("\n")
    
    return final_output


def main():
    """Main entry point for the orchestrator."""
    parser = argparse.ArgumentParser(
        description="Diplomacy Map Generator - Complete Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with default settings
  python orchestrator.py
  
  # Generate with custom parameters
  python orchestrator.py --num-cells 100 --num-powers 7 --seed 12345
  
  # Generate without saving intermediate files
  python orchestrator.py --no-intermediate
  
  # Generate with custom output directory
  python orchestrator.py --output-dir my_maps/map_001
        """
    )
    
    # Phase 1 parameters
    parser.add_argument("--num-cells", type=int, default=80, help="Number of Voronoi cells (Phase 1)")
    parser.add_argument("--width", type=float, default=1.0, help="Map width (Phase 1)")
    parser.add_argument("--height", type=float, default=1.0, help="Map height (Phase 1)")
    parser.add_argument("--min-distance", type=float, default=0.05, help="Min distance for Poisson sampling (Phase 1)")
    parser.add_argument("--lloyd-iterations", type=int, default=0, help="Lloyd relaxation iterations (Phase 1)")
    
    # Phase 2 parameters
    parser.add_argument("--threshold", type=float, default=0.4, help="Land/sea threshold (Phase 2)")
    parser.add_argument("--land-ratio", type=float, default=0.6, help="Target land ratio (Phase 2)")
    parser.add_argument("--octaves", type=int, default=4, help="Noise octaves (Phase 2)")
    parser.add_argument("--radial-falloff", type=float, default=0.8, help="Radial mask falloff (Phase 2)")
    parser.add_argument("--cull-iterations", type=int, default=2, help="Island/lake culling iterations (Phase 2)")
    
    # Phase 3 parameters
    parser.add_argument("--num-impassable-zones", type=int, default=1, help="Number of impassable zones (Phase 3)")
    
    # Phase 4 parameters
    parser.add_argument("--num-powers", type=int, default=7, help="Number of player powers (Phase 4)")
    parser.add_argument("--territory-size", type=int, default=3, help="Home territory size (Phase 4)")
    parser.add_argument("--max-retries", type=int, default=10, help="Max retries for seed placement (Phase 4)")
    
    # Phase 5 parameters
    parser.add_argument("--num-neutral-scs", type=int, default=13, help="Number of neutral supply centers (Phase 5)")
    
    # General parameters
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    parser.add_argument("--no-intermediate", action="store_true", help="Don't save intermediate phase outputs")
    
    args = parser.parse_args()
    
    # Build configuration
    config = {
        "num_cells": args.num_cells,
        "width": args.width,
        "height": args.height,
        "min_distance": args.min_distance,
        "lloyd_iterations": args.lloyd_iterations,
        "threshold": args.threshold,
        "land_ratio": args.land_ratio,
        "octaves": args.octaves,
        "radial_falloff": args.radial_falloff,
        "cull_iterations": args.cull_iterations,
        "num_impassable_zones": args.num_impassable_zones,
        "num_powers": args.num_powers,
        "territory_size": args.territory_size,
        "max_retries": args.max_retries,
        "num_neutral_scs": args.num_neutral_scs,
        "seed": args.seed
    }
    
    # Run pipeline
    try:
        final_output = run_full_pipeline(
            config,
            output_dir=args.output_dir,
            save_intermediate=not args.no_intermediate
        )
        
        return 0
    except Exception as e:
        print(f"\nERROR: Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
