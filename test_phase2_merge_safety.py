#!/usr/bin/env python3
"""
Test Phase 2 Merge Safety

This test verifies that the merge_dead_end_node function in Phase 2
doesn't create invalid connections (e.g., land to sea).
"""

import sys
import os

# Add the phases directory to path
try:
    from map_gen.phases.phase2_terrain import merge_dead_end_node
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
    from phase2_terrain import merge_dead_end_node


def test_merge_prevents_land_sea_connection():
    """Test that merge doesn't connect land and sea cells."""
    print("\nTest: Merge prevents land-to-sea connections")
    
    # Dead-end land cell with one land and one sea neighbor
    cells = {
        "L1": {"id": "L1", "type": "land", "neighbors": ["L2", "S1"]},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1"]},
        "S1": {"id": "S1", "type": "sea", "neighbors": ["L1"]}
    }
    
    # Try to merge L1 (which has 2 neighbors of different types)
    result = merge_dead_end_node("L1", cells)
    
    # Merge should fail because neighbors are different types
    assert result == False, "Should not merge when neighbors are different types"
    assert cells["L1"]["type"] == "land", "L1 should remain land"
    assert "S1" not in cells["L2"]["neighbors"], "Should not connect land L2 to sea S1"
    
    print("  ✓ Merge correctly refused to connect land and sea")


def test_merge_allows_same_type_connection():
    """Test that merge does allow same-type connections."""
    print("\nTest: Merge allows same-type connections")
    
    # Dead-end land cell with two land neighbors
    cells = {
        "L1": {"id": "L1", "type": "land", "neighbors": ["L2", "L3"]},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1"]},
        "L3": {"id": "L3", "type": "land", "neighbors": ["L1"]}
    }
    
    # Try to merge L1
    result = merge_dead_end_node("L1", cells)
    
    # Merge should succeed
    assert result == True, "Should merge when neighbors are same type"
    assert cells["L1"]["type"] == "impassable", "L1 should be impassable"
    assert "L3" in cells["L2"]["neighbors"], "Should connect L2 to L3"
    assert "L2" in cells["L3"]["neighbors"], "Should connect L3 to L2"
    
    print("  ✓ Merge correctly allowed same-type connection")


def test_merge_sea_cells():
    """Test that merge works for sea cells too."""
    print("\nTest: Merge works for sea cells")
    
    # Dead-end sea cell with two sea neighbors
    cells = {
        "S1": {"id": "S1", "type": "sea", "neighbors": ["S2", "S3"]},
        "S2": {"id": "S2", "type": "sea", "neighbors": ["S1"]},
        "S3": {"id": "S3", "type": "sea", "neighbors": ["S1"]}
    }
    
    # Try to merge S1
    result = merge_dead_end_node("S1", cells)
    
    # Merge should succeed
    assert result == True, "Should merge sea cells"
    assert cells["S1"]["type"] == "impassable", "S1 should be impassable"
    assert "S3" in cells["S2"]["neighbors"], "Should connect S2 to S3"
    
    print("  ✓ Merge correctly works for sea cells")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 2 MERGE SAFETY TESTS")
    print("=" * 60)
    
    try:
        test_merge_prevents_land_sea_connection()
        test_merge_allows_same_type_connection()
        test_merge_sea_cells()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nMerge function is safe - won't create invalid connections!")
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
