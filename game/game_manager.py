"""
GameManager - Main interface for managing Diplomacy games.

The GameManager provides:
- Game initialization from map JSON
- Initial unit placement
- Game state export (JSON and JPEG)
- Query interface for game state
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .game_state import GameState, Season, Phase
from .units import Unit, UnitType


class GameManager:
    """
    High-level manager for Diplomacy games.
    
    Provides the main API for:
    - Initializing games from map files
    - Querying game state
    - Exporting game state as JSON and JPEG
    """
    
    def __init__(self, map_path: Optional[str] = None, map_data: Optional[dict] = None):
        """
        Initialize a GameManager.
        
        Args:
            map_path: Path to map JSON file (optional if map_data provided)
            map_data: Pre-loaded map data dictionary (optional if map_path provided)
        """
        if map_path:
            self.map_path = Path(map_path)
            with open(map_path, 'r') as f:
                self.map_data = json.load(f)
        elif map_data:
            self.map_path = None
            self.map_data = map_data
        else:
            raise ValueError("Either map_path or map_data must be provided")
        
        self.state: Optional[GameState] = None
        self.history: List[dict] = []
    
    def initialize_game(self) -> GameState:
        """
        Initialize a new game ready for the first turn.
        
        This sets up:
        - Initial turn state (Spring 1901, Order phase)
        - Supply center ownership based on map powers
        - Initial unit placement (one unit per home supply center)
        
        Returns:
            The initialized GameState
        """
        # Extract powers from map
        powers = set(self.map_data.get('powers', {}).keys())
        
        # Initialize game state
        self.state = GameState(
            turn=1,
            year=1901,
            season=Season.SPRING,
            phase=Phase.ORDER,
            powers=powers,
            map_data=self.map_data
        )
        
        # Set up ownership and supply center control
        self._initialize_ownership()
        
        # Place initial units
        self._place_initial_units()
        
        # Record initial state in history
        self.history = [self.state.to_dict()]
        
        return self.state
    
    def _initialize_ownership(self) -> None:
        """Initialize province ownership and supply center control."""
        # Get topology faces for province info
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        # Set ownership based on map data
        for face_id, face_data in faces.items():
            owner = face_data.get('owner')
            if owner:
                self.state.ownership[face_id] = owner
                
                # If this is a supply center, also set SC control
                if face_data.get('is_supply_center', False):
                    self.state.sc_control[face_id] = owner
        
        # Also handle supply centers from the supply_centers key
        supply_centers = self.map_data.get('supply_centers', {})
        for sc in supply_centers.get('home', []):
            cell_id = sc.get('cell_id')
            # Supply center data uses 'owner' key
            owner = sc.get('owner')
            if cell_id and owner:
                self.state.sc_control[cell_id] = owner
    
    def _place_initial_units(self) -> None:
        """Place initial units at home supply centers."""
        supply_centers = self.map_data.get('supply_centers', {})
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        # Place one unit at each home supply center
        for sc in supply_centers.get('home', []):
            cell_id = sc.get('cell_id')
            # Supply center data uses 'owner' key for the controlling power
            power = sc.get('owner')
            
            if not cell_id or not power:
                continue
            
            # Determine unit type based on province type
            face_data = faces.get(cell_id, {})
            province_type = face_data.get('type', 'land')
            is_coastal = face_data.get('coastal', False)
            
            # Default to army, but place fleet if coastal and not already occupied
            # In standard Diplomacy, coastal provinces can have either armies or fleets
            # For initial placement, we'll use a simple heuristic:
            # - If it's a sea province, place a fleet
            # - If it's coastal, alternate between army and fleet based on power needs
            # - If it's inland, place an army
            
            if province_type == 'sea':
                unit_type = UnitType.FLEET
            elif is_coastal:
                # For initial placement, we need to decide between army and fleet
                # Use heuristic: check if power already has enough fleets
                power_units = self.state.get_units_for_power(power)
                fleet_count = sum(1 for u in power_units if u.unit_type == UnitType.FLEET)
                army_count = sum(1 for u in power_units if u.unit_type == UnitType.ARMY)
                
                # Try to have at least 1 fleet per power on coastal SCs
                if fleet_count == 0:
                    unit_type = UnitType.FLEET
                else:
                    unit_type = UnitType.ARMY
            else:
                unit_type = UnitType.ARMY
            
            # Create and place the unit
            unit = Unit(
                unit_type=unit_type,
                power=power,
                location=cell_id
            )
            self.state.units[cell_id] = unit
    
    def get_game_state(self) -> dict:
        """
        Get the current game state as a JSON-serializable dictionary.
        
        Returns:
            Dictionary containing complete game state
        """
        if not self.state:
            raise RuntimeError("Game not initialized. Call initialize_game() first.")
        
        return {
            "game_state": self.state.to_dict(),
            "map_info": {
                "total_provinces": len(self.map_data.get('topology', {}).get('faces', {})),
                "powers": list(self.state.powers),
                "total_supply_centers": len(self.state.sc_control)
            }
        }
    
    def export_game_state_json(self, output_path: str) -> str:
        """
        Export the current game state to a JSON file.
        
        Args:
            output_path: Path to save the JSON file
            
        Returns:
            The path where the file was saved
        """
        if not self.state:
            raise RuntimeError("Game not initialized. Call initialize_game() first.")
        
        game_data = {
            "game_state": self.state.to_dict(),
            "map_data": self.map_data,
            "history": self.history
        }
        
        with open(output_path, 'w') as f:
            json.dump(game_data, f, indent=2)
        
        return output_path
    
    def export_board_image(self, output_path: str, dpi: int = 150) -> str:
        """
        Export the current board state as a JPEG image.
        
        The image shows:
        - Province territories colored by owner
        - Supply center markers
        - Unit positions (armies and fleets)
        - Turn information
        
        Args:
            output_path: Path to save the image (will be saved as JPEG)
            dpi: Resolution of the output image
            
        Returns:
            The path where the image was saved
        """
        if not self.state:
            raise RuntimeError("Game not initialized. Call initialize_game() first.")
        
        # Import visualization dependencies
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import numpy as np
        
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 12))
        
        # Color schemes
        terrain_colors = {
            "land": "#C5E0B4",
            "sea": "#BDD7EE",
            "impassable": "#A6A6A6"
        }
        power_colors_list = list(mcolors.TABLEAU_COLORS.values())
        
        # Build power-to-color mapping
        power_list = sorted(self.state.powers)
        power_colors = {p: power_colors_list[i % len(power_colors_list)] 
                       for i, p in enumerate(power_list)}
        
        # Get topology data
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        borders = topology.get('borders', {})
        edges = topology.get('edges', {})
        vertices_list = topology.get('vertices', [])
        
        # Create vertex lookup
        vertex_coords = {v['id']: v['coords'] for v in vertices_list}
        
        # Draw provinces
        for face_id, face_data in faces.items():
            # Get province polygon
            polygon = self._get_face_polygon(face_id, faces, borders, edges, vertex_coords)
            if not polygon or len(polygon) < 3:
                continue
            
            poly_array = np.array(polygon)
            
            # Determine color
            face_type = face_data.get('type', 'land')
            owner = self.state.ownership.get(face_id)
            is_sc = face_data.get('is_supply_center', False)
            
            if owner and owner in power_colors:
                color = power_colors[owner]
                alpha = 0.8
            elif is_sc and face_type == 'land':
                color = '#FFE699'  # Neutral SC
                alpha = 0.8
            else:
                color = terrain_colors.get(face_type, 'gray')
                alpha = 0.6 if face_type == 'land' else 0.7
            
            # Draw polygon
            ax.fill(poly_array[:, 0], poly_array[:, 1], 
                   color=color, alpha=alpha, edgecolor='black', linewidth=0.5)
            
            # Draw supply center marker
            if is_sc:
                center = face_data.get('center', [0.5, 0.5])
                ax.plot(center[0], center[1], 'o', 
                       markersize=10, color='gold', 
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
        
        # Draw units
        for location, unit in self.state.units.items():
            face_data = faces.get(location, {})
            center = face_data.get('center', [0.5, 0.5])
            
            # Get unit color based on power
            unit_color = power_colors.get(unit.power, 'gray')
            
            # Draw unit symbol
            if unit.unit_type == UnitType.ARMY:
                # Army: filled circle
                ax.plot(center[0], center[1], 'o', 
                       markersize=14, color=unit_color,
                       markeredgecolor='black', markeredgewidth=2, zorder=15)
                ax.text(center[0], center[1], 'A', 
                       ha='center', va='center', fontsize=8, fontweight='bold',
                       color='white', zorder=16)
            else:
                # Fleet: filled triangle
                ax.plot(center[0], center[1], '^', 
                       markersize=14, color=unit_color,
                       markeredgecolor='black', markeredgewidth=2, zorder=15)
                ax.text(center[0], center[1] - 0.003, 'F', 
                       ha='center', va='center', fontsize=7, fontweight='bold',
                       color='white', zorder=16)
        
        # Add province names (for land and important sea provinces)
        for face_id, face_data in faces.items():
            face_type = face_data.get('type', 'land')
            name = face_data.get('name', '')
            is_sc = face_data.get('is_supply_center', False)
            
            if name and (face_type == 'land' or is_sc):
                center = face_data.get('center', [0.5, 0.5])
                # Offset if there's a unit there
                if face_id in self.state.units:
                    offset_y = 0.025
                else:
                    offset_y = 0
                ax.text(center[0], center[1] + offset_y, name, 
                       ha='center', va='bottom' if offset_y else 'center',
                       fontsize=6, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                               alpha=0.7, edgecolor='none'), zorder=5)
        
        # Add legend for powers
        legend_elements = []
        for power in power_list:
            color = power_colors[power]
            unit_count = self.state.get_unit_count(power)
            sc_count = self.state.get_sc_count(power)
            legend_elements.append(
                plt.Rectangle((0, 0), 1, 1, fc=color, 
                             label=f"{power}: {unit_count}u/{sc_count}sc")
            )
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper left', 
                     bbox_to_anchor=(0, 1), fontsize=9, framealpha=0.9)
        
        # Add turn information
        turn_str = self.state.get_turn_string()
        phase_str = self.state.phase.value.capitalize()
        ax.set_title(f"Diplomacy - {turn_str} ({phase_str} Phase)\n"
                    f"{len(self.state.units)} units, {len(self.state.sc_control)} supply centers",
                    fontsize=14, fontweight='bold', pad=20)
        
        # Finalize
        ax.set_aspect('equal')
        ax.axis('off')
        plt.tight_layout()
        
        # Save as JPEG
        # Ensure output path has .jpeg or .jpg extension
        output_path = str(output_path)
        if not output_path.lower().endswith(('.jpeg', '.jpg')):
            output_path = output_path.rsplit('.', 1)[0] + '.jpeg'
        
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                   format='jpeg', pil_kwargs={'quality': 95})
        plt.close(fig)
        
        return output_path
    
    def _get_face_polygon(self, face_id: str, faces: dict, borders: dict, 
                          edges: dict, vertex_coords: dict) -> List[List[float]]:
        """
        Reconstruct a face polygon from topology data.
        
        Args:
            face_id: ID of the face
            faces: Dictionary of face data
            borders: Dictionary of border data
            edges: Dictionary of edge data
            vertex_coords: Dictionary mapping vertex ID to coordinates
            
        Returns:
            List of [x, y] coordinates forming the polygon
        """
        face_data = faces.get(face_id, {})
        
        # Try to get fractal polygon using visual_path if available
        face_edges = []
        for border_id in face_data.get('borders', []):
            if border_id in borders:
                border = borders[border_id]
                face_edges.extend(border.get('edges', []))
        
        if not face_edges:
            return []
        
        # Build graph of vertex connections
        vertex_graph = {}
        for edge_id in face_edges:
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
        
        # Trace boundary
        start_vertex = next(iter(vertex_graph.keys()))
        polygon = []
        current = start_vertex
        visited = set()
        
        for _ in range(len(vertex_graph) + 1):
            if current in visited:
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
            
            if next_vertex is None:
                break
            current = next_vertex
        
        return polygon
    
    def get_province_info(self, province_id: str) -> Optional[dict]:
        """
        Get information about a specific province.
        
        Args:
            province_id: ID of the province
            
        Returns:
            Dictionary with province information, or None if not found
        """
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        face_data = faces.get(province_id)
        if not face_data:
            return None
        
        return {
            "id": province_id,
            "name": face_data.get('name', province_id),
            "type": face_data.get('type', 'land'),
            "coastal": face_data.get('coastal', False),
            "is_supply_center": face_data.get('is_supply_center', False),
            "owner": self.state.ownership.get(province_id) if self.state else None,
            "unit": self.state.units.get(province_id).to_dict() if self.state and province_id in self.state.units else None
        }
    
    def get_all_units(self) -> List[dict]:
        """Get a list of all units on the board."""
        if not self.state:
            return []
        return [
            {**unit.to_dict(), "location": loc}
            for loc, unit in self.state.units.items()
        ]
    
    def get_supply_center_status(self) -> dict:
        """Get the current supply center control status."""
        if not self.state:
            return {}
        
        result = {
            "controlled": {},
            "neutral": []
        }
        
        # Get all supply centers from map
        supply_centers = self.map_data.get('supply_centers', {})
        all_scs = set()
        
        for sc in supply_centers.get('home', []):
            all_scs.add(sc.get('cell_id'))
        for sc in supply_centers.get('neutral', []):
            all_scs.add(sc.get('cell_id'))
        
        # Categorize by current control
        for power in self.state.powers:
            result["controlled"][power] = []
        
        for sc_id in all_scs:
            controller = self.state.sc_control.get(sc_id)
            if controller:
                if controller in result["controlled"]:
                    result["controlled"][controller].append(sc_id)
            else:
                result["neutral"].append(sc_id)
        
        return result
