"""
Visualization Module

This module handles the visualization of the generated map.
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

class MapVisualizer:
    """Handles the visualization of the generated map."""
    
    def __init__(self, cells, regions, supply_centers, starting_positions):
        """Initialize with map data."""
        self.cells = cells
        self.regions = regions
        self.supply_centers = supply_centers
        self.starting_positions = starting_positions
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
