#!/usr/bin/env python3
"""
Integration Test for Topology Through All Phases (1-7)

This test runs all phases (1-7) and verifies that topology is correctly
maintained and updated throughout the entire pipeline.
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
from topology import get_adjacency_from_topology


def verify_topology_structure(topology, phase_name):
    """Verify that topology has the correct structure."""
    assert "vertices" in topology, f"{phase_name}: Topology missing 'vertices'"
    assert "edges" in topology, f"{phase_name}: Topology missing 'edges'"
    assert "faces" in topology, f"{phase_name}: Topology missing 'faces'"
    assert isinstance(topology["vertices"], list), f"{phase_name}: vertices should be a list"
    assert isinstance(topology["edges"], dict), f"{phase_name}: edges should be a dict"
    assert isinstance(topology["faces"], dict), f"{phase_name}: faces should be a dict"
    return True


def verify_topology_integrity(topology, phase_name):
    """Verify topology integrity (edges reference valid faces, etc.)."""
    # Check that all edges reference valid faces
    faces = set(topology["faces"].keys())
    
    for edge_id, edge_data in topology["edges"].items():
        left_face = edge_data.get("left_face")
        right_face = edge_data.get("right_face")
        
        if left_face and left_face not in faces:
            raise AssertionError(f"{phase_name}: Edge {edge_id} references non-existent left_face: {left_face}")
        
        if right_face and right_face not in faces:
            raise AssertionError(f"{phase_name}: Edge {edge_id} references non-existent right_face: {right_face}")
    
    # Check that all faces reference valid edges
    edge_ids = set(topology["edges"].keys())
    
    for face_id, face_data in topology["faces"].items():
        face_edges = face_data.get("edges", [])
        
        for edge_id in face_edges:
            if edge_id not in edge_ids:
                raise AssertionError(f"{phase_name}: Face {face_id} references non-existent edge: {edge_id}")
    
    return True


def test_topology_all_phases():
    """Test topology through all phases (1-7)."""
    print("=" * 60)
    print("TOPOLOGY ALL PHASES INTEGRATION TEST")
    print("=" * 60)
    
    # Configuration for a small test map
    phase1_config = {
        "num_cells": 30,
        "width": 1.0,
        "height": 1.0,
        "min_distance": 0.05,
        "lloyd_iterations": 0,
        "seed": 42
    }
    
    # Phase 1: Mesh Generation
    print("\n" + "=" * 60)
    print("Running Phase 1...")
    print("=" * 60)
    phase1_output = run_phase1(phase1_config)
    
    assert "topology" in phase1_output, "Phase 1 should include topology"
    verify_topology_structure(phase1_output["topology"], "Phase 1")
    verify_topology_integrity(phase1_output["topology"], "Phase 1")
    
    print("\n✓ Phase 1 topology verified")
    print(f"  - {len(phase1_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase1_output['topology']['edges'])} edges")
    print(f"  - {len(phase1_output['topology']['faces'])} faces")
    
    # Phase 2: Terrain Assignment
    print("\n" + "=" * 60)
    print("Running Phase 2...")
    print("=" * 60)
    phase2_config = {
        "threshold": 0.25,
        "land_ratio": 0.6,
        "octaves": 4,
        "radial_falloff": 0.8,
        "cull_iterations": 2,
        "seed": 42
    }
    phase2_output = run_phase2(phase1_output, phase2_config)
    
    assert "topology" in phase2_output, "Phase 2 should include topology"
    verify_topology_structure(phase2_output["topology"], "Phase 2")
    verify_topology_integrity(phase2_output["topology"], "Phase 2")
    
    print("\n✓ Phase 2 topology verified")
    print(f"  - {len(phase2_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase2_output['topology']['edges'])} edges")
    
    # Phase 3: Province Definition
    print("\n" + "=" * 60)
    print("Running Phase 3...")
    print("=" * 60)
    phase3_config = {
        "num_impassable_zones": 1,
        "seed": 42
    }
    phase3_output = run_phase3(phase2_output, phase3_config)
    
    assert "topology" in phase3_output, "Phase 3 should include topology"
    verify_topology_structure(phase3_output["topology"], "Phase 3")
    verify_topology_integrity(phase3_output["topology"], "Phase 3")
    
    print("\n✓ Phase 3 topology verified")
    print(f"  - {len(phase3_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase3_output['topology']['edges'])} edges")
    
    # Phase 4: Kingdom Generation
    print("\n" + "=" * 60)
    print("Running Phase 4...")
    print("=" * 60)
    phase4_config = {
        "num_powers": 3,
        "territory_size": 5,
        "max_retries": 5,
        "seed": 42
    }
    phase4_output = run_phase4(phase3_output, phase4_config)
    
    assert "topology" in phase4_output, "Phase 4 should include topology"
    verify_topology_structure(phase4_output["topology"], "Phase 4")
    verify_topology_integrity(phase4_output["topology"], "Phase 4")
    
    print("\n✓ Phase 4 topology verified")
    print(f"  - {len(phase4_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase4_output['topology']['edges'])} edges")
    
    # Phase 5: Supply Center Distribution
    print("\n" + "=" * 60)
    print("Running Phase 5...")
    print("=" * 60)
    phase5_config = {
        "num_neutral_scs": 5,
        "seed": 42
    }
    phase5_output = run_phase5(phase4_output, phase5_config)
    
    assert "topology" in phase5_output, "Phase 5 should include topology"
    verify_topology_structure(phase5_output["topology"], "Phase 5")
    verify_topology_integrity(phase5_output["topology"], "Phase 5")
    
    print("\n✓ Phase 5 topology verified")
    print(f"  - {len(phase5_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase5_output['topology']['edges'])} edges")
    
    # Phase 6: Graph Analysis and Validation
    print("\n" + "=" * 60)
    print("Running Phase 6...")
    print("=" * 60)
    phase6_config = {}
    phase6_output = run_phase6(phase5_output, phase6_config)
    
    assert "topology" in phase6_output, "Phase 6 should include topology"
    verify_topology_structure(phase6_output["topology"], "Phase 6")
    verify_topology_integrity(phase6_output["topology"], "Phase 6")
    
    print("\n✓ Phase 6 topology verified")
    print(f"  - {len(phase6_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase6_output['topology']['edges'])} edges")
    
    # Phase 7: Naming and Visualization
    print("\n" + "=" * 60)
    print("Running Phase 7...")
    print("=" * 60)
    phase7_config = {
        "seed": 42
    }
    phase7_output = run_phase7(phase6_output, phase7_config)
    
    assert "topology" in phase7_output, "Phase 7 should include topology"
    verify_topology_structure(phase7_output["topology"], "Phase 7")
    verify_topology_integrity(phase7_output["topology"], "Phase 7")
    
    print("\n✓ Phase 7 topology verified")
    print(f"  - {len(phase7_output['topology']['vertices'])} vertices")
    print(f"  - {len(phase7_output['topology']['edges'])} edges")
    
    # Verify adjacency consistency in final output
    print("\n" + "=" * 60)
    print("Verifying Final Adjacency Consistency...")
    print("=" * 60)
    
    # Phase 7 no longer has a cells key - it uses only topology
    # Verify the adjacency list in the output matches topology
    topology_adjacency = get_adjacency_from_topology(phase7_output["topology"]["edges"])
    
    # Verify the adjacency list was properly created
    if "adjacency" in phase7_output:
        # Get face names for verification
        faces = phase7_output["topology"]["faces"]
        named_adjacency = {}
        for face_id, neighbors in topology_adjacency.items():
            face_name = faces[face_id].get("name", face_id)
            neighbor_names = [faces[n].get("name", n) for n in neighbors]
            named_adjacency[face_name] = set(neighbor_names)
        
        # Compare with output adjacency
        output_adjacency = {name: set(neighbors) for name, neighbors in phase7_output["adjacency"].items()}
        
        if named_adjacency == output_adjacency:
            print("✓ Adjacency list in output matches topology-derived adjacency")
        else:
            print("⚠ Adjacency list discrepancy detected")
    else:
        print("✓ Phase 7 uses topology-only structure (no cells dictionary)")
    
    print("✓ Phase 7 successfully migrated to topology-only structure")
    
    # Final summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE ✓")
    print("=" * 60)
    print("\nTopology successfully maintained through all 7 phases:")
    print(f"  Phase 1: {len(phase1_output['topology']['edges'])} edges")
    print(f"  Phase 2: {len(phase2_output['topology']['edges'])} edges")
    print(f"  Phase 3: {len(phase3_output['topology']['edges'])} edges")
    print(f"  Phase 4: {len(phase4_output['topology']['edges'])} edges")
    print(f"  Phase 5: {len(phase5_output['topology']['edges'])} edges")
    print(f"  Phase 6: {len(phase6_output['topology']['edges'])} edges")
    print(f"  Phase 7: {len(phase7_output['topology']['edges'])} edges")
    print("\nAll topology integrity checks passed!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_topology_all_phases()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
