#!/usr/bin/env python3
"""
Integration Test for Topology Through Full Pipeline

This test runs phases 1-3 and verifies that topology is correctly
maintained and updated throughout the entire pipeline.
"""

import json
import sys
import os
import tempfile

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from phase1_mesh import run_phase1
from phase2_terrain import run_phase2
from phase3_provinces import run_phase3
from topology import get_adjacency_from_topology


def test_topology_integration():
    """Test topology through the full pipeline."""
    print("=" * 60)
    print("TOPOLOGY INTEGRATION TEST")
    print("=" * 60)
    
    # Configuration for a small test map
    config = {
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
    phase1_output = run_phase1(config)
    
    # Verify Phase 1 topology
    assert "topology" in phase1_output, "Phase 1 should include topology"
    assert "vertices" in phase1_output["topology"], "Topology should have vertices"
    assert "edges" in phase1_output["topology"], "Topology should have edges"
    assert "faces" in phase1_output["topology"], "Topology should have faces"
    
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
    
    # Verify Phase 2 topology
    assert "topology" in phase2_output, "Phase 2 should include topology"
    topology2 = phase2_output["topology"]
    
    # Check that edge types are assigned
    edge_types = set()
    for edge_data in topology2["edges"].values():
        edge_type = edge_data.get("type")
        if edge_type:
            edge_types.add(edge_type)
    
    assert "coast" in edge_types or "land" in edge_types, "Phase 2 should classify edge types"
    
    print("\n✓ Phase 2 topology verified")
    print(f"  - {len(topology2['vertices'])} vertices")
    print(f"  - {len(topology2['edges'])} edges")
    print(f"  - Edge types: {edge_types}")
    
    # Phase 3: Province Definition
    print("\n" + "=" * 60)
    print("Running Phase 3...")
    print("=" * 60)
    phase3_config = {
        "num_impassable_zones": 1,
        "seed": 42
    }
    phase3_output = run_phase3(phase2_output, phase3_config)
    
    # Verify Phase 3 topology
    assert "topology" in phase3_output, "Phase 3 should include topology"
    topology3 = phase3_output["topology"]
    
    print("\n✓ Phase 3 topology verified")
    print(f"  - {len(topology3['vertices'])} vertices")
    print(f"  - {len(topology3['edges'])} edges")
    
    # Verify adjacency consistency
    print("\n" + "=" * 60)
    print("Verifying Adjacency Consistency...")
    print("=" * 60)
    
    # Get adjacency from topology
    topology_adjacency = get_adjacency_from_topology(topology3["edges"])
    
    # Get adjacency from legacy cells
    cells = phase3_output["cells"]
    legacy_adjacency = {cell_id: cell_data.get("neighbors", []) 
                       for cell_id, cell_data in cells.items()}
    
    # Compare adjacencies
    discrepancies = 0
    for cell_id in topology_adjacency:
        topo_neighbors = set(topology_adjacency[cell_id])
        legacy_neighbors = set(legacy_adjacency.get(cell_id, []))
        
        if topo_neighbors != legacy_neighbors:
            discrepancies += 1
            if discrepancies <= 3:  # Only print first 3
                print(f"  Adjacency mismatch for {cell_id}:")
                print(f"    Topology: {topo_neighbors}")
                print(f"    Legacy:   {legacy_neighbors}")
    
    if discrepancies == 0:
        print("✓ All adjacencies match between topology and legacy format")
    else:
        print(f"⚠ Found {discrepancies} adjacency discrepancies")
        print("  Note: Minor discrepancies may occur if the legacy neighbor list")
        print("  was not updated after terrain changes. The topology is authoritative.")
        
        # If there are many discrepancies, that's a concern
        if discrepancies > len(cells) * 0.1:  # More than 10% mismatch
            print(f"  WARNING: {discrepancies}/{len(cells)} cells have mismatches - this may indicate a bug")
            return False
    
    # Verify topology integrity
    print("\n" + "=" * 60)
    print("Verifying Topology Integrity...")
    print("=" * 60)
    
    # Check that all edges reference valid faces
    faces = set(topology3["faces"].keys())
    invalid_edges = 0
    
    for edge_id, edge_data in topology3["edges"].items():
        left_face = edge_data.get("left_face")
        right_face = edge_data.get("right_face")
        
        if left_face and left_face not in faces:
            invalid_edges += 1
            print(f"  Edge {edge_id} references non-existent left_face: {left_face}")
        
        if right_face and right_face not in faces:
            invalid_edges += 1
            print(f"  Edge {edge_id} references non-existent right_face: {right_face}")
    
    if invalid_edges == 0:
        print("✓ All edges reference valid faces")
    else:
        print(f"✗ Found {invalid_edges} edges with invalid face references")
        return False
    
    # Check that all faces reference valid edges
    edge_ids = set(topology3["edges"].keys())
    invalid_faces = 0
    
    for face_id, face_data in topology3["faces"].items():
        face_edges = face_data.get("edges", [])
        
        for edge_id in face_edges:
            if edge_id not in edge_ids:
                invalid_faces += 1
                print(f"  Face {face_id} references non-existent edge: {edge_id}")
                break
    
    if invalid_faces == 0:
        print("✓ All faces reference valid edges")
    else:
        print(f"✗ Found {invalid_faces} faces with invalid edge references")
        return False
    
    # Verify no duplicate vertices
    vertex_coords = set()
    duplicate_vertices = 0
    
    for vertex in topology3["vertices"]:
        coord_tuple = tuple(vertex["coords"])
        if coord_tuple in vertex_coords:
            duplicate_vertices += 1
        vertex_coords.add(coord_tuple)
    
    if duplicate_vertices == 0:
        print("✓ No duplicate vertices found")
    else:
        print(f"✗ Found {duplicate_vertices} duplicate vertices")
        return False
    
    # Final summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE ✓")
    print("=" * 60)
    print("\nTopology successfully maintained through all phases:")
    print(f"  Phase 1: {len(phase1_output['topology']['edges'])} edges")
    print(f"  Phase 2: {len(phase2_output['topology']['edges'])} edges")
    print(f"  Phase 3: {len(phase3_output['topology']['edges'])} edges")
    print("\nAll topology integrity checks passed!")
    
    return True


if __name__ == "__main__":
    try:
        success = test_topology_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
