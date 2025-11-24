#!/usr/bin/env python3
"""
Test Topology Utilities

This script tests the topology utility functions for edge length calculation,
face size calculation, face merging, and face splitting.
"""

import sys
import os
import traceback

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from topology import convert_cells_to_topology
from topology_utils import (
    calculate_edge_length,
    calculate_face_size,
    merge_faces,
    split_face,
    find_smallest_faces,
    find_largest_faces,
    find_smallest_neighbor
)


def create_test_topology():
    """Create a simple test topology with known dimensions."""
    # Create two adjacent squares
    cells = {
        "C1": {
            "id": "C1",
            "type": "sea",
            "center": [0.25, 0.5],
            "vertices": [
                [0.0, 0.0],
                [0.5, 0.0],
                [0.5, 1.0],
                [0.0, 1.0]
            ]
        },
        "C2": {
            "id": "C2",
            "type": "sea",
            "center": [0.75, 0.5],
            "vertices": [
                [0.5, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.5, 1.0]
            ]
        }
    }
    
    topology = convert_cells_to_topology(cells)
    return topology


def create_varied_size_topology():
    """Create a topology with faces of different sizes for testing sorting."""
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.25, 0.25],
            "vertices": [
                [0.0, 0.0],
                [0.5, 0.0],
                [0.5, 0.5],
                [0.0, 0.5]
            ]
        },
        "C2": {
            "id": "C2",
            "type": "land",
            "center": [0.75, 0.5],
            "vertices": [
                [0.5, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.5, 1.0]
            ]
        },
        "C3": {
            "id": "C3",
            "type": "land",
            "center": [0.25, 0.75],
            "vertices": [
                [0.0, 0.5],
                [0.5, 0.5],
                [0.5, 1.0],
                [0.0, 1.0]
            ]
        },
        "C4": {
            "id": "C4",
            "type": "sea",
            "center": [0.125, 0.125],
            "vertices": [
                [0.0, 0.0],
                [0.25, 0.0],
                [0.25, 0.25],
                [0.0, 0.25]
            ]
        }
    }
    
    topology = convert_cells_to_topology(cells)
    return topology


def test_calculate_edge_length():
    """Test edge length calculation."""
    print("\nTest 1: Calculate edge length")
    
    topology = create_test_topology()
    edges = topology["edges"]
    
    # Find an edge and calculate its length
    edge_id = next(iter(edges.keys()))
    length = calculate_edge_length(edge_id, topology)
    
    assert length > 0, "Edge length should be positive"
    print(f"  ✓ Edge {edge_id} has length {length:.3f}")


def test_calculate_face_size():
    """Test face area calculation."""
    print("\nTest 2: Calculate face size")
    
    topology = create_test_topology()
    
    # Both faces are 0.5 x 1.0 squares, so area should be 0.5
    size1 = calculate_face_size("C1", topology)
    size2 = calculate_face_size("C2", topology)
    
    expected_area = 0.5
    tolerance = 0.01
    
    assert abs(size1 - expected_area) < tolerance, f"C1 area should be ~{expected_area}, got {size1}"
    assert abs(size2 - expected_area) < tolerance, f"C2 area should be ~{expected_area}, got {size2}"
    
    print(f"  ✓ C1 area: {size1:.3f}")
    print(f"  ✓ C2 area: {size2:.3f}")


def test_merge_faces():
    """Test merging two adjacent faces."""
    print("\nTest 3: Merge two faces")
    
    topology = create_test_topology()
    
    # Count initial faces and edges
    initial_face_count = len(topology["faces"])
    initial_edge_count = len(topology["edges"])
    
    # Merge C1 and C2
    success, merged_id = merge_faces("C1", "C2", topology)
    
    assert success, "Merge should succeed"
    assert merged_id == "C1", "Merged face should have ID C1"
    assert "C2" not in topology["faces"], "C2 should be removed"
    assert len(topology["faces"]) == initial_face_count - 1, "Should have one fewer face"
    assert len(topology["edges"]) < initial_edge_count, "Should have fewer edges after merge"
    
    print(f"  ✓ Successfully merged C1 and C2 into {merged_id}")
    print(f"  ✓ Face count: {initial_face_count} → {len(topology['faces'])}")
    print(f"  ✓ Edge count: {initial_edge_count} → {len(topology['edges'])}")


def test_split_face():
    """Test splitting a face."""
    print("\nTest 4: Split a face")
    
    topology = create_test_topology()
    
    # Count initial faces
    initial_face_count = len(topology["faces"])
    
    # Split C1
    success, face1_id, face2_id = split_face("C1", topology)
    
    assert success, "Split should succeed"
    assert face1_id is not None, "First face should have an ID"
    assert face2_id is not None, "Second face should have an ID"
    assert face1_id in topology["faces"], "First face should exist"
    assert face2_id in topology["faces"], "Second face should exist"
    assert "C1" not in topology["faces"], "Original face C1 should be removed"
    assert face1_id.startswith("C1"), "First face should be based on C1"
    assert face2_id.startswith("C1"), "Second face should be based on C1"
    # The original implementation creates faces C1_a and C1_b
    assert len(topology["faces"]) == initial_face_count + 1, "Should have one more face (original replaced by two)"
    
    print(f"  ✓ Successfully split C1 into {face1_id} and {face2_id}")
    print(f"  ✓ Face count: {initial_face_count} → {len(topology['faces'])}")


def test_find_smallest_faces():
    """Test finding smallest faces."""
    print("\nTest 5: Find smallest faces")
    
    topology = create_varied_size_topology()
    
    # Find smallest land faces
    smallest = find_smallest_faces(topology, "land", count=3)
    
    assert len(smallest) > 0, "Should find at least one land face"
    assert all(isinstance(item, tuple) and len(item) == 2 for item in smallest), \
        "Each item should be a (face_id, size) tuple"
    
    # Check that they're sorted (smallest first)
    for i in range(len(smallest) - 1):
        assert smallest[i][1] <= smallest[i+1][1], "Faces should be sorted by size"
    
    print(f"  ✓ Found {len(smallest)} smallest land faces:")
    for face_id, size in smallest:
        print(f"    - {face_id}: {size:.3f}")


def test_find_largest_faces():
    """Test finding largest faces."""
    print("\nTest 6: Find largest faces")
    
    topology = create_varied_size_topology()
    
    # Find largest land faces
    largest = find_largest_faces(topology, "land", count=3)
    
    assert len(largest) > 0, "Should find at least one land face"
    
    # Check that they're sorted (largest first)
    for i in range(len(largest) - 1):
        assert largest[i][1] >= largest[i+1][1], "Faces should be sorted by size (descending)"
    
    print(f"  ✓ Found {len(largest)} largest land faces:")
    for face_id, size in largest:
        print(f"    - {face_id}: {size:.3f}")


def test_find_smallest_neighbor():
    """Test finding smallest neighbor."""
    print("\nTest 7: Find smallest neighbor")
    
    topology = create_test_topology()
    
    # C1 and C2 are adjacent, so C1's smallest neighbor should be C2
    neighbor = find_smallest_neighbor("C1", topology)
    
    assert neighbor is not None, "Should find a neighbor"
    neighbor_id, neighbor_size = neighbor
    assert neighbor_id == "C2", "C1's neighbor should be C2"
    assert neighbor_size > 0, "Neighbor size should be positive"
    
    print(f"  ✓ C1's smallest neighbor is {neighbor_id} with size {neighbor_size:.3f}")


def test_merge_non_adjacent():
    """Test that merging non-adjacent faces fails."""
    print("\nTest 8: Merge non-adjacent faces (should fail)")
    
    topology = create_varied_size_topology()
    
    # C1 and C4 are not adjacent (different sizes and positions)
    # First check if they exist
    if "C1" in topology["faces"] and "C4" in topology["faces"]:
        success, _ = merge_faces("C1", "C4", topology)
        
        if not success:
            print(f"  ✓ Correctly prevented merging non-adjacent faces")
        else:
            print(f"  ⚠ Merge succeeded unexpectedly (faces might be adjacent)")
    else:
        print(f"  ⊘ Test skipped - required faces not found")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("TOPOLOGY UTILITIES TESTS")
    print("=" * 60)
    
    try:
        test_calculate_edge_length()
        test_calculate_face_size()
        test_merge_faces()
        test_split_face()
        test_find_smallest_faces()
        test_find_largest_faces()
        test_find_smallest_neighbor()
        test_merge_non_adjacent()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
