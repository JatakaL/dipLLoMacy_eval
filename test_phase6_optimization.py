#!/usr/bin/env python3
"""
Test Phase 6 Optimization Functions

This script tests the optimization functions in Phase 6 to ensure they work correctly.
"""

import sys
import os

# Add the phases directory to path only if not already available
try:
    from map_gen.phases.phase6_optimization import (
        merge_dead_end_node,
        split_highly_connected_node,
        connect_sea_components,
        analyze_node_degrees,
        check_sea_connectivity
    )
except ImportError:
    # Fallback for direct script execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
    from phase6_optimization import (
        merge_dead_end_node,
        split_highly_connected_node,
        connect_sea_components,
        analyze_node_degrees,
        check_sea_connectivity
    )


def test_merge_dead_end_with_2_neighbors():
    """Test merging a dead-end node with 2 neighbors."""
    print("\nTest 1: Merge dead-end node with 2 neighbors")
    
    cells = {
        "A": {"id": "A", "type": "land", "neighbors": ["B", "C"]},
        "B": {"id": "B", "type": "land", "neighbors": ["A", "C", "D"]},
        "C": {"id": "C", "type": "land", "neighbors": ["A", "B"]},
        "D": {"id": "D", "type": "land", "neighbors": ["B"]}
    }
    
    # A is a dead-end with 2 neighbors (B and C)
    result = merge_dead_end_node("A", cells)
    
    assert result == True, "Should successfully merge A"
    assert cells["A"]["type"] == "impassable", "A should be marked as impassable"
    assert "A" not in cells["B"]["neighbors"], "B should not have A as neighbor"
    assert "A" not in cells["C"]["neighbors"], "C should not have A as neighbor"
    assert "C" in cells["B"]["neighbors"], "B and C should be connected"
    assert "B" in cells["C"]["neighbors"], "C and B should be connected"
    
    print("  ✓ Dead-end node with 2 neighbors merged successfully")


def test_merge_dead_end_with_1_neighbor():
    """Test merging a dead-end node with 1 neighbor."""
    print("\nTest 2: Merge dead-end node with 1 neighbor")
    
    cells = {
        "A": {"id": "A", "type": "sea", "neighbors": ["B"]},
        "B": {"id": "B", "type": "sea", "neighbors": ["A", "C"]},
        "C": {"id": "C", "type": "sea", "neighbors": ["B"]}
    }
    
    # A is a dead-end with 1 neighbor (B)
    result = merge_dead_end_node("A", cells)
    
    assert result == True, "Should successfully merge A"
    assert cells["A"]["type"] == "impassable", "A should be marked as impassable"
    assert "A" not in cells["B"]["neighbors"], "B should not have A as neighbor"
    
    print("  ✓ Dead-end node with 1 neighbor merged successfully")


def test_split_highly_connected_node():
    """Test splitting a highly connected node."""
    print("\nTest 3: Split highly connected node")
    
    cells = {
        "A": {"id": "A", "type": "land", "neighbors": ["B", "C", "D", "E", "F", "G", "H", "I"]},
        "B": {"id": "B", "type": "land", "neighbors": ["A"]},
        "C": {"id": "C", "type": "land", "neighbors": ["A"]},
        "D": {"id": "D", "type": "land", "neighbors": ["A"]},
        "E": {"id": "E", "type": "land", "neighbors": ["A"]},
        "F": {"id": "F", "type": "land", "neighbors": ["A"]},
        "G": {"id": "G", "type": "land", "neighbors": ["A"]},
        "H": {"id": "H", "type": "land", "neighbors": ["A"]},
        "I": {"id": "I", "type": "land", "neighbors": ["A"]}
    }
    
    # A has 8 neighbors (highly connected)
    initial_degree = len(cells["A"]["neighbors"])
    edges_removed = split_highly_connected_node("A", cells)
    final_degree = len(cells["A"]["neighbors"])
    
    assert edges_removed > 0, "Should remove at least one edge"
    assert final_degree < initial_degree, "Degree should decrease"
    assert final_degree <= 6, "Final degree should be at most 6"
    
    print(f"  ✓ Highly connected node split: {initial_degree} → {final_degree} neighbors")


def test_connect_sea_components():
    """Test connecting disconnected sea components."""
    print("\nTest 4: Connect disconnected sea components")
    
    cells = {
        "S1": {"id": "S1", "type": "sea", "neighbors": ["S2", "L1"]},
        "S2": {"id": "S2", "type": "sea", "neighbors": ["S1"]},
        "L1": {"id": "L1", "type": "land", "neighbors": ["S1", "L2"]},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1", "S3"]},
        "S3": {"id": "S3", "type": "sea", "neighbors": ["S4", "L2"]},
        "S4": {"id": "S4", "type": "sea", "neighbors": ["S3"]}
    }
    
    # Check initial connectivity
    initial_connectivity = check_sea_connectivity(cells)
    assert initial_connectivity["components"] == 2, "Should have 2 sea components initially"
    
    # Connect components (iterate like in the actual implementation)
    total_converted = 0
    max_attempts = 10
    attempts = 0
    
    while attempts < max_attempts:
        current_connectivity = check_sea_connectivity(cells)
        if current_connectivity['connected']:
            break
        
        converted = connect_sea_components(cells, current_connectivity)
        if converted == 0:
            break
        
        total_converted += converted
        attempts += 1
    
    # Check final connectivity
    final_connectivity = check_sea_connectivity(cells)
    
    assert total_converted > 0, "Should convert at least one land cell"
    assert final_connectivity["connected"], "Seas should be connected"
    assert final_connectivity["components"] == 1, "Should have 1 sea component"
    
    print(f"  ✓ Sea components connected by converting {total_converted} land cells")


def test_analyze_node_degrees():
    """Test node degree analysis."""
    print("\nTest 5: Analyze node degrees")
    
    cells = {
        "A": {"id": "A", "type": "land", "neighbors": ["B", "C"]},
        "B": {"id": "B", "type": "land", "neighbors": ["A", "C", "D", "E", "F", "G", "H", "I"]},
        "C": {"id": "C", "type": "land", "neighbors": ["A", "B"]},
        "D": {"id": "D", "type": "land", "neighbors": ["B"]},
        "E": {"id": "E", "type": "land", "neighbors": ["B"]},
        "F": {"id": "F", "type": "land", "neighbors": ["B"]},
        "G": {"id": "G", "type": "land", "neighbors": ["B"]},
        "H": {"id": "H", "type": "land", "neighbors": ["B"]},
        "I": {"id": "I", "type": "land", "neighbors": ["B"]},
        "X": {"id": "X", "type": "impassable", "neighbors": []}
    }
    
    analysis = analyze_node_degrees(cells)
    
    assert analysis["min"] == 1, "Min degree should be 1 (node D, E, F, G, H, I)"
    assert analysis["max"] == 8, "Max degree should be 8 (node B)"
    assert len(analysis["highly_connected"]) == 1, "Should have 1 highly connected node"
    assert "B" in analysis["highly_connected"], "B should be highly connected"
    assert len(analysis["dead_ends"]) == 8, "Should have 8 dead-end nodes: A and C (degree 2), D-I (degree 1)"
    
    print("  ✓ Node degree analysis correct")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 6 OPTIMIZATION TESTS")
    print("=" * 60)
    
    try:
        test_merge_dead_end_with_2_neighbors()
        test_merge_dead_end_with_1_neighbor()
        test_split_highly_connected_node()
        test_connect_sea_components()
        test_analyze_node_degrees()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
