#!/usr/bin/env python3
"""
Integration Test: Verify Phase 6 Does Not Break the Map

This test verifies that Phase 6 (now analysis-only) does not break the map
by removing supply centers or power territories.
"""

import sys
import os

# Add the phases directory to path
try:
    from map_gen.phases.phase6_optimization import run_phase6
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
    from phase6_optimization import run_phase6


def test_phase6_does_not_modify_map():
    """Test that Phase 6 does not modify the map data."""
    print("\nTest: Phase 6 does not modify map")
    
    # Create a sample phase5 output with disconnected seas and SCs
    phase5_output = {
        "config": {"num_powers": 2, "seed": 42},
        "cells": {
            # Power 1 territory with SCs
            "C1": {"id": "C1", "type": "land", "neighbors": ["C2", "C3"], 
                   "owner": "Power1", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            "C2": {"id": "C2", "type": "land", "neighbors": ["C1", "C3"], 
                   "owner": "Power1", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            "C3": {"id": "C3", "type": "land", "neighbors": ["C1", "C2"], 
                   "owner": "Power1", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            
            # Power 2 territory with SCs
            "C4": {"id": "C4", "type": "land", "neighbors": ["C5", "C6"], 
                   "owner": "Power2", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            "C5": {"id": "C5", "type": "land", "neighbors": ["C4", "C6"], 
                   "owner": "Power2", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            "C6": {"id": "C6", "type": "land", "neighbors": ["C4", "C5"], 
                   "owner": "Power2", "is_home": True, "is_supply_center": True, "sc_type": "home"},
            
            # Neutral SC
            "C7": {"id": "C7", "type": "land", "neighbors": ["C1", "C4"], 
                   "is_supply_center": True, "sc_type": "neutral"},
            
            # Disconnected seas (intentional problem)
            "S1": {"id": "S1", "type": "sea", "neighbors": ["C1"]},
            "S2": {"id": "S2", "type": "sea", "neighbors": ["C4"]},
        },
        "territories": {
            "Power1": {"cells": ["C1", "C2", "C3"], "seed": "C1", "size": 3},
            "Power2": {"cells": ["C4", "C5", "C6"], "seed": "C4", "size": 3}
        },
        "supply_centers": {
            "home": ["C1", "C2", "C3", "C4", "C5", "C6"],
            "neutral": ["C7"]
        },
        "statistics": {}
    }
    
    # Take a snapshot of the original data
    original_cells = {cell_id: dict(cell) for cell_id, cell in phase5_output["cells"].items()}
    original_territories = {power: dict(data) for power, data in phase5_output["territories"].items()}
    original_scs = dict(phase5_output["supply_centers"])
    
    # Run Phase 6
    output = run_phase6(phase5_output, {})
    
    # Verify cells were not modified
    for cell_id, cell in output["cells"].items():
        original = original_cells[cell_id]
        
        # Check type
        assert cell["type"] == original["type"], \
            f"Cell {cell_id} type changed: {original['type']} -> {cell['type']}"
        
        # Check ownership
        assert cell.get("owner") == original.get("owner"), \
            f"Cell {cell_id} ownership changed"
        
        # Check SC status
        assert cell.get("is_supply_center") == original.get("is_supply_center"), \
            f"Cell {cell_id} SC status changed"
        
        # Check home status
        assert cell.get("is_home") == original.get("is_home"), \
            f"Cell {cell_id} home status changed"
    
    # Verify territories were not modified
    for power, data in output["territories"].items():
        assert data["cells"] == original_territories[power]["cells"], \
            f"Territory {power} cells changed"
    
    # Verify supply centers were not modified
    assert output["supply_centers"]["home"] == original_scs["home"], \
        "Home SCs changed"
    assert output["supply_centers"]["neutral"] == original_scs["neutral"], \
        "Neutral SCs changed"
    
    # Verify Phase 6 detected the disconnected seas issue
    assert not output["analysis"]["sea_connectivity"]["connected"], \
        "Phase 6 should detect disconnected seas"
    
    # Verify Phase 6 added a recommendation about it
    recommendations = output["recommendations"]
    assert any("CRITICAL" in rec and "not fully connected" in rec for rec in recommendations), \
        "Phase 6 should recommend fixing disconnected seas"
    
    print("  ✓ Phase 6 did not modify any map data")
    print("  ✓ Phase 6 correctly detected issues")
    print("  ✓ Phase 6 provided appropriate recommendations")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 6 NO-BREAKAGE INTEGRATION TEST")
    print("=" * 60)
    
    try:
        test_phase6_does_not_modify_map()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nPhase 6 is now safe and will not break the map!")
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
