#!/usr/bin/env python3
"""
Demonstration of Merge and Split Functionality

This script demonstrates the face merging and splitting capabilities
added to the topology system.
"""

import sys
import os

# Add the map_gen directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'map_gen'))

from topology import convert_cells_to_topology
from topology_utils import (
    calculate_edge_length,
    calculate_face_size,
    merge_faces,
    split_face,
    find_smallest_faces,
    find_largest_faces,
    find_smallest_neighbor
)


def create_demo_topology():
    """Create a simple demo topology with various sized faces."""
    cells = {
        # Large face
        "L1": {
            "id": "L1",
            "type": "land",
            "center": [0.5, 0.5],
            "vertices": [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0]
            ]
        },
        # Small water face 1
        "W1": {
            "id": "W1",
            "type": "sea",
            "center": [0.125, 0.125],
            "vertices": [
                [0.0, 0.0],
                [0.25, 0.0],
                [0.25, 0.25],
                [0.0, 0.25]
            ]
        },
        # Small water face 2 (adjacent to W1)
        "W2": {
            "id": "W2",
            "type": "sea",
            "center": [0.125, 0.375],
            "vertices": [
                [0.0, 0.25],
                [0.25, 0.25],
                [0.25, 0.5],
                [0.0, 0.5]
            ]
        }
    }
    
    topology = convert_cells_to_topology(cells)
    return topology


def demonstrate_utility_functions():
    """Demonstrate basic utility functions."""
    print("=" * 60)
    print("DEMONSTRATION: Utility Functions")
    print("=" * 60)
    
    topology = create_demo_topology()
    
    # Calculate edge length
    print("\n1. Edge Length Calculation:")
    first_edge_id = next(iter(topology["edges"].keys()))
    length = calculate_edge_length(first_edge_id, topology)
    print(f"   Edge {first_edge_id} has length: {length:.4f}")
    
    # Calculate face size
    print("\n2. Face Size Calculation:")
    for face_id in ["L1", "W1", "W2"]:
        if face_id in topology["faces"]:
            size = calculate_face_size(face_id, topology)
            face_type = topology["faces"][face_id]["type"]
            print(f"   {face_id} ({face_type}): {size:.4f} square units")
    
    # Find smallest and largest
    print("\n3. Finding Smallest/Largest Faces:")
    smallest_water = find_smallest_faces(topology, "sea", count=2)
    print(f"   Smallest water faces:")
    for face_id, size in smallest_water:
        print(f"     - {face_id}: {size:.4f}")
    
    largest_land = find_largest_faces(topology, "land", count=1)
    print(f"   Largest land face:")
    for face_id, size in largest_land:
        print(f"     - {face_id}: {size:.4f}")


def demonstrate_merge():
    """Demonstrate face merging."""
    print("\n" + "=" * 60)
    print("DEMONSTRATION: Face Merging")
    print("=" * 60)
    
    topology = create_demo_topology()
    
    print("\nBefore merge:")
    print(f"   Total faces: {len(topology['faces'])}")
    print(f"   Total edges: {len(topology['edges'])}")
    
    # Find W1's smallest neighbor
    neighbor = find_smallest_neighbor("W1", topology)
    if neighbor:
        neighbor_id, neighbor_size = neighbor
        w1_size = calculate_face_size("W1", topology)
        
        print(f"\n   W1 (size {w1_size:.4f}) has neighbor {neighbor_id} (size {neighbor_size:.4f})")
        
        # Merge them
        success, merged_id = merge_faces("W1", neighbor_id, topology)
        
        if success:
            merged_size = calculate_face_size(merged_id, topology)
            print(f"\nAfter merge:")
            print(f"   Total faces: {len(topology['faces'])} (decreased by 1)")
            print(f"   Total edges: {len(topology['edges'])} (shared edges removed)")
            print(f"   Merged face {merged_id} size: {merged_size:.4f}")
            print(f"   ✓ Successfully merged W1 and {neighbor_id}")


def demonstrate_split():
    """Demonstrate face splitting."""
    print("\n" + "=" * 60)
    print("DEMONSTRATION: Face Splitting")
    print("=" * 60)
    
    topology = create_demo_topology()
    
    print("\nBefore split:")
    print(f"   Total faces: {len(topology['faces'])}")
    l1_size = calculate_face_size("L1", topology)
    print(f"   L1 size: {l1_size:.4f}")
    
    # Split L1
    success, face1_id, face2_id = split_face("L1", topology)
    
    if success:
        print(f"\nAfter split:")
        print(f"   Total faces: {len(topology['faces'])} (increased by 1)")
        print(f"   Created faces: {face1_id} and {face2_id}")
        print(f"   ✓ Successfully split L1")
        print(f"\n   Note: This is a simplified split for demonstration.")
        print(f"   The faces share edges but are tracked separately.")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("TOPOLOGY MERGE AND SPLIT DEMONSTRATIONS")
    print("=" * 60)
    
    demonstrate_utility_functions()
    demonstrate_merge()
    demonstrate_split()
    
    print("\n" + "=" * 60)
    print("ALL DEMONSTRATIONS COMPLETE")
    print("=" * 60)
    print("\nThese utilities are integrated into Phase 2 of the map generation")
    print("pipeline to merge small water territories and split large land")
    print("territories for better gameplay balance.")


if __name__ == "__main__":
    main()
