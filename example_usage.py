#!/usr/bin/env python3
"""
Example usage of the Diplomacy Map Generator module.
"""

from dipLLoMacy_eval.map_gen import DiplomacyMapGenerator

# Create map generator with custom parameters
map_gen = DiplomacyMapGenerator(
    num_regions=75,         # Target number of regions
    num_powers=7,           # Number of player powers
    land_ratio=0.6,         # Ratio of land to total area
    supply_density=0.3,     # Density of supply centers
    cell_multiplier=12,     # Cells per region in initial generation
    num_sea_starters=6,     # Number of sea starting points
    sea_growth_bias=0.2     # Lower = more organic sea shapes
)

# Generate the map
print("Generating map...")
regions, adjacency_graph, supply_centers, starting_positions = map_gen.generate_map()

# Visualize the map with default settings
print("Displaying map...")
plt = map_gen.visualize_map(show_names=True, show_cells=False)
plt.show()

# You can also save the figure
# plt.savefig('diplomacy_map.png', dpi=300, bbox_inches='tight')

# Print some statistics
print("\nMap Statistics:")
print(f"Total regions: {len(regions)}")
print(f"Land regions: {sum(1 for r in regions.values() if r['type'] == 'land')}")
print(f"Sea regions: {sum(1 for r in regions.values() if r['type'] == 'sea')}")
print(f"Supply centers: {len(supply_centers)}")
print(f"Powers: {len(starting_positions)}")

# Print starting positions for each power
print("\nStarting positions:")
for power, positions in starting_positions.items():
    region_names = [regions[pos['region']]['name'] for pos in positions]
    print(f"{power}: {', '.join(region_names)}")
