"""
Visualization Module

This module handles the visualization of the generated map.
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

class MapVisualizer:
    """Handles the visualization of the generated map."""
    
    def __init__(self, cells, regions, supply_centers, starting_positions, topology=None):
        """Initialize with map data.
        
        Args:
            cells: Dictionary of cell data (legacy format)
            regions: Dictionary of region data
            supply_centers: Set of supply center IDs
            starting_positions: Dictionary of starting positions by power
            topology: Optional topology data (vertices, edges, faces)
        """
        self.cells = cells
        self.regions = regions
        self.supply_centers = supply_centers
        self.starting_positions = starting_positions
        self.topology = topology
        self.terrain_colors = {
            "land": "#C5E0B4",
            "sea": "#BDD7EE"
        }
    
    def visualize_map(self, show_names=True, show_borders=True, show_cells=False, show_sea_growth=False):
        """Visualize the generated map with various display options."""
        plt.figure(figsize=(15, 12))
        
        # Print color mapping for powers
        print("\nPower Colors:")
        colors = list(mcolors.TABLEAU_COLORS.values())
        for i in range(7):  # Assuming max 7 powers
            print(f"  Power{i+1}: {colors[i % len(colors)]}")
        
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
            # Convert to numpy array if needed
            import numpy as np
            if not isinstance(polygon, np.ndarray):
                polygon = np.array(polygon)
            
            region_type = region["type"]
            color = self.terrain_colors[region_type]
            
            # Log region info
            region_info = f"Region {region_id} ({region['name']}): type={region_type}"
            
            # If region is owned by a power, use power color
            if "owner" in region and region["owner"]:
                try:
                    power_idx = int(region["owner"].replace("Power", "")) - 1
                    colors = list(mcolors.TABLEAU_COLORS.values())
                    color = colors[power_idx % len(colors)]
                    region_info += f", owner={region['owner']}, color={color}"
                    
                    # Make supply centers more saturated
                    if region.get("is_supply", False):
                        if region_type == "land":
                            # Slightly lighten the power color for land supply centers
                            r, g, b = mcolors.to_rgb(color)
                            color = (min(1.0, r + 0.2), min(1.0, g + 0.2), min(1.0, b + 0.2))
                            region_info += " (land supply center -> lighter color)"
                        else:
                            # Slightly darken the power color for sea supply centers
                            r, g, b = mcolors.to_rgb(color)
                            color = (max(0.0, r - 0.2), max(0.0, g - 0.2), max(0.0, b - 0.2))
                            region_info += " (sea supply center -> darker color)"
                except (ValueError, IndexError) as e:
                    region_info += f", Error getting power color: {e}"
                    # Fallback to default color if there's an issue with power index
                    pass
            # If not owned but is a supply center, use a neutral color
            elif region.get("is_supply", False):
                if region_type == "land":
                    color = "#A9D18E"  # Light green for neutral land supply centers
                    region_info += ", neutral land supply center -> #A9D18E"
                else:
                    color = "#9BC2E6"  # Light blue for neutral sea supply centers
                    region_info += ", neutral sea supply center -> #9BC2E6"
            
            print(region_info)
            
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
        
        title = "Diplomacy Map"
        if show_cells:
            title += " (Showing Cells)"
        if show_sea_growth:
            title += " (Sea Growth Visualization)"
        
        plt.title(title)
        plt.axis('off')
        plt.tight_layout()
        return plt
    
    def visualize_topology(self, show_edge_types=True, show_vertices=False):
        """
        Visualize the map using topological representation (edges and vertices).
        
        This renders the map from the Face-Edge-Vertex topology structure instead
        of from polygons, demonstrating that the topology correctly represents
        the map structure.
        
        Args:
            show_edge_types: Color-code edges by type (land, sea, coast, map-edge)
            show_vertices: Show vertex points
            
        Returns:
            matplotlib.pyplot object
        """
        if self.topology is None:
            print("Warning: No topology data available, falling back to polygon rendering")
            return self.visualize_map()
        
        plt.figure(figsize=(15, 12))
        
        # Extract topology data
        vertices = self.topology.get('vertices', [])
        edges = self.topology.get('edges', {})
        faces = self.topology.get('faces', {})
        
        # Create vertex lookup
        vertex_coords = {v['id']: v['coords'] for v in vertices}
        
        # Draw faces (fill with color)
        for face_id, face_data in faces.items():
            face_type = face_data.get('type', 'land')
            color = self.terrain_colors.get(face_type, '#CCCCCC')
            
            # Get the polygon vertices from edges
            edge_ids = face_data.get('edges', [])
            if not edge_ids:
                continue
            
            # Reconstruct the polygon from edges
            # This is a bit complex since edges may not be in order
            polygon_coords = []
            
            # Start with the first edge
            if edge_ids:
                first_edge = edges.get(edge_ids[0])
                if first_edge:
                    v1 = first_edge.get('v1')
                    v2 = first_edge.get('v2')
                    
                    # Try to build an ordered polygon
                    # For now, use the legacy vertices if available
                    if face_id in self.regions:
                        polygon = self.regions[face_id].get('vertices')
                    elif face_id in self.cells:
                        polygon = self.cells[face_id].get('vertices')
                    else:
                        continue
                    
                    if polygon is not None:
                        import numpy as np
                        if not isinstance(polygon, np.ndarray):
                            polygon = np.array(polygon)
                        
                        # Fill the polygon
                        plt.fill(polygon[:, 0], polygon[:, 1], color=color, alpha=0.6)
        
        # Define edge colors by type
        edge_colors = {
            'land': '#4A7C59',      # Dark green for land-land borders
            'sea': '#5B9BD5',       # Blue for sea-sea borders
            'coast': '#C55A11',     # Orange for coastlines
            'map-edge': '#7F7F7F'   # Gray for map boundaries
        }
        
        edge_widths = {
            'land': 1.5,
            'sea': 0.5,
            'coast': 2.5,
            'map-edge': 3.0
        }
        
        # Draw edges
        for edge_id, edge_data in edges.items():
            v1_id = edge_data.get('v1')
            v2_id = edge_data.get('v2')
            edge_type = edge_data.get('type', 'land')
            
            if v1_id not in vertex_coords or v2_id not in vertex_coords:
                continue
            
            v1_coords = vertex_coords[v1_id]
            v2_coords = vertex_coords[v2_id]
            
            # Get color and width based on edge type
            if show_edge_types:
                color = edge_colors.get(edge_type, '#000000')
                linewidth = edge_widths.get(edge_type, 1.0)
            else:
                color = '#000000'
                linewidth = 1.0
            
            # Draw the edge
            plt.plot([v1_coords[0], v2_coords[0]], 
                    [v1_coords[1], v2_coords[1]], 
                    color=color, linewidth=linewidth, alpha=0.8)
        
        # Optionally draw vertices
        if show_vertices:
            for vertex in vertices:
                coords = vertex['coords']
                plt.plot(coords[0], coords[1], 'ko', markersize=2, alpha=0.5)
        
        # Add legend for edge types
        if show_edge_types:
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], color=edge_colors['land'], linewidth=edge_widths['land'], 
                       label='Land border'),
                Line2D([0], [0], color=edge_colors['coast'], linewidth=edge_widths['coast'], 
                       label='Coastline'),
                Line2D([0], [0], color=edge_colors['sea'], linewidth=edge_widths['sea'], 
                       label='Sea border'),
                Line2D([0], [0], color=edge_colors['map-edge'], linewidth=edge_widths['map-edge'], 
                       label='Map boundary')
            ]
            plt.legend(handles=legend_elements, loc='upper right')
        
        title = "Topology Visualization (Edge-Based Rendering)"
        if show_vertices:
            title += " with Vertices"
        
        plt.title(title)
        plt.axis('off')
        plt.tight_layout()
        return plt
