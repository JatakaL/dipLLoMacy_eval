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
    def __init__(self, num_regions=100, num_powers=7, land_ratio=0.7, supply_density=0.25, 
                 cell_multiplier=10, num_sea_starters=4, sea_growth_bias=0.7):
        self.num_regions = num_regions
        self.num_powers = num_powers
        self.land_ratio = land_ratio
        self.supply_density = supply_density
        self.cell_multiplier = cell_multiplier
        self.num_sea_starters = num_sea_starters
        self.sea_growth_bias = sea_growth_bias
        
        # Initialize structures
        self.cells = {}
        self.cell_polygons = {}
        self.cell_adjacency = nx.Graph()
        
        self.regions = {}
        self.region_polygons = {}
        self.borders = []
        self.adjacency_graph = nx.Graph()
        self.supply_centers = set()
        self.starting_positions = {}
        self.terrain_colors = {
            "land": "#C5E0B4",
            "sea": "#BDD7EE"
        }
        
    def generate_map(self):
        """Generate a complete Diplomacy-style map using cell merging"""
        self._generate_voronoi_cells()
        self._build_cell_adjacency()
        self._grow_seas_from_starters()
        self._merge_cells_into_regions()
        self._validate_all_cells_merged()  # NEW: Validation step
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
            
            # Store cell data - START ALL AS LAND, we'll grow seas later
            self.cells[cell_id] = {
                "id": cell_id,
                "center": points[i],
                "vertices": clipped_vertices,
                "type": "land",
                "area": clipped_poly.area,
                "neighbors": [],
                "merged_into": None,
                "sea_starter": False,
                "sea_generation": None
            }
            
            self.cell_polygons[cell_id] = clipped_poly
            
            # Add node to cell adjacency graph
            self.cell_adjacency.add_node(cell_id, pos=points[i])
    
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
    
    def _grow_seas_from_starters(self):
        """Grow seas from strategic starter points using organic growth"""
        print(f"Growing seas from {self.num_sea_starters} starter points...")
        
        # Calculate target number of sea cells
        total_cells = len(self.cells)
        target_sea_cells = int(total_cells * (1 - self.land_ratio))
        
        print(f"Target: {target_sea_cells} sea cells out of {total_cells} total")
        
        # Choose strategic starter positions for seas
        sea_starters = self._choose_sea_starters()
        
        # Convert starters to sea
        current_sea_cells = set()
        sea_frontier = []
        
        for starter in sea_starters:
            self.cells[starter]["type"] = "sea"
            self.cells[starter]["sea_starter"] = True
            self.cells[starter]["sea_generation"] = 0
            current_sea_cells.add(starter)
            sea_frontier.append(starter)
        
        print(f"Started with {len(sea_starters)} sea starter cells")
        
        # Grow seas until we reach target
        generation = 1
        while len(current_sea_cells) < target_sea_cells and sea_frontier:
            new_sea_cells = []
            
            # For each cell in the current frontier
            for sea_cell in sea_frontier:
                # Find land neighbors that could become sea
                land_neighbors = [
                    neighbor for neighbor in self.cells[sea_cell]["neighbors"]
                    if self.cells[neighbor]["type"] == "land"
                ]
                
                # Grow to some of these neighbors
                for neighbor in land_neighbors:
                    if len(current_sea_cells) >= target_sea_cells:
                        break
                    
                    # Probability of growth - higher if more sea neighbors
                    sea_neighbor_count = sum(
                        1 for n in self.cells[neighbor]["neighbors"]
                        if self.cells[n]["type"] == "sea"
                    )
                    
                    # Base probability plus bonus for having sea neighbors
                    growth_probability = 0.3 + (sea_neighbor_count * 0.2)
                    growth_probability *= self.sea_growth_bias
                    
                    if random.random() < growth_probability:
                        self.cells[neighbor]["type"] = "sea"
                        self.cells[neighbor]["sea_generation"] = generation
                        current_sea_cells.add(neighbor)
                        new_sea_cells.append(neighbor)
            
            # Update frontier - remove cells with no land neighbors, add new sea cells
            sea_frontier = []
            for sea_cell in list(current_sea_cells):
                has_land_neighbors = any(
                    self.cells[neighbor]["type"] == "land"
                    for neighbor in self.cells[sea_cell]["neighbors"]
                )
                if has_land_neighbors:
                    sea_frontier.append(sea_cell)
            
            generation += 1
            print(f"Generation {generation}: {len(current_sea_cells)} total sea cells")
            
            # Safety check to prevent infinite loops
            if generation > 50:
                break
        
        print(f"Final: {len(current_sea_cells)} sea cells ({len(current_sea_cells)/total_cells:.1%})")
        
        # Ensure we have some land left
        land_cells = [cell for cell in self.cells if self.cells[cell]["type"] == "land"]
        print(f"Remaining land cells: {len(land_cells)} ({len(land_cells)/total_cells:.1%})")
    
    def _choose_sea_starters(self):
        """Choose strategic starting positions for seas"""
        cell_ids = list(self.cells.keys())
        
        # Strategy: Place starters near edges and corners, plus maybe one inland
        starters = []
        
        # Get cells near each edge/corner
        edge_cells = {
            'left': [],
            'right': [],
            'top': [],
            'bottom': [],
            'center': []
        }
        
        for cell_id in cell_ids:
            center = self.cells[cell_id]["center"]
            x, y = center[0], center[1]
            
            # Categorize by position
            if x < 0.2:
                edge_cells['left'].append(cell_id)
            elif x > 0.8:
                edge_cells['right'].append(cell_id)
            elif y < 0.2:
                edge_cells['bottom'].append(cell_id)
            elif y > 0.8:
                edge_cells['top'].append(cell_id)
            elif 0.3 < x < 0.7 and 0.3 < y < 0.7:
                edge_cells['center'].append(cell_id)
        
        # Choose one starter from each edge (if we have enough)
        edge_order = ['left', 'bottom', 'right', 'top', 'center']
        
        for i, edge in enumerate(edge_order):
            if i >= self.num_sea_starters:
                break
            if edge_cells[edge]:
                starter = random.choice(edge_cells[edge])
                starters.append(starter)
        
        # If we need more starters, choose randomly from remaining cells
        while len(starters) < self.num_sea_starters:
            remaining = [c for c in cell_ids if c not in starters]
            if remaining:
                starters.append(random.choice(remaining))
            else:
                break
        
        return starters
    
    def _merge_cells_into_regions(self):
        """Merge cells into larger regions using various strategies"""
        # Separate land and sea cells
        land_cells = [c for c in self.cells if self.cells[c]["type"] == "land"]
        sea_cells = [c for c in self.cells if self.cells[c]["type"] == "sea"]
        
        print(f"Merging {len(land_cells)} land cells and {len(sea_cells)} sea cells into {self.num_regions} regions")
        
        # Create more strategic sea regions (like original Diplomacy)
        target_sea_regions = max(5, int(self.num_regions * 0.35))
        target_land_regions = self.num_regions - target_sea_regions
        
        # Merge land cells normally
        land_regions = self._merge_cells_by_type(land_cells, target_land_regions, "land")
        
        # Merge sea cells with special handling for connectivity
        sea_regions = self._merge_seas_for_connectivity(sea_cells, target_sea_regions)
        
        # Combine all regions
        all_regions = land_regions + sea_regions
        
        print(f"Created {len(land_regions)} land regions and {len(sea_regions)} sea regions")
        
        # Track which cells have been assigned to regions
        assigned_cells = set()
        
        # Create final region data structures
        for i, (region_cells, region_type) in enumerate(all_regions):
            region_id = f"R{i+1}"
            
            # Validate region cells
            if not region_cells:
                print(f"WARNING: Empty region cells for {region_id}")
                continue
                
            # Check for duplicate assignments
            duplicate_cells = assigned_cells.intersection(set(region_cells))
            if duplicate_cells:
                print(f"WARNING: Duplicate cell assignments detected: {duplicate_cells}")
            
            assigned_cells.update(region_cells)
            
            try:
                # Merge all cell polygons into one region polygon
                cell_polys = [self.cell_polygons[cell] for cell in region_cells if cell in self.cell_polygons]
                
                if not cell_polys:
                    print(f"WARNING: No valid cell polygons for region {region_id}")
                    continue
                    
                merged_poly = unary_union(cell_polys)
                
                # Calculate region center (centroid of merged polygon)
                if merged_poly.geom_type == 'Polygon':
                    region_center = np.array([merged_poly.centroid.x, merged_poly.centroid.y])
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
                    if cell in self.cells:
                        self.cells[cell]["merged_into"] = region_id
                    else:
                        print(f"WARNING: Cell {cell} not found in self.cells")
                
                # Add node to adjacency graph
                self.adjacency_graph.add_node(region_id, pos=region_center)
                
            except Exception as e:
                print(f"ERROR creating region {region_id}: {e}")
                print(f"  Region cells: {region_cells[:5]}...")
                # Create individual regions for each cell in the failed region
                for cell in region_cells:
                    if cell in self.cells and self.cells[cell]["merged_into"] is None:
                        single_region_id = f"R{len(self.regions) + 1}"
                        cell_data = self.cells[cell]
                        
                        self.regions[single_region_id] = {
                            "id": single_region_id,
                            "center": cell_data["center"],
                            "vertices": cell_data["vertices"],
                            "type": cell_data["type"],
                            "is_supply": False,
                            "owner": None,
                            "name": None,
                            "neighbors": [],
                            "constituent_cells": [cell],
                            "area": cell_data["area"]
                        }
                        
                        self.region_polygons[single_region_id] = self.cell_polygons[cell]
                        self.cells[cell]["merged_into"] = single_region_id
                        self.adjacency_graph.add_node(single_region_id, pos=cell_data["center"])
        
        # Report on assignment success
        all_cells = set(self.cells.keys())
        unassigned_cells = all_cells - assigned_cells
        if unassigned_cells:
            print(f"WARNING: {len(unassigned_cells)} cells were not assigned to any region during clustering")
            print(f"Sample unassigned: {list(unassigned_cells)[:5]}")
        
        print(f"Successfully assigned {len(assigned_cells)} out of {len(all_cells)} cells to regions")
    
    def _validate_all_cells_merged(self):
        """Validate that all cells have been merged into regions"""
        unmerged_cells = [cell_id for cell_id, cell in self.cells.items() 
                         if cell["merged_into"] is None]
        
        if unmerged_cells:
            print(f"WARNING: Found {len(unmerged_cells)} unmerged cells!")
            # Only show first few for brevity
            sample_cells = unmerged_cells[:5]
            print(f"Sample unmerged cells: {sample_cells}")
            if len(unmerged_cells) > 5:
                print(f"... and {len(unmerged_cells) - 5} more")
                
            print("This indicates the clustering algorithm failed - creating single-cell regions as backup")
            
            # Create individual regions for unmerged cells
            for cell_id in unmerged_cells:
                region_id = f"R{len(self.regions) + 1}"
                cell = self.cells[cell_id]
                
                # Create region from single cell
                self.regions[region_id] = {
                    "id": region_id,
                    "center": cell["center"],
                    "vertices": cell["vertices"],
                    "type": cell["type"],
                    "is_supply": False,
                    "owner": None,
                    "name": None,
                    "neighbors": [],
                    "constituent_cells": [cell_id],
                    "area": cell["area"]
                }
                
                self.region_polygons[region_id] = self.cell_polygons[cell_id]
                cell["merged_into"] = region_id
                self.adjacency_graph.add_node(region_id, pos=cell["center"])
        
        # Final verification
        still_unmerged = [cell_id for cell_id, cell in self.cells.items() 
                         if cell["merged_into"] is None]
        
        if still_unmerged:
            print(f"ERROR: Still have {len(still_unmerged)} unmerged cells after validation!")
        else:
            print(f"SUCCESS: All {len(self.cells)} cells merged into {len(self.regions)} regions")
            
            # Show region type breakdown
            land_regions = sum(1 for r in self.regions.values() if r["type"] == "land")
            sea_regions = sum(1 for r in self.regions.values() if r["type"] == "sea")
            print(f"Final regions: {land_regions} land, {sea_regions} sea")
    
    def _merge_cells_by_type(self, cells, target_count, region_type):
        """Merge cells of the same type into regions"""
        if not cells or target_count <= 0:
            return []
        
        print(f"Processing {len(cells)} {region_type} cells for merging")
        
        if len(cells) <= target_count:
            # If we have fewer cells than target regions, each cell becomes its own region
            return [([cell], region_type) for cell in cells]
        
        # Create subgraph of only these cell types
        subgraph = self.cell_adjacency.subgraph(cells)
        
        # Handle disconnected components
        components = list(nx.connected_components(subgraph))
        print(f"Found {len(components)} components for {region_type} cells")
        
        # Check for isolated cells (not in any component)
        cells_in_components = set()
        for component in components:
            cells_in_components.update(component)
        
        isolated_cells = set(cells) - cells_in_components
        if isolated_cells:
            print(f"WARNING: Found {len(isolated_cells)} isolated {region_type} cells not in any component!")
            print(f"Sample isolated cells: {list(isolated_cells)[:5]}")
            # Add isolated cells as single-cell components
            for cell in isolated_cells:
                components.append({cell})
        
        merged_regions = []
        all_assigned_cells = set()
        
        print(f"Processing {len(components)} components (including isolated cells)")
        
        for i, component in enumerate(components):
            component_cells = list(component)
            
            if len(component_cells) == 1:
                merged_regions.append((component_cells, region_type))
                all_assigned_cells.update(component_cells)
                continue
            
            # Calculate how many regions this component should have
            component_ratio = len(component_cells) / len(cells)
            component_target = max(1, int(target_count * component_ratio))
            
            if len(component_cells) <= component_target:
                # Small component, make each cell its own region
                for cell in component_cells:
                    merged_regions.append(([cell], region_type))
                    all_assigned_cells.add(cell)
            else:
                # Large component, use robust clustering
                component_regions = self._robust_cluster_cells(component_cells, component_target)
                for region_cells in component_regions:
                    merged_regions.append((region_cells, region_type))
                    all_assigned_cells.update(region_cells)
        
        # Verify all cells were assigned
        unassigned = set(cells) - all_assigned_cells
        if unassigned:
            print(f"ERROR: {len(unassigned)} {region_type} cells still not assigned after processing!")
            print(f"Sample unassigned: {list(unassigned)[:5]}")
            for cell in unassigned:
                merged_regions.append(([cell], region_type))
        
        print(f"Final: Created {len(merged_regions)} {region_type} regions from {len(cells)} cells")
        return merged_regions
    
    def _robust_cluster_cells(self, cells, target_count):
        """Robust clustering that ensures all cells are assigned"""
        if len(cells) <= target_count:
            return [[cell] for cell in cells]
        
        print(f"Clustering {len(cells)} cells into {target_count} regions")
        
        # Try multiple clustering approaches in order of preference
        
        # Approach 1: NetworkX-based spatial clustering
        try:
            clusters = self._networkx_spatial_clustering(cells, target_count)
            if self._validate_clustering(clusters, cells):
                print("  Success with NetworkX spatial clustering")
                return clusters
        except Exception as e:
            print(f"  NetworkX clustering failed: {e}")
        
        # Approach 2: Simple geographic clustering
        try:
            clusters = self._geographic_clustering(cells, target_count)
            if self._validate_clustering(clusters, cells):
                print("  Success with geographic clustering")
                return clusters
        except Exception as e:
            print(f"  Geographic clustering failed: {e}")
        
        # Approach 3: Connected component partitioning
        try:
            clusters = self._connected_partitioning(cells, target_count)
            if self._validate_clustering(clusters, cells):
                print("  Success with connected partitioning")
                return clusters
        except Exception as e:
            print(f"  Connected partitioning failed: {e}")
        
        # Fallback: Simple sequential partitioning (guaranteed to work)
        print("  Using fallback sequential partitioning")
        return self._sequential_partitioning(cells, target_count)
    
    def _networkx_spatial_clustering(self, cells, target_count):
        """Use NetworkX and spatial proximity for clustering"""
        # Create subgraph
        subgraph = self.cell_adjacency.subgraph(cells)
        
        if not nx.is_connected(subgraph):
            # Handle each component separately
            components = list(nx.connected_components(subgraph))
            all_clusters = []
            
            for component in components:
                comp_cells = list(component)
                comp_target = max(1, len(comp_cells) * target_count // len(cells))
                comp_clusters = self._networkx_spatial_clustering(comp_cells, comp_target)
                all_clusters.extend(comp_clusters)
            
            return all_clusters
        
        # Try sklearn clustering with connectivity
        positions = np.array([self.cells[cell]["center"] for cell in cells])
        
        # Build connectivity matrix
        cell_to_idx = {cell: i for i, cell in enumerate(cells)}
        n = len(cells)
        connectivity = np.zeros((n, n))
        
        for cell1, cell2 in subgraph.edges():
            i, j = cell_to_idx[cell1], cell_to_idx[cell2]
            connectivity[i, j] = 1
            connectivity[j, i] = 1
        
        from sklearn.cluster import AgglomerativeClustering
        clustering = AgglomerativeClustering(
            n_clusters=target_count,
            connectivity=connectivity,
            linkage='ward'
        )
        
        labels = clustering.fit_predict(positions)
        
        # Group cells by cluster
        clusters = {}
        for i, cell in enumerate(cells):
            label = labels[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(cell)
        
        return list(clusters.values())
    
    def _geographic_clustering(self, cells, target_count):
        """Simple geographic clustering using KMeans"""
        positions = np.array([self.cells[cell]["center"] for cell in cells])
        
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=target_count, random_state=42)
        labels = kmeans.fit_predict(positions)
        
        # Group cells by cluster
        clusters = {}
        for i, cell in enumerate(cells):
            label = labels[i]
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(cell)
        
        return list(clusters.values())
    
    def _connected_partitioning(self, cells, target_count):
        """Partition based on graph connectivity"""
        subgraph = self.cell_adjacency.subgraph(cells)
        
        # Use NetworkX community detection
        import networkx.algorithms.community as nx_comm
        
        # Try different community detection methods
        try:
            communities = list(nx_comm.greedy_modularity_communities(subgraph))
        except:
            # Fallback to simple partitioning
            return self._sequential_partitioning(cells, target_count)
        
        # If we have too many communities, merge the smallest ones
        while len(communities) > target_count:
            # Find two smallest communities to merge
            sizes = [(len(comm), i) for i, comm in enumerate(communities)]
            sizes.sort()
            
            # Merge the two smallest
            _, idx1 = sizes[0]
            _, idx2 = sizes[1]
            
            merged = communities[idx1] | communities[idx2]
            communities = [comm for i, comm in enumerate(communities) if i not in [idx1, idx2]]
            communities.append(merged)
        
        # If we have too few communities, split the largest ones
        while len(communities) < target_count:
            # Find largest community to split
            largest_idx = max(range(len(communities)), key=lambda i: len(communities[i]))
            largest = list(communities[largest_idx])
            
            if len(largest) <= 1:
                break  # Can't split further
            
            # Split roughly in half
            mid = len(largest) // 2
            part1 = largest[:mid]
            part2 = largest[mid:]
            
            communities[largest_idx] = set(part1)
            communities.append(set(part2))
        
        return [list(comm) for comm in communities]
    
    def _sequential_partitioning(self, cells, target_count):
        """Simple sequential partitioning - guaranteed to work"""
        cells_per_cluster = len(cells) // target_count
        remainder = len(cells) % target_count
        
        clusters = []
        start_idx = 0
        
        for i in range(target_count):
            # Some clusters get one extra cell to handle remainder
            cluster_size = cells_per_cluster + (1 if i < remainder else 0)
            cluster = cells[start_idx:start_idx + cluster_size]
            
            if cluster:  # Only add non-empty clusters
                clusters.append(cluster)
            
            start_idx += cluster_size
        
        return clusters
    
    def _validate_clustering(self, clusters, original_cells):
        """Validate that clustering assigned all cells exactly once"""
        assigned_cells = set()
        
        for i, cluster in enumerate(clusters):
            if not cluster:  # Empty cluster
                print(f"    Empty cluster {i} found!")
                return False
            for cell in cluster:
                if cell in assigned_cells:  # Duplicate assignment
                    print(f"    Duplicate assignment: cell {cell} in multiple clusters")
                    return False
                assigned_cells.add(cell)
        
        missing_cells = set(original_cells) - assigned_cells
        extra_cells = assigned_cells - set(original_cells)
        
        if missing_cells:
            print(f"    Missing cells: {len(missing_cells)} cells not assigned to any cluster")
            print(f"    Sample missing: {list(missing_cells)[:5]}")
            return False
            
        if extra_cells:
            print(f"    Extra cells: {len(extra_cells)} unknown cells assigned")
            return False
        
        print(f"    Validation passed: {len(assigned_cells)} cells properly assigned to {len(clusters)} clusters")
        return True
    
    def _merge_seas_for_connectivity(self, sea_cells, target_count):
        """Merge sea cells into appropriately-sized strategic sea regions"""
        if not sea_cells or target_count <= 0:
            return []
        
        # Create subgraph of only sea cells
        sea_subgraph = self.cell_adjacency.subgraph(sea_cells)
        
        # Get all connected components of sea cells
        sea_components = list(nx.connected_components(sea_subgraph))
        
        print(f"Found {len(sea_components)} sea components, targeting {target_count} sea regions")
        
        merged_regions = []
        
        for component in sea_components:
            component_cells = list(component)
            
            # Calculate optimal number of regions for this component
            optimal_cells_per_region = 5
            component_regions = max(1, len(component_cells) // optimal_cells_per_region)
            
            # But don't exceed our remaining target
            remaining_target = target_count - len(merged_regions)
            component_regions = min(component_regions, remaining_target)
            component_regions = max(1, component_regions)
            
            if len(component_cells) <= optimal_cells_per_region or component_regions == 1:
                # Small component, keep as single region
                merged_regions.append((component_cells, "sea"))
            else:
                # Large component, break into multiple strategic sea regions
                component_clusters = self._robust_cluster_cells(component_cells, component_regions)
                for cluster in component_clusters:
                    merged_regions.append((cluster, "sea"))
                    if len(merged_regions) >= target_count:
                        break
            
            if len(merged_regions) >= target_count:
                break
        
        return merged_regions
    
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
    
    def _name_regions(self):
        """Generate names for regions"""
        land_prefixes = ["Ar", "Bel", "Cor", "Dun", "El", "Fal", "Gal", "Hy", "Il", "Jor", 
                        "Kyl", "Lun", "Mor", "Nor", "Os", "Pyr", "Qar", "Ryn", "Sul", "Tyr"]
        
        land_suffixes = ["ania", "borg", "crest", "dor", "ell", "ford", "gate", "heim", "isle", 
                        "keep", "land", "moor", "nia", "oria", "peak", "quar", "ria", "shire", 
                        "ton", "vale", "wood"]
        
        sea_names = [
            "North Sea", "South Sea", "Eastern Sea", "Western Sea",
            "Great Bay", "Golden Bay", "Storm Bay", "Crystal Bay",
            "Narrow Strait", "Wide Strait", "Iron Strait", "Silver Strait",
            "Inner Sea", "Outer Sea", "Deep Waters", "Shallow Waters",
            "Merchant Sea", "Warrior Sea", "Royal Sea", "Ancient Sea",
            "Misty Waters", "Clear Waters", "Dark Sea", "Bright Sea",
            "Frozen Sea", "Warm Sea", "Peaceful Sea", "Wild Sea"
        ]
        
        used_names = set()
        sea_name_index = 0
        
        for region_id, region in self.regions.items():
            region_type = region["type"]
            
            if region_type == "land":
                num_attempts = 0
                while True:
                    name = random.choice(land_prefixes) + random.choice(land_suffixes)
                    if name not in used_names:
                        break
                    num_attempts += 1
                    if num_attempts > 100:  # Prevent infinite loop
                        name = f"{random.choice(land_prefixes)}{random.choice(land_suffixes)}{num_attempts}"
                        break
            else:  # sea
                if sea_name_index < len(sea_names):
                    name = sea_names[sea_name_index]
                    sea_name_index += 1
                else:
                    num_attempts = 0
                    while True:
                        feature = random.choice(["Sea", "Bay", "Strait", "Waters", "Channel", "Currents"])
                        if num_attempts < 20:
                            direction = random.choice(["North", "South", "East", "West", "Central", "Narrow", "Deep", "Great"])
                            name = f"{direction} {feature}"
                        else:
                            main_name = random.choice(land_prefixes) + random.choice(land_prefixes).lower()
                            name = f"{main_name} {feature}"
                        if name not in used_names:
                            break
                        num_attempts += 1
                        if num_attempts > 100:  # Prevent infinite loop
                            name = f"{feature} {num_attempts}"
                            break
            
            used_names.add(name)
            region["name"] = name
    
    def visualize_map(self, show_names=True, show_borders=True, show_cells=False, show_sea_growth=False):
        """Visualize the generated map with various display options"""
        plt.figure(figsize=(15, 12))
        
        # Optionally show underlying cell structure
        if show_cells:
            for cell_id, cell in self.cells.items():
                polygon = cell["vertices"]
                
                if show_sea_growth and cell["type"] == "sea":
                    if cell["sea_starter"]:
                        cell_color = "darkblue"
                    else:
                        generation = cell.get("sea_generation", 0)
                        blue_intensity = max(0.3, 1.0 - generation * 0.1)
                        cell_color = (0, 0, blue_intensity)
                else:
                    cell_color = "lightgray"
                
                plt.plot(polygon[:, 0], polygon[:, 1], color=cell_color, linewidth=0.3, alpha=0.7)
        
        # Draw region polygons
        for region_id, region in self.regions.items():
            polygon = region["vertices"]
            region_type = region["type"]
            color = self.terrain_colors[region_type]
            
            # If region is a supply center, make it more saturated
            if region["is_supply"]:
                if region_type == "land":
                    color = "#A9D18E"
                else:
                    color = "#9BC2E6"
            
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
        
        # Show sea starter points if displaying sea growth
        if show_sea_growth:
            for cell_id, cell in self.cells.items():
                if cell.get("sea_starter"):
                    center = cell["center"]
                    plt.plot(center[0], center[1], '*', markersize=12, color='red', 
                            markeredgecolor='darkred', markeredgewidth=1)
        
        title = "Fixed Diplomacy Map"
        if show_cells:
            title += " (Showing Cells)"
        if show_sea_growth:
            title += " (Sea Growth Visualization)"
        
        plt.title(title)
        plt.axis('off')
        plt.tight_layout()
        return plt

# Usage example
if __name__ == "__main__":
    # Create map generator
    map_gen = DiplomacyMapGenerator(
        num_regions=75,
        num_powers=7,
        land_ratio=0.6,
        supply_density=0.3,
        cell_multiplier=12,
        num_sea_starters=4,
        sea_growth_bias=0.5
    )
    
    # Generate map
    regions, adjacency_graph, supply_centers, starting_positions = map_gen.generate_map()
    
    # Visualize the final map
    plt = map_gen.visualize_map(show_names=True, show_cells=False)
    plt.show()
    
    # Print statistics
    print(f"\nGenerated map with {len(regions)} regions from {len(map_gen.cells)} cells")
    print(f"Land regions: {sum(1 for r in regions.values() if r['type'] == 'land')}")
    print(f"Sea regions: {sum(1 for r in regions.values() if r['type'] == 'sea')}")
    print(f"Supply centers: {len(supply_centers)}")
    print(f"Powers: {len(starting_positions)}")