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
