#!/usr/bin/env python3
"""
Test Topology Module

This script tests the Face-Edge-Vertex topology conversion.
"""

import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from topology import (
    TopologyConverter, 
    convert_cells_to_topology, 
    get_adjacency_from_topology, 
    get_adjacency_from_borders, 
    get_coastal_faces_from_borders
)


def test_vertex_deduplication():
    """Test that shared vertices are properly deduplicated."""
    print("\nTest 1: Vertex deduplication")
    
    # Create two adjacent squares that share two vertices
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
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
            "type": "land",
            "center": [0.75, 0.5],
            "vertices": [
                [0.5, 0.0],  # Shared with C1
                [1.0, 0.0],
                [1.0, 1.0],
                [0.5, 1.0]   # Shared with C1
            ]
        }
    }
    
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    # Should have 6 unique vertices (not 8)
    assert len(vertices) == 6, f"Expected 6 unique vertices, got {len(vertices)}"
    
    # Should have 7 edges (4 for C1 + 4 for C2 - 1 shared)
    assert len(edges) == 7, f"Expected 7 edges, got {len(edges)}"
    
    # The shared edge should have both faces
    shared_edge = None
    for edge_id, edge_data in edges.items():
        if edge_data.get("left_face") and edge_data.get("right_face"):
            shared_edge = edge_data
            break
    
    assert shared_edge is not None, "Should have found a shared edge"
    assert set([shared_edge["left_face"], shared_edge["right_face"]]) == {"C1", "C2"}, \
        f"Shared edge should connect C1 and C2"
    
    print("  ✓ Vertices deduplicated correctly")
    print(f"    Created {len(vertices)} vertices from 8 vertex references")
    print(f"    Created {len(edges)} edges from 8 edge references")


def test_edge_creation_and_face_assignment():
    """Test that edges are created with correct face assignments."""
    print("\nTest 2: Edge creation and face assignment")
    
    # Create three cells in a row
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.33, 0.0], [0.33, 1.0], [0.0, 1.0]]
        },
        "C2": {
            "id": "C2",
            "type": "land",
            "center": [0.5, 0.5],
            "vertices": [[0.33, 0.0], [0.67, 0.0], [0.67, 1.0], [0.33, 1.0]]
        },
        "C3": {
            "id": "C3",
            "type": "land",
            "center": [0.75, 0.5],
            "vertices": [[0.67, 0.0], [1.0, 0.0], [1.0, 1.0], [0.67, 1.0]]
        }
    }
    
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    # Check that we have the expected number of elements
    assert len(faces) == 3, f"Expected 3 faces, got {len(faces)}"
    
    # Count edges by type
    map_edges = sum(1 for e in edges.values() if e.get("type") == "map-edge")
    internal_edges = sum(1 for e in edges.values() if e.get("left_face") and e.get("right_face"))
    
    assert internal_edges == 2, f"Expected 2 internal edges, got {internal_edges}"
    assert map_edges == 8, f"Expected 8 map boundary edges, got {map_edges}"
    
    print("  ✓ Edges created with correct face assignments")
    print(f"    {internal_edges} internal edges (shared between cells)")
    print(f"    {map_edges} map boundary edges")


def test_adjacency_derivation():
    """Test that adjacency can be correctly derived from edges."""
    print("\nTest 3: Adjacency derivation from edges")
    
    # Create a simple 2x2 grid
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.25, 0.25],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]
        },
        "C2": {
            "id": "C2",
            "type": "land",
            "center": [0.75, 0.25],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]]
        },
        "C3": {
            "id": "C3",
            "type": "land",
            "center": [0.25, 0.75],
            "vertices": [[0.0, 0.5], [0.5, 0.5], [0.5, 1.0], [0.0, 1.0]]
        },
        "C4": {
            "id": "C4",
            "type": "land",
            "center": [0.75, 0.75],
            "vertices": [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]]
        }
    }
    
    converter = TopologyConverter()
    _, edges, faces = converter.convert_cells_to_topology(cells)
    
    # Derive adjacency
    adjacency = converter.get_adjacency_from_topology()
    
    # Check adjacency relationships
    assert "C2" in adjacency["C1"], "C1 should be adjacent to C2"
    assert "C3" in adjacency["C1"], "C1 should be adjacent to C3"
    assert len(adjacency["C1"]) == 2, f"C1 should have 2 neighbors, got {len(adjacency['C1'])}"
    
    assert "C1" in adjacency["C2"], "C2 should be adjacent to C1"
    assert "C4" in adjacency["C2"], "C2 should be adjacent to C4"
    assert len(adjacency["C2"]) == 2, f"C2 should have 2 neighbors, got {len(adjacency['C2'])}"
    
    assert "C1" in adjacency["C3"], "C3 should be adjacent to C1"
    assert "C4" in adjacency["C3"], "C3 should be adjacent to C4"
    assert len(adjacency["C3"]) == 2, f"C3 should have 2 neighbors, got {len(adjacency['C3'])}"
    
    assert "C2" in adjacency["C4"], "C4 should be adjacent to C2"
    assert "C3" in adjacency["C4"], "C4 should be adjacent to C3"
    assert len(adjacency["C4"]) == 2, f"C4 should have 2 neighbors, got {len(adjacency['C4'])}"
    
    print("  ✓ Adjacency correctly derived from edge topology")
    print("    All 4 cells have correct neighbor relationships")


def test_coastline_detection():
    """Test that coastlines are correctly identified."""
    print("\nTest 4: Coastline detection")
    
    # Create land and sea cells
    cells = {
        "L1": {
            "id": "L1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]
        },
        "S1": {
            "id": "S1",
            "type": "sea",
            "center": [0.75, 0.5],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 1.0], [0.5, 1.0]]
        }
    }
    
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    # Find coastline edges
    coastline_edges = [e for e in edges.values() if e.get("type") == "coast"]
    
    assert len(coastline_edges) == 1, f"Expected 1 coastline edge, got {len(coastline_edges)}"
    
    coast_edge = coastline_edges[0]
    assert set([coast_edge["left_face"], coast_edge["right_face"]]) == {"L1", "S1"}, \
        "Coastline should connect land and sea"
    
    print("  ✓ Coastline edges correctly identified")
    print(f"    Found {len(coastline_edges)} coastline edge between land and sea")


def test_map_edge_detection():
    """Test that map boundaries are correctly identified."""
    print("\nTest 5: Map edge detection")
    
    # Create a single cell
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.5, 0.5],
            "vertices": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
        }
    }
    
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    # All edges should be map edges
    map_edges = [e for e in edges.values() if e.get("type") == "map-edge"]
    
    assert len(map_edges) == 4, f"Expected 4 map edges, got {len(map_edges)}"
    
    # All map edges should have only one face
    for edge in map_edges:
        assert edge.get("left_face") is not None, "Map edge should have left_face"
        assert edge.get("right_face") is None, "Map edge should not have right_face"
    
    print("  ✓ Map boundary edges correctly identified")
    print(f"    Found {len(map_edges)} boundary edges")


def test_impassable_edge_detection():
    """Test that impassable terrain borders are correctly identified."""
    print("\nTest 6: Impassable edge detection")
    
    # Create land, sea, and impassable cells
    cells = {
        "L1": {
            "id": "L1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.33, 0.0], [0.33, 1.0], [0.0, 1.0]]
        },
        "I1": {
            "id": "I1",
            "type": "impassable",
            "center": [0.5, 0.5],
            "vertices": [[0.33, 0.0], [0.67, 0.0], [0.67, 1.0], [0.33, 1.0]]
        },
        "S1": {
            "id": "S1",
            "type": "sea",
            "center": [0.84, 0.5],
            "vertices": [[0.67, 0.0], [1.0, 0.0], [1.0, 1.0], [0.67, 1.0]]
        }
    }
    
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    # Find impassable edges
    impassable_edges = [e for e in edges.values() if e.get("type") == "impassable"]
    
    # Should have 2 impassable edges (land-impassable and sea-impassable)
    assert len(impassable_edges) == 2, f"Expected 2 impassable edges, got {len(impassable_edges)}"
    
    # Verify no false coastlines (there should be none - land and sea don't touch directly)
    coastline_edges = [e for e in edges.values() if e.get("type") == "coast"]
    assert len(coastline_edges) == 0, f"Expected 0 coastline edges, got {len(coastline_edges)}"
    
    print("  ✓ Impassable terrain edges correctly identified")
    print(f"    Found {len(impassable_edges)} impassable border edges")
    print(f"    Found {len(coastline_edges)} coastline edges (correct: 0)")


def test_convenience_functions():
    """Test the convenience functions."""
    print("\nTest 7: Convenience functions")
    
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]
        },
        "C2": {
            "id": "C2",
            "type": "land",
            "center": [0.75, 0.5],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 1.0], [0.5, 1.0]]
        }
    }
    
    # Test convert_cells_to_topology
    topology = convert_cells_to_topology(cells)
    
    assert "vertices" in topology, "Should have vertices key"
    assert "edges" in topology, "Should have edges key"
    assert "faces" in topology, "Should have faces key"
    assert "borders" in topology, "Should have borders key"
    
    # Test get_adjacency_from_topology (with both edges and borders)
    adjacency_from_edges = get_adjacency_from_topology(topology["edges"])
    adjacency_from_borders = get_adjacency_from_topology(topology["edges"], topology["borders"])
    
    assert "C1" in adjacency_from_edges, "C1 should be in edge-based adjacency"
    assert "C2" in adjacency_from_edges, "C2 should be in edge-based adjacency"
    assert "C2" in adjacency_from_edges["C1"], "C1 should be adjacent to C2 (edges)"
    assert "C1" in adjacency_from_edges["C2"], "C2 should be adjacent to C1 (edges)"
    
    assert "C1" in adjacency_from_borders, "C1 should be in border-based adjacency"
    assert "C2" in adjacency_from_borders, "C2 should be in border-based adjacency"
    assert "C2" in adjacency_from_borders["C1"], "C1 should be adjacent to C2 (borders)"
    assert "C1" in adjacency_from_borders["C2"], "C2 should be adjacent to C1 (borders)"
    
    # Both methods should give the same result
    assert adjacency_from_edges == adjacency_from_borders, "Edge-based and border-based adjacency should match"
    
    print("  ✓ Convenience functions work correctly")


def test_border_based_adjacency():
    """Test that adjacency derived from borders matches edges."""
    print("\nTest 8: Border-based adjacency")
    
    # Create a 2x2 grid to test adjacency
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.25, 0.25],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 0.5], [0.0, 0.5]]
        },
        "C2": {
            "id": "C2",
            "type": "sea",
            "center": [0.75, 0.25],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]]
        },
        "C3": {
            "id": "C3",
            "type": "land",
            "center": [0.25, 0.75],
            "vertices": [[0.0, 0.5], [0.5, 0.5], [0.5, 1.0], [0.0, 1.0]]
        },
        "C4": {
            "id": "C4",
            "type": "sea",
            "center": [0.75, 0.75],
            "vertices": [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]]
        }
    }
    
    topology = convert_cells_to_topology(cells)
    
    # Test get_adjacency_from_borders directly
    adjacency_from_borders = get_adjacency_from_borders(topology["borders"])
    
    # C1 should be adjacent to C2 and C3 (shares edges)
    assert "C2" in adjacency_from_borders.get("C1", []), "C1 should be adjacent to C2"
    assert "C3" in adjacency_from_borders.get("C1", []), "C1 should be adjacent to C3"
    assert len(adjacency_from_borders.get("C1", [])) == 2, "C1 should have exactly 2 neighbors"
    
    # C4 should be adjacent to C2 and C3
    assert "C2" in adjacency_from_borders.get("C4", []), "C4 should be adjacent to C2"
    assert "C3" in adjacency_from_borders.get("C4", []), "C4 should be adjacent to C3"
    assert len(adjacency_from_borders.get("C4", [])) == 2, "C4 should have exactly 2 neighbors"
    
    print("  ✓ Border-based adjacency correctly derived")
    print("    All faces have correct neighbor relationships")


def test_coastal_faces_from_borders():
    """Test that coastal faces are correctly detected from borders."""
    print("\nTest 9: Coastal faces from borders")
    
    # Create a simple map with land and sea
    cells = {
        "L1": {
            "id": "L1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]
        },
        "S1": {
            "id": "S1",
            "type": "sea",
            "center": [0.75, 0.5],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 1.0], [0.5, 1.0]]
        }
    }
    
    topology = convert_cells_to_topology(cells)
    
    # Test get_coastal_faces_from_borders
    coastal_faces = get_coastal_faces_from_borders(topology["borders"])
    
    # Both L1 and S1 should be coastal (they share a coast border)
    assert "L1" in coastal_faces, "L1 should be coastal"
    assert "S1" in coastal_faces, "S1 should be coastal"
    assert len(coastal_faces) == 2, f"Expected 2 coastal faces, got {len(coastal_faces)}"
    
    print("  ✓ Coastal faces correctly detected from borders")
    print(f"    Found {len(coastal_faces)} coastal faces")


def run_all_tests():
    """Run all topology tests."""
    print("=" * 60)
    print("TOPOLOGY MODULE TESTS")
    print("=" * 60)
    
    try:
        test_vertex_deduplication()
        test_edge_creation_and_face_assignment()
        test_adjacency_derivation()
        test_coastline_detection()
        test_map_edge_detection()
        test_impassable_edge_detection()
        test_convenience_functions()
        test_border_based_adjacency()
        test_coastal_faces_from_borders()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        print("=" * 60)
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
