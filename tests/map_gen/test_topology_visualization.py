#!/usr/bin/env python3
"""
Test Topology Visualization

This script generates a small map and visualizes it using both legacy and topology rendering.
"""

import json
import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'map_gen'))

from visualization import MapVisualizer


def test_topology_visualization():
    """Test that topology visualization works correctly."""
    print("=" * 60)
    print("TOPOLOGY VISUALIZATION TEST")
    print("=" * 60)
    
    # Load a phase2 output with topology
    import tempfile
    test_file = os.path.join(tempfile.gettempdir(), 'test_phase2_topo.json')
    
    try:
        with open(test_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Test data not found at {test_file}. Please run phase1 and phase2 first.")
        return False
    
    cells = data.get('cells', {})
    topology = data.get('topology')
    
    if not topology:
        print("Error: No topology data in the output file")
        return False
    
    print(f"\nLoaded map data:")
    print(f"  Cells: {len(cells)}")
    print(f"  Vertices: {len(topology['vertices'])}")
    print(f"  Edges: {len(topology['edges'])}")
    print(f"  Faces: {len(topology['faces'])}")
    
    # Add dummy names for cells to avoid errors in legacy visualization
    for cell_id, cell_data in cells.items():
        if 'name' not in cell_data:
            cell_data['name'] = cell_id
    
    # Create visualizer with topology
    visualizer = MapVisualizer(
        cells=cells,
        regions=cells,  # Use cells as regions for this test
        supply_centers=set(),
        starting_positions={},
        topology=topology
    )
    
    print("\nGenerating topology visualization...")
    plt = visualizer.visualize_topology(show_edge_types=True, show_vertices=False)
    
    # Save the visualization
    output_path = os.path.join(tempfile.gettempdir(), 'topology_visualization.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved topology visualization to: {output_path}")
    
    # Also generate traditional visualization for comparison
    print("\nGenerating traditional polygon visualization for comparison...")
    plt2 = visualizer.visualize_map(show_names=False, show_borders=True, show_cells=False)
    comparison_path = os.path.join(tempfile.gettempdir(), 'polygon_visualization.png')
    plt2.savefig(comparison_path, dpi=150, bbox_inches='tight')
    print(f"Saved polygon visualization to: {comparison_path}")
    
    print("\n" + "=" * 60)
    print("VISUALIZATION TEST COMPLETE ✓")
    print("=" * 60)
    print("\nGenerated two visualizations:")
    print(f"  1. Topology-based: {output_path}")
    print(f"  2. Polygon-based:  {comparison_path}")
    print("\nBoth should look similar, demonstrating that topology preserves geometry.")
    
    return True


if __name__ == "__main__":
    success = test_topology_visualization()
    sys.exit(0 if success else 1)
