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
        name = f"{random.choice(self.land_prefixes)}{random.choice(self.land_suffixes)}{len(self.used_names)}"
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
        name = f"{random.choice(self.sea_features)} {len(self.used_names)}"
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


def assign_names(cells, seed=None):
    """
    Assign names to all cells.
    
    Args:
        cells: Dictionary of cell data
        seed: Random seed
        
    Returns:
        Updated cells with names
    """
    namer = RegionNamer(seed)
    
    land_count = 0
    sea_count = 0
    impassable_count = 0
    
    for cell_id, cell in cells.items():
        if cell["type"] == "land":
            cell["name"] = namer.generate_land_name()
            land_count += 1
        elif cell["type"] == "sea":
            cell["name"] = namer.generate_sea_name()
            sea_count += 1
        elif cell["type"] == "impassable":
            cell["name"] = namer.generate_impassable_name()
            impassable_count += 1
        else:
            cell["name"] = f"Unknown_{cell_id}"
    
    return cells, land_count, sea_count, impassable_count


def create_adjacency_list(cells):
    """
    Create a simple adjacency list representation of the graph.
    
    Args:
        cells: Dictionary of cell data
        
    Returns:
        Dictionary mapping cell names to neighbor names
    """
    adjacency = {}
    
    for cell_id, cell in cells.items():
        cell_name = cell.get("name", cell_id)
        neighbor_names = [
            cells[n].get("name", n)
            for n in cell["neighbors"]
            if n in cells
        ]
        adjacency[cell_name] = neighbor_names
    
    return adjacency


def create_power_map(cells, territories):
    """
    Create a mapping of power names to their territories.
    
    Args:
        cells: Dictionary of cell data
        territories: Dictionary of power territories
        
    Returns:
        Dictionary mapping power IDs to territory info
    """
    power_map = {}
    
    for power_id, territory_data in territories.items():
        territory_cells = territory_data["cells"]
        
        power_map[power_id] = {
            "home_territories": [
                {
                    "cell_id": cell_id,
                    "name": cells[cell_id].get("name", cell_id),
                    "is_supply_center": cells[cell_id].get("is_supply_center", False),
                    "coastal": cells[cell_id].get("coastal", False)
                }
                for cell_id in territory_cells
                if cell_id in cells
            ],
            "seed": territory_data.get("seed"),
            "size": territory_data.get("size", len(territory_cells))
        }
    
    return power_map


def create_supply_center_list(cells, supply_centers):
    """
    Create a formatted list of all supply centers.
    
    Args:
        cells: Dictionary of cell data
        supply_centers: Supply center data
        
    Returns:
        Dictionary with SC lists
    """
    sc_list = {
        "home": [
            {
                "cell_id": cell_id,
                "name": cells[cell_id].get("name", cell_id),
                "owner": cells[cell_id].get("owner"),
                "coastal": cells[cell_id].get("coastal", False)
            }
            for cell_id in supply_centers.get("home", [])
            if cell_id in cells
        ],
        "neutral": [
            {
                "cell_id": cell_id,
                "name": cells[cell_id].get("name", cell_id),
                "coastal": cells[cell_id].get("coastal", False)
            }
            for cell_id in supply_centers.get("neutral", [])
            if cell_id in cells
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
    summary.append(f"Total Cells: {stats['total_cells']}")
    summary.append(f"  - Land: {stats['land_cells']}")
    summary.append(f"  - Sea: {stats['sea_cells']}")
    summary.append(f"  - Impassable: {stats['impassable_cells']}")
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
    summary.append(f"  - Coastal Cells: {stats['coastal_cells']}")
    summary.append(f"  - Inland Cells: {stats['inland_cells']}")
    summary.append(f"  - Ocean Regions: {stats['num_oceans']}")
    summary.append("")
    
    if "analysis" in output:
        analysis = output["analysis"]
        summary.append(f"Graph Quality:")
        summary.append(f"  - Average Degree: {analysis['degree_analysis']['average_degree']:.2f}")
        summary.append(f"  - Triangle Density: {analysis['triangle_analysis']['triangle_density']:.1%}")
        summary.append(f"  - Seas Connected: {analysis['sea_connectivity']['connected']}")
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
    
    cells = phase6_output["cells"]
    territories = phase6_output["territories"]
    supply_centers = phase6_output["supply_centers"]
    
    # Extract configuration
    seed = config.get("seed", 42)
    
    print(f"\nConfiguration:")
    print(f"  Random seed: {seed}")
    
    # Step 1: Assign names
    print("\nStep 1: Assigning names to all provinces...")
    cells, land_count, sea_count, impassable_count = assign_names(cells, seed)
    print(f"  Named {land_count} land provinces")
    print(f"  Named {sea_count} sea regions")
    print(f"  Named {impassable_count} impassable zones")
    
    # Step 2: Create adjacency representation
    print("\nStep 2: Creating adjacency list...")
    adjacency_list = create_adjacency_list(cells)
    print(f"  Created adjacency list with {len(adjacency_list)} nodes")
    
    # Step 3: Create power map
    print("\nStep 3: Creating power territories map...")
    power_map = create_power_map(cells, territories)
    print(f"  Mapped {len(power_map)} powers")
    
    # Step 4: Create supply center list
    print("\nStep 4: Creating supply center list...")
    sc_list = create_supply_center_list(cells, supply_centers)
    print(f"  Listed {len(sc_list['home'])} home SCs")
    print(f"  Listed {len(sc_list['neutral'])} neutral SCs")
    
    # Create final output
    output = {
        "config": phase6_output["config"],
        "metadata": {
            "version": "1.0",
            "generator": "Diplomacy Map Generator - Phased Pipeline",
            "phases_completed": 7
        },
        "cells": cells,
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
    parser.add_argument("--input", type=str, default="optimized_graph_output.json", help="Input JSON from Phase 6")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="final_map.json", help="Output JSON file")
    parser.add_argument("--summary", type=str, default="map_summary.txt", help="Summary text file")
    
    args = parser.parse_args()
    
    # Load Phase 6 output
    with open(args.input, 'r') as f:
        phase6_output = json.load(f)
    
    config = {
        "seed": args.seed
    }
    
    # Run phase 7
    output = run_phase7(phase6_output, config)
    
    # Save output
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nFinal map saved to: {args.output}")
    
    # Save summary
    summary = generate_map_summary(output)
    with open(args.summary, 'w') as f:
        f.write(summary)
    
    print(f"Summary saved to: {args.summary}")


if __name__ == "__main__":
    main()
