#!/usr/bin/env python3
"""
Example Usage - Map Viewer

This script demonstrates how to use the map viewer tools.
"""

import os
import sys
import subprocess
from pathlib import Path


def example_cli_single_file():
    """Example 1: Render a single JSON file to PNG."""
    print("=" * 70)
    print("Example 1: Render a single file")
    print("=" * 70)
    
    # Check if we have a test output directory
    if not Path("test_output/final_map.json").exists():
        print("No test output found. Generating a sample map first...")
        subprocess.run([
            sys.executable, "map_gen/phases/orchestrator.py",
            "--num-cells", "60",
            "--output-dir", "test_output"
        ])
    
    # Render the final map
    print("\nRendering final_map.json to PNG...")
    subprocess.run([
        sys.executable, "map_viewer_cli.py",
        "test_output/final_map.json"
    ])
    
    print("\n✓ Created test_output/final_map.png")


def example_cli_directory():
    """Example 2: Render all JSON files in a directory."""
    print("\n" + "=" * 70)
    print("Example 2: Render all files in a directory")
    print("=" * 70)
    
    print("\nRendering all JSON files in test_output/...")
    subprocess.run([
        sys.executable, "map_viewer_cli.py",
        "--directory", "test_output"
    ])
    
    print("\n✓ Created PNG files for all phases")


def example_gui_viewer():
    """Example 3: Launch GUI with multiple files."""
    print("\n" + "=" * 70)
    print("Example 3: Launch interactive GUI viewer")
    print("=" * 70)
    
    print("\nTo launch the GUI viewer with multiple files:")
    print("  python map_viewer.py test_output/phase*.json test_output/final_map.json")
    print("\nOr launch empty and use File > Open Directory:")
    print("  python map_viewer.py")
    print("\nNote: GUI requires tkinter and a display (not available in headless mode)")


def example_compare_parameters():
    """Example 4: Compare maps with different parameters."""
    print("\n" + "=" * 70)
    print("Example 4: Compare different map parameters")
    print("=" * 70)
    
    print("\nGenerating maps with different land ratios...")
    
    configs = [
        ("low_land", 0.4, "Archipelago"),
        ("medium_land", 0.6, "Balanced"),
        ("high_land", 0.8, "Continental")
    ]
    
    for dirname, land_ratio, description in configs:
        output_dir = f"test_output/{dirname}"
        print(f"\n  Generating {description} map (land_ratio={land_ratio})...")
        subprocess.run([
            sys.executable, "map_gen/phases/orchestrator.py",
            "--num-cells", "50",
            "--land-ratio", str(land_ratio),
            "--output-dir", output_dir,
            "--seed", "42"  # Same seed for fair comparison
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Render just the final map
        subprocess.run([
            sys.executable, "map_viewer_cli.py",
            f"{output_dir}/final_map.json"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("\n✓ Generated comparison maps:")
    print("  - test_output/low_land/final_map.png")
    print("  - test_output/medium_land/final_map.png")
    print("  - test_output/high_land/final_map.png")
    print("\nView them in the GUI:")
    print("  python map_viewer.py test_output/*/final_map.json")


def main():
    """Run examples."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run map viewer examples")
    parser.add_argument('--with-comparison', action='store_true',
                       help='Include comparison example (takes longer)')
    args = parser.parse_args()
    
    print("=" * 70)
    print(" MAP VIEWER EXAMPLES")
    print("=" * 70)
    print()
    
    try:
        # Example 1: Single file
        example_cli_single_file()
        
        # Example 2: Directory
        example_cli_directory()
        
        # Example 3: GUI info
        example_gui_viewer()
        
        # Example 4: Comparison (optional, takes longer)
        if args.with_comparison:
            example_compare_parameters()
        else:
            print("\n" + "=" * 70)
            print("Skipping comparison example (use --with-comparison to run it)")
            print("=" * 70)
        
        print("\n" + "=" * 70)
        print(" EXAMPLES COMPLETED")
        print("=" * 70)
        print("\nCheck the test_output/ directory for generated PNG files.")
        print("\nFor more information, see MAP_VIEWER_README.md")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
