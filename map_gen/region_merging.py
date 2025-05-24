"""
Region Merging Module

This module handles the merging of cells into larger regions and managing region adjacency.
"""

import numpy as np
import networkx as nx
from shapely.ops import unary_union

class RegionMerger:
    """Handles merging cells into regions and managing region adjacency."""
    
    def __init__(self, cells, cell_polygons, cell_adjacency, num_regions):
        """Initialize with cell data and configuration."""
        self.cells = cells
        self.cell_polygons = cell_polygons
        self.cell_adjacency = cell_adjacency
        self.num_regions = num_regions
        
        # Initialize region structures
        self.regions = {}
        self.region_polygons = {}
        self.adjacency_graph = nx.Graph()
        self.borders = []
    
    def merge_cells_into_regions(self):
        """Merge cells into larger regions using various strategies."""
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
    
    def _merge_cells_by_type(self, cells, target_count, region_type):
        """Merge cells of the same type into regions."""
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
                from .clustering import robust_cluster_cells
                component_regions = robust_cluster_cells(
                    component_cells, component_target, self.cell_adjacency, self.cells
                )
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
    
    def _merge_seas_for_connectivity(self, sea_cells, target_count):
        """Merge sea cells into appropriately-sized strategic sea regions."""
        if not sea_cells or target_count <= 0:
            return []
        
        # Create subgraph of only sea cells
        sea_subgraph = self.cell_adjacency.subgraph(sea_cells)
        
        # Get all connected components of sea cells
        sea_components = list(nx.connected_components(sea_subgraph))
        
        print(f"Found {len(sea_components)} sea components, targeting {target_count} sea regions")
        
        merged_regions = []
        
        # Process ALL components - don't break early
        for i, component in enumerate(sea_components):
            component_cells = list(component)
            print(f"  Processing sea component {i+1} with {len(component_cells)} cells")
            
            # Calculate optimal number of regions for this component
            optimal_cells_per_region = 10  # TODO: Make this configurable or dynamic
            
            # If we've already reached our target, just make this one region
            if len(merged_regions) >= target_count:
                merged_regions.append((component_cells, "sea"))
                print(f"    Merged as single region (over target)")
            else:
                # Calculate how many regions this component should have
                remaining_target = target_count - len(merged_regions)
                component_regions = max(1, len(component_cells) // optimal_cells_per_region)
                component_regions = min(component_regions, remaining_target)
                
                print(f"    Component size: {len(component_cells)}, optimal regions: {component_regions}, "
                      f"remaining target: {remaining_target}")
                
                if len(component_cells) <= optimal_cells_per_region or component_regions == 1:
                    # Small component, keep as single region
                    merged_regions.append((component_cells, "sea"))
                    print(f"    Merged as single region")
                else:
                    # Large component, break into multiple strategic sea regions
                    from .clustering import robust_cluster_cells
                    component_clusters = robust_cluster_cells(
                        component_cells, component_regions, self.cell_adjacency, self.cells
                    )
                    for cluster in component_clusters:
                        merged_regions.append((cluster, "sea"))
                    print(f"    Split into {len(component_clusters)} regions")
        
        print(f"Final: Created {len(merged_regions)} sea regions from {len(sea_cells)} cells")
        
        # Verify all cells were assigned
        assigned_cells = set()
        for region_cells, _ in merged_regions:
            assigned_cells.update(region_cells)
        
        unassigned = set(sea_cells) - assigned_cells
        if unassigned:
            print(f"ERROR: {len(unassigned)} sea cells not assigned!")
            # Create single-cell regions for any unassigned cells
            for cell in unassigned:
                merged_regions.append(([cell], "sea"))
                print(f"  Created single-cell region for unassigned cell {cell}")
        
        return merged_regions
    
    def determine_region_adjacency(self):
        """Determine which regions are adjacent to each other."""
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
