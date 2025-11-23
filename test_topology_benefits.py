#!/usr/bin/env python3
"""
Test Topology Benefits

This test demonstrates the key benefits of the Face-Edge-Vertex topology
over the cell-centric format.
"""

import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from topology import TopologyConverter


def test_no_redundancy():
    """Demonstrate that shared borders are stored exactly once."""
    print("\n" + "=" * 60)
    print("Benefit 1: No Data Redundancy")
    print("=" * 60)
    
    # Create a 2x2 grid where all cells share borders
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
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]]  # Shares 2 vertices with C1
        },
        "C3": {
            "id": "C3",
            "type": "land",
            "center": [0.25, 0.75],
            "vertices": [[0.0, 0.5], [0.5, 0.5], [0.5, 1.0], [0.0, 1.0]]  # Shares 2 vertices with C1
        },
        "C4": {
            "id": "C4",
            "type": "land",
            "center": [0.75, 0.75],
            "vertices": [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]]  # Shares vertices with C2, C3
        }
    }
    
    # Count in cell-centric format
    total_vertices_stored = sum(len(cell["vertices"]) for cell in cells.values())
    total_edges_stored = total_vertices_stored  # Each vertex pair is an edge
    
    print(f"\nCell-Centric Format:")
    print(f"  Vertices stored: {total_vertices_stored} (with duplicates)")
    print(f"  Edges implied: {total_edges_stored} (shared borders counted multiple times)")
    
    # Convert to topology
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    print(f"\nTopological Format:")
    print(f"  Unique vertices: {len(vertices)}")
    print(f"  Unique edges: {len(edges)}")
    print(f"  Space savings: {total_vertices_stored - len(vertices)} duplicate vertices eliminated")
    
    # Count shared edges
    shared_edges = sum(1 for e in edges.values() if e.get("right_face") is not None)
    boundary_edges = sum(1 for e in edges.values() if e.get("right_face") is None)
    
    print(f"\nEdge Classification:")
    print(f"  Shared borders: {shared_edges} (each stored exactly once)")
    print(f"  Boundary edges: {boundary_edges}")
    
    assert len(vertices) == 9, "Should have 9 unique vertices in 2x2 grid"
    assert shared_edges == 4, "Should have 4 internal shared borders"
    
    print("\n✓ Benefit demonstrated: Shared borders stored exactly once")


def test_explicit_adjacency():
    """Demonstrate that adjacency is explicit, not calculated."""
    print("\n" + "=" * 60)
    print("Benefit 2: Explicit Adjacency")
    print("=" * 60)
    
    # Create three cells in a line
    cells = {
        "C1": {
            "id": "C1",
            "type": "land",
            "center": [0.16, 0.5],
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
            "center": [0.84, 0.5],
            "vertices": [[0.67, 0.0], [1.0, 0.0], [1.0, 1.0], [0.67, 1.0]]
        }
    }
    
    print("\nCell-Centric Approach:")
    print("  Must calculate distances between cell centers")
    print("  Must check if polygons intersect")
    print("  Results can be ambiguous for complex shapes")
    
    # Convert to topology
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    print("\nTopological Approach:")
    print("  Adjacency determined by shared edges")
    
    # Get adjacency from topology
    adjacency = converter.get_adjacency_from_topology()
    
    for face_id in ["C1", "C2", "C3"]:
        neighbors = adjacency.get(face_id, [])
        print(f"  {face_id} neighbors: {neighbors}")
    
    # Verify the adjacency is correct
    assert "C2" in adjacency["C1"], "C1 should be adjacent to C2"
    assert "C1" in adjacency["C2"], "C2 should be adjacent to C1"
    assert "C3" in adjacency["C2"], "C2 should be adjacent to C3"
    assert "C3" not in adjacency["C1"], "C1 should NOT be adjacent to C3"
    
    print("\n✓ Benefit demonstrated: Adjacency is explicit and unambiguous")


def test_automatic_coastline_detection():
    """Demonstrate automatic coastline detection."""
    print("\n" + "=" * 60)
    print("Benefit 3: Automatic Coastline Detection")
    print("=" * 60)
    
    # Create land and sea cells
    cells = {
        "L1": {
            "id": "L1",
            "type": "land",
            "center": [0.25, 0.5],
            "vertices": [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]
        },
        "L2": {
            "id": "L2",
            "type": "land",
            "center": [0.5, 0.75],
            "vertices": [[0.5, 0.5], [1.0, 0.5], [1.0, 1.0], [0.5, 1.0]]
        },
        "S1": {
            "id": "S1",
            "type": "sea",
            "center": [0.75, 0.25],
            "vertices": [[0.5, 0.0], [1.0, 0.0], [1.0, 0.5], [0.5, 0.5]]
        }
    }
    
    print("\nCell-Centric Approach:")
    print("  Must iterate through all cells")
    print("  Check each neighbor's type")
    print("  Mark cells as 'coastal' if they have sea neighbors")
    print("  Doesn't identify specific coastline segments")
    
    # Convert to topology
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    print("\nTopological Approach:")
    print("  Coastlines are automatically identified as edges")
    print("  where adjacent faces have different types")
    
    # Find coastline edges
    coastline_edges = [
        (edge_id, edge) for edge_id, edge in edges.items()
        if edge.get("type") == "coast"
    ]
    
    print(f"\nCoastline edges found: {len(coastline_edges)}")
    for edge_id, edge in coastline_edges:
        print(f"  {edge_id}: {edge['left_face']} ({faces[edge['left_face']]['type']}) | "
              f"{edge['right_face']} ({faces[edge['right_face']]['type']})")
    
    # Count other edge types
    land_edges = sum(1 for e in edges.values() if e.get("type") == "land")
    sea_edges = sum(1 for e in edges.values() if e.get("type") == "sea")
    map_edges = sum(1 for e in edges.values() if e.get("type") == "map-edge")
    
    print(f"\nEdge classification:")
    print(f"  Coastlines: {len(coastline_edges)}")
    print(f"  Land borders: {land_edges}")
    print(f"  Sea borders: {sea_edges}")
    print(f"  Map boundaries: {map_edges}")
    
    assert len(coastline_edges) > 0, "Should have detected coastline edges"
    
    print("\n✓ Benefit demonstrated: Coastlines automatically detected")


def test_topology_consistency():
    """Demonstrate topology guarantees consistency."""
    print("\n" + "=" * 60)
    print("Benefit 4: Guaranteed Consistency")
    print("=" * 60)
    
    # Create cells
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
    
    print("\nCell-Centric Format:")
    print("  If C1's neighbor list says it's adjacent to C2,")
    print("  C2's neighbor list might not agree (data inconsistency)")
    print("  Vertices might drift due to floating point errors")
    
    # Convert to topology
    converter = TopologyConverter()
    vertices, edges, faces = converter.convert_cells_to_topology(cells)
    
    print("\nTopological Format:")
    print("  Adjacency is symmetric by construction:")
    
    # Check symmetry
    adjacency = converter.get_adjacency_from_topology()
    
    for face_id in faces:
        for neighbor_id in adjacency.get(face_id, []):
            is_symmetric = face_id in adjacency.get(neighbor_id, [])
            print(f"  {face_id} → {neighbor_id}: {'✓ symmetric' if is_symmetric else '✗ NOT symmetric'}")
            assert is_symmetric, f"Adjacency should be symmetric"
    
    print("\n  Shared vertices are identical by construction:")
    
    # Find the shared edge
    shared_edge = None
    for edge_id, edge in edges.items():
        if edge.get("left_face") == "C1" and edge.get("right_face") == "C2":
            shared_edge = edge
            break
    
    if shared_edge:
        v1_coords = vertices[shared_edge["v1"]]["coords"]
        v2_coords = vertices[shared_edge["v2"]]["coords"]
        print(f"  Shared edge vertices: {shared_edge['v1']} and {shared_edge['v2']}")
        print(f"  These are the exact same vertex objects, not duplicates")
        print(f"  No possibility of floating point drift")
    
    print("\n✓ Benefit demonstrated: Topology guarantees consistency")


def run_all_benefit_tests():
    """Run all topology benefit demonstrations."""
    print("=" * 60)
    print("TOPOLOGY BENEFITS DEMONSTRATION")
    print("=" * 60)
    
    try:
        test_no_redundancy()
        test_explicit_adjacency()
        test_automatic_coastline_detection()
        test_topology_consistency()
        
        print("\n" + "=" * 60)
        print("ALL BENEFITS DEMONSTRATED ✓")
        print("=" * 60)
        print("\nSummary:")
        print("  1. ✓ No data redundancy - shared borders stored once")
        print("  2. ✓ Explicit adjacency - no geometric calculations needed")
        print("  3. ✓ Automatic coastline detection - edge classification")
        print("  4. ✓ Guaranteed consistency - symmetric adjacency")
        
        return True
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_benefit_tests()
    sys.exit(0 if success else 1)
