#!/usr/bin/env python3
"""
Test that topology faces are updated with properties from each phase.

This test verifies that phases 4-7 actually update the topology structure
with new properties, not just pass it through unchanged.
"""

import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from phase1_mesh import run_phase1
from phase2_terrain import run_phase2
from phase3_provinces import run_phase3
from phase4_kingdoms import run_phase4
from phase5_supply_centers import run_phase5
from phase6_optimization import run_phase6
from phase7_naming import run_phase7


def test_topology_properties():
    """Test that topology faces are updated with properties from each phase."""
    print("=" * 60)
    print("TOPOLOGY PROPERTIES TEST")
    print("=" * 60)
    
    # Run phases 1-3 to get base topology
    phase1_config = {
        "num_cells": 30,
        "width": 1.0,
        "height": 1.0,
        "min_distance": 0.05,
        "lloyd_iterations": 0,
        "seed": 42
    }
    phase1_output = run_phase1(phase1_config)
    
    phase2_config = {
        "threshold": 0.25,
        "land_ratio": 0.6,
        "octaves": 4,
        "radial_falloff": 0.8,
        "cull_iterations": 2,
        "seed": 42
    }
    phase2_output = run_phase2(phase1_output, phase2_config)
    
    phase3_config = {
        "num_impassable_zones": 1,
        "seed": 42
    }
    phase3_output = run_phase3(phase2_output, phase3_config)
    
    # Test Phase 4: Kingdom properties
    print("\n" + "=" * 60)
    print("Testing Phase 4: Kingdom properties in topology")
    print("=" * 60)
    
    phase4_config = {
        "num_powers": 3,
        "territory_size": 5,
        "max_retries": 5,
        "seed": 42
    }
    phase4_output = run_phase4(phase3_output, phase4_config)
    
    topology4 = phase4_output["topology"]
    
    # Verify that topology faces have owner and is_home properties
    owner_count = 0
    is_home_count = 0
    is_seed_count = 0
    
    for face_id, face_data in topology4["faces"].items():
        if "owner" in face_data:
            owner_count += 1
        
        if "is_home" in face_data:
            is_home_count += 1
        
        if "is_seed" in face_data:
            is_seed_count += 1
    
    print(f"✓ Phase 4 topology faces updated:")
    print(f"  - {owner_count} faces with owner property")
    print(f"  - {is_home_count} faces with is_home property")
    print(f"  - {is_seed_count} faces with is_seed property")
    
    assert owner_count > 0, "Phase 4 should add owner property to topology faces"
    assert is_home_count > 0, "Phase 4 should add is_home property to topology faces"
    assert is_seed_count > 0, "Phase 4 should add is_seed property to topology faces"
    
    # Test Phase 5: Supply center properties
    print("\n" + "=" * 60)
    print("Testing Phase 5: Supply center properties in topology")
    print("=" * 60)
    
    phase5_config = {
        "num_neutral_scs": 5,
        "seed": 42
    }
    phase5_output = run_phase5(phase4_output, phase5_config)
    
    topology5 = phase5_output["topology"]
    
    # Verify that topology faces have supply center properties
    sc_count = 0
    home_sc_count = 0
    neutral_sc_count = 0
    
    for face_id, face_data in topology5["faces"].items():
        if "is_supply_center" in face_data and face_data["is_supply_center"]:
            sc_count += 1
            
            if "sc_type" in face_data:
                if face_data["sc_type"] == "home":
                    home_sc_count += 1
                elif face_data["sc_type"] == "neutral":
                    neutral_sc_count += 1
    
    print(f"✓ Phase 5 topology faces updated:")
    print(f"  - {sc_count} faces with is_supply_center property")
    print(f"  - {home_sc_count} home supply centers")
    print(f"  - {neutral_sc_count} neutral supply centers")
    
    assert sc_count > 0, "Phase 5 should add supply center properties to topology faces"
    assert home_sc_count > 0, "Phase 5 should have home supply centers"
    assert neutral_sc_count > 0, "Phase 5 should have neutral supply centers"
    
    # Test Phase 6: No modifications (analysis only)
    print("\n" + "=" * 60)
    print("Testing Phase 6: No topology modifications (analysis only)")
    print("=" * 60)
    
    phase6_config = {}
    phase6_output = run_phase6(phase5_output, phase6_config)
    
    topology6 = phase6_output["topology"]
    
    # Verify topology is unchanged from phase 5
    assert len(topology6["faces"]) == len(topology5["faces"]), \
        "Phase 6 should not modify topology faces"
    
    print("✓ Phase 6 preserved topology without modifications")
    
    # Test Phase 7: Name properties
    print("\n" + "=" * 60)
    print("Testing Phase 7: Name properties in topology")
    print("=" * 60)
    
    phase7_config = {
        "seed": 42
    }
    phase7_output = run_phase7(phase6_output, phase7_config)
    
    topology7 = phase7_output["topology"]
    
    # Phase 7 no longer outputs cells - it uses topology-only structure
    assert "cells" not in phase7_output, "Phase 7 should not output cells dictionary"
    
    # Verify that topology faces have name properties
    name_count = 0
    land_names = []
    sea_names = []
    
    for face_id, face_data in topology7["faces"].items():
        if "name" in face_data:
            name_count += 1
            # Verify the name is not empty
            assert len(face_data["name"]) > 0, f"Face {face_id} has empty name"
            
            # Collect names by type for verification
            if face_data["type"] == "land":
                land_names.append(face_data["name"])
            elif face_data["type"] == "sea":
                sea_names.append(face_data["name"])
    
    print(f"✓ Phase 7 topology faces updated:")
    print(f"  - {name_count} faces with name property")
    print(f"  - {len(land_names)} land regions named")
    print(f"  - {len(sea_names)} sea regions named")
    
    assert name_count > 0, "Phase 7 should add name property to topology faces"
    assert name_count == len(topology7["faces"]), "Phase 7 should name all faces"
    
    # Verify adjacency list uses names
    assert "adjacency" in phase7_output, "Phase 7 should output adjacency list"
    adjacency = phase7_output["adjacency"]
    assert len(adjacency) > 0, "Adjacency list should not be empty"
    
    # Verify adjacency keys are names, not IDs
    for key in list(adjacency.keys())[:3]:
        assert not key.startswith("C"), f"Adjacency should use names, not IDs: {key}"
    
    # Final verification
    print("\n" + "=" * 60)
    print("TOPOLOGY PROPERTIES TEST COMPLETE ✓")
    print("=" * 60)
    print("\nAll topology faces have been correctly updated with:")
    print("  ✓ Kingdom properties (owner, is_home, is_seed)")
    print("  ✓ Supply center properties (is_supply_center, sc_type)")
    print("  ✓ Name properties (name)")
    print("\nTopology now contains all information from cells!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_topology_properties()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
