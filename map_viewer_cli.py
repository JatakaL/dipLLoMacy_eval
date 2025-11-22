#!/usr/bin/env python3
"""
CLI Map Viewer for Diplomacy Map Generator

This script renders JSON outputs from any phase to PNG images.
Useful for batch processing, headless environments, or quick visualization.

Usage:
    python map_viewer_cli.py input.json [output.png]
    python map_viewer_cli.py --directory output_dir/
"""

import json
import sys
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


class MapData:
    """Holds parsed map data from a JSON file."""
    
    def __init__(self, filepath):
        """Load and parse the JSON file."""
        self.filepath = Path(filepath)
        self.filename = self.filepath.name
        
        with open(filepath, 'r') as f:
            self.data = json.load(f)
        
        self.cells = self.data.get('cells', {})
        self.config = self.data.get('config', {})
        self.metadata = self.data.get('metadata', {})
        self.powers = self.data.get('powers', {})
        self.supply_centers = self.data.get('supply_centers', {})
        self.adjacency = self.data.get('adjacency', {})
        self.analysis = self.data.get('analysis', {})
        
        # Detect phase
        self.phase = self._detect_phase()
    
    def _detect_phase(self):
        """Detect which phase this JSON represents."""
        # Check metadata first
        phases_completed = self.metadata.get('phases_completed', 0)
        if phases_completed:
            return phases_completed
        
        # Check filename
        filename_lower = self.filename.lower()
        if 'phase1' in filename_lower or 'mesh' in filename_lower:
            return 1
        elif 'phase2' in filename_lower or 'terrain' in filename_lower:
            return 2
        elif 'phase3' in filename_lower or 'province' in filename_lower:
            return 3
        elif 'phase4' in filename_lower or 'kingdom' in filename_lower:
            return 4
        elif 'phase5' in filename_lower or 'supply' in filename_lower:
            return 5
        elif 'phase6' in filename_lower or 'optimization' in filename_lower:
            return 6
        elif 'phase7' in filename_lower or 'final' in filename_lower or 'naming' in filename_lower:
            return 7
        
        # Infer from data content
        sample_cell = next(iter(self.cells.values())) if self.cells else {}
        
        if 'name' in sample_cell and sample_cell.get('name'):
            return 7  # Phase 7: has names
        elif self.supply_centers:
            return 5  # Phase 5+: has supply centers
        elif self.powers:
            return 4  # Phase 4+: has powers/kingdoms
        elif 'type' in sample_cell and sample_cell.get('type') in ['land', 'sea', 'impassable']:
            if 'coastal' in sample_cell:
                return 3  # Phase 3+: has province info
            return 2  # Phase 2: has terrain
        elif 'vertices' in sample_cell:
            return 1  # Phase 1: basic mesh
        
        return 7  # Default to final phase if unsure
    
    def get_phase_name(self):
        """Get human-readable phase name."""
        phase_names = {
            1: "Phase 1: Mesh Generation",
            2: "Phase 2: Terrain Assignment",
            3: "Phase 3: Province Definition",
            4: "Phase 4: Kingdom Generation",
            5: "Phase 5: Supply Centers",
            6: "Phase 6: Graph Optimization",
            7: "Phase 7: Final Map"
        }
        return phase_names.get(self.phase, "Unknown Phase")


def visualize_map(map_data, output_path=None, dpi=150):
    """Visualize the map and save to file or display."""
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Color schemes
    terrain_colors = {
        "land": "#C5E0B4",
        "sea": "#BDD7EE",
        "impassable": "#A6A6A6"
    }
    power_colors = list(mcolors.TABLEAU_COLORS.values())
    
    phase = map_data.phase
    
    # Visualize based on phase
    if phase == 1:
        # Phase 1: Basic mesh
        for cell_id, cell in map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            # Draw cell polygon
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color='lightgray', alpha=0.5, edgecolor='black', linewidth=0.8)
            
            # Draw center point
            center = cell.get('center', [0, 0])
            ax.plot(center[0], center[1], 'o', color='red', markersize=2)
            
            # Label with cell ID (only for small maps)
            if len(map_data.cells) < 50:
                ax.text(center[0], center[1], cell_id, 
                       ha='center', va='center', fontsize=5, alpha=0.7)
    
    elif phase == 2:
        # Phase 2: Terrain
        for cell_id, cell in map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            color = terrain_colors.get(cell_type, 'gray')
            
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    elif phase == 3:
        # Phase 3: Provinces
        for cell_id, cell in map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            color = terrain_colors.get(cell_type, 'gray')
            
            # Highlight coastal cells
            if cell.get('coastal', False):
                color = '#FFE699'  # Yellow for coastal
            
            # Highlight impassable zones
            if cell.get('impassable', False):
                color = terrain_colors['impassable']
            
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
    
    else:
        # Phase 4+: Kingdoms and supply centers
        # Get list of powers - either from powers dict or by extracting from cell owners
        if map_data.powers:
            power_list = sorted(map_data.powers.keys())
        else:
            # Extract unique power names from cells
            power_set = set()
            for cell in map_data.cells.values():
                owner = cell.get('owner')
                if owner:
                    power_set.add(owner)
            power_list = sorted(power_set)
        
        for cell_id, cell in map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            owner = cell.get('owner')
            is_sc = cell.get('is_supply_center', False)
            
            # Default color
            color = terrain_colors.get(cell_type, 'gray')
            
            # Color by owner
            if owner and power_list:
                if owner in power_list:
                    power_idx = power_list.index(owner)
                    color = power_colors[power_idx % len(power_colors)]
            elif is_sc and not owner:
                # Neutral supply center
                color = '#FFE699' if cell_type == 'land' else '#9BC2E6'
            
            # Draw cell polygon
            alpha = 0.9 if owner or is_sc else 0.6
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color=color, alpha=alpha, edgecolor='black', linewidth=0.8)
            
            # Draw supply center marker
            if is_sc:
                center = cell.get('center', [0, 0])
                ax.plot(center[0], center[1], 'o', 
                       markersize=10, color='gold', 
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
            
            # Label with name if available (Phase 7)
            if phase >= 7:
                center = cell.get('center', [0, 0])
                name = cell.get('name', '')
                if name and (cell_type == 'land' or is_sc):
                    ax.text(center[0], center[1], name, 
                           ha='center', va='center', fontsize=7, weight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   alpha=0.8, edgecolor='none'), zorder=5)
        
        # Add legend for powers
        if power_list:
            legend_elements = []
            for power_idx, power_id in enumerate(power_list):
                color = power_colors[power_idx % len(power_colors)]
                legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, label=power_id))
            
            if legend_elements:
                ax.legend(handles=legend_elements, loc='upper left', 
                         bbox_to_anchor=(0, 1), fontsize=9, framealpha=0.9)
    
    # Finishing touches
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Build title - keep it concise to avoid overflow
    title = f"{map_data.filename}\n{map_data.get_phase_name()}"
    
    # Add statistics to title for later phases (condensed format)
    if phase >= 4:
        stats = []
        if map_data.cells:
            land_count = sum(1 for c in map_data.cells.values() if c.get('type') == 'land')
            sea_count = sum(1 for c in map_data.cells.values() if c.get('type') == 'sea')
            stats.append(f"Land: {land_count}, Sea: {sea_count}")
        if map_data.powers:
            stats.append(f"Powers: {len(map_data.powers)}")
        if map_data.supply_centers:
            total_scs = len(map_data.supply_centers.get('home', [])) + len(map_data.supply_centers.get('neutral', []))
            stats.append(f"SCs: {total_scs}")
        
        # Only add stats if they fit reasonably (limit to ~60 chars)
        if stats:
            stats_line = " | ".join(stats)
            if len(stats_line) < 60:
                title += "\n" + stats_line
    
    ax.set_title(title, fontsize=13, weight='bold', pad=20)
    
    plt.tight_layout()
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        print(f"Saved visualization to: {output_path}")
    else:
        plt.show()
    
    plt.close(fig)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Render Diplomacy map JSON files to PNG images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render a single file
  python map_viewer_cli.py output/final_map.json
  
  # Render with custom output path
  python map_viewer_cli.py output/final_map.json my_map.png
  
  # Render all JSON files in a directory
  python map_viewer_cli.py --directory output/
  
  # High resolution rendering
  python map_viewer_cli.py input.json output.png --dpi 300
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input JSON file')
    parser.add_argument('output', nargs='?', help='Output PNG file (optional)')
    parser.add_argument('-d', '--directory', help='Process all JSON files in directory')
    parser.add_argument('--dpi', type=int, default=150, help='Output DPI (default: 150)')
    
    args = parser.parse_args()
    
    # Process directory
    if args.directory:
        directory = Path(args.directory)
        if not directory.is_dir():
            print(f"Error: {directory} is not a directory", file=sys.stderr)
            return 1
        
        json_files = sorted(directory.glob('*.json'))
        if not json_files:
            print(f"No JSON files found in {directory}", file=sys.stderr)
            return 1
        
        print(f"Found {len(json_files)} JSON file(s) in {directory}")
        
        for json_file in json_files:
            try:
                print(f"\nProcessing {json_file.name}...")
                map_data = MapData(json_file)
                output_path = json_file.with_suffix('.png')
                visualize_map(map_data, output_path, args.dpi)
            except Exception as e:
                print(f"Error processing {json_file.name}: {e}", file=sys.stderr)
                continue
        
        print(f"\nCompleted processing {len(json_files)} file(s)")
        return 0
    
    # Process single file
    if not args.input:
        parser.print_help()
        return 1
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        return 1
    
    try:
        print(f"Loading {input_path}...")
        map_data = MapData(input_path)
        print(f"Detected: {map_data.get_phase_name()}")
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix('.png')
        
        print(f"Rendering map...")
        visualize_map(map_data, output_path, args.dpi)
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
