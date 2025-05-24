"""
Game Elements Module

This module handles game-specific elements like supply centers and starting positions.
"""

import random
import networkx as nx

class GameElements:
    """Manages game elements like supply centers and starting positions."""
    
    def __init__(self, regions, adjacency_graph, num_powers, supply_density):
        """Initialize with region data and game configuration."""
        self.regions = regions
        self.adjacency_graph = adjacency_graph
        self.num_powers = num_powers
        self.supply_density = supply_density
        self.supply_centers = set()
        self.starting_positions = {}
    
    def place_supply_centers(self):
        """Place supply centers across the map."""
        land_regions = [r for r in self.regions if self.regions[r]["type"] == "land"]
        
        # Calculate total number of supply centers
        total_supply = int(len(self.regions) * self.supply_density)
        
        # Ensure we have enough land regions
        if len(land_regions) < total_supply:
            # Convert some sea regions to coastal land if needed
            sea_regions = [r for r in self.regions if self.regions[r]["type"] == "sea"]
            sea_with_land_neighbors = []
            
            for r in sea_regions:
                neighbors = self.regions[r]["neighbors"]
                if any(self.regions[n]["type"] == "land" for n in neighbors):
                    sea_with_land_neighbors.append(r)
            
            convert_count = min(total_supply - len(land_regions), len(sea_with_land_neighbors))
            for r in sea_with_land_neighbors[:convert_count]:
                self.regions[r]["type"] = "land"
                land_regions.append(r)
        
        # Select supply centers, preferring larger regions
        land_regions_with_size = [(r, self.regions[r]["area"]) for r in land_regions]
        land_regions_with_size.sort(key=lambda x: x[1], reverse=True)
        
        # Take a mix of large and random regions
        large_regions = [r for r, _ in land_regions_with_size[:total_supply//2]]
        remaining_regions = [r for r, _ in land_regions_with_size[total_supply//2:]]
        random_regions = random.sample(remaining_regions, 
                                     min(total_supply - len(large_regions), len(remaining_regions)))
        
        supply_centers = large_regions + random_regions
        
        # Mark supply centers
        for r in supply_centers:
            self.regions[r]["is_supply"] = True
            self.supply_centers.add(r)
    
    def assign_starting_positions(self):
        """Assign starting territories to each power."""
        # Use community detection to find potential starting clusters
        try:
            communities = list(nx.community.greedy_modularity_communities(self.adjacency_graph))
        except:
            # Fallback if community detection fails
            # Just divide regions roughly equally
            all_regions = list(self.regions.keys())
            regions_per_power = len(all_regions) // self.num_powers
            communities = []
            for i in range(self.num_powers):
                start_idx = i * regions_per_power
                end_idx = start_idx + regions_per_power
                if i == self.num_powers - 1:  # Last power gets remaining regions
                    end_idx = len(all_regions)
                communities.append(set(all_regions[start_idx:end_idx]))
        
        # Filter to communities with enough supply centers
        valid_communities = []
        for community in communities:
            supply_count = sum(1 for r in community if r in self.supply_centers)
            if supply_count >= 1:  # Lowered requirement
                valid_communities.append((community, supply_count))
        
        # Sort by supply center count
        valid_communities.sort(key=lambda x: x[1], reverse=True)
        
        # Assign starting positions
        assigned_regions = set()
        
        for power_idx in range(min(self.num_powers, len(valid_communities))):
            power_id = f"Power{power_idx+1}"
            self.starting_positions[power_id] = []
            
            # Get community and its supply centers
            community, _ = valid_communities[power_idx]
            supply_in_community = [r for r in community if r in self.supply_centers and r not in assigned_regions]
            
            # Pick up to 3 supply centers
            home_centers = supply_in_community[:3]
            
            for region in home_centers:
                assigned_regions.add(region)
                self.regions[region]["owner"] = power_id
                unit_type = "army" if self.regions[region]["type"] == "land" else "fleet"
                self.starting_positions[power_id].append({
                    "region": region,
                    "unit_type": unit_type
                })
