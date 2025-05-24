"""
Cell Generation Module

This module handles the generation of Voronoi cells and sea/land distribution.
"""

import numpy as np
import random
from shapely.geometry import Polygon as ShapelyPolygon
import networkx as nx

class CellGenerator:
    """Handles the generation and management of Voronoi cells for the map."""
    
    def __init__(self, num_regions, land_ratio, cell_multiplier, 
                 num_sea_starters, sea_growth_bias):
        """Initialize the cell generator with configuration parameters."""
        self.num_regions = num_regions
        self.land_ratio = land_ratio
        self.cell_multiplier = cell_multiplier
        self.num_sea_starters = num_sea_starters
        self.sea_growth_bias = sea_growth_bias
        
        # Initialize structures
        self.cells = {}
        self.cell_polygons = {}
        self.cell_adjacency = nx.Graph()
    
    def generate_voronoi_cells(self):
        """Generate Voronoi cells that will be merged into regions."""
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
        from scipy.spatial import Voronoi
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
    
    def build_cell_adjacency(self):
        """Build adjacency graph for cells."""
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
    
    def grow_seas_from_starters(self):
        """Grow seas from strategic starter points using organic growth."""
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
                    
                    # Count sea neighbors - higher is better
                    sea_neighbors = [
                        n for n in self.cells[neighbor]["neighbors"] 
                        if self.cells[n]["type"] == "sea"
                    ]
                    sea_neighbor_count = len(sea_neighbors)
                    
                    # Calculate distance to nearest sea starter with falloff
                    if current_sea_cells:
                        min_distance = min(
                            np.linalg.norm(
                                np.array(self.cells[neighbor]["center"]) - 
                                np.array(self.cells[starter]["center"])
                            )
                            for starter in current_sea_cells
                        )
                        # More gradual falloff for larger maps
                        distance_factor = max(0.3, 1.0 - (min_distance * 0.1))
                    else:
                        distance_factor = 0.5
                    
                    # Base probability with distance falloff
                    growth_probability = 0.4 * distance_factor
                    
                    # Strong neighbor influence with diminishing returns
                    if sea_neighbor_count > 0:
                        growth_probability += min(0.5, sea_neighbor_count * 0.2)
                    
                    # Apply global growth bias with some randomness
                    growth_probability *= self.sea_growth_bias * random.uniform(0.9, 1.1)
                    
                    # Significant bonus for being adjacent to existing sea
                    if sea_neighbor_count >= 3:
                        growth_probability *= 2.5
                    elif sea_neighbor_count == 2:
                        growth_probability *= 2.0
                    elif sea_neighbor_count == 1:
                        growth_probability *= 1.5
                        
                    # Bonus for being near map edges
                    x, y = self.cells[neighbor]["center"]
                    edge_factor = 1.0
                    if x < 0.1 or x > 0.9 or y < 0.1 or y > 0.9:
                        edge_factor = 1.3
                    growth_probability *= edge_factor
                    
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
        """Choose strategic starting positions for seas."""
        cell_ids = list(self.cells.keys())
        
        # Strategy: Place starters near edges and corners
        starters = []
        
        # Get cells near each corner and edge center
        corner_cells = {
            'topleft': [],
            'topright': [],
            'bottomleft': [],
            'bottomright': []
        }
        edge_cells = {
            'left': [],
            'right': [],
            'top': [],
            'bottom': []
        }
        
        for cell_id in cell_ids:
            center = self.cells[cell_id]["center"]
            x, y = center[0], center[1]
            
            # Categorize by position
            if x < 0.3 and y > 0.7:
                corner_cells['topleft'].append(cell_id)
            elif x > 0.7 and y > 0.7:
                corner_cells['topright'].append(cell_id)
            elif x < 0.3 and y < 0.3:
                corner_cells['bottomleft'].append(cell_id)
            elif x > 0.7 and y < 0.3:
                corner_cells['bottomright'].append(cell_id)
            elif x < 0.2:
                edge_cells['left'].append(cell_id)
            elif x > 0.8:
                edge_cells['right'].append(cell_id)
            elif y < 0.2:
                edge_cells['bottom'].append(cell_id)
            elif y > 0.8:
                edge_cells['top'].append(cell_id)
        
        # First, try to place starters in corners
        corner_order = ['topleft', 'topright', 'bottomleft', 'bottomright']
        for corner in corner_order:
            if len(starters) >= self.num_sea_starters:
                break
            if corner_cells[corner]:
                # Choose the cell closest to the corner
                if corner == 'topleft':
                    target = np.array([0, 1])
                elif corner == 'topright':
                    target = np.array([1, 1])
                elif corner == 'bottomleft':
                    target = np.array([0, 0])
                else:  # bottomright
                    target = np.array([1, 0])
                
                distances = [
                    (cell_id, np.linalg.norm(np.array(self.cells[cell_id]["center"]) - target))
                    for cell_id in corner_cells[corner]
                ]
                if distances:
                    distances.sort(key=lambda x: x[1])
                    starter = distances[0][0]  # Closest to corner
                    starters.append(starter)
        
        # If we need more starters, place them at the middle of edges
        edge_order = ['left', 'right', 'top', 'bottom']
        for edge in edge_order:
            if len(starters) >= self.num_sea_starters:
                break
            if edge_cells[edge]:
                # Find the middle of the edge
                if edge in ['left', 'right']:
                    target_y = 0.5
                    target_x = 0 if edge == 'left' else 1
                else:  # top or bottom
                    target_x = 0.5
                    target_y = 1 if edge == 'top' else 0
                
                target = np.array([target_x, target_y])
                
                # Find the cell closest to the middle of the edge
                distances = [
                    (cell_id, np.linalg.norm(np.array(self.cells[cell_id]["center"]) - target))
                    for cell_id in edge_cells[edge]
                ]
                if distances:
                    distances.sort(key=lambda x: x[1])
                    starter = distances[0][0]  # Closest to edge middle
                    if starter not in starters:
                        starters.append(starter)
        
        # If we still need more starters, choose from remaining edge cells
        edge_cell_list = [cell for cells in edge_cells.values() for cell in cells]
        while len(starters) < self.num_sea_starters and edge_cell_list:
            cell = random.choice(edge_cell_list)
            if cell not in starters:
                starters.append(cell)
            edge_cell_list.remove(cell)
        
        # As a last resort, choose any remaining cells
        remaining = [c for c in cell_ids if c not in starters]
        while len(starters) < self.num_sea_starters and remaining:
            starters.append(remaining.pop(0))
        
        return starters