#!/usr/bin/env python3
"""
Phase 7: Naming and Visualization

This phase adds flavor and creates visual output:
1. Generate names for all provinces using Markov-style names
2. Create visualization showing the complete map
3. Export final map data

Input: optimized_graph_output.json from Phase 6
Output: final_map.json and visual output
"""

import json
import random
import argparse
import os
import sys

# Add parent directory to path for topology import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from output_utils import get_output_path_for_phase, get_input_directory, get_datetime_filename
from topology import get_adjacency_from_topology, get_coastal_faces_from_borders
from fractal_subdivision import subdivide_all_edges


class RegionNamer:
    """Generates names for regions using Markov-style generation."""
    
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        
        # Land name components
        self.land_prefixes = [
            "Ar", "Bel", "Cor", "Dun", "El", "Fal", "Gal", "Hy", "Il", "Jor",
            "Kyl", "Lun", "Mor", "Nor", "Os", "Pyr", "Qar", "Ryn", "Sul", "Tyr",
            "Ald", "Bor", "Cal", "Der", "Eth", "Fyr", "Gar", "Har", "Ith", "Kar",
            "Lyr", "Mer", "Nyr", "Oth", "Por", "Ral", "Ser", "Tol", "Ur", "Val"
        ]
        
        self.land_suffixes = [
            "ania", "borg", "crest", "dor", "ell", "ford", "gate", "heim", "isle",
            "keep", "land", "moor", "nia", "oria", "peak", "quar", "ria", "shire",
            "ton", "vale", "wood", "dal", "mar", "wyn", "thas", "dore", "helm",
            "mere", "haven", "stead", "mark", "fell", "barrow", "mount"
        ]
        
        # Sea name components
        self.sea_features = [
            "Sea", "Bay", "Strait", "Waters", "Channel", "Currents",
            "Gulf", "Sound", "Passage", "Narrows"
        ]
        
        self.sea_adjectives = [
            "North", "South", "East", "West", "Central", "Great", "Lesser",
            "Narrow", "Wide", "Deep", "Shallow", "Upper", "Lower",
            "Inner", "Outer", "Crystal", "Storm", "Calm", "Frozen",
            "Warm", "Dark", "Bright", "Misty", "Golden", "Silver"
        ]
        
        self.used_names = set()
    
    def generate_land_name(self):
        """Generate a unique land province name."""
        max_attempts = 100
        
        for attempt in range(max_attempts):
            prefix = random.choice(self.land_prefixes)
            suffix = random.choice(self.land_suffixes)
            name = f"{prefix}{suffix}"
            
            if name not in self.used_names:
                self.used_names.add(name)
                return name
        
        # Fallback with number
        name = f"{random.choice(self.land_prefixes)}{random.choice(self.land_suffixes)} {len(self.used_names)}"
        self.used_names.add(name)
        return name
    
    def generate_sea_name(self):
        """Generate a unique sea region name."""
        max_attempts = 100
        
        for attempt in range(max_attempts):
            adjective = random.choice(self.sea_adjectives)
            feature = random.choice(self.sea_features)
            name = f"{adjective} {feature}"
            
            if name not in self.used_names:
                self.used_names.add(name)
                return name
        
        # Fallback with number
        name = f"Unnamed {random.choice(self.sea_features)} {len(self.used_names)}"
        self.used_names.add(name)
        return name
    
    def generate_impassable_name(self):
        """Generate a name for an impassable zone."""
        neutrals = [
            "Switzerland", "Highlands", "Mountains", "Peaks",
            "Wastes", "Marshes", "Badlands", "Wilderness"
        ]
        
        for name in neutrals:
            if name not in self.used_names:
                self.used_names.add(name)
                return name
        
        # Fallback
        name = f"Neutral Zone {len(self.used_names)}"
        self.used_names.add(name)
        return name


def get_coastal_faces(edges, borders=None):
    """
    Determine which faces are coastal by checking if they have coast borders/edges.
    
    Args:
        edges: Dictionary of edge data from topology
        borders: Optional dictionary of border data (preferred when available)
        
    Returns:
        Set of face IDs that are coastal
    """
    # Prefer borders when available - they are the proper abstraction layer
    if borders:
        return get_coastal_faces_from_borders(borders)
    
    # Fall back to edges for backward compatibility
    coastal_faces = set()
    for edge_data in edges.values():
        if edge_data.get("type") == "coast":
            left_face = edge_data.get("left_face")
            right_face = edge_data.get("right_face")
            if left_face:
                coastal_faces.add(left_face)
            if right_face:
                coastal_faces.add(right_face)
    return coastal_faces


def assign_names(faces, seed=None):
    """
    Assign names to all faces.
    
    Args:
        faces: Dictionary of face data from topology
        seed: Random seed
        
    Returns:
        Updated faces with names
    """
    namer = RegionNamer(seed)
    
    land_count = 0
    sea_count = 0
    impassable_count = 0
    
    for face_id, face in faces.items():
        if face["type"] == "land":
            face["name"] = namer.generate_land_name()
            land_count += 1
        elif face["type"] == "sea":
            face["name"] = namer.generate_sea_name()
            sea_count += 1
        elif face["type"] == "impassable":
            face["name"] = namer.generate_impassable_name()
            impassable_count += 1
        else:
            face["name"] = f"Unknown_{face_id}"
    
    return faces, land_count, sea_count, impassable_count


def create_adjacency_list(faces, edges, borders=None):
    """
    Create a simple adjacency list representation of the graph using topology.
    
    Args:
        faces: Dictionary of face data from topology
        edges: Dictionary of edge data from topology
        borders: Optional dictionary of border data (preferred when available)
        
    Returns:
        Dictionary mapping face names to neighbor names
    """
    adjacency = {}
    
    # Get adjacency by face ID from topology using borders (proper abstraction layer)
    face_adjacency = get_adjacency_from_topology(edges, borders)
    
    # Convert to name-based adjacency
    for face_id, face in faces.items():
        face_name = face.get("name", face_id)
        neighbor_names = [
            faces[n].get("name", n)
            for n in face_adjacency.get(face_id, [])
            if n in faces
        ]
        adjacency[face_name] = neighbor_names
    
    return adjacency


def create_power_map(faces, edges, territories):
    """
    Create a mapping of power names to their territories.
    
    Args:
        faces: Dictionary of face data from topology
        edges: Dictionary of edge data from topology
        territories: Dictionary of power territories
        
    Returns:
        Dictionary mapping power IDs to territory info
    """
    power_map = {}
    
    # Determine which faces are coastal
    coastal_faces = get_coastal_faces(edges)
    
    for power_id, territory_data in territories.items():
        territory_faces = territory_data["faces"]
        
        power_map[power_id] = {
            "home_territories": [
                {
                    "cell_id": face_id,
                    "name": faces[face_id].get("name", face_id),
                    "is_supply_center": faces[face_id].get("is_supply_center", False),
                    "coastal": face_id in coastal_faces
                }
                for face_id in territory_faces
                if face_id in faces
            ],
            "seed": territory_data.get("seed"),
            "size": territory_data.get("size", len(territory_faces))
        }
    
    return power_map


def create_supply_center_list(faces, edges, supply_centers):
    """
    Create a formatted list of all supply centers.
    
    Args:
        faces: Dictionary of face data from topology
        edges: Dictionary of edge data from topology
        supply_centers: Supply center data
        
    Returns:
        Dictionary with SC lists
    """
    # Determine which faces are coastal
    coastal_faces = get_coastal_faces(edges)
    
    sc_list = {
        "home": [
            {
                "cell_id": face_id,
                "name": faces[face_id].get("name", face_id),
                "owner": faces[face_id].get("owner"),
                "coastal": face_id in coastal_faces
            }
            for face_id in supply_centers.get("home", [])
            if face_id in faces
        ],
        "neutral": [
            {
                "cell_id": face_id,
                "name": faces[face_id].get("name", face_id),
                "coastal": face_id in coastal_faces
            }
            for face_id in supply_centers.get("neutral", [])
            if face_id in faces
        ]
    }
    
    return sc_list


def generate_map_summary(output):
    """
    Generate a human-readable summary of the map.
    
    Args:
        output: Complete phase output
        
    Returns:
        String with map summary
    """
    stats = output["statistics"]
    
    summary = []
    summary.append("=" * 60)
    summary.append("DIPLOMACY MAP SUMMARY")
    summary.append("=" * 60)
    summary.append("")
    # Use 'total_faces' if available, fall back to 'total_cells' for backward compatibility
    total_key = 'total_faces' if 'total_faces' in stats else 'total_cells'
    land_key = 'land_faces' if 'land_faces' in stats else 'land_cells'
    sea_key = 'sea_faces' if 'sea_faces' in stats else 'sea_cells'
    impassable_key = 'impassable_faces' if 'impassable_faces' in stats else 'impassable_cells'
    
    summary.append(f"Total Faces: {stats[total_key]}")
    summary.append(f"  - Land: {stats[land_key]}")
    summary.append(f"  - Sea: {stats[sea_key]}")
    summary.append(f"  - Impassable: {stats[impassable_key]}")
    summary.append("")
    summary.append(f"Supply Centers: {stats['total_supply_centers']}")
    summary.append(f"  - Home: {stats['home_supply_centers']}")
    summary.append(f"  - Neutral: {stats['neutral_supply_centers']}")
    summary.append("")
    summary.append(f"Powers: {stats['num_powers']}")
    summary.append(f"  - Corner Powers: {stats['corner_powers']}")
    summary.append(f"  - Central Powers: {stats['central_powers']}")
    summary.append("")
    summary.append(f"Geography:")
    coastal_key = 'coastal_faces' if 'coastal_faces' in stats else 'coastal_cells'
    inland_key = 'inland_faces' if 'inland_faces' in stats else 'inland_cells'
    summary.append(f"  - Coastal Faces: {stats[coastal_key]}")
    summary.append(f"  - Inland Faces: {stats[inland_key]}")
    summary.append(f"  - Ocean Regions: {stats['num_oceans']}")
    summary.append("")
    
    if "analysis" in output:
        analysis = output["analysis"]
        
        # Handle new Phase 6 structure with before/after optimization
        # Use after_optimization if available, otherwise use direct keys (backward compatibility)
        if "after_optimization" in analysis:
            degree_data = analysis["after_optimization"]["degree_analysis"]
            triangle_data = analysis["after_optimization"]["triangle_analysis"]
            sea_data = analysis["after_optimization"]["sea_connectivity"]
        else:
            # Backward compatibility with old structure
            degree_data = analysis.get("degree_analysis", {})
            triangle_data = analysis.get("triangle_analysis", {})
            sea_data = analysis.get("sea_connectivity", {})
        
        if degree_data and triangle_data and sea_data:
            summary.append(f"Graph Quality:")
            summary.append(f"  - Average Degree: {degree_data['average_degree']:.2f}")
            summary.append(f"  - Triangle Density: {triangle_data['triangle_density']:.1%}")
            summary.append(f"  - Seas Connected: {sea_data['connected']}")
            summary.append(f"  - Contested Neutral SCs: {stats.get('contested_neutral_scs', 0)}")
            summary.append("")
    
    if output.get("recommendations"):
        summary.append("Recommendations:")
        for rec in output["recommendations"]:
            summary.append(f"  • {rec}")
        summary.append("")
    
    summary.append("=" * 60)
    
    return "\n".join(summary)


def run_phase7(phase6_output, config):
    """
    Run Phase 7: Naming and Visualization.
    
    Args:
        phase6_output: Output from Phase 6
        config: Configuration parameters
        
    Returns:
        Dictionary with final map data
    """
    print("=" * 60)
    print("PHASE 7: NAMING AND VISUALIZATION")
    print("=" * 60)
    
    # Use topology structure instead of cells
    topology = phase6_output.get("topology", {})
    if not topology or "faces" not in topology:
        raise ValueError("Phase 6 output must contain topology with faces")
    
    faces = topology["faces"]
    edges = topology["edges"]
    borders = topology.get("borders", {})
    territories = phase6_output["territories"]
    supply_centers = phase6_output["supply_centers"]
    
    # Extract configuration
    seed = config.get("seed", 42)
    
    print(f"\nConfiguration:")
    print(f"  Random seed: {seed}")
    
    # Step 1: Assign names
    print("\nStep 1: Assigning names to all provinces...")
    faces, land_count, sea_count, impassable_count = assign_names(faces, seed)
    print(f"  Named {land_count} land provinces")
    print(f"  Named {sea_count} sea regions")
    print(f"  Named {impassable_count} impassable zones")
    
    # Step 2: Create adjacency representation using borders (proper abstraction layer)
    print("\nStep 2: Creating adjacency list...")
    adjacency_list = create_adjacency_list(faces, edges, borders)
    print(f"  Created adjacency list with {len(adjacency_list)} nodes")
    
    # Step 3: Create power map
    print("\nStep 3: Creating power territories map...")
    power_map = create_power_map(faces, edges, territories)
    print(f"  Mapped {len(power_map)} powers")
    
    # Step 4: Create supply center list
    print("\nStep 4: Creating supply center list...")
    sc_list = create_supply_center_list(faces, edges, supply_centers)
    print(f"  Listed {len(sc_list['home'])} home SCs")
    print(f"  Listed {len(sc_list['neutral'])} neutral SCs")
    
    # Step 5: Generate fractal edge subdivision for visual rendering
    # Use the new topological subdivision approach that creates actual edges
    # instead of just visual paths
    print("\nStep 5: Generating fractal edge subdivision...")
    
    # Ensure borders exist in topology (for backward compatibility with older data)
    if "borders" not in topology:
        topology["borders"] = {}
    
    original_edge_count = len(topology["edges"])
    original_vertex_count = len(topology["vertices"])
    
    # Subdivide edges topologically (creates new vertices and edges)
    topology = subdivide_all_edges(topology, seed)
    
    new_edge_count = len(topology["edges"])
    new_vertex_count = len(topology["vertices"])
    
    # Count edges by type
    edge_type_counts = {}
    for edge_data in topology["edges"].values():
        edge_type = edge_data.get("type", "unknown")
        edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
    
    print(f"  Subdivided edges: {original_edge_count} -> {new_edge_count}")
    print(f"  Added vertices: {original_vertex_count} -> {new_vertex_count}")
    for edge_type, count in sorted(edge_type_counts.items()):
        print(f"    - {edge_type}: {count} edges")
    
    # Create final output (without cells dictionary)
    output = {
        "config": phase6_output["config"],
        "metadata": {
            "version": "1.0",
            "generator": "Diplomacy Map Generator - Phased Pipeline",
            "phases_completed": 7
        },
        "topology": topology,
        "adjacency": adjacency_list,
        "powers": power_map,
        "supply_centers": sc_list,
        "analysis": phase6_output.get("analysis", {}),
        "recommendations": phase6_output.get("recommendations", []),
        "statistics": phase6_output["statistics"]
    }
    
    # Generate summary
    summary = generate_map_summary(output)
    
    print("\n" + summary)
    
    return output


def main():
    """Main entry point for Phase 7."""
    parser = argparse.ArgumentParser(description="Phase 7: Naming and Visualization")
    parser.add_argument("--input", type=str, required=True, help="Input JSON from Phase 6")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path (default: auto-generated in same directory as input)")
    parser.add_argument("--summary", type=str, default=None, help="Summary text file path (default: auto-generated in same directory as input)")
    
    args = parser.parse_args()
    
    # Load Phase 6 output
    with open(args.input, 'r') as f:
        phase6_output = json.load(f)
    
    config = {
        "seed": args.seed
    }
    
    # Run phase 7
    output = run_phase7(phase6_output, config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        _, _, output_path = get_output_path_for_phase(
            "phase7_final_map",
            input_file=args.input,
            is_orchestrator=False
        )
    
    # Save output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nFinal map saved to: {output_path}")
    
    # Determine summary path
    if args.summary:
        summary_path = args.summary
    else:
        output_dir = get_input_directory(args.input)
        summary_filename, _ = get_datetime_filename("map_summary", extension=".txt")
        summary_path = os.path.join(output_dir, summary_filename)
    
    # Save summary
    summary = generate_map_summary(output)
    with open(summary_path, 'w') as f:
        f.write(summary)
    
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
