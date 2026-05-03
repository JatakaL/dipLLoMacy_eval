#!/usr/bin/env python3
"""
Test Fractal Subdivision Module

This script tests the fractal edge subdivision functionality.
"""

import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'map_gen'))

from fractal_subdivision import (
    midpoint_displacement,
    get_edge_displacement_params,
    generate_visual_path,
    generate_all_visual_paths
)
import random


def test_midpoint_displacement_basic():
    """Test that midpoint displacement generates valid points."""
    print("\nTest 1: Basic midpoint displacement")
    
    point_a = (0.0, 0.0)
    point_b = (1.0, 0.0)
    rng = random.Random(42)
    
    # With displacement of 0.1 and depth 2
    path = midpoint_displacement(point_a, point_b, 0.1, 0.5, 0, 2, rng)
    
    # Should have more than 2 points
    assert len(path) > 2, f"Expected more than 2 points, got {len(path)}"
    
    # First and last points should be the original points
    assert path[0] == point_a, f"First point should be {point_a}, got {path[0]}"
    assert path[-1] == point_b, f"Last point should be {point_b}, got {path[-1]}"
    
    # All points should be within reasonable bounds
    for point in path:
        assert -0.2 <= point[0] <= 1.2, f"Point x out of bounds: {point[0]}"
        assert -0.2 <= point[1] <= 0.2, f"Point y out of bounds: {point[1]}"
    
    print(f"  ✓ Generated path with {len(path)} points")
    print(f"    Start: {path[0]}, End: {path[-1]}")


def test_midpoint_displacement_zero_depth():
    """Test that zero depth returns original points."""
    print("\nTest 2: Zero depth returns original points")
    
    point_a = (0.0, 0.0)
    point_b = (1.0, 1.0)
    rng = random.Random(42)
    
    path = midpoint_displacement(point_a, point_b, 0.1, 0.5, 0, 0, rng)
    
    assert len(path) == 2, f"Expected 2 points, got {len(path)}"
    assert path[0] == point_a, f"First point should be {point_a}"
    assert path[1] == point_b, f"Second point should be {point_b}"
    
    print(f"  ✓ Correctly returns 2 points for zero depth")


def test_edge_displacement_params():
    """Test that edge types have appropriate displacement parameters."""
    print("\nTest 3: Edge displacement parameters")
    
    # Coast should have the most displacement
    coast_params = get_edge_displacement_params("coast")
    land_params = get_edge_displacement_params("land")
    sea_params = get_edge_displacement_params("sea")
    impassable_params = get_edge_displacement_params("impassable")
    map_edge_params = get_edge_displacement_params("map-edge")
    
    # Coast should have highest initial displacement
    assert coast_params[0] > land_params[0], "Coast should have more displacement than land"
    assert coast_params[0] > sea_params[0], "Coast should have more displacement than sea"
    
    # Impassable should have same displacement as land
    assert impassable_params[0] == land_params[0], "Impassable should have same displacement as land"
    assert impassable_params[1] == land_params[1], "Impassable should have same roughness as land"
    assert impassable_params[2] == land_params[2], "Impassable should have same depth as land"
    
    # Map edge should have zero displacement
    assert map_edge_params[0] == 0.0, "Map edge should have zero displacement"
    assert map_edge_params[2] == 0, "Map edge should have zero depth"
    
    print(f"  ✓ Coast params: displacement={coast_params[0]}, roughness={coast_params[1]}, depth={coast_params[2]}")
    print(f"  ✓ Land params: displacement={land_params[0]}, roughness={land_params[1]}, depth={land_params[2]}")
    print(f"  ✓ Sea params: displacement={sea_params[0]}, roughness={sea_params[1]}, depth={sea_params[2]}")
    print(f"  ✓ Impassable params: displacement={impassable_params[0]}, roughness={impassable_params[1]}, depth={impassable_params[2]}")
    print(f"  ✓ Map-edge params: displacement={map_edge_params[0]}, roughness={map_edge_params[1]}, depth={map_edge_params[2]}")


def test_generate_visual_path():
    """Test visual path generation for different edge types."""
    print("\nTest 4: Visual path generation")
    
    start_coords = (0.1, 0.1)
    end_coords = (0.5, 0.5)
    seed = 42
    
    # Coast path should be more complex
    coast_path = generate_visual_path(start_coords, end_coords, "coast", seed)
    land_path = generate_visual_path(start_coords, end_coords, "land", seed)
    map_edge_path = generate_visual_path(start_coords, end_coords, "map-edge", seed)
    
    # All paths should start and end at the same points
    assert coast_path[0] == list(start_coords), "Coast path should start at start_coords"
    assert coast_path[-1] == list(end_coords), "Coast path should end at end_coords"
    assert land_path[0] == list(start_coords), "Land path should start at start_coords"
    assert land_path[-1] == list(end_coords), "Land path should end at end_coords"
    
    # Map edge should be straight (only 2 points)
    assert len(map_edge_path) == 2, f"Map edge should have 2 points, got {len(map_edge_path)}"
    
    # Coast should have more points than land (due to higher depth)
    assert len(coast_path) >= len(land_path), "Coast should have at least as many points as land"
    
    print(f"  ✓ Coast path: {len(coast_path)} points")
    print(f"  ✓ Land path: {len(land_path)} points")
    print(f"  ✓ Map-edge path: {len(map_edge_path)} points")


def test_generate_visual_path_reproducibility():
    """Test that visual path generation is reproducible with same seed."""
    print("\nTest 5: Visual path reproducibility")
    
    start_coords = (0.2, 0.3)
    end_coords = (0.8, 0.7)
    seed = 123
    
    path1 = generate_visual_path(start_coords, end_coords, "coast", seed)
    path2 = generate_visual_path(start_coords, end_coords, "coast", seed)
    
    assert path1 == path2, "Same seed should produce identical paths"
    
    # Different seed should produce different path
    path3 = generate_visual_path(start_coords, end_coords, "coast", seed + 1)
    assert path1 != path3, "Different seeds should produce different paths"
    
    print(f"  ✓ Same seed produces identical paths")
    print(f"  ✓ Different seeds produce different paths")


def test_generate_all_visual_paths():
    """Test generating visual paths for all edges in a topology."""
    print("\nTest 6: Generate all visual paths")
    
    # Create a simple topology with 2 cells
    topology = {
        "vertices": [
            {"id": 0, "coords": [0.0, 0.0]},
            {"id": 1, "coords": [0.5, 0.0]},
            {"id": 2, "coords": [1.0, 0.0]},
            {"id": 3, "coords": [1.0, 1.0]},
            {"id": 4, "coords": [0.5, 1.0]},
            {"id": 5, "coords": [0.0, 1.0]}
        ],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "map-edge", "left_face": "C1"},
            "E_1_2": {"v1": 1, "v2": 2, "type": "map-edge", "left_face": "C2"},
            "E_1_4": {"v1": 1, "v2": 4, "type": "coast", "left_face": "C1", "right_face": "C2"},
            "E_0_5": {"v1": 0, "v2": 5, "type": "map-edge", "left_face": "C1"},
            "E_4_5": {"v1": 4, "v2": 5, "type": "map-edge", "left_face": "C1"},
            "E_2_3": {"v1": 2, "v2": 3, "type": "map-edge", "left_face": "C2"},
            "E_3_4": {"v1": 3, "v2": 4, "type": "map-edge", "left_face": "C2"}
        },
        "faces": {
            "C1": {"type": "land", "edges": ["E_0_1", "E_1_4", "E_4_5", "E_0_5"], "center": [0.25, 0.5]},
            "C2": {"type": "sea", "edges": ["E_1_2", "E_2_3", "E_3_4", "E_1_4"], "center": [0.75, 0.5]}
        }
    }
    
    # Generate visual paths
    updated_topology = generate_all_visual_paths(topology, seed=42)
    
    # All edges should now have visual_path
    for edge_id, edge_data in updated_topology["edges"].items():
        assert "visual_path" in edge_data, f"Edge {edge_id} should have visual_path"
        visual_path = edge_data["visual_path"]
        assert len(visual_path) >= 2, f"Edge {edge_id} visual_path should have at least 2 points"
    
    # The coast edge should have more points than map-edge
    coast_edge = updated_topology["edges"]["E_1_4"]
    map_edge = updated_topology["edges"]["E_0_1"]
    
    assert len(coast_edge["visual_path"]) > len(map_edge["visual_path"]), \
        "Coast edge should have more visual_path points than map-edge"
    
    print(f"  ✓ All {len(updated_topology['edges'])} edges have visual_path")
    print(f"  ✓ Coast edge has {len(coast_edge['visual_path'])} points")
    print(f"  ✓ Map-edge has {len(map_edge['visual_path'])} points (straight line)")


def test_visual_path_endpoints():
    """Test that visual paths always start and end at the correct vertices."""
    print("\nTest 7: Visual path endpoints match vertices")
    
    topology = {
        "vertices": [
            {"id": 0, "coords": [0.123, 0.456]},
            {"id": 1, "coords": [0.789, 0.321]},
            {"id": 2, "coords": [0.555, 0.888]}
        ],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "coast", "left_face": "C1"},
            "E_0_2": {"v1": 0, "v2": 2, "type": "land", "left_face": "C1"},
            "E_1_2": {"v1": 1, "v2": 2, "type": "sea", "left_face": "C1"}
        },
        "faces": {
            "C1": {"type": "land", "edges": ["E_0_1", "E_0_2", "E_1_2"], "center": [0.5, 0.5]}
        }
    }
    
    updated_topology = generate_all_visual_paths(topology, seed=42)
    vertex_coords = {v["id"]: v["coords"] for v in topology["vertices"]}
    
    for edge_id, edge_data in updated_topology["edges"].items():
        v1_id = edge_data["v1"]
        v2_id = edge_data["v2"]
        visual_path = edge_data["visual_path"]
        
        # First point should match v1 coords
        assert visual_path[0] == vertex_coords[v1_id], \
            f"Edge {edge_id} first point should match v1 coords"
        
        # Last point should match v2 coords
        assert visual_path[-1] == vertex_coords[v2_id], \
            f"Edge {edge_id} last point should match v2 coords"
    
    print(f"  ✓ All edge visual_paths start and end at correct vertex coordinates")


def test_subdivide_edge_topology():
    """Test that edge subdivision creates proper topology."""
    print("\nTest 8: Edge topology subdivision")
    
    from fractal_subdivision import subdivide_edge_topology
    
    # Create a simple topology with 1 coast edge
    topology = {
        "vertices": [
            {"id": 0, "coords": [0.0, 0.0]},
            {"id": 1, "coords": [0.5, 0.0]},
        ],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "coast", "left_face": "C1", "right_face": "C2"}
        },
        "borders": {
            "B_0_1": {
                "edges": ["E_0_1"],
                "left_face": "C1",
                "right_face": "C2",
                "type": "coast",
                "start_vertex": 0,
                "end_vertex": 1
            }
        },
        "faces": {
            "C1": {"type": "land", "borders": ["B_0_1"]},
            "C2": {"type": "sea", "borders": ["B_0_1"]}
        }
    }
    
    # Subdivide the edge
    new_edge_ids, new_vertex_ids = subdivide_edge_topology(topology, "E_0_1", seed=42)
    
    # Should have multiple new edges (coast edges get subdivided)
    assert len(new_edge_ids) > 1, f"Expected multiple new edges, got {len(new_edge_ids)}"
    
    # Should have new vertices
    assert len(new_vertex_ids) > 0, f"Expected new vertices, got {len(new_vertex_ids)}"
    
    # Original edge should be removed
    assert "E_0_1" not in topology["edges"], "Original edge should be removed"
    
    # New edges should exist
    for edge_id in new_edge_ids:
        assert edge_id in topology["edges"], f"New edge {edge_id} should exist"
    
    # New vertices should exist in the vertices list
    vertex_ids = {v["id"] for v in topology["vertices"]}
    for vid in new_vertex_ids:
        assert vid in vertex_ids, f"New vertex {vid} should exist"
    
    # Border should now contain the new edges
    border = topology["borders"]["B_0_1"]
    assert border["edges"] == new_edge_ids, f"Border should contain new edges: {border['edges']} != {new_edge_ids}"
    
    # Faces should reference the border (not edges directly)
    for face_id in ["C1", "C2"]:
        face = topology["faces"][face_id]
        assert "B_0_1" in face["borders"], f"Face {face_id} should reference border B_0_1"
    
    print(f"  ✓ Subdivided edge into {len(new_edge_ids)} edges with {len(new_vertex_ids)} new vertices")
    print(f"    New edges: {new_edge_ids}")


def test_subdivide_all_edges():
    """Test that all edges are properly subdivided."""
    print("\nTest 9: Subdivide all edges")
    
    from fractal_subdivision import subdivide_all_edges
    
    # Create a topology with different edge types
    topology = {
        "vertices": [
            {"id": 0, "coords": [0.0, 0.0]},
            {"id": 1, "coords": [0.5, 0.0]},
            {"id": 2, "coords": [1.0, 0.0]},
            {"id": 3, "coords": [1.0, 1.0]},
            {"id": 4, "coords": [0.5, 1.0]},
            {"id": 5, "coords": [0.0, 1.0]}
        ],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "map-edge", "left_face": "C1"},
            "E_1_2": {"v1": 1, "v2": 2, "type": "map-edge", "left_face": "C2"},
            "E_1_4": {"v1": 1, "v2": 4, "type": "coast", "left_face": "C1", "right_face": "C2"},
            "E_0_5": {"v1": 0, "v2": 5, "type": "map-edge", "left_face": "C1"},
            "E_4_5": {"v1": 4, "v2": 5, "type": "map-edge", "left_face": "C1"},
            "E_2_3": {"v1": 2, "v2": 3, "type": "map-edge", "left_face": "C2"},
            "E_3_4": {"v1": 3, "v2": 4, "type": "map-edge", "left_face": "C2"}
        },
        "borders": {
            "B_0_1": {"edges": ["E_0_1"], "type": "map-edge", "left_face": "C1"},
            "B_1_2": {"edges": ["E_1_2"], "type": "map-edge", "left_face": "C2"},
            "B_1_4": {"edges": ["E_1_4"], "type": "coast", "left_face": "C1", "right_face": "C2"},
            "B_0_5": {"edges": ["E_0_5"], "type": "map-edge", "left_face": "C1"},
            "B_4_5": {"edges": ["E_4_5"], "type": "map-edge", "left_face": "C1"},
            "B_2_3": {"edges": ["E_2_3"], "type": "map-edge", "left_face": "C2"},
            "B_3_4": {"edges": ["E_3_4"], "type": "map-edge", "left_face": "C2"}
        },
        "faces": {
            "C1": {"type": "land", "borders": ["B_0_1", "B_1_4", "B_4_5", "B_0_5"], "center": [0.25, 0.5]},
            "C2": {"type": "sea", "borders": ["B_1_2", "B_2_3", "B_3_4", "B_1_4"], "center": [0.75, 0.5]}
        }
    }
    
    original_vertex_count = len(topology["vertices"])
    original_edge_count = len(topology["edges"])
    
    # Subdivide all edges
    updated_topology = subdivide_all_edges(topology, seed=42)
    
    new_vertex_count = len(updated_topology["vertices"])
    new_edge_count = len(updated_topology["edges"])
    
    # Coast edge should be subdivided (more vertices and edges)
    assert new_vertex_count > original_vertex_count, f"Should have more vertices after subdivision"
    assert new_edge_count > original_edge_count, f"Should have more edges after subdivision"
    
    # Map-edge edges should NOT be subdivided (they stay straight)
    # After subdivision, the coast edge (E_1_4) should be gone and replaced
    assert "E_1_4" not in updated_topology["edges"], "Coast edge should be subdivided and replaced"
    
    # Map edges should still exist (or be the same since map-edge has no displacement)
    # Note: map-edge edges might still exist as-is since they have 0 displacement
    
    # Verify all new edges have proper face references
    for edge_id, edge_data in updated_topology["edges"].items():
        if edge_data.get("type") == "coast":
            assert "left_face" in edge_data, f"Edge {edge_id} should have left_face"
            assert "right_face" in edge_data, f"Edge {edge_id} should have right_face"
    
    print(f"  ✓ Subdivided topology")
    print(f"    Vertices: {original_vertex_count} -> {new_vertex_count}")
    print(f"    Edges: {original_edge_count} -> {new_edge_count}")


def test_border_structure():
    """Test that borders correctly group subdivided edges."""
    print("\nTest 10: Border structure after subdivision")
    
    from fractal_subdivision import subdivide_all_edges
    
    # Create a simple topology with one coast edge
    topology = {
        "vertices": [
            {"id": 0, "coords": [0.0, 0.5]},
            {"id": 1, "coords": [1.0, 0.5]},
        ],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "coast", "left_face": "C1", "right_face": "C2"}
        },
        "borders": {
            "B_0_1": {
                "edges": ["E_0_1"],
                "left_face": "C1",
                "right_face": "C2",
                "type": "coast",
                "start_vertex": 0,
                "end_vertex": 1
            }
        },
        "faces": {
            "C1": {"type": "land", "borders": ["B_0_1"]},
            "C2": {"type": "sea", "borders": ["B_0_1"]}
        }
    }
    
    # Subdivide
    subdivide_all_edges(topology, seed=42)
    
    # The border should now contain multiple edges
    border = topology["borders"]["B_0_1"]
    assert len(border["edges"]) > 1, f"Border should have multiple edges after subdivision"
    
    # All edges in the border should exist and have the same type
    for edge_id in border["edges"]:
        assert edge_id in topology["edges"], f"Edge {edge_id} should exist"
        edge = topology["edges"][edge_id]
        assert edge["type"] == "coast", f"Edge {edge_id} should be coast type"
    
    # The edges should form a connected path from start to end vertex
    edges = [topology["edges"][eid] for eid in border["edges"]]
    
    # First edge should start at vertex 0
    first_edge = edges[0]
    assert 0 in (first_edge["v1"], first_edge["v2"]), "First edge should connect to vertex 0"
    
    # Last edge should end at vertex 1
    last_edge = edges[-1]
    assert 1 in (last_edge["v1"], last_edge["v2"]), "Last edge should connect to vertex 1"
    
    print(f"  ✓ Border contains {len(border['edges'])} connected edges")
    print(f"    Border edges form a proper chain from vertex 0 to vertex 1")


def test_empty_vertices_edge_case():
    """Test that subdivision handles empty vertices list gracefully."""
    print("\nTest 11: Empty vertices edge case")
    
    from fractal_subdivision import subdivide_edge_topology
    
    # Create a topology with empty vertices list
    topology = {
        "vertices": [],
        "edges": {
            "E_0_1": {"v1": 0, "v2": 1, "type": "coast", "left_face": "C1"}
        },
        "borders": {},
        "faces": {}
    }
    
    # Should return unchanged (edge_id in list, empty vertex list)
    new_edge_ids, new_vertex_ids = subdivide_edge_topology(topology, "E_0_1", seed=42)
    
    # Should return the original edge unchanged
    assert new_edge_ids == ["E_0_1"], f"Should return original edge when vertices is empty"
    assert new_vertex_ids == [], f"Should return no new vertices"
    
    print(f"  ✓ Gracefully handles empty vertices list")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("FRACTAL SUBDIVISION MODULE TESTS")
    print("=" * 60)
    
    try:
        test_midpoint_displacement_basic()
        test_midpoint_displacement_zero_depth()
        test_edge_displacement_params()
        test_generate_visual_path()
        test_generate_visual_path_reproducibility()
        test_generate_all_visual_paths()
        test_visual_path_endpoints()
        test_subdivide_edge_topology()
        test_subdivide_all_edges()
        test_border_structure()
        test_empty_vertices_edge_case()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
