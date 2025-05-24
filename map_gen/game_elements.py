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
        self.power_regions = {}
    
    def assign_power_regions(self):
        """Assign home regions to each power.
        
        This method assigns home regions to each power and expands their territory
        to include connected regions. Each power gets 3 home regions and additional
        connected regions up to a maximum of 7 regions per power.
        """
        print("\n=== Assigning Power Regions ===")
        
        # Reset power regions and owner information
        self.power_regions = {f"Power{i+1}": set() for i in range(self.num_powers)}
        
        # Clear any existing owner information
        for region_id, region in self.regions.items():
            if 'owner' in region:
                del region['owner']
                print(f"  Cleared owner for region {region_id} ({region.get('name', 'unnamed')})")
        
        # Get all land regions
        land_regions = [r for r, data in self.regions.items() if data['type'] == 'land']
        
        # If no land regions, nothing to do
        if not land_regions:
            return
            
        # Make a copy of the adjacency graph for region assignment
        import networkx as nx
        graph = nx.Graph()
        for region, data in self.regions.items():
            if data['type'] == 'land':
                for neighbor in data.get('neighbors', []):
                    if neighbor in self.regions and self.regions[neighbor]['type'] == 'land':
                        graph.add_edge(region, neighbor)
        
        # First, assign 3 home regions to each power
        unassigned = set(land_regions)
        
        for power_id in self.power_regions:
            if len(unassigned) < 3:
                break
                
            # Sort unassigned regions by centrality (number of neighbors)
            central_regions = sorted(unassigned, 
                                   key=lambda r: len([n for n in self.regions[r].get('neighbors', []) 
                                                   if n in unassigned and self.regions[n]['type'] == 'land']),
                                   reverse=True)
            
            # Start with the most central unassigned region
            start = central_regions[0]
            
            # Find 3 connected regions using BFS
            queue = [start]
            visited = set()
            
            while queue and len(visited) < 3:
                region = queue.pop(0)
                if region in visited:
                    continue
                    
                visited.add(region)
                
                # Add unvisited neighbors to the queue
                neighbors = [n for n in self.regions[region].get('neighbors', []) 
                           if n in unassigned and self.regions[n]['type'] == 'land' and n not in visited]
                queue.extend(neighbors)
            
            # If we found at least 3 connected regions, assign them as home regions
            if len(visited) >= 3:
                # Take the first 3 regions as home regions
                home_regions = set(list(visited)[:3])
                self.power_regions[power_id].update(home_regions)
                unassigned -= home_regions
                
                # Set owner and mark as home for these regions
                print(f"\nAssigning home regions to {power_id}:")
                for region in home_regions:
                    self.regions[region]['owner'] = power_id
                    self.regions[region]['is_home'] = True
                    print(f"  - {region} ({self.regions[region].get('name', 'unnamed')}) assigned as home region")
            else:
                # If we couldn't find 3 connected regions, just take what we have
                self.power_regions[power_id].update(visited)
                for region in visited:
                    self.regions[region]['owner'] = power_id
                    self.regions[region]['is_home'] = True
                unassigned -= visited
        
        # First, expand each power to have at least 5 regions
        for power_id in self.power_regions:
            if not self.power_regions[power_id] or len(self.power_regions[power_id]) >= 5:
                continue
                
            # Start with the home regions
            queue = list(self.power_regions[power_id])
            expanded = set()
            
            # Use BFS to expand the territory to 5 regions
            while queue and len(self.power_regions[power_id]) < 5:
                region = queue.pop(0)
                if region in expanded:
                    continue
                    
                expanded.add(region)
                
                # Add unassigned neighbors to this power's territory
                for neighbor in self.regions[region].get('neighbors', []):
                    if (neighbor in unassigned and 
                        self.regions[neighbor]['type'] == 'land' and 
                        len(self.power_regions[power_id]) < 5):
                        
                        self.power_regions[power_id].add(neighbor)
                        self.regions[neighbor]['owner'] = power_id
                        unassigned.remove(neighbor)
                        queue.append(neighbor)
                        print(f"  - {neighbor} ({self.regions[neighbor].get('name', 'unnamed')}) added to {power_id}'s territory (5-region minimum)")
    
        # Then, give each power a chance to get a 6th region (85% chance)
        for power_id in self.power_regions:
            if (not self.power_regions[power_id] or 
                len(self.power_regions[power_id]) < 5 or 
                random.random() > 0.85):  # 85% chance to get a 6th region
                continue
                
            # Start BFS from all current regions
            queue = list(self.power_regions[power_id])
            expanded = set()
            
            while queue and len(self.power_regions[power_id]) < 6:
                region = queue.pop(0)
                if region in expanded:
                    continue
                    
                expanded.add(region)
                
                # Add unassigned neighbors to this power's territory
                for neighbor in self.regions[region].get('neighbors', []):
                    if (neighbor in unassigned and 
                        self.regions[neighbor]['type'] == 'land' and 
                        len(self.power_regions[power_id]) < 6):
                        
                        self.power_regions[power_id].add(neighbor)
                        self.regions[neighbor]['owner'] = power_id
                        unassigned.remove(neighbor)
                        print(f"  - {neighbor} ({self.regions[neighbor].get('name', 'unnamed')}) added to {power_id}'s territory (6th region)")
                        break  # Only add one region at this stage
                
                if len(self.power_regions[power_id]) >= 6:
                    break
    
        # Finally, give some powers a 7th region (20% of those with 6 regions)
        for power_id in self.power_regions:
            if (len(self.power_regions[power_id]) != 6 or 
                random.random() > 0.20):  # 20% chance to get a 7th region
                continue
                
            # Start BFS from all current regions
            queue = list(self.power_regions[power_id])
            expanded = set()
            
            while queue and len(self.power_regions[power_id]) < 7:
                region = queue.pop(0)
                if region in expanded:
                    continue
                    
                expanded.add(region)
                
                # Add unassigned neighbors to this power's territory
                for neighbor in self.regions[region].get('neighbors', []):
                    if (neighbor in unassigned and 
                        self.regions[neighbor]['type'] == 'land' and 
                        len(self.power_regions[power_id]) < 7):
                        
                        self.power_regions[power_id].add(neighbor)
                        self.regions[neighbor]['owner'] = power_id
                        unassigned.remove(neighbor)
                        print(f"  - {neighbor} ({self.regions[neighbor].get('name', 'unnamed')}) added to {power_id}'s territory (7th region)")
                        break  # Only add one region at this stage
                
                if len(self.power_regions[power_id]) >= 7:
                    break
        
        # The remaining regions are neutral (no owner)
        
        # The remaining regions are neutral (no owner)
    
    def place_supply_centers(self):
        """Place supply centers across the map.
        
        Places supply centers in:
        1. All home centers (3 per power)
        2. Additional neutral supply centers to reach the desired density
        """
        self.supply_centers = set()
        self.starting_positions = {}
        
        # First, assign home centers as supply centers
        for power_id, regions in self.power_regions.items():
            # Get all land regions for this power
            land_regions = [r for r in regions if self.regions[r].get('type') == 'land']
            
            # If no land regions, skip this power
            if not land_regions:
                continue
                
            # Mark home centers as supply centers
            home_centers = [r for r in land_regions if self.regions[r].get('is_home', False)]
            
            for region in home_centers:
                self.regions[region]["is_supply"] = True
                self.supply_centers.add(region)
                unit_type = "army" if self.regions[region].get("type") == "land" else "fleet"
                self.starting_positions.setdefault(power_id, []).append({
                    "region": region,
                    "unit_type": unit_type
                })
        
        # Calculate how many more supply centers we need to reach the desired density
        total_supply_centers = max(3 * self.num_powers, 
                                 int(len([r for r, data in self.regions.items() 
                                        if data.get('type') == 'land']) * self.supply_density))
        
        # Get all land regions that aren't already supply centers
        neutral_land = [r for r, data in self.regions.items() 
                       if data.get('type') == 'land' and not data.get('is_supply', False)]
        
        # Sort neutral land by centrality (number of land neighbors)
        neutral_land.sort(key=lambda r: len([n for n in self.regions[r].get('neighbors', []) 
                                           if self.regions.get(n, {}).get('type') == 'land']), 
                         reverse=True)
        
        # Add neutral supply centers until we reach the desired number
        for region in neutral_land[:total_supply_centers - len(self.supply_centers)]:
            self.regions[region]["is_supply"] = True
            self.supply_centers.add(region)
    
    def assign_starting_positions(self):
        """Assign starting territories to each power."""
        self.starting_positions = {}  # Reset starting positions
        
        # First, assign supply centers as starting positions
        for power_id, regions in self.power_regions.items():
            # Get this power's supply centers
            power_supply_centers = [r for r in (self.supply_centers or []) 
                                  if r in regions and self.regions[r].get('type') == 'land']
            
            # Add supply centers as starting positions
            for region in power_supply_centers:
                unit_type = "army" if self.regions[region].get("type") == "land" else "fleet"
                self.starting_positions.setdefault(power_id, []).append({
                    "region": region,
                    "unit_type": unit_type
                })
        
        # If we don't have supply centers or need more starting positions
        if not self.starting_positions or any(len(positions) < 3 for positions in self.starting_positions.values()):
            # Get all land regions that aren't already starting positions
            used_regions = set()
            for positions in self.starting_positions.values():
                used_regions.update(pos['region'] for pos in positions)
            
            # Assign up to 3 regions per power
            for power_id, regions in self.power_regions.items():
                if power_id not in self.starting_positions:
                    self.starting_positions[power_id] = []
                
                # Get this power's land regions that aren't already starting positions
                power_land = [r for r in regions 
                            if self.regions[r].get('type') == 'land' 
                            and r not in used_regions]
                
                # If we still need more starting positions for this power
                needed = 3 - len(self.starting_positions[power_id])
                if needed > 0 and power_land:
                    # Sort by centrality (regions with more neighbors first)
                    central_regions = sorted(power_land, 
                                           key=lambda r: len([n for n in self.regions[r].get('neighbors', []) 
                                                           if n in regions]), 
                                           reverse=True)
                    
                    # Add up to needed regions as starting positions
                    for region in central_regions[:needed]:
                        if region not in used_regions:
                            used_regions.add(region)
                            unit_type = "army" if self.regions[region].get("type") == "land" else "fleet"
                            self.starting_positions[power_id].append({
                                "region": region,
                                "unit_type": unit_type
                            })
