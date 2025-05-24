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
        """Choose strategic starting positions for seas."""
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