#!/usr/bin/env python3
"""
Test Phase 2 Ocean Connectivity Functions

This script tests the ocean connectivity check and fix in Phase 2.
"""

import sys
import os

# Add the phases directory to path
try:
    from map_gen.phases.phase2_terrain import check_sea_connectivity, connect_sea_components
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'map_gen', 'phases'))
    from phase2_terrain import check_sea_connectivity, connect_sea_components


def test_connected_seas():
    """Test that already-connected seas are detected correctly."""
    print("\nTest 1: Connected seas")
    
    cells = {
        "S1": {"id": "S1", "type": "sea", "neighbors": ["S2", "L1"]},
        "S2": {"id": "S2", "type": "sea", "neighbors": ["S1", "S3"]},
        "S3": {"id": "S3", "type": "sea", "neighbors": ["S2"]},
        "L1": {"id": "L1", "type": "land", "neighbors": ["S1"]}
    }
    
    connectivity = check_sea_connectivity(cells)
    
    assert connectivity["connected"] == True, "Seas should be connected"
    assert connectivity["components"] == 1, "Should have 1 component"
    
    print("  ✓ Connected seas detected correctly")


def test_disconnected_seas_no_fix():
    """Test that disconnected seas are detected correctly."""
    print("\nTest 2: Disconnected seas detection")
    
    cells = {
        "S1": {"id": "S1", "type": "sea", "neighbors": ["S2", "L1"]},
        "S2": {"id": "S2", "type": "sea", "neighbors": ["S1"]},
        "L1": {"id": "L1", "type": "land", "neighbors": ["S1", "L2"]},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1", "S3"]},
        "S3": {"id": "S3", "type": "sea", "neighbors": ["S4", "L2"]},
        "S4": {"id": "S4", "type": "sea", "neighbors": ["S3"]}
    }
    
    connectivity = check_sea_connectivity(cells)
    
    assert connectivity["connected"] == False, "Seas should not be connected"
    assert connectivity["components"] == 2, "Should have 2 components"
    
    print("  ✓ Disconnected seas detected correctly")


def test_sea_connectivity_fix():
    """Test that disconnected seas can be fixed."""
    print("\nTest 3: Fix disconnected seas")
    
    cells = {
        "S1": {"id": "S1", "type": "sea", "neighbors": ["S2", "L1"]},
        "S2": {"id": "S2", "type": "sea", "neighbors": ["S1"]},
        "L1": {"id": "L1", "type": "land", "neighbors": ["S1", "L2"], "coastal": False},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1", "S3"], "coastal": False},
        "S3": {"id": "S3", "type": "sea", "neighbors": ["S4", "L2"]},
        "S4": {"id": "S4", "type": "sea", "neighbors": ["S3"]}
    }
    
    # Check initial state
    initial_connectivity = check_sea_connectivity(cells)
    assert initial_connectivity["connected"] == False, "Initially disconnected"
    
    # Fix connectivity
    total_converted = 0
    max_attempts = 10
    
    for _ in range(max_attempts):
        current_connectivity = check_sea_connectivity(cells)
        if current_connectivity['connected']:
            break
        
        converted = connect_sea_components(cells, current_connectivity)
        if converted == 0:
            break
        
        total_converted += converted
    
    # Check final state
    final_connectivity = check_sea_connectivity(cells)
    
    assert total_converted > 0, "Should have converted at least one cell"
    assert final_connectivity["connected"] == True, "Seas should be connected after fix"
    assert final_connectivity["components"] == 1, "Should have 1 component after fix"
    
    print(f"  ✓ Seas connected by converting {total_converted} land cells")


def test_no_seas():
    """Test handling of maps with no sea cells."""
    print("\nTest 4: No seas")
    
    cells = {
        "L1": {"id": "L1", "type": "land", "neighbors": ["L2"]},
        "L2": {"id": "L2", "type": "land", "neighbors": ["L1", "L3"]},
        "L3": {"id": "L3", "type": "land", "neighbors": ["L2"]}
    }
    
    connectivity = check_sea_connectivity(cells)
    
    assert connectivity["connected"] == True, "Should report as connected when no seas"
    assert connectivity["components"] == 0, "Should have 0 components"
    
    print("  ✓ No seas case handled correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 2 OCEAN CONNECTIVITY TESTS")
    print("=" * 60)
    
    try:
        test_connected_seas()
        test_disconnected_seas_no_fix()
        test_sea_connectivity_fix()
        test_no_seas()
        
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
