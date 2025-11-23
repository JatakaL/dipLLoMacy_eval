#!/usr/bin/env python3
"""
Interactive Map Viewer for Diplomacy Map Generator

This application allows loading and viewing JSON outputs from any phase of map generation.
It supports:
- Loading multiple JSON files as tabs
- Auto-detecting phase from metadata
- Visualizing mesh, terrain, provinces, kingdoms, supply centers
- Interactive pan/zoom
- Phase-appropriate coloring and labels
"""

import json
import sys
import os
from pathlib import Path
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for better GUI support
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.colors as mcolors
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
        
        # For phase 7 (or any phase without cells), reconstruct cell-like data from topology
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
        
        # Check if topology has faces with names (phase 7 without cells)
        if self.topology and 'faces' in self.topology:
            sample_face = next(iter(self.topology['faces'].values()), {})
            if 'name' in sample_face:
                return 7
        
        return 7  # Default to final phase if unsure
    
    def _reconstruct_cells_from_topology(self):
        """Reconstruct cell-like data from topology for visualization.
        
        This is used for phase 7 which doesn't have a cells dictionary.
        """
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
            }
            
            self.cells[face_id] = cell
    
    def _reconstruct_polygon_from_edges(self, edge_ids, edges, vertex_coords):
        """Reconstruct an ordered polygon from a list of edge IDs.
        
        Args:
            edge_ids: List of edge IDs that form the face boundary
            edges: Dictionary of all edges
            vertex_coords: Dictionary mapping vertex ID to coordinates
            
        Returns:
            List of [x, y] coordinates forming the polygon
        """
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


class MapVisualizer:
    """Visualizes map data on a matplotlib figure."""
    
    def __init__(self, figure, map_data):
        """Initialize with a figure and map data."""
        self.figure = figure
        self.map_data = map_data
        self.ax = None
        
        # Color schemes
        self.terrain_colors = {
            "land": "#C5E0B4",
            "sea": "#BDD7EE",
            "impassable": "#A6A6A6"
        }
        self.power_colors = list(mcolors.TABLEAU_COLORS.values())
    
    def visualize(self):
        """Visualize the map based on its phase."""
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        
        phase = self.map_data.phase
        
        if phase == 1:
            self._visualize_mesh()
        elif phase == 2:
            self._visualize_terrain()
        elif phase == 3:
            self._visualize_provinces()
        elif phase == 6:
            self._visualize_optimization()
        elif phase >= 4:
            self._visualize_kingdoms()
        
        # Common finishing touches
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        title = f"{self.map_data.filename}\n{self.map_data.get_phase_name()}"
        self.ax.set_title(title, fontsize=12, weight='bold')
        
        self.figure.tight_layout()
    
    def _visualize_mesh(self):
        """Visualize Phase 1: Basic mesh structure."""
        # If topology is available, visualize edges
        if self.map_data.topology:
            self._visualize_with_topology(show_labels=True)
        else:
            # Legacy visualization
            for cell_id, cell in self.map_data.cells.items():
                vertices = np.array(cell.get('vertices', []))
                if len(vertices) < 3:
                    continue
                
                # Draw cell polygon
                self.ax.fill(vertices[:, 0], vertices[:, 1], 
                            color='lightgray', alpha=0.5, edgecolor='black', linewidth=1)
                
                # Draw center point
                center = cell.get('center', [0, 0])
                self.ax.plot(center[0], center[1], 'o', color='red', markersize=3)
                
                # Label with cell ID
                self.ax.text(center[0], center[1], cell_id, 
                            ha='center', va='center', fontsize=6)
    
    def _visualize_terrain(self):
        """Visualize Phase 2: Terrain (land vs sea)."""
        # If topology is available, use topology-based rendering
        if self.map_data.topology:
            self._visualize_with_topology(show_labels=(self.map_data.config.get('num_cells', 100) < 50))
        else:
            # Legacy visualization
            for cell_id, cell in self.map_data.cells.items():
                vertices = np.array(cell.get('vertices', []))
                if len(vertices) < 3:
                    continue
                
                cell_type = cell.get('type', 'land')
                color = self.terrain_colors.get(cell_type, 'gray')
                
                # Draw cell polygon
                self.ax.fill(vertices[:, 0], vertices[:, 1], 
                            color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
                
                # Optional: Label with cell ID
                if self.map_data.config.get('num_cells', 100) < 50:  # Only for small maps
                    center = cell.get('center', [0, 0])
                    self.ax.text(center[0], center[1], cell_id, 
                                ha='center', va='center', fontsize=6, alpha=0.7)
    
    def _visualize_provinces(self):
        """Visualize Phase 3: Provinces (coastlines, oceans)."""
        for cell_id, cell in self.map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            color = self.terrain_colors.get(cell_type, 'gray')
            
            # Highlight coastal cells
            if cell.get('coastal', False):
                color = '#FFE699'  # Yellow for coastal
            
            # Highlight impassable zones
            if cell.get('impassable', False):
                color = self.terrain_colors['impassable']
            
            # Draw cell polygon
            self.ax.fill(vertices[:, 0], vertices[:, 1], 
                        color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
            
            # Label provinces
            center = cell.get('center', [0, 0])
            label_text = cell_id
            if cell.get('coastal'):
                label_text += '\n(C)'
            if cell.get('impassable'):
                label_text += '\n(IMP)'
                
            if self.map_data.config.get('num_cells', 100) < 60:
                self.ax.text(center[0], center[1], label_text, 
                            ha='center', va='center', fontsize=5, alpha=0.7)
    
    def _visualize_kingdoms(self):
        """Visualize Phase 4+: Kingdoms, supply centers, final map."""
        # Get list of powers - either from powers dict or by extracting from cell owners
        if self.map_data.powers:
            power_list = sorted(self.map_data.powers.keys())
        else:
            # Extract unique power names from cells
            power_set = set()
            for cell in self.map_data.cells.values():
                owner = cell.get('owner')
                if owner:
                    power_set.add(owner)
            power_list = sorted(power_set)
        
        # Draw cells with power colors
        for cell_id, cell in self.map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            owner = cell.get('owner')
            is_sc = cell.get('is_supply_center', False)
            
            # Default color
            color = self.terrain_colors.get(cell_type, 'gray')
            
            # Color by owner
            if owner and power_list:
                if owner in power_list:
                    power_idx = power_list.index(owner)
                    color = self.power_colors[power_idx % len(self.power_colors)]
            elif is_sc and not owner:
                # Neutral supply center
                color = '#FFE699' if cell_type == 'land' else '#9BC2E6'
            
            # Draw cell polygon
            alpha = 0.9 if owner or is_sc else 0.6
            self.ax.fill(vertices[:, 0], vertices[:, 1], 
                        color=color, alpha=alpha, edgecolor='black', linewidth=0.8)
            
            # Draw supply center marker
            if is_sc:
                center = cell.get('center', [0, 0])
                self.ax.plot(center[0], center[1], 'o', 
                           markersize=8, color='gold', 
                           markeredgecolor='black', markeredgewidth=1.5)
            
            # Label with name if available
            center = cell.get('center', [0, 0])
            name = cell.get('name', '')
            if name and self.map_data.phase >= 7:
                # Only show names for land provinces or major seas
                if cell_type == 'land' or (cell_type == 'sea' and is_sc):
                    self.ax.text(center[0], center[1], name, 
                               ha='center', va='center', fontsize=6, weight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       alpha=0.7, edgecolor='none'))
            elif self.map_data.config.get('num_cells', 100) < 50:
                # Show cell IDs for small maps
                label = cell_id
                if owner:
                    label += f'\n{owner}'
                self.ax.text(center[0], center[1], label, 
                           ha='center', va='center', fontsize=5, alpha=0.8)
        
        # Add legend for powers
        if power_list:
            legend_elements = []
            for power_idx, power_id in enumerate(power_list):
                color = self.power_colors[power_idx % len(self.power_colors)]
                legend_elements.append(plt.Rectangle((0, 0), 1, 1, fc=color, label=power_id))
            
            if legend_elements:
                self.ax.legend(handles=legend_elements, loc='upper left', 
                             bbox_to_anchor=(0, 1), fontsize=8)
    
    def _visualize_with_topology(self, show_labels=False):
        """Visualize using topology data structure (Face-Edge-Vertex).
        
        Args:
            show_labels: Whether to show cell ID labels
        """
        topology = self.map_data.topology
        vertices_list = topology.get('vertices', [])
        edges = topology.get('edges', {})
        faces = topology.get('faces', {})
        cells = self.map_data.cells
        
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
        
        # First pass: Draw filled faces
        for face_id, face_data in faces.items():
            face_type = face_data.get('type', 'land')
            color = self.terrain_colors.get(face_type, 'gray')
            
            # Get polygon vertices from legacy cell data if available
            if face_id in cells and 'vertices' in cells[face_id]:
                polygon = np.array(cells[face_id]['vertices'])
                if len(polygon) >= 3:
                    self.ax.fill(polygon[:, 0], polygon[:, 1], color=color, alpha=0.7)
        
        # Second pass: Draw edges with type-based styling
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
            
            # Draw the edge
            self.ax.plot([v1_coords[0], v2_coords[0]], 
                        [v1_coords[1], v2_coords[1]], 
                        color=color, linewidth=linewidth, alpha=0.9, solid_capstyle='round')
        
        # Optional: Add labels
        if show_labels:
            for face_id, face_data in faces.items():
                center = face_data.get('center')
                if center:
                    self.ax.text(center[0], center[1], face_id, 
                                ha='center', va='center', fontsize=6, alpha=0.8)
        
        # Add simple legend for edge types
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
        self.ax.legend(handles=legend_elements, loc='upper right', fontsize=8, framealpha=0.9)
    
    def _visualize_optimization(self):
        """Visualize Phase 6: Graph Optimization with analysis data."""
        # Get analysis data
        analysis = self.map_data.analysis
        
        # Get list of powers
        if self.map_data.powers:
            power_list = sorted(self.map_data.powers.keys())
        else:
            power_set = set()
            for cell in self.map_data.cells.values():
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
        for cell_id, cell in self.map_data.cells.items():
            vertices = np.array(cell.get('vertices', []))
            if len(vertices) < 3:
                continue
            
            cell_type = cell.get('type', 'land')
            owner = cell.get('owner')
            is_sc = cell.get('is_supply_center', False)
            
            # Default color
            color = self.terrain_colors.get(cell_type, 'gray')
            
            # Color by owner
            if owner and power_list:
                if owner in power_list:
                    power_idx = power_list.index(owner)
                    color = self.power_colors[power_idx % len(self.power_colors)]
            elif is_sc and not owner:
                # Neutral supply center
                color = '#FFE699' if cell_type == 'land' else '#9BC2E6'
            
            # Special border for highly connected nodes
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
            self.ax.fill(vertices[:, 0], vertices[:, 1], 
                        color=color, alpha=alpha, edgecolor=edge_color, linewidth=edge_width)
            
            # Draw supply center marker
            center = cell.get('center', [0, 0])
            if is_sc:
                # Special marker for contested SCs (Belgium factor)
                if cell_id in contested_sc_ids:
                    self.ax.plot(center[0], center[1], '*', 
                               markersize=14, color='red', 
                               markeredgecolor='darkred', markeredgewidth=2,
                               zorder=10)
                else:
                    self.ax.plot(center[0], center[1], 'o', 
                               markersize=8, color='gold', 
                               markeredgecolor='black', markeredgewidth=1.5,
                               zorder=10)
            
            # Add markers for highly connected and dead-end nodes
            if cell_id in highly_connected:
                self.ax.plot(center[0], center[1], 'X', 
                           markersize=10, color='red', 
                           markeredgecolor='darkred', markeredgewidth=1.5,
                           zorder=5)
            elif cell_id in dead_ends:
                self.ax.plot(center[0], center[1], 'D', 
                           markersize=8, color='orange', 
                           markeredgecolor='darkorange', markeredgewidth=1.5,
                           zorder=5)
        
        # Create legend with powers and analysis indicators
        legend_elements = []
        
        # Add power colors
        if power_list:
            for power_idx, power_id in enumerate(power_list):
                color = self.power_colors[power_idx % len(self.power_colors)]
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
        
        # Add statistics text
        if analysis:
            avg_degree = degree_analysis.get('average_degree', 0)
            triangle_density = triangle_analysis.get('triangle_density', 0)
            
            stats_text = f"Avg Degree: {avg_degree:.1f}\n"
            stats_text += f"Triangle Density: {triangle_density:.1%}\n"
            stats_text += f"Seas Connected: {'Yes' if sea_connectivity.get('connected', False) else 'No'}"
            
            # Add text box with statistics
            self.ax.text(0.98, 0.02, stats_text,
                        transform=self.ax.transAxes,
                        fontsize=8,
                        verticalalignment='bottom',
                        horizontalalignment='right',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Add legend
        if legend_elements:
            self.ax.legend(handles=legend_elements, loc='upper left', 
                         bbox_to_anchor=(0, 1), fontsize=7, framealpha=0.9)


class MapViewerApp:
    """Main application window with tabbed interface."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Diplomacy Map Viewer")
        self.root.geometry("1200x800")
        
        # Store loaded maps
        self.maps = []  # List of MapData objects
        
        # Create UI
        self._create_menu()
        self._create_toolbar()
        self._create_notebook()
        self._create_status_bar()
        
        # Load any files passed as arguments
        if len(sys.argv) > 1:
            for filepath in sys.argv[1:]:
                self.load_file(filepath)
    
    def _create_menu(self):
        """Create the menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File(s)...", command=self.open_files, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Directory...", command=self.open_directory, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="Close Tab", command=self.close_current_tab, accelerator="Ctrl+W")
        file_menu.add_command(label="Close All", command=self.close_all_tabs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self.refresh_current_tab, accelerator="F5")
        view_menu.add_command(label="Zoom to Fit", command=self.zoom_fit_current)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.open_files())
        self.root.bind('<Control-d>', lambda e: self.open_directory())
        self.root.bind('<Control-w>', lambda e: self.close_current_tab())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F5>', lambda e: self.refresh_current_tab())
    
    def _create_toolbar(self):
        """Create the toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Open File(s)", command=self.open_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open Directory", command=self.open_directory).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(toolbar, text="Refresh", command=self.refresh_current_tab).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Close Tab", command=self.close_current_tab).pack(side=tk.LEFT, padx=2)
    
    def _create_notebook(self):
        """Create the notebook (tabbed interface)."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Show welcome message if no tabs
        self.welcome_frame = ttk.Frame(self.notebook)
        welcome_label = ttk.Label(self.welcome_frame, 
                                  text="Welcome to Diplomacy Map Viewer\n\n"
                                       "Use File > Open to load JSON map files\n"
                                       "or drag and drop files here",
                                  font=('Arial', 12), justify=tk.CENTER)
        welcome_label.pack(expand=True)
        self.notebook.add(self.welcome_frame, text="Welcome")
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def set_status(self, message):
        """Update status bar message."""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
    
    def open_files(self):
        """Open file dialog to select JSON files."""
        filetypes = [
            ('JSON files', '*.json'),
            ('All files', '*.*')
        ]
        filepaths = filedialog.askopenfilenames(
            title="Select Map JSON Files",
            filetypes=filetypes
        )
        
        if filepaths:
            for filepath in filepaths:
                self.load_file(filepath)
    
    def open_directory(self):
        """Open directory dialog to load all JSON files from a directory."""
        directory = filedialog.askdirectory(title="Select Directory with Map JSONs")
        
        if directory:
            json_files = list(Path(directory).glob('*.json'))
            if not json_files:
                messagebox.showwarning("No JSON Files", 
                                     f"No JSON files found in:\n{directory}")
                return
            
            # Sort by phase if possible
            def get_phase_order(filepath):
                name = filepath.name.lower()
                for i in range(1, 8):
                    if f'phase{i}' in name:
                        return i
                return 99
            
            json_files.sort(key=get_phase_order)
            
            for filepath in json_files:
                self.load_file(str(filepath))
    
    def load_file(self, filepath):
        """Load a JSON file and create a tab for it."""
        try:
            self.set_status(f"Loading {filepath}...")
            
            # Parse the map data
            map_data = MapData(filepath)
            self.maps.append(map_data)
            
            # Remove welcome tab if it's the only tab
            if len(self.maps) == 1 and self.notebook.index('end') == 1:
                self.notebook.forget(0)
            
            # Create a new tab
            tab_frame = ttk.Frame(self.notebook)
            self.notebook.add(tab_frame, text=f"{map_data.filename}")
            
            # Create matplotlib figure
            fig = plt.Figure(figsize=(10, 8), dpi=100)
            
            # Visualize the map
            visualizer = MapVisualizer(fig, map_data)
            visualizer.visualize()
            
            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=tab_frame)
            canvas.draw()
            
            # Add toolbar
            toolbar = NavigationToolbar2Tk(canvas, tab_frame)
            toolbar.update()
            
            # Pack canvas widget
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # Store references
            tab_frame.map_data = map_data
            tab_frame.figure = fig
            tab_frame.canvas = canvas
            
            # Switch to the new tab
            self.notebook.select(tab_frame)
            
            self.set_status(f"Loaded {filepath} - {map_data.get_phase_name()}")
            
        except Exception as e:
            messagebox.showerror("Error Loading File", 
                               f"Failed to load {filepath}:\n{str(e)}")
            self.set_status(f"Error loading {filepath}")
            import traceback
            traceback.print_exc()
    
    def close_current_tab(self):
        """Close the currently selected tab."""
        current_tab = self.notebook.select()
        if current_tab:
            tab_widget = self.notebook.nametowidget(current_tab)
            
            # Only close if it's not the welcome tab
            if hasattr(tab_widget, 'map_data'):
                # Find and remove the map data from our list
                map_data = tab_widget.map_data
                if map_data in self.maps:
                    self.maps.remove(map_data)
            
            # Remove the tab
            self.notebook.forget(current_tab)
            
            # Show welcome tab if no tabs left
            if self.notebook.index('end') == 0:
                self.notebook.add(self.welcome_frame, text="Welcome")
            
            self.set_status("Tab closed")
    
    def close_all_tabs(self):
        """Close all tabs."""
        while self.notebook.index('end') > 0:
            self.notebook.forget(0)
        
        self.maps.clear()
        self.notebook.add(self.welcome_frame, text="Welcome")
        self.set_status("All tabs closed")
    
    def refresh_current_tab(self):
        """Refresh the visualization in the current tab."""
        current_tab = self.notebook.select()
        if not current_tab or not hasattr(self.notebook.nametowidget(current_tab), 'map_data'):
            return
        
        tab_widget = self.notebook.nametowidget(current_tab)
        map_data = tab_widget.map_data
        figure = tab_widget.figure
        
        # Re-visualize
        visualizer = MapVisualizer(figure, map_data)
        visualizer.visualize()
        
        tab_widget.canvas.draw()
        self.set_status("Refreshed visualization")
    
    def zoom_fit_current(self):
        """Zoom to fit the entire map in the current tab."""
        current_tab = self.notebook.select()
        if not current_tab or not hasattr(self.notebook.nametowidget(current_tab), 'figure'):
            return
        
        tab_widget = self.notebook.nametowidget(current_tab)
        ax = tab_widget.figure.axes[0] if tab_widget.figure.axes else None
        if ax:
            ax.autoscale()
            tab_widget.canvas.draw()
        
        self.set_status("Zoomed to fit")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Diplomacy Map Viewer
Version 1.0

An interactive viewer for Diplomacy map generation JSON outputs.

Features:
• Load multiple JSON files as tabs
• Auto-detect map generation phase
• Visualize mesh, terrain, provinces, kingdoms, and more
• Interactive pan and zoom

Created for the dipLLoMacy_eval project."""
        
        messagebox.showinfo("About", about_text)


def main():
    """Main entry point."""
    root = tk.Tk()
    app = MapViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
