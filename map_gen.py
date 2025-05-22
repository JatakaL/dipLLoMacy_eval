import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import Voronoi
from matplotlib.patches import Polygon
import random
import matplotlib.colors as mcolors
from shapely.geometry import Polygon as ShapelyPolygon, Point
from shapely.ops import unary_union
import networkx as nx
from sklearn.cluster import AgglomerativeClustering, KMeans
import itertools

class DiplomacyMapGenerator:
    def __init__(self, num_regions=100, num_powers=7, land_ratio=0.7, supply_density=0.25, cell_multiplier=10):
        self.num_regions = num_regions
        self.num_powers = num_powers
        self.land_ratio = land_ratio
        self.supply_density = supply_density
        self.cell_multiplier = cell_multiplier  # How many more cells to generate than regions
        
        # Initialize structures
        self.cells = {}  # Individual Voronoi cells
        self.cell_polygons = {}
        self.cell_adjacency = nx.Graph()
        
        self.regions = {}  # Final merged territories
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
        """Generate a complete Diplomacy-style map using cell merging"""
        self._generate_voronoi_cells()
        self._determine_cell_types()
        self._build_cell_adjacency()
        self._merge_cells_into_regions()
        self._determine_region_adjacency()
        self._place_supply_centers()
        self._assign_starting_positions()
        self._name_regions()
        return self.regions, self.adjacency_graph, self.supply_centers, self.starting_positions
    
    def _generate_voronoi_cells(self):
        """Generate many Voronoi cells that will be merged into regions"""
        num_cells = self.num_regions * self.cell_multiplier
        
        # Create points with a slight buffer from the edges
        buffer = 0.05
        points = np.random.uniform(buffer, 1-buffer, (num_cells, 2))
        
        # Add corner points to ensure the Voronoi diagram covers the entire map
        corner_points = np.array([
            [-0.1, -0.1], [0.5, -0.1], [1.1, -0.1],
            [-0.1, 0.5], [1.1, 0.5],
            [-0.1, 1.1], [0.5, 1.1], [1.1, 1.1]
        ])
        all_points = np.vstack([points, corner_points])
        
        # Generate Voronoi diagram
        vor = Voronoi(all_points)
        
        # Define boundary polygon
        boundary = ShapelyPolygon([
            (0, 0), (1, 0), (1, 1), (0, 1)
        ])
        
        # Process cells (only the original points, not corners)
        for i in range(num_cells):
            cell_id = f"C{i+1}"
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
                clipped_vertices = np.array(clipped_poly.exterior.coords)
            else:  # MultiPolygon - use the largest part
                largest = max(clipped_poly.geoms, key=lambda p: p.area)
                clipped_vertices = np.array(largest.exterior.coords)
            
            # Store cell data
            self.cells[cell_id] = {
                "id": cell_id,
                "center": points[i],
                "vertices": clipped_vertices,
                "type": None,  # Will be "land" or "sea"
                "area": clipped_poly.area,
                "neighbors": [],
                "merged_into": None  # Track which region this cell belongs to
            }
            
            self.cell_polygons[cell_id] = clipped_poly
            
            # Add node to cell adjacency graph
            self.cell_adjacency.add_node(cell_id, pos=points[i])
    
    def _determine_cell_types(self):
        """Determine which cells are land or sea"""
        # Create several "continent" centers
        num_continents = int(self.num_powers * 1.5)
        continent_centers = np.random.rand(num_continents, 2)
        
        for cell_id, cell in self.cells.items():
            center = cell["center"]
            
            # Calculate distance to nearest continent center
            distances = np.linalg.norm(continent_centers - center, axis=1)
            min_distance = np.min(distances)
            
            # Closer to continent = more likely to be land
            land_probability = np.exp(-min_distance * 5) * 2
            
            if random.random() < land_probability or random.random() < self.land_ratio:
                cell["type"] = "land"
            else:
                cell["type"] = "sea"
    
    def _build_cell_adjacency(self):
        """Build adjacency graph for cells"""
        cell_ids = list(self.cells.keys())
        
        for i, cell1 in enumerate(cell_ids):
            poly1 = self.cell_polygons[cell1]
            
            for j, cell2 in enumerate(cell_ids[i+1:], i+1):
                poly2 = self.cell_polygons[cell2]
                
                # Check if polygons share a border
                if poly1.touches(poly2) or poly1.intersects(poly2):
                    self.cell_adjacency.add_edge(cell1, cell2)
                    self.cells[cell1]["neighbors"].append(cell2)
                    self.cells[cell2]["neighbors"].append(cell1)
    
    def _merge_cells_into_regions(self):
        """Merge cells into larger regions using various strategies"""
        # Separate land and sea cells
        land_cells = [c for c in self.cells if self.cells[c]["type"] == "land"]
        sea_cells = [c for c in self.cells if self.cells[c]["type"] == "sea"]
        
        # For seas, use much fewer regions to create large connected bodies of water
        target_sea_regions = max(3, int(self.num_regions * 0.25))  # Much fewer sea regions
        target_land_regions = self.num_regions - target_sea_regions
        
        # Merge land cells normally
        land_regions = self._merge_cells_by_type(land_cells, target_land_regions, "land")
        
        # Merge sea cells with special handling for connectivity
        sea_regions = self._merge_seas_for_connectivity(sea_cells, target_sea_regions)
        
        # Combine all regions
        all_regions = land_regions + sea_regions
        
        # Create final region data structures
        for i, (region_cells, region_type) in enumerate(all_regions):
            region_id = f"R{i+1}"
            
            # Merge all cell polygons into one region polygon
            cell_polys = [self.cell_polygons[cell] for cell in region_cells]
            merged_poly = unary_union(cell_polys)
            
            # Calculate region center (centroid of merged polygon)
            if merged_poly.geom_type == 'Polygon':
                region_center = np.array([merged_poly.centroid.x, merged_poly.centroid.y])
                # Get exterior coordinates
                region_vertices = np.array(merged_poly.exterior.coords)
            else:  # MultiPolygon - use the largest part
                largest = max(merged_poly.geoms, key=lambda p: p.area)
                region_center = np.array([largest.centroid.x, largest.centroid.y])
                region_vertices = np.array(largest.exterior.coords)
            
            # Store region data
            self.regions[region_id] = {
                "id": region_id,
                "center": region_center,
                "vertices": region_vertices,
                "type": region_type,
                "is_supply": False,
                "owner": None,
                "name": None,
                "neighbors": [],
                "constituent_cells": region_cells,
                "area": merged_poly.area
            }
            
            self.region_polygons[region_id] = merged_poly
            
            # Mark cells as merged into this region
            for cell in region_cells:
                self.cells[cell]["merged_into"] = region_id
            
            # Add node to adjacency graph
            self.adjacency_graph.add_node(region_id, pos=region_center)
    
    def _merge_cells_by_type(self, cells, target_count, region_type):
        """Merge cells of the same type into regions"""
        if not cells or target_count <= 0:
            return []
        
        if len(cells) <= target_count:
            # If we have fewer cells than target regions, each cell becomes its own region
            return [(cell,) for cell in cells]
        
        # Create subgraph of only these cell types
        subgraph = self.cell_adjacency.subgraph(cells)
        
        # Handle disconnected components
        components = list(nx.connected_components(subgraph))
        
        merged_regions = []
        
        for component in components:
            component_cells = list(component)
            
            if len(component_cells) == 1:
                merged_regions.append((component_cells, region_type))
                continue
            
            # Calculate how many regions this component should have
            component_ratio = len(component_cells) / len(cells)
            component_target = max(1, int(target_count * component_ratio))
            
            if len(component_cells) <= component_target:
                # Small component, make each cell its own region
                for cell in component_cells:
                    merged_regions.append(([cell], region_type))
            else:
                # Large component, use clustering
                component_regions = self._cluster_cells(component_cells, component_target)
                for region_cells in component_regions:
                    merged_regions.append((region_cells, region_type))
        
        return merged_regions
    
    def _merge_seas_for_connectivity(self, sea_cells, target_count):
        """Merge sea cells prioritizing large connected bodies of water"""
        if not sea_cells or target_count <= 0:
            return []
        
        # Create subgraph of only sea cells
        sea_subgraph = self.cell_adjacency.subgraph(sea_cells)
        
        # Get all connected components of sea cells
        sea_components = list(nx.connected_components(sea_subgraph))
        
        # If we have fewer components than target regions, each component becomes a region
        if len(sea_components) <= target_count:
            return [(list(component), "sea") for component in sea_components]
        
        # If we have more components than target regions, we need to merge some
        # Sort components by size (larger components are more important)
        sea_components = sorted(sea_components, key=len, reverse=True)
        
        # Strategy: Keep the largest components as single regions,
        # and merge smaller components using geographical proximity
        
        large_components = sea_components[:target_count//2]  # Keep largest as-is
        small_components = sea_components[target_count//2:]
        
        merged_regions = []
        
        # Add large components as individual regions
        for component in large_components:
            merged_regions.append((list(component), "sea"))
        
        # Merge small components using clustering if we have remaining budget
        remaining_target = target_count - len(large_components)
        
        if small_components and remaining_target > 0:
            # Flatten small components into a single list
            small_cells = []
            for component in small_components:
                small_cells.extend(component)
            
            # Use simple geographical clustering for remaining small sea areas
            if len(small_cells) <= remaining_target:
                # If few enough cells, each gets its own region
                for cell in small_cells:
                    merged_regions.append(([cell], "sea"))
            else:
                # Cluster small cells geographically
                small_clusters = self._cluster_cells_geographically(small_cells, remaining_target)
                for cluster in small_clusters:
                    merged_regions.append((cluster, "sea"))
        
        return merged_regions
    
    def _cluster_cells(self, cells, target_count):
        """Cluster cells using graph-based approach"""
        if len(cells) <= target_count:
            return [[cell] for cell in cells]
        
        # Create position matrix for clustering
        positions = np.array([self.cells[cell]["center"] for cell in cells])
        
        # Use agglomerative clustering with connectivity constraint
        cell_subgraph = self.cell_adjacency.subgraph(cells)
        
        # Convert to adjacency matrix for sklearn
        cell_to_idx = {cell: i for i, cell in enumerate(cells)}
        n = len(cells)
        connectivity = np.zeros((n, n))
        
        for cell1, cell2 in cell_subgraph.edges():
            i, j = cell_to_idx[cell1], cell_to_idx[cell2]
            connectivity[i, j] = 1
            connectivity[j, i] = 1
        
        # Perform clustering
        clustering = AgglomerativeClustering(
            n_clusters=target_count,
            connectivity=connectivity,
            linkage='ward'
        )
        
        try:
            labels = clustering.fit_predict(positions)
        except:
            # Fallback to simple partitioning if clustering fails
            labels = np.arange(len(cells)) % target_count
        
        # Group cells by cluster
        clusters = {}
        for i, cell in enumerate(cells):
            label = labels[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(cell)
        
        return list(clusters.values())
    
    def _cluster_cells_geographically(self, cells, target_count):
        """Cluster cells based purely on geographical proximity"""
        if len(cells) <= target_count:
            return [[cell] for cell in cells]
        
        # Get positions
        positions = np.array([self.cells[cell]["center"] for cell in cells])
        
        # Use simple k-means style clustering based on distance
        try:
            kmeans = KMeans(n_clusters=target_count, random_state=42, n_init=10)
            labels = kmeans.fit_predict(positions)
        except:
            # Fallback to simple partitioning
            labels = np.arange(len(cells)) % target_count
        
        # Group cells by cluster
        clusters = {}
        for i, cell in enumerate(cells):
            label = labels[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(cell)
        
        return list(clusters.values())
    
    def _determine_region_adjacency(self):
        """Determine which regions are adjacent to each other"""
        region_ids = list(self.regions.keys())
        
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
            
            while len(components) > 1:
                comp1, comp2 = components[0], components[1]
                
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
                
                r1, r2 = closest_pair
                self.adjacency_graph.add_edge(r1, r2)
                self.regions[r1]["neighbors"].append(r2)
                self.regions[r2]["neighbors"].append(r1)
                self.borders.append((r1, r2))
                
                components = list(nx.connected_components(self.adjacency_graph))
    
    def _place_supply_centers(self):
        """Place supply centers across the map"""
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
                    name = f"Sea of {random.choice(prefixes) + random.choice(prefixes)}ia"
                    if name not in used_names:
                        break
            
            used_names.add(name)
            region["name"] = name
    
    def visualize_map(self, show_names=True, show_borders=True, show_cells=False):
        """Visualize the generated map with option to show underlying cells"""
        plt.figure(figsize=(15, 12))
        
        # Optionally show underlying cell structure
        if show_cells:
            for cell_id, cell in self.cells.items():
                polygon = cell["vertices"]
                plt.plot(polygon[:, 0], polygon[:, 1], color="lightgray", linewidth=0.3, alpha=0.5)
        
        # Draw region polygons
        for region_id, region in self.regions.items():
            polygon = region["vertices"]
            region_type = region["type"]
            color = self.terrain_colors[region_type]
            
            # If region is a supply center, make it more saturated
            if region["is_supply"]:
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
            plt.plot(polygon[:, 0], polygon[:, 1], color="black", linewidth=1.0)
        
        # Draw supply centers
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
                        ha='center', va='center', fontsize=8, weight='bold')
        
        title = "Procedurally Generated Diplomacy Map (Cell Merging)"
        if show_cells:
            title += " - Showing Underlying Cells"
        plt.title(title)
        plt.axis('off')
        plt.tight_layout()
        return plt

# Usage example
if __name__ == "__main__":
    # Create map generator with cell merging
    map_gen = DiplomacyMapGenerator(
        num_regions=75,  # Final number of territories
        num_powers=7,
        land_ratio=0.6,  # Slightly less land to create more sea
        supply_density=0.3,
        cell_multiplier=12  # Generate more cells for better merging
    )
    
    # Generate map
    regions, adjacency_graph, supply_centers, starting_positions = map_gen.generate_map()
    
    # Visualize the map
    plt = map_gen.visualize_map(show_names=True, show_cells=False)
    plt.show()
    
    # Show with underlying cells visible
    plt = map_gen.visualize_map(show_names=False, show_cells=True)
    plt.show()
    
    # Print statistics
    print(f"Generated map with {len(regions)} regions from {len(map_gen.cells)} cells")
    print(f"Land regions: {sum(1 for r in regions.values() if r['type'] == 'land')}")
    print(f"Sea regions: {sum(1 for r in regions.values() if r['type'] == 'sea')}")
    print(f"Supply centers: {len(supply_centers)}")
    print(f"Powers: {len(starting_positions)}")
    
    # Print average cells per region
    cells_per_region = [len(region['constituent_cells']) for region in regions.values()]
    print(f"Average cells per region: {np.mean(cells_per_region):.1f}")
    print(f"Region size range: {min(cells_per_region)} to {max(cells_per_region)} cells")