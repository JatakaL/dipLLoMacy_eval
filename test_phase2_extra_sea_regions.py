#!/usr/bin/env python3
"""
Test Phase 2 Extra Sea Region Merging Functionality

This script tests that Phase 2 correctly identifies and merges sea regions
that are not adjacent to any land territory, as per the official Diplomacy
map rule that all sea regions should be adjacent to land.
"""

import sys
import os
import traceback

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen', 'phases'))

from topology import convert_cells_to_topology
from topology_utils import (
    is_sea_adjacent_to_land,
    find_sea_regions_not_adjacent_to_land,
    find_best_sea_neighbor_toward_center,
    merge_extra_sea_regions,

)


def create_test_topology_with_extra_sea():
    """
    Create a test topology with sea regions not adjacent to land.
    
    Layout (5x5 grid):
    L L L L L
    L S S S L    <- Sea regions at (1,1), (2,1), (3,1)
    L S S S L    <- Sea regions at (1,2), (2,2), (3,2) - center (2,2) has no land neighbors
    L S S S L    <- Sea regions at (1,3), (2,3), (3,3)
    L L L L L
    
    The center sea region (2,2) has only sea neighbors, so it should be merged.
    """
    cells = {}
    cell_size = 0.2
    
    for row in range(5):
        for col in range(5):
            x0 = col * cell_size
            y0 = row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            
            cell_name = f"C_{row}_{col}"
            
            # Determine if cell is land or sea
            # Border cells are land, inner 3x3 are sea
            is_border = row == 0 or row == 4 or col == 0 or col == 4
            cell_type = "land" if is_border else "sea"
            
            cells[cell_name] = {
                "id": cell_name,
                "type": cell_type,
                "center": [x0 + cell_size/2, y0 + cell_size/2],
                "vertices": [
                    [x0, y0],
                    [x1, y0],
                    [x1, y1],
                    [x0, y1]
                ],
                "neighbors": []
            }
    
    # Set up neighbors (4-connected grid)
    for row in range(5):
        for col in range(5):
            cell_name = f"C_{row}_{col}"
            neighbors = []
            
            # Right neighbor
            if col < 4:
                neighbors.append(f"C_{row}_{col + 1}")
            # Bottom neighbor
            if row < 4:
                neighbors.append(f"C_{row + 1}_{col}")
            # Left neighbor
            if col > 0:
                neighbors.append(f"C_{row}_{col - 1}")
            # Top neighbor
            if row > 0:
                neighbors.append(f"C_{row - 1}_{col}")
            
            cells[cell_name]["neighbors"] = neighbors
    
    # Convert to topology
    topology = convert_cells_to_topology(cells)
    
    return topology


def test_is_sea_adjacent_to_land():
    """Test that is_sea_adjacent_to_land correctly identifies sea regions adjacent to land."""
    print("\nTest 1: is_sea_adjacent_to_land function")
    
    topology = create_test_topology_with_extra_sea()
    
    # Sea regions on the edge of the sea area (adjacent to land)
    edge_sea_cells = ["C_1_1", "C_1_2", "C_1_3", "C_2_1", "C_2_3", "C_3_1", "C_3_2", "C_3_3"]
    for cell_id in edge_sea_cells:
        result = is_sea_adjacent_to_land(cell_id, topology)
        assert result == True, f"{cell_id} should be adjacent to land"
    
    # Center sea cell (not adjacent to land)
    center_sea = "C_2_2"
    result = is_sea_adjacent_to_land(center_sea, topology)
    assert result == False, f"{center_sea} should NOT be adjacent to land"
    
    # Land cells should return True (they don't need this check)
    land_cell = "C_0_0"
    result = is_sea_adjacent_to_land(land_cell, topology)
    assert result == True, f"Land cell {land_cell} should return True"
    
    print("  ✓ is_sea_adjacent_to_land correctly identifies adjacency")


def test_find_sea_regions_not_adjacent_to_land():
    """Test finding all sea regions not adjacent to land."""
    print("\nTest 2: find_sea_regions_not_adjacent_to_land function")
    
    topology = create_test_topology_with_extra_sea()
    
    extra_sea = find_sea_regions_not_adjacent_to_land(topology)
    
    # Only the center cell (C_2_2) should be identified
    assert len(extra_sea) == 1, f"Expected 1 extra sea region, found {len(extra_sea)}"
    assert "C_2_2" in extra_sea, f"C_2_2 should be in extra sea regions"
    
    print(f"  Found {len(extra_sea)} sea regions not adjacent to land: {extra_sea}")
    print("  ✓ find_sea_regions_not_adjacent_to_land works correctly")


def test_find_best_sea_neighbor_toward_center():
    """Test finding the best sea neighbor with center preference."""
    print("\nTest 3: find_best_sea_neighbor_toward_center function")
    
    topology = create_test_topology_with_extra_sea()
    
    # Get best neighbor for the center sea cell
    # All neighbors are sea and adjacent to land, so preference should be toward center
    best_neighbor = find_best_sea_neighbor_toward_center("C_2_2", topology, map_center=(0.5, 0.5))
    
    assert best_neighbor is not None, "Should find a best neighbor"
    
    # The neighbor should be a sea cell adjacent to land
    assert best_neighbor.startswith("C_"), f"Neighbor should be a cell ID"
    assert is_sea_adjacent_to_land(best_neighbor, topology), f"Best neighbor {best_neighbor} should be adjacent to land"
    
    print(f"  Best neighbor for C_2_2: {best_neighbor}")
    print("  ✓ find_best_sea_neighbor_toward_center works correctly")


def test_merge_extra_sea_regions():
    """Test merging all extra sea regions."""
    print("\nTest 4: merge_extra_sea_regions function")
    
    topology = create_test_topology_with_extra_sea()
    
    # Initial state: 1 extra sea region (C_2_2)
    initial_extra = find_sea_regions_not_adjacent_to_land(topology)
    assert len(initial_extra) == 1, f"Expected 1 extra sea region initially, found {len(initial_extra)}"
    
    # Merge extra sea regions
    merged_count = merge_extra_sea_regions(topology, map_center=(0.5, 0.5))
    
    # After merging: 0 extra sea regions
    final_extra = find_sea_regions_not_adjacent_to_land(topology)
    assert len(final_extra) == 0, f"Expected 0 extra sea regions after merging, found {len(final_extra)}"
    
    assert merged_count == 1, f"Expected 1 merge, got {merged_count}"
    
    print(f"  Merged {merged_count} extra sea regions")
    print(f"  Final extra sea regions: {len(final_extra)}")
    print("  ✓ merge_extra_sea_regions works correctly")


def test_larger_grid_with_multiple_extra_sea():
    """Test with a larger grid having multiple sea regions not adjacent to land."""
    print("\nTest 5: Larger grid with multiple extra sea regions")
    
    # Create a 7x7 grid with a 5x5 inner sea area
    # Border is land, inner 5x5 is sea
    # Center 3x3 of the sea area has no land neighbors
    
    grid_size = 7
    cells = {}
    cell_size = 1.0 / grid_size
    
    for row in range(grid_size):
        for col in range(grid_size):
            x0 = col * cell_size
            y0 = row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            
            cell_name = f"C_{row}_{col}"
            
            # Border is land, inner 5x5 is sea
            is_border = row == 0 or row == grid_size - 1 or col == 0 or col == grid_size - 1
            cell_type = "land" if is_border else "sea"
            
            cells[cell_name] = {
                "id": cell_name,
                "type": cell_type,
                "center": [x0 + cell_size/2, y0 + cell_size/2],
                "vertices": [
                    [x0, y0],
                    [x1, y0],
                    [x1, y1],
                    [x0, y1]
                ],
                "neighbors": []
            }
    
    # Set up neighbors
    for row in range(grid_size):
        for col in range(grid_size):
            cell_name = f"C_{row}_{col}"
            neighbors = []
            if col < grid_size - 1: neighbors.append(f"C_{row}_{col + 1}")
            if row < grid_size - 1: neighbors.append(f"C_{row + 1}_{col}")
            if col > 0: neighbors.append(f"C_{row}_{col - 1}")
            if row > 0: neighbors.append(f"C_{row - 1}_{col}")
            cells[cell_name]["neighbors"] = neighbors
    
    topology = convert_cells_to_topology(cells)
    
    # Initial state: center 3x3 sea cells should not be adjacent to land
    initial_extra = find_sea_regions_not_adjacent_to_land(topology)
    print(f"  Initial extra sea regions: {len(initial_extra)}")
    print(f"  Extra sea IDs: {initial_extra}")
    
    # Expected: C_2_2, C_2_3, C_2_4, C_3_2, C_3_3, C_3_4, C_4_2, C_4_3, C_4_4 (9 cells)
    assert len(initial_extra) == 9, f"Expected 9 extra sea regions initially, found {len(initial_extra)}"
    
    # Merge extra sea regions
    merged_count = merge_extra_sea_regions(topology, map_center=(0.5, 0.5))
    print(f"  Merged {merged_count} extra sea regions")
    
    # After merging: 0 extra sea regions
    final_extra = find_sea_regions_not_adjacent_to_land(topology)
    assert len(final_extra) == 0, f"Expected 0 extra sea regions after merging, found {len(final_extra)}"
    
    print(f"  Final extra sea regions: {len(final_extra)}")
    print("  ✓ All extra sea regions merged successfully")


def test_topology_validity_after_merge():
    """Test that topology remains valid after merging extra sea regions."""
    print("\nTest 6: Topology validity after merging")
    
    topology = create_test_topology_with_extra_sea()
    
    # Merge extra sea regions
    merge_extra_sea_regions(topology, map_center=(0.5, 0.5))
    
    # Check topology structure
    faces = topology.get("faces", {})
    edges = topology.get("edges", {})
    borders = topology.get("borders", {})
    
    # Verify edges reference valid faces
    for edge_id, edge_data in edges.items():
        left_face = edge_data.get("left_face")
        right_face = edge_data.get("right_face")
        
        if left_face:
            assert left_face in faces, f"Edge {edge_id} references non-existent left face {left_face}"
        if right_face:
            assert right_face in faces, f"Edge {edge_id} references non-existent right face {right_face}"
    
    # Verify borders reference valid faces
    for border_id, border_data in borders.items():
        left_face = border_data.get("left_face")
        right_face = border_data.get("right_face")
        
        if left_face:
            assert left_face in faces, f"Border {border_id} references non-existent left face {left_face}"
        if right_face:
            assert right_face in faces, f"Border {border_id} references non-existent right face {right_face}"
    
    # Verify faces reference valid borders
    for face_id, face_data in faces.items():
        for border_id in face_data.get("borders", []):
            assert border_id in borders, f"Face {face_id} references non-existent border {border_id}"
    
    print(f"  Faces: {len(faces)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Borders: {len(borders)}")
    print("  ✓ Topology structure is valid after merging")


def test_no_extra_sea_regions_case():
    """Test that function handles the case where there are no extra sea regions."""
    print("\nTest 7: No extra sea regions case")
    
    # Create a simple case where all sea regions touch land
    cells = {
        "L1": {"id": "L1", "type": "land", "center": [0.25, 0.5], 
               "vertices": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]], "neighbors": ["S1"]},
        "S1": {"id": "S1", "type": "sea", "center": [0.75, 0.5],
               "vertices": [[0.5, 0], [1, 0], [1, 1], [0.5, 1]], "neighbors": ["L1"]}
    }
    
    topology = convert_cells_to_topology(cells)
    
    # Should find no extra sea regions
    extra_sea = find_sea_regions_not_adjacent_to_land(topology)
    assert len(extra_sea) == 0, f"Expected 0 extra sea regions, found {len(extra_sea)}"
    
    # Merging should do nothing
    merged_count = merge_extra_sea_regions(topology)
    assert merged_count == 0, f"Expected 0 merges, got {merged_count}"
    
    print("  ✓ No extra sea regions case handled correctly")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 2 EXTRA SEA REGION TESTS")
    print("=" * 60)
    
    try:
        test_is_sea_adjacent_to_land()
        test_find_sea_regions_not_adjacent_to_land()
        test_find_best_sea_neighbor_toward_center()
        test_merge_extra_sea_regions()
        test_larger_grid_with_multiple_extra_sea()
        test_topology_validity_after_merge()
        test_no_extra_sea_regions_case()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
