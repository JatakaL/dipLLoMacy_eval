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
        self.topology = self.data.get('topology', None)
        
        # Detect phase
        self.phase = self._detect_phase()
        
        # Reconstruct cells from topology if cells are not present
        if not self.cells and self.topology:
            self._reconstruct_cells_from_topology()
    
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
    
    def _reconstruct_cells_from_topology(self):
        """Reconstruct cell-like data from topology for visualization."""
        if not self.topology:
            return
        
        vertices_list = self.topology.get('vertices', [])
        edges = self.topology.get('edges', {})
        faces = self.topology.get('faces', {})
        
        # Create vertex lookup
        vertex_coords = {v['id']: v['coords'] for v in vertices_list}
        
        # Reconstruct cells from faces
        self.cells = {}
        for face_id, face_data in faces.items():
            # Get the edges that form this face
            face_edges = face_data.get('edges', [])
            
            # Reconstruct polygon from edges
            polygon_vertices = self._reconstruct_polygon_from_edges(
                face_edges, edges, vertex_coords
            )
            
            # Create cell-like structure
            cell = {
                'id': face_id,
                'type': face_data.get('type', 'land'),
                'center': face_data.get('center', [0.5, 0.5]),
                'vertices': polygon_vertices,
                'name': face_data.get('name', face_id),
                'owner': face_data.get('owner'),
                'is_supply_center': face_data.get('is_supply_center', False),
                'sc_type': face_data.get('sc_type'),
                'is_home': face_data.get('is_home', False),
                'coastal': face_data.get('coastal', False),
                'impassable': face_data.get('impassable', False),
            }
            
            self.cells[face_id] = cell
    
    def _reconstruct_polygon_from_edges(self, edge_ids, edges, vertex_coords):
        """Reconstruct an ordered polygon from a list of edge IDs."""
        if not edge_ids:
            return []
        
        # Build a graph of vertex connections from edges
        vertex_graph = {}
        for edge_id in edge_ids:
            if edge_id not in edges:
                continue
            edge = edges[edge_id]
            v1, v2 = edge['v1'], edge['v2']
            
            if v1 not in vertex_graph:
                vertex_graph[v1] = []
            if v2 not in vertex_graph:
                vertex_graph[v2] = []
            vertex_graph[v1].append(v2)
            vertex_graph[v2].append(v1)
        
        if not vertex_graph:
            return []
        
        # Start from any vertex and trace the boundary
        start_vertex = next(iter(vertex_graph.keys()))
        polygon = []
        current = start_vertex
        visited = set()
        
        # Trace the polygon boundary by following unvisited neighbors
        max_iterations = len(vertex_graph) + 1  # Safety limit
        for _ in range(max_iterations):
            if current in visited:
                # We've completed the loop back to a visited vertex
                break
            
            visited.add(current)
            if current in vertex_coords:
                polygon.append(vertex_coords[current])
            
            # Find next unvisited neighbor
            neighbors = vertex_graph.get(current, [])
            next_vertex = None
            for neighbor in neighbors:
                if neighbor not in visited:
                    next_vertex = neighbor
                    break
                # Allow closing the loop by returning to start
                elif neighbor == start_vertex and len(visited) == len(vertex_graph):
                    next_vertex = neighbor
                    break
            
            if next_vertex is None:
                # No more neighbors to visit
                break
            current = next_vertex
        
        return polygon


def visualize_with_topology(ax, map_data, show_labels=False):
    """Visualize using topology data structure.
    
    Args:
        ax: Matplotlib axis
        map_data: MapData object
        show_labels: Whether to show cell ID labels
    """
    topology = map_data.topology
    vertices_list = topology.get('vertices', [])
    edges = topology.get('edges', {})
    faces = topology.get('faces', {})
    cells = map_data.cells
    
    terrain_colors = {
        "land": "#C5E0B4",
        "sea": "#BDD7EE",
        "impassable": "#A6A6A6"
    }
    
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in vertices_list}
    
    # Define edge colors by type
    edge_colors = {
        'land': '#4A7C59',
        'sea': '#5B9BD5',
        'coast': '#C55A11',
        'map-edge': '#2F2F2F'
    }
    
    edge_widths = {
        'land': 1.0,
        'sea': 0.8,
        'coast': 1.8,
        'map-edge': 2.0
    }
    
    # First pass: Draw filled faces
    for face_id, face_data in faces.items():
        face_type = face_data.get('type', 'land')
        color = terrain_colors.get(face_type, 'gray')
        
        # Get polygon from legacy cell data
        if face_id in cells and 'vertices' in cells[face_id]:
            polygon = np.array(cells[face_id]['vertices'])
            if len(polygon) >= 3:
                ax.fill(polygon[:, 0], polygon[:, 1], color=color, alpha=0.7)
    
    # Second pass: Draw edges
    for edge_id, edge_data in edges.items():
        v1_id = edge_data.get('v1')
        v2_id = edge_data.get('v2')
        edge_type = edge_data.get('type', 'land')
        
        if v1_id not in vertex_coords or v2_id not in vertex_coords:
            continue
        
        v1_coords = vertex_coords[v1_id]
        v2_coords = vertex_coords[v2_id]
        
        color = edge_colors.get(edge_type, '#000000')
        linewidth = edge_widths.get(edge_type, 1.0)
        
        # Check if visual_path is available (fractal subdivision)
        visual_path = edge_data.get('visual_path')
        if visual_path and len(visual_path) >= 2:
            # Draw the fractal edge using visual_path
            path_array = np.array(visual_path)
            ax.plot(path_array[:, 0], path_array[:, 1], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')
        else:
            # Draw simple straight line
            ax.plot([v1_coords[0], v2_coords[0]], 
                    [v1_coords[1], v2_coords[1]], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')
    
    # Optional labels
    if show_labels:
        for face_id, face_data in faces.items():
            center = face_data.get('center')
            if center:
                ax.text(center[0], center[1], face_id, 
                        ha='center', va='center', fontsize=6, alpha=0.8)
    
    # Legend for edge types
    legend_elements = [
        plt.Line2D([0], [0], color=edge_colors['land'], linewidth=edge_widths['land'], 
                   label='Land border'),
        plt.Line2D([0], [0], color=edge_colors['coast'], linewidth=edge_widths['coast'], 
                   label='Coastline'),
        plt.Line2D([0], [0], color=edge_colors['sea'], linewidth=edge_widths['sea'], 
                   label='Sea border'),
        plt.Line2D([0], [0], color=edge_colors['map-edge'], linewidth=edge_widths['map-edge'], 
                   label='Map boundary')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8, framealpha=0.9)


def draw_fractal_edges(ax, map_data):
    """Draw edges using visual_path from topology for fractal appearance.
    
    Args:
        ax: Matplotlib axis
        map_data: MapData object with topology
    """
    topology = map_data.topology
    if not topology:
        return
    
    vertices_list = topology.get('vertices', [])
    edges = topology.get('edges', {})
    
    # Create vertex lookup
    vertex_coords = {v['id']: v['coords'] for v in vertices_list}
    
    # Define edge colors by type
    edge_colors = {
        'land': '#4A7C59',      # Dark green for land-land borders
        'sea': '#5B9BD5',       # Blue for sea-sea borders
        'coast': '#C55A11',     # Orange for coastlines
        'map-edge': '#2F2F2F'   # Dark gray for map boundaries
    }
    
    edge_widths = {
        'land': 1.0,
        'sea': 0.8,
        'coast': 1.8,
        'map-edge': 2.0
    }
    
    # Draw edges with type-based styling
    for edge_id, edge_data in edges.items():
        v1_id = edge_data.get('v1')
        v2_id = edge_data.get('v2')
        edge_type = edge_data.get('type', 'land')
        
        if v1_id not in vertex_coords or v2_id not in vertex_coords:
            continue
        
        v1_coords = vertex_coords[v1_id]
        v2_coords = vertex_coords[v2_id]
        
        # Get color and width based on edge type
        color = edge_colors.get(edge_type, '#000000')
        linewidth = edge_widths.get(edge_type, 1.0)
        
        # Check if visual_path is available (fractal subdivision)
        visual_path = edge_data.get('visual_path')
        if visual_path and len(visual_path) >= 2:
            # Draw the fractal edge using visual_path
            path_array = np.array(visual_path)
            ax.plot(path_array[:, 0], path_array[:, 1], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')
        else:
            # Draw simple straight line
            ax.plot([v1_coords[0], v2_coords[0]], 
                    [v1_coords[1], v2_coords[1]], 
                    color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')


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
        if map_data.topology:
            visualize_with_topology(ax, map_data, show_labels=(len(map_data.cells) < 50))
        else:
            # Legacy visualization
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
        if map_data.topology:
            visualize_with_topology(ax, map_data, show_labels=False)
        else:
            # Legacy visualization
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
    
    elif phase == 6:
        # Phase 6: Graph Optimization with analysis data
        # Get analysis data
        analysis = map_data.analysis
        
        # Get list of powers
        if map_data.powers:
            power_list = sorted(map_data.powers.keys())
        else:
            power_set = set()
            for cell in map_data.cells.values():
                owner = cell.get('owner')
                if owner:
                    power_set.add(owner)
            power_list = sorted(power_set)
        
        # Get analysis-specific data
        # Handle new Phase 6 structure with before/after optimization
        # Use after_optimization if available, otherwise use direct keys (backward compatibility)
        if 'after_optimization' in analysis:
            degree_analysis = analysis['after_optimization'].get('degree_analysis', {})
            triangle_analysis = analysis['after_optimization'].get('triangle_analysis', {})
            sea_connectivity = analysis['after_optimization'].get('sea_connectivity', {})
        else:
            # Backward compatibility with old structure
            degree_analysis = analysis.get('degree_analysis', {})
            triangle_analysis = analysis.get('triangle_analysis', {})
            sea_connectivity = analysis.get('sea_connectivity', {})
        
        highly_connected = set(degree_analysis.get('highly_connected_nodes', []))
        dead_ends = set(degree_analysis.get('dead_end_nodes', []))
        contested_scs = analysis.get('contested_scs', [])
        contested_sc_ids = set(sc['cell_id'] for sc in contested_scs)
        power_classifications = analysis.get('power_classifications', {})
        
        # Draw cells with power colors and analysis overlays
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
            
            # Special border for highly connected nodes and dead ends
            edge_color = 'black'
            edge_width = 0.8
            if cell_id in highly_connected:
                edge_color = 'red'
                edge_width = 2.5
            elif cell_id in dead_ends:
                edge_color = 'orange'
                edge_width = 2.5
            
            # Draw cell polygon
            alpha = 0.9 if owner or is_sc else 0.6
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color=color, alpha=alpha, edgecolor=edge_color, linewidth=edge_width)
            
            # Draw supply center marker
            center = cell.get('center', [0, 0])
            if is_sc:
                # Special marker for contested SCs (Belgium factor)
                if cell_id in contested_sc_ids:
                    ax.plot(center[0], center[1], '*', 
                           markersize=14, color='red', 
                           markeredgecolor='darkred', markeredgewidth=2,
                           zorder=10)
                else:
                    ax.plot(center[0], center[1], 'o', 
                           markersize=10, color='gold', 
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
            
            # Add markers for highly connected and dead-end nodes
            if cell_id in highly_connected:
                ax.plot(center[0], center[1], 'X', 
                       markersize=10, color='red', 
                       markeredgecolor='darkred', markeredgewidth=1.5,
                       zorder=5)
            elif cell_id in dead_ends:
                ax.plot(center[0], center[1], 'D', 
                       markersize=8, color='orange', 
                       markeredgecolor='darkorange', markeredgewidth=1.5,
                       zorder=5)
        
        # Create legend with powers and analysis indicators
        legend_elements = []
        
        # Add power colors with classifications
        if power_list:
            for power_idx, power_id in enumerate(power_list):
                color = power_colors[power_idx % len(power_colors)]
                # Add classification if available
                classification = power_classifications.get(power_id, {}).get('classification', '')
                label = f"{power_id}"
                if classification:
                    label += f" ({classification[0].upper()})"  # C/M/C for corner/moderate/central
                legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, label=label))
        
        # Add separator
        if legend_elements:
            legend_elements.append(plt.Line2D([0], [0], color='none', label=''))
        
        # Add analysis indicators
        if highly_connected:
            legend_elements.append(plt.Line2D([0], [0], marker='X', color='w', 
                                             markerfacecolor='red', markeredgecolor='darkred',
                                             markersize=10, label=f'High Connectivity (n={len(highly_connected)})'))
        if dead_ends:
            legend_elements.append(plt.Line2D([0], [0], marker='D', color='w',
                                             markerfacecolor='orange', markeredgecolor='darkorange',
                                             markersize=8, label=f'Dead Ends (n={len(dead_ends)})'))
        if contested_sc_ids:
            legend_elements.append(plt.Line2D([0], [0], marker='*', color='w',
                                             markerfacecolor='red', markeredgecolor='darkred',
                                             markersize=14, label=f'Contested SC (n={len(contested_sc_ids)})'))
        
        # Add legend
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper left', 
                     bbox_to_anchor=(0, 1), fontsize=8, framealpha=0.9)
        
        # Add statistics text box
        if analysis:
            avg_degree = degree_analysis.get('average_degree', 0)
            triangle_density = triangle_analysis.get('triangle_density', 0)
            
            stats_text = f"Avg Degree: {avg_degree:.1f}\n"
            stats_text += f"Triangle Density: {triangle_density:.1%}\n"
            stats_text += f"Seas Connected: {'Yes' if sea_connectivity.get('connected', False) else 'No'}"
            
            # Add text box with statistics
            ax.text(0.98, 0.02, stats_text,
                   transform=ax.transAxes,
                   fontsize=9,
                   verticalalignment='bottom',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    else:
        # Phase 4, 5, 7: Kingdoms and supply centers
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
            
            # Draw cell polygon (without edge if we'll draw fractal edges separately)
            alpha = 0.9 if owner or is_sc else 0.6
            has_fractal_edges = (map_data.topology and 
                                any(e.get('visual_path') for e in map_data.topology.get('edges', {}).values()))
            edge_color = 'none' if has_fractal_edges else 'black'
            ax.fill(vertices[:, 0], vertices[:, 1], 
                   color=color, alpha=alpha, edgecolor=edge_color, linewidth=0.8)
            
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
        
        # Draw fractal edges if topology with visual_path is available
        if map_data.topology:
            draw_fractal_edges(ax, map_data)
        
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
