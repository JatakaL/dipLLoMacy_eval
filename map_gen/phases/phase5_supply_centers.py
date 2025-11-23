#!/usr/bin/env python3
"""
Phase 5: Supply Center Distribution

This phase places supply centers across the map:
1. Mark all home territories as supply centers (3 per power)
2. Place neutral supply centers in strategic locations
3. Ensure neutral SCs are equidistant between powers

Data Structure:
This phase uses TOPOLOGY exclusively (Face-Edge-Vertex structure), not cell-centered data.
The output no longer includes the 'cells' dictionary - only topology, territories, and supply centers.

Input: kingdoms_output.json from Phase 4
Output: supply_centers_output.json with SC placements
"""

import json
import numpy as np
import random
import argparse
import sys
import os

# Add parent directory to path for topology import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_utils import get_output_path_for_phase
from topology import get_adjacency_from_topology

# Configuration constants for SC placement
PREFERRED_NEUTRAL_SC_DISTANCE = 0.2  # Preferred average distance of neutral SCs from powers
BALANCE_WEIGHT = 0.4                 # Weight for balance score in SC selection
COASTAL_WEIGHT = 0.3                 # Weight for coastal preference in SC selection
DISTANCE_WEIGHT = 0.3                # Weight for distance score in SC selection


def mark_home_centers(faces, territories):
    """
    Mark all home territory faces as supply centers using topology.
    
    Args:
        faces: Dictionary of all faces from topology
        territories: Dictionary of power territories
        
    Returns:
        Updated faces, count of home supply centers
    """
    home_sc_count = 0
    
    for power_id, territory_data in territories.items():
        territory_cells = territory_data["cells"]
        
        for face_id in territory_cells:
            if face_id in faces:
                faces[face_id]["is_supply_center"] = True
                faces[face_id]["sc_type"] = "home"
                home_sc_count += 1
    
    return faces, home_sc_count


def find_neutral_candidates(faces, edges, territories):
    """
    Find candidate faces for neutral supply centers using topology.
    
    Args:
        faces: Dictionary of all faces from topology
        edges: Dictionary of all edges from topology
        territories: Dictionary of power territories
        
    Returns:
        List of candidate face IDs
    """
    # Get all owned faces
    owned_faces = set()
    for territory_data in territories.values():
        owned_faces.update(territory_data["cells"])
    
    # Determine which faces are coastal by checking for coast edges
    coastal_faces = set()
    for edge_data in edges.values():
        if edge_data.get("type") == "coast":
            left_face = edge_data.get("left_face")
            right_face = edge_data.get("right_face")
            if left_face:
                coastal_faces.add(left_face)
            if right_face:
                coastal_faces.add(right_face)
    
    # Find neutral land faces (not owned, preferably coastal)
    coastal_neutral = []
    inland_neutral = []
    
    for face_id, face in faces.items():
        if face["type"] != "land":
            continue
        
        if face_id in owned_faces:
            continue
        
        if face["type"] == "impassable":
            continue
        
        if face_id in coastal_faces:
            coastal_neutral.append(face_id)
        else:
            inland_neutral.append(face_id)
    
    # Prefer coastal faces
    return coastal_neutral + inland_neutral


def calculate_power_distances(face_id, faces, territories):
    """
    Calculate distances from a face to all power territories using topology.
    
    Args:
        face_id: ID of the face to check
        faces: Dictionary of all faces from topology
        territories: Dictionary of power territories
        
    Returns:
        List of (power_id, distance) tuples
    """
    face_pos = np.array(faces[face_id]["center"])
    distances = []
    
    for power_id, territory_data in territories.items():
        # Find closest face in this power's territory
        min_dist = float('inf')
        
        for territory_face in territory_data["cells"]:
            if territory_face not in faces:
                continue
            
            territory_pos = np.array(faces[territory_face]["center"])
            dist = np.linalg.norm(face_pos - territory_pos)
            min_dist = min(min_dist, dist)
        
        distances.append((power_id, min_dist))
    
    return distances


def select_neutral_scs(candidates, faces, edges, territories, num_neutral, seed=None):
    """
    Select neutral supply centers from candidates using topology.
    
    Priority:
    1. Faces equidistant between multiple powers
    2. Coastal faces
    3. Not adjacent to other neutral SCs
    
    Args:
        candidates: List of candidate face IDs
        faces: Dictionary of all faces from topology
        edges: Dictionary of all edges from topology
        territories: Dictionary of power territories
        num_neutral: Number of neutral SCs to place
        seed: Random seed
        
    Returns:
        List of selected neutral SC face IDs
    """
    if seed is not None:
        random.seed(seed)
    
    if not candidates:
        return []
    
    selected = []
    available = set(candidates)
    
    # Get adjacency from topology
    adjacency = get_adjacency_from_topology(edges)
    
    # Determine which faces are coastal
    coastal_faces = set()
    for edge_data in edges.values():
        if edge_data.get("type") == "coast":
            left_face = edge_data.get("left_face")
            right_face = edge_data.get("right_face")
            if left_face:
                coastal_faces.add(left_face)
            if right_face:
                coastal_faces.add(right_face)
    
    # Score each candidate
    candidate_scores = []
    
    for face_id in available:
        # Calculate distances to all powers
        power_distances = calculate_power_distances(face_id, faces, territories)
        
        # Score based on:
        # 1. Balance (how evenly distributed are the distances to powers)
        distances = [d for _, d in power_distances]
        if not distances:
            continue
        
        # Preference for faces that are roughly equidistant to multiple powers
        min_dist = min(distances)
        max_dist = max(distances)
        balance_score = 1.0 - (max_dist - min_dist) / (max_dist + 0.001)
        
        # 2. Coastal preference
        coastal_score = 1.0 if face_id in coastal_faces else 0.5
        
        # 3. Average distance to powers (prefer contested areas, not too far)
        avg_dist = np.mean(distances)
        distance_score = 1.0 / (1.0 + abs(avg_dist - PREFERRED_NEUTRAL_SC_DISTANCE))  # Prefer moderate distances
        
        # Combined score
        total_score = balance_score * BALANCE_WEIGHT + coastal_score * COASTAL_WEIGHT + distance_score * DISTANCE_WEIGHT
        
        candidate_scores.append((face_id, total_score, power_distances))
    
    # Sort by score (descending)
    candidate_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Select top candidates, avoiding adjacent placements
    for face_id, score, _ in candidate_scores:
        if len(selected) >= num_neutral:
            break
        
        # Check if adjacent to any already selected SC using topology adjacency
        neighbors = adjacency.get(face_id, [])
        is_adjacent = any(neighbor in selected for neighbor in neighbors)
        
        if not is_adjacent:
            selected.append(face_id)
    
    # If we couldn't find enough non-adjacent faces, just take top scoring ones
    if len(selected) < num_neutral:
        for face_id, score, _ in candidate_scores:
            if face_id not in selected:
                selected.append(face_id)
                if len(selected) >= num_neutral:
                    break
    
    return selected


def run_phase5(phase4_output, config):
    """
    Run Phase 5: Supply Center Distribution.
    
    Args:
        phase4_output: Output from Phase 4
        config: Configuration parameters
        
    Returns:
        Dictionary with supply center data (using topology, no cells dictionary)
    """
    print("=" * 60)
    print("PHASE 5: SUPPLY CENTER DISTRIBUTION")
    print("=" * 60)
    
    # Use topology structure instead of cells
    topology = phase4_output.get("topology", {})
    if not topology or "faces" not in topology:
        raise ValueError("Phase 4 output must contain topology with faces")
    
    faces = topology["faces"]
    edges = topology["edges"]
    territories = phase4_output["territories"]
    
    # Extract configuration
    num_neutral = config.get("num_neutral_scs", 13)
    seed = config.get("seed", 42)
    
    print(f"\nConfiguration:")
    print(f"  Target neutral SCs: {num_neutral}")
    
    # Step 1: Mark home centers
    print("\nStep 1: Marking home territory supply centers...")
    faces, home_sc_count = mark_home_centers(faces, territories)
    print(f"  Marked {home_sc_count} home supply centers")
    
    # Step 2: Find neutral candidates
    print("\nStep 2: Finding neutral supply center candidates...")
    candidates = find_neutral_candidates(faces, edges, territories)
    print(f"  Found {len(candidates)} candidate faces")
    
    # Step 3: Select neutral SCs
    print("\nStep 3: Selecting neutral supply centers...")
    neutral_scs = select_neutral_scs(candidates, faces, edges, territories, num_neutral, seed)
    print(f"  Selected {len(neutral_scs)} neutral supply centers")
    
    # Mark neutral SCs in faces
    for face_id in neutral_scs:
        faces[face_id]["is_supply_center"] = True
        faces[face_id]["sc_type"] = "neutral"
    
    # Compile all supply centers
    all_scs = {
        "home": [
            face_id for face_id, face in faces.items()
            if face.get("is_supply_center", False) and face.get("sc_type") == "home"
        ],
        "neutral": neutral_scs
    }
    
    total_scs = len(all_scs["home"]) + len(all_scs["neutral"])
    
    output = {
        "config": {**phase4_output["config"], **config},
        "topology": topology,
        "territories": territories,
        "supply_centers": all_scs,
        "statistics": {
            **phase4_output["statistics"],
            "total_supply_centers": total_scs,
            "home_supply_centers": len(all_scs["home"]),
            "neutral_supply_centers": len(all_scs["neutral"])
        }
    }
    
    print("\n" + "=" * 60)
    print(f"PHASE 5 COMPLETE: {total_scs} total SCs ({len(all_scs['home'])} home, {len(all_scs['neutral'])} neutral)")
    print("=" * 60)
    
    return output


def main():
    """Main entry point for Phase 5."""
    parser = argparse.ArgumentParser(description="Phase 5: Supply Center Distribution")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 4")
    parser.add_argument("--num-neutral-scs", type=int, default=13, help="Number of neutral supply centers")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 4 output
    with open(args.input, 'r') as f:
        phase4_output = json.load(f)
    
    config = {
        "num_neutral_scs": args.num_neutral_scs,
        "seed": args.seed
    }
    
    # Run phase 5
    output = run_phase5(phase4_output, config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        _, _, output_path = get_output_path_for_phase(
            "phase5_supply_centers_output",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
