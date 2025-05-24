"""
Diplomacy Map Generator

This module provides a class for generating Diplomacy-style maps with land and sea regions,
supply centers, and starting positions for multiple players.
"""

from .cell_generation import CellGenerator
from .region_merging import RegionMerger
from .game_elements import GameElements
from .naming import RegionNamer
from .visualization import MapVisualizer

class DiplomacyMapGenerator:
    """Generates Diplomacy-style maps with various configuration options."""
    
    def __init__(self, num_regions=100, num_powers=7, land_ratio=0.7, supply_density=0.25, 
                 cell_multiplier=10, num_sea_starters=4, sea_growth_bias=0.7):
        """Initialize the map generator with configuration parameters.
        
        Args:
            num_regions: Target number of regions in the final map
            num_powers: Number of player powers in the game
            land_ratio: Target ratio of land to total area (0-1)
            supply_density: Density of supply centers as a ratio of total regions
            cell_multiplier: Number of cells per region in initial generation
            num_sea_starters: Number of starting points for sea generation
            sea_growth_bias: Bias for sea growth (lower = more organic shapes)
        """
        self.num_regions = num_regions
        self.num_powers = num_powers
        self.land_ratio = land_ratio
        self.supply_density = supply_density
        self.cell_multiplier = cell_multiplier
        self.num_sea_starters = num_sea_starters
        self.sea_growth_bias = sea_growth_bias
        
        # Initialize structures
        self.cells = {}
        self.regions = {}
        self.supply_centers = set()
        self.starting_positions = {}
    
    def generate_map(self):
        """Generate a complete Diplomacy-style map using cell merging.
        
        Returns:
            tuple: (regions_dict, adjacency_graph, supply_centers_set, starting_positions_dict)
        """
        # Step 1: Generate Voronoi cells and set up initial structures
        cell_gen = CellGenerator(
            num_regions=self.num_regions,
            land_ratio=self.land_ratio,
            cell_multiplier=self.cell_multiplier,
            num_sea_starters=self.num_sea_starters,
            sea_growth_bias=self.sea_growth_bias
        )
        
        print("Generating Voronoi cells...")
        cell_gen.generate_voronoi_cells()
        cell_gen.build_cell_adjacency()
        
        # Step 2: Grow seas from starter points
        print("\nGrowing seas...")
        cell_gen.grow_seas_from_starters()
        
        # Step 3: Merge cells into regions
        print("\nMerging cells into regions...")
        region_merger = RegionMerger(
            cells=cell_gen.cells,
            cell_polygons=cell_gen.cell_polygons,
            cell_adjacency=cell_gen.cell_adjacency,
            num_regions=self.num_regions
        )
        
        region_merger.merge_cells_into_regions()
        region_merger.determine_region_adjacency()
        
        # Step 4: Add game elements
        print("\nAdding game elements...")
        game_elements = GameElements(
            regions=region_merger.regions,
            adjacency_graph=region_merger.adjacency_graph,
            num_powers=self.num_powers,
            supply_density=self.supply_density
        )
        
        game_elements.place_supply_centers()
        game_elements.assign_starting_positions()
        
        # Step 5: Name regions
        print("\nNaming regions...")
        namer = RegionNamer()
        namer.name_regions(region_merger.regions)
        
        # Update instance variables
        self.cells = cell_gen.cells
        self.regions = region_merger.regions
        self.supply_centers = game_elements.supply_centers
        self.starting_positions = game_elements.starting_positions
        self.adjacency_graph = region_merger.adjacency_graph
        self.region_polygons = region_merger.region_polygons
        self.borders = region_merger.borders
        
        print("\nMap generation complete!")
        print(f"Generated {len(self.regions)} regions ({sum(1 for r in self.regions.values() if r['type'] == 'land')} land, "
              f"{sum(1 for r in self.regions.values() if r['type'] == 'sea')} sea)")
        print(f"{len(self.supply_centers)} supply centers")
        print(f"{len(self.starting_positions)} powers with starting positions")
        
        return self.regions, self.adjacency_graph, self.supply_centers, self.starting_positions
    
    def visualize_map(self, show_names=True, show_borders=True, show_cells=False, show_sea_growth=False):
        """Visualize the generated map with various display options.
        
        Args:
            show_names: Whether to show region names
            show_borders: Whether to show region borders
            show_cells: Whether to show the underlying cell structure
            show_sea_growth: Whether to visualize sea growth patterns
            
        Returns:
            matplotlib.pyplot: The pyplot figure for further customization or display
        """
        visualizer = MapVisualizer(
            cells=self.cells,
            regions=self.regions,
            supply_centers=self.supply_centers,
            starting_positions=self.starting_positions
        )
        
        return visualizer.visualize_map(
            show_names=show_names,
            show_borders=show_borders,
            show_cells=show_cells,
            show_sea_growth=show_sea_growth
        )
