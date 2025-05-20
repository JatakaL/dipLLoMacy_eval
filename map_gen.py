import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi
from matplotlib.patches import Polygon
import random
import matplotlib.colors as mcolors
from shapely.geometry import Polygon as ShapelyPolygon, Point
import networkx as nx

class DiplomacyMapGenerator:
    def __init__(self, num_regions=100, num_powers=7, land_ratio=0.7, supply_density=0.25):
        self.num_regions = num_regions
        self.num_powers = num_powers
        self.land_ratio = land_ratio
        self.supply_density = supply_density
        
        # Initialize structures
        self.regions = {}
        self.region_polygons = {}
        self.borders = []
        self.adjacency_graph = nx.Graph()
        self.supply_centers = set()
        self.starting_positions = {}
        self.terrain_colors = {
            "land": "#C5E0B4",  # Light green
            "sea": "#BDD7EE"    # Light blue
        }
        
    def generate_map(self):
        """Generate a complete Diplomacy-style map"""
        self._generate_voronoi_regions()
        self._determine_region_types()
        self._determine_adjacency()
        self._place_supply_centers()
        self._assign_starting_positions()
        self._name_regions()
        return self.regions, self.adjacency_graph, self.supply_centers, self.starting_positions
    
    def _generate_voronoi_regions(self):
        """Generate Voronoi regions for the map with boundary clipping"""
        # Create points with a slight buffer from the edges
        buffer = 0.05
        points = np.random.uniform(buffer, 1-buffer, (self.num_regions, 2))
        
        # Add corner points to ensure the Voronoi diagram covers the entire map
        corner_points = np.array([
            [-0.1, -0.1], [0.5, -0.1], [1.1, -0.1],
            [-0.1, 0.5], [1.1, 0.5],
            [-0.1, 1.1], [0.5, 1.1], [1.1, 1.1]
        ])
        all_points = np.vstack([points, corner_points])
        
        # Generate Voronoi diagram
        vor = Voronoi(all_points)
        
        # Define boundary polygon - this is where we trim the map
        # For now using a rectangle from (0,0) to (1,1)
        boundary = ShapelyPolygon([
            (0, 0), (1, 0), (1, 1), (0, 1)
        ])
        
        # Process regions
        for i in range(self.num_regions):  # Only process the original points, not corners
            region_id = f"R{i+1}"
            region_idx = vor.point_region[i]
            region_vertices = vor.regions[region_idx]
            
            # Skip any region with -1 (unbounded)
            if -1 in region_vertices:
                continue
            
            # Get the polygon vertices
            polygon_vertices = vor.vertices[region_vertices]
            
            # Create Shapely polygon for spatial calculations
            shapely_poly = ShapelyPolygon(polygon_vertices)
            
            # Clip the polygon to the boundary
            clipped_poly = shapely_poly.intersection(boundary)
            
            # Skip if the clipped polygon is empty or not a polygon
            if clipped_poly.is_empty or clipped_poly.geom_type not in ['Polygon', 'MultiPolygon']:
                continue
            
            # Extract coordinates from the clipped polygon
            if clipped_poly.geom_type == 'Polygon':
                # Get exterior coordinates
                clipped_vertices = np.array(clipped_poly.exterior.coords)
            else:  # MultiPolygon - use the largest part
                largest = max(clipped_poly.geoms, key=lambda p: p.area)
                clipped_vertices = np.array(largest.exterior.coords)
            
            # Store region data
            self.regions[region_id] = {
                "id": region_id,
                "center": points[i],
                "vertices": clipped_vertices,
                "type": None,  # Will be "land" or "sea"
                "is_supply": False,
                "owner": None,
                "name": None,
                "neighbors": []
            }
            
            self.region_polygons[region_id] = clipped_poly
            
            # Add node to adjacency graph
            self.adjacency_graph.add_node(region_id, pos=points[i])
    
    def _determine_region_types(self):
        """Determine which regions are land or sea using a continental approach"""
        # Create several "continent" centers
        num_continents = int(self.num_powers * 1.5)
        continent_centers = np.random.rand(num_continents, 2)
        
        # Create coastal profile with distance fields
        for region_id, region in self.regions.items():
            center = region["center"]
            
            # Calculate distance to nearest continent center
            distances = np.linalg.norm(continent_centers - center, axis=1)
            min_distance = np.min(distances)
            
            # Closer to continent = more likely to be land
            # Further from continent = more likely to be sea
            land_probability = np.exp(-min_distance * 5) * 2  # Tune these parameters as needed
            
            # Determine type with some randomness
            combined_probability = min(land_probability + self.land_ratio * 0.5, 0.9)  # Cap at 90%
            if random.random() < combined_probability:
                region["type"] = "land"
            else:
                region["type"] = "sea"
            
    def _determine_adjacency(self):
        """Determine which regions are adjacent to each other"""
        region_ids = list(self.regions.keys())
        
        # For each pair of regions, check if they share a border
        for i, region1 in enumerate(region_ids):
            poly1 = self.region_polygons[region1]
            
            for j, region2 in enumerate(region_ids[i+1:], i+1):
                poly2 = self.region_polygons[region2]
                
                # Check if polygons share a border
                if poly1.touches(poly2) or poly1.intersects(poly2):
                    # Add edge to adjacency graph
                    self.adjacency_graph.add_edge(region1, region2)
                    
                    # Update neighbors lists
                    self.regions[region1]["neighbors"].append(region2)
                    self.regions[region2]["neighbors"].append(region1)
                    
                    # Store border for visualization
                    self.borders.append((region1, region2))
        
        # Ensure the graph is connected
        if not nx.is_connected(self.adjacency_graph):
            components = list(nx.connected_components(self.adjacency_graph))
            
            # Connect components
            while len(components) > 1:
                comp1, comp2 = components[0], components[1]
                
                # Find closest regions between components
                min_dist = float('inf')
                closest_pair = None
                
                for r1 in comp1:
                    pos1 = self.regions[r1]["center"]
                    for r2 in comp2:
                        pos2 = self.regions[r2]["center"]
                        dist = np.linalg.norm(np.array(pos1) - np.array(pos2))
                        
                        if dist < min_dist:
                            min_dist = dist
                            closest_pair = (r1, r2)
                
                # Connect these regions
                r1, r2 = closest_pair
                self.adjacency_graph.add_edge(r1, r2)
                self.regions[r1]["neighbors"].append(r2)
                self.regions[r2]["neighbors"].append(r1)
                self.borders.append((r1, r2))
                
                # Recalculate components
                components = list(nx.connected_components(self.adjacency_graph))
    
    def _place_supply_centers(self):
        """Place supply centers across the map"""
        land_regions = [r for r in self.regions if self.regions[r]["type"] == "land"]
        
        # Calculate total number of supply centers
        total_supply = int(len(self.regions) * self.supply_density)
        
        # Ensure we have enough land regions
        if len(land_regions) < total_supply:
            # Convert some sea regions to coastal land
            sea_regions = [r for r in self.regions if self.regions[r]["type"] == "sea"]
            sea_with_land_neighbors = []
            
            for r in sea_regions:
                neighbors = self.regions[r]["neighbors"]
                if any(self.regions[n]["type"] == "land" for n in neighbors):
                    sea_with_land_neighbors.append(r)
            
            # Convert enough sea regions to land
            convert_count = min(total_supply - len(land_regions), len(sea_with_land_neighbors))
            for r in sea_with_land_neighbors[:convert_count]:
                self.regions[r]["type"] = "land"
                land_regions.append(r)
        
        # Select supply centers
        supply_centers = random.sample(land_regions, min(total_supply, len(land_regions)))
        
        # Mark supply centers
        for r in supply_centers:
            self.regions[r]["is_supply"] = True
            self.supply_centers.add(r)
    
    def _assign_starting_positions(self):
        """Assign starting territories to each power"""
        # Use community detection to find potential starting clusters
        communities = list(nx.community.greedy_modularity_communities(self.adjacency_graph))
        
        # Filter to communities with enough supply centers
        valid_communities = []
        for community in communities:
            supply_count = sum(1 for r in community if r in self.supply_centers)
            if supply_count >= 3:
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
    
    def _name_regions(self):
        """Generate names for regions"""
        prefixes = ["Ar", "Bel", "Cor", "Dun", "El", "Fal", "Gal", "Hy", "Il", "Jor", 
                    "Kyl", "Lun", "Mor", "Nor", "Os", "Pyr", "Qar", "Ryn", "Sul", "Tyr"]
        
        suffixes = ["ania", "borg", "crest", "dor", "ell", "ford", "gate", "heim", "isle", 
                   "keep", "land", "moor", "nia", "oria", "peak", "quar", "ria", "shire", 
                   "ton", "vale", "wood"]
        
        # Generate unique names
        used_names = set()
        for region_id, region in self.regions.items():
            region_type = region["type"]
            
            if region_type == "land":
                while True:
                    name = random.choice(prefixes) + random.choice(suffixes)
                    if name not in used_names:
                        break
            else:
                while True:
                    name = f"Sea of {random.choice(prefixes)}ia"
                    if name not in used_names:
                        break
            
            used_names.add(name)
            region["name"] = name
    
    def visualize_map(self, show_names=True, show_borders=True):
        """Visualize the generated map"""
        plt.figure(figsize=(15, 12))
        
        # Draw region polygons
        for region_id, region in self.regions.items():
            polygon = region["vertices"]
            region_type = region["type"]
            color = self.terrain_colors[region_type]
            
            # If region is a supply center, make it more saturated
            if region["is_supply"]:
                # Slightly adjust color to indicate supply center
                if region_type == "land":
                    color = "#A9D18E"  # Darker green
                else:
                    color = "#9BC2E6"  # Darker blue
            
            # If region is owned by a power, use power color
            if region["owner"]:
                power_idx = int(region["owner"].replace("Power", "")) - 1
                colors = list(mcolors.TABLEAU_COLORS.values())
                color = colors[power_idx % len(colors)]
            
            # Draw the polygon
            plt.fill(polygon[:, 0], polygon[:, 1], color=color, alpha=0.8)
            
            # Draw polygon border
            plt.plot(polygon[:, 0], polygon[:, 1], color="gray", linewidth=0.5)
        
        # Draw supply centers with bigger, more prominent markers
        for sc in self.supply_centers:
            center = self.regions[sc]["center"]
            plt.plot(center[0], center[1], 'o', markersize=10, color='gold', 
                    markeredgecolor='black', markeredgewidth=1.5)
        
        # Draw units for starting positions
        for power_id, positions in self.starting_positions.items():
            power_idx = int(power_id.replace("Power", "")) - 1
            colors = list(mcolors.TABLEAU_COLORS.values())
            color = colors[power_idx % len(colors)]
            
            for pos in positions:
                region = pos["region"]
                unit_type = pos["unit_type"]
                center = self.regions[region]["center"]
                
                # Different markers for armies and fleets
                if unit_type == "army":
                    plt.plot(center[0], center[1], 's', markersize=8, color=color, 
                            markeredgecolor='black', markeredgewidth=1)
                else:  # fleet
                    plt.plot(center[0], center[1], '^', markersize=8, color=color, 
                            markeredgecolor='black', markeredgewidth=1)
        
        # Add labels if requested
        if show_names:
            for region_id, region in self.regions.items():
                center = region["center"]
                plt.text(center[0], center[1], region["name"], 
                        ha='center', va='center', fontsize=7)
        
        plt.title("Procedurally Generated Diplomacy Map")
        plt.axis('off')
        plt.tight_layout()
        return plt

# Usage example
if __name__ == "__main__":
    # Create map generator
    map_gen = DiplomacyMapGenerator(
        num_regions=100,
        num_powers=7,
        land_ratio=0.7,
        supply_density=0.25
    )
    
    # Generate map
    regions, adjacency_graph, supply_centers, starting_positions = map_gen.generate_map()
    
    # Visualize the map
    plt = map_gen.visualize_map(show_names=True)
    plt.show()
    
    # Print some statistics
    print(f"Generated map with {len(regions)} regions")
    print(f"Land regions: {sum(1 for r in regions.values() if r['type'] == 'land')}")
    print(f"Sea regions: {sum(1 for r in regions.values() if r['type'] == 'sea')}")
    print(f"Supply centers: {len(supply_centers)}")
    print(f"Powers: {len(starting_positions)}")
    
    # Print starting positions for each power
    for power_id, positions in starting_positions.items():
        print(f"\n{power_id} starting positions:")
        for pos in positions:
            region = regions[pos["region"]]
            print(f"  {pos['unit_type']} in {region['name']} ({pos['region']})")