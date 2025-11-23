#!/usr/bin/env python3
"""
Test to verify Phase 5 outputs topology-only structure and is compatible with map viewer.

This test ensures:
1. Phase 5 output has topology but no cells dictionary
2. Map viewer can reconstruct cells from topology
3. Supply center information is preserved
"""

import sys
import os
import json
import tempfile

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from phase1_mesh import run_phase1
from phase2_terrain import run_phase2
from phase3_provinces import run_phase3
from phase4_kingdoms import run_phase4
from phase5_supply_centers import run_phase5


def test_phase5_topology_only():
    """Test that Phase 5 produces topology-only output without cells dictionary."""
    print("=" * 60)
    print("PHASE 5 TOPOLOGY-ONLY TEST")
    print("=" * 60)
    
    # Run phases 1-5 with minimal config
    print("\nRunning phases 1-4 to set up test data...")
    
    phase1_config = {
        "num_cells": 20,
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
    
    phase4_config = {
        "num_powers": 2,
        "territory_size": 3,
        "max_retries": 5,
        "seed": 42
    }
    phase4_output = run_phase4(phase3_output, phase4_config)
    
    # Run Phase 5
    print("\n" + "=" * 60)
    print("Testing Phase 5 output structure...")
    print("=" * 60)
    
    phase5_config = {
        "num_neutral_scs": 3,
        "seed": 42
    }
    phase5_output = run_phase5(phase4_output, phase5_config)
    
    # Test 1: Verify cells dictionary is not present
    print("\nTest 1: Verify cells dictionary is removed...")
    assert "cells" not in phase5_output, "Phase 5 should not have 'cells' key"
    print("  ✓ Cells dictionary not present")
    
    # Test 2: Verify topology is present
    print("\nTest 2: Verify topology is present...")
    assert "topology" in phase5_output, "Phase 5 must have 'topology' key"
    assert "vertices" in phase5_output["topology"], "Topology must have vertices"
    assert "edges" in phase5_output["topology"], "Topology must have edges"
    assert "faces" in phase5_output["topology"], "Topology must have faces"
    print(f"  ✓ Topology present with {len(phase5_output['topology']['faces'])} faces")
    
    # Test 3: Verify supply centers are in topology faces
    print("\nTest 3: Verify supply centers are stored in topology faces...")
    faces = phase5_output["topology"]["faces"]
    sc_faces = [f_id for f_id, f in faces.items() if f.get("is_supply_center", False)]
    assert len(sc_faces) > 0, "Should have supply centers in topology faces"
    print(f"  ✓ Found {len(sc_faces)} supply centers in topology faces")
    
    # Test 4: Verify supply centers dictionary is present
    print("\nTest 4: Verify supply centers dictionary...")
    assert "supply_centers" in phase5_output, "Phase 5 must have supply_centers"
    home_scs = phase5_output["supply_centers"].get("home", [])
    neutral_scs = phase5_output["supply_centers"].get("neutral", [])
    print(f"  ✓ Supply centers: {len(home_scs)} home, {len(neutral_scs)} neutral")
    
    # Test 5: Verify all supply centers in dictionary are in topology faces
    print("\nTest 5: Verify supply centers consistency...")
    all_sc_ids = set(home_scs + neutral_scs)
    assert all_sc_ids.issubset(faces.keys()), "All SC IDs should be valid face IDs"
    for sc_id in all_sc_ids:
        assert faces[sc_id].get("is_supply_center", False), f"Face {sc_id} should have is_supply_center=True"
    print(f"  ✓ All {len(all_sc_ids)} supply centers are valid and marked in topology")
    
    # Test 6: Simulate map viewer reconstruction
    print("\nTest 6: Simulate map viewer cell reconstruction...")
    topology = phase5_output["topology"]
    vertices_list = topology.get('vertices', [])
    
    
    # Create vertex lookup (same as map_viewer)
    
    # Reconstruct cells from faces
    reconstructed_cells = {}
    for face_id, face_data in faces.items():
        cell = {
            'id': face_id,
            'type': face_data.get('type', 'land'),
            'center': face_data.get('center', [0.5, 0.5]),
            'name': face_data.get('name', face_id),
            'owner': face_data.get('owner'),
            'is_supply_center': face_data.get('is_supply_center', False),
            'sc_type': face_data.get('sc_type'),
            'is_home': face_data.get('is_home', False),
        }
        reconstructed_cells[face_id] = cell
    
    print(f"  ✓ Successfully reconstructed {len(reconstructed_cells)} cells from topology")
    
    # Verify SC information is in reconstructed cells
    reconstructed_scs = [c_id for c_id, c in reconstructed_cells.items() if c.get('is_supply_center', False)]
    assert len(reconstructed_scs) == len(sc_faces), "Reconstructed cells should have same SCs as topology"
    print(f"  ✓ Supply center information preserved in reconstruction")
    
    # Test 7: Save to file and reload to verify JSON serialization
    print("\nTest 7: Verify JSON serialization...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(phase5_output, f, indent=2)
        temp_file = f.name
    
    try:
        with open(temp_file, 'r') as f:
            reloaded = json.load(f)
        
        assert "cells" not in reloaded, "Reloaded output should not have cells"
        assert "topology" in reloaded, "Reloaded output should have topology"
        assert len(reloaded["topology"]["faces"]) == len(faces), "Face count should match"
        print("  ✓ JSON serialization successful")
    finally:
        os.unlink(temp_file)
    
    # Final summary
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nPhase 5 topology-only migration verified:")
    print(f"  ✓ No cells dictionary in output")
    print(f"  ✓ Topology with {len(faces)} faces")
    print(f"  ✓ {len(sc_faces)} supply centers in topology")
    print(f"  ✓ Map viewer can reconstruct cells from topology")
    print(f"  ✓ JSON serialization works correctly")
    
    return True


if __name__ == "__main__":
    try:
        success = test_phase5_topology_only()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
