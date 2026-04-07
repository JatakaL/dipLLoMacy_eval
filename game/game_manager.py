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


# Power name mappings - gives meaningful names to generated powers
POWER_NAMES = [
    "Avalon",
    "Borealis", 
    "Crimson",
    "Dawnland",
    "Eastmark",
    "Frostheim",
    "Greenwood",
    "Highvale",
    "Ironhold",
    "Jadekeep",
]


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
        
        # Build power-to-color mapping with display names
        power_list = sorted(self.state.powers)
        power_colors = {p: power_colors_list[i % len(power_colors_list)] 
                       for i, p in enumerate(power_list)}
        
        # Create display names for powers
        power_display_names = {}
        for i, power in enumerate(power_list):
            if i < len(POWER_NAMES):
                power_display_names[power] = POWER_NAMES[i]
            else:
                power_display_names[power] = power
        
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
        
        # Draw supply center markers using pre-determined positions
        for face_id, face_data in faces.items():
            is_sc = face_data.get('is_supply_center', False)
            if is_sc:
                # Use pre-determined SC position if available, otherwise fall back to center
                label_positions = face_data.get('label_positions', {})
                sc_pos = label_positions.get('sc_position', face_data.get('center', [0.5, 0.5]))
                ax.plot(sc_pos[0], sc_pos[1], 'o', 
                       markersize=8, color='gold', 
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
        
        # Draw units using pre-determined positions
        for location, unit in self.state.units.items():
            face_data = faces.get(location, {})
            
            # Use pre-determined unit position if available
            label_positions = face_data.get('label_positions', {})
            unit_pos = label_positions.get('unit_position')
            
            if not unit_pos:
                # Fall back to legacy offset-based positioning
                center = face_data.get('center', [0.5, 0.5])
                is_sc = face_data.get('is_supply_center', False)
                unit_offset_x = 0.008 if is_sc else 0
                unit_offset_y = -0.008 if is_sc else 0
                unit_pos = [center[0] + unit_offset_x, center[1] + unit_offset_y]
            
            unit_x, unit_y = unit_pos[0], unit_pos[1]
            
            # Get unit color based on power
            unit_color = power_colors.get(unit.power, 'gray')
            
            # Draw unit symbol
            if unit.unit_type == UnitType.ARMY:
                # Army: filled circle
                ax.plot(unit_x, unit_y, 'o', 
                       markersize=12, color=unit_color,
                       markeredgecolor='black', markeredgewidth=2, zorder=15)
                ax.text(unit_x, unit_y, 'A', 
                       ha='center', va='center', fontsize=7, fontweight='bold',
                       color='white', zorder=16)
            else:
                # Fleet: filled triangle
                ax.plot(unit_x, unit_y, '^', 
                       markersize=12, color=unit_color,
                       markeredgecolor='black', markeredgewidth=2, zorder=15)
                ax.text(unit_x, unit_y - 0.002, 'F', 
                       ha='center', va='center', fontsize=6, fontweight='bold',
                       color='white', zorder=16)
        
        # Add province names using pre-determined positions
        for face_id, face_data in faces.items():
            face_type = face_data.get('type', 'land')
            name = face_data.get('name', '')
            
            if not name:
                continue
            
            # Use pre-determined name position if available
            label_positions = face_data.get('label_positions', {})
            name_pos = label_positions.get('name_position')
            
            if name_pos:
                # Use pre-determined position
                text_x, text_y = name_pos[0], name_pos[1]
                va = 'center'
            else:
                # Fall back to legacy offset-based positioning
                center = face_data.get('center', [0.5, 0.5])
                is_sc = face_data.get('is_supply_center', False)
                has_unit = face_id in self.state.units
                
                if has_unit and is_sc:
                    offset_y = 0.035
                    va = 'bottom'
                elif has_unit:
                    offset_y = 0.025
                    va = 'bottom'
                elif is_sc:
                    offset_y = 0.02
                    va = 'bottom'
                else:
                    offset_y = 0
                    va = 'center'
                
                text_x = center[0]
                text_y = center[1] + offset_y
            
            # Style based on province type
            if face_type == 'sea':
                # Sea territory names: smaller, italic, no background
                ax.text(text_x, text_y, name, 
                       ha='center', va=va,
                       fontsize=5, fontstyle='italic', color='#2B5797',
                       zorder=4)
            else:
                # Land territory names: with background box
                ax.text(text_x, text_y, name, 
                       ha='center', va=va,
                       fontsize=5, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.15', facecolor='white', 
                               alpha=0.7, edgecolor='none'), zorder=5)
        
        # Add legend for powers with display names
        legend_elements = []
        for power in power_list:
            color = power_colors[power]
            display_name = power_display_names[power]
            unit_count = self.state.get_unit_count(power)
            sc_count = self.state.get_sc_count(power)
            legend_elements.append(
                plt.Rectangle((0, 0), 1, 1, fc=color, 
                             label=f"{display_name}: {unit_count}u/{sc_count}sc")
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
    
    def get_adjacency(self) -> Dict[str, List[str]]:
        """
        Get the adjacency mapping for the map.
        
        Returns:
            Dictionary mapping territory ID to list of adjacent territory IDs
        """
        from .validators import build_adjacency_from_map
        return build_adjacency_from_map(self.map_data)
    
    def get_territory_name(self, territory_id: str) -> str:
        """Get the name of a territory by its ID."""
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        face_data = faces.get(territory_id, {})
        return face_data.get('name', territory_id)
    
    def write_order_files(self, output_dir: str) -> Dict[str, str]:
        """
        Write initial order files for each power with all units holding.
        
        Args:
            output_dir: Directory to write order files
            
        Returns:
            Dictionary mapping power name to order file path
        """
        if not self.state:
            raise RuntimeError("Game not initialized. Call initialize_game() first.")
        
        os.makedirs(output_dir, exist_ok=True)
        
        order_files = {}
        
        for power in sorted(self.state.powers):
            units = self.state.get_units_for_power(power)
            
            # Create order file
            filename = f"{power}_orders.txt"
            filepath = os.path.join(output_dir, filename)
            
            lines = []
            lines.append(f"# Orders for {power}")
            lines.append(f"# {self.state.get_turn_string()} - {self.state.phase.value.capitalize()} Phase")
            lines.append(f"# Format: A/F {{Territory Name}} H/M/S/C ...")
            lines.append(f"#")
            lines.append(f"# Order types:")
            lines.append(f"#   H - Hold")
            lines.append(f"#   M {{Target}} - Move to target")
            lines.append(f"#   S A/F {{Unit}} H - Support hold")
            lines.append(f"#   S A/F {{Unit}} M {{Target}} - Support move")
            lines.append(f"#   C A {{Army}} M {{Target}} - Convoy army")
            lines.append(f"#")
            lines.append("")
            
            for unit in units:
                unit_type = 'A' if unit.unit_type == UnitType.ARMY else 'F'
                territory_name = self.get_territory_name(unit.location)
                # Default to hold
                lines.append(f"{unit_type} {{{territory_name}}} H")
            
            with open(filepath, 'w') as f:
                f.write("\n".join(lines))
            
            order_files[power] = filepath
        
        return order_files
    
    def read_order_files(self, order_files: Dict[str, str]) -> Dict[str, List]:
        """
        Read and parse order files for each power.
        
        Args:
            order_files: Dictionary mapping power name to order file path
            
        Returns:
            Dictionary mapping power name to list of Order objects
        """
        from .orders import OrderParser
        
        all_orders = {}
        
        for power, filepath in order_files.items():
            orders = OrderParser.parse_file(filepath)
            # Set power for each order
            for order in orders:
                order.power = power
            all_orders[power] = orders
        
        return all_orders
    
    def process_turn(self, orders: Dict[str, List]) -> Tuple[List, Dict[str, str], str]:
        """
        Process a turn with the given orders.
        
        Args:
            orders: Dictionary mapping power name to list of Order objects
            
        Returns:
            Tuple of (all orders with results, dislodged units, resolution log)
        """
        if not self.state:
            raise RuntimeError("Game not initialized. Call initialize_game() first.")
        
        from .validators import OrderValidator
        from .resolver import OrderResolver
        
        adjacency = self.get_adjacency()
        
        # Flatten orders
        all_orders = []
        for power, power_orders in orders.items():
            all_orders.extend(power_orders)
        
        # Validate orders
        validator = OrderValidator(self.state, adjacency)
        validated_orders = validator.validate_all_orders(all_orders)
        
        # Resolve orders
        resolver = OrderResolver(self.state, adjacency)
        resolved_orders, dislodged = resolver.resolve(validated_orders)
        
        # Generate log
        log = resolver.get_resolution_log(resolved_orders)
        
        # Apply successful moves
        resolver.apply_moves()
        
        # Record in history
        self.history.append({
            "turn": self.state.get_turn_string(),
            "phase": self.state.phase.value,
            "orders": [o.to_dict() for o in resolved_orders]
        })
        
        return resolved_orders, dislodged, log
    
    def get_retreat_options(self, dislodged_location: str) -> List[str]:
        """
        Get valid retreat options for a dislodged unit.
        
        Args:
            dislodged_location: Original location of the dislodged unit
            
        Returns:
            List of valid retreat destinations
        """
        if not self.state:
            return []
        
        adjacency = self.get_adjacency()
        
        # Look for the unit in dislodged_units dictionary
        unit = self.state.dislodged_units.get(dislodged_location)
        
        if not unit:
            return []
        
        # Get the territory the attack came from (cannot retreat there)
        attack_from = self.state.dislodged_from.get(dislodged_location)
        
        valid_retreats = []
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        for adj in adjacency.get(dislodged_location, []):
            # Cannot retreat to the territory the attack came from
            if adj == attack_from:
                continue
            
            # Check if territory is unoccupied (by non-dislodged units)
            if self.state.get_unit_at(adj):
                continue
            
            # Also check if another dislodged unit is retreating there
            if adj in self.state.dislodged_units:
                continue
            
            # Check terrain compatibility
            face_data = faces.get(adj, {})
            face_type = face_data.get('type', 'land')
            is_coastal = face_data.get('coastal', False)
            
            if unit.unit_type == UnitType.ARMY:
                if face_type == 'sea':
                    continue
            else:  # Fleet
                if face_type == 'land' and not is_coastal:
                    continue
            
            valid_retreats.append(adj)
        
        return valid_retreats
    
    def process_retreat(self, location: str, destination: str) -> bool:
        """
        Process a retreat order for a dislodged unit.
        
        Args:
            location: Original location of dislodged unit
            destination: Retreat destination
            
        Returns:
            True if retreat succeeded, False otherwise
        """
        if not self.state:
            return False
        
        # Get unit from dislodged_units
        unit = self.state.dislodged_units.get(location)
        if not unit:
            return False
        
        valid_retreats = self.get_retreat_options(location)
        if destination not in valid_retreats:
            return False
        
        # Move unit from dislodged_units to units
        del self.state.dislodged_units[location]
        if location in self.state.dislodged_from:
            del self.state.dislodged_from[location]
        unit.location = destination
        unit.dislodged = False
        self.state.units[destination] = unit
        
        return True
    
    def disband_unit(self, location: str) -> bool:
        """
        Disband a unit (for retreats or winter adjustments).
        
        Args:
            location: Location of unit to disband
            
        Returns:
            True if unit was disbanded, False otherwise
        """
        if not self.state:
            return False
        
        # Check dislodged_units first
        if location in self.state.dislodged_units:
            del self.state.dislodged_units[location]
            if location in self.state.dislodged_from:
                del self.state.dislodged_from[location]
            return True
        
        # Then check regular units
        if location in self.state.units:
            del self.state.units[location]
            return True
        
        return False
    
    def advance_to_next_phase(self) -> None:
        """Advance the game to the next phase."""
        if not self.state:
            return
        
        self.state.advance_phase()
        
        # If we're in fall retreat phase that's complete, update SC control
        if self.state.season == Season.WINTER and self.state.phase == Phase.BUILD:
            self._update_sc_control()
    
    def _update_sc_control(self) -> None:
        """Update supply center control based on unit positions (fall only)."""
        if not self.state:
            return
        
        topology = self.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        # Check each unit's position
        for location, unit in self.state.units.items():
            face_data = faces.get(location, {})
            if face_data.get('is_supply_center', False):
                # Unit occupies an SC - transfer control
                self.state.sc_control[location] = unit.power
    
    def has_retreats_pending(self) -> bool:
        """Check if there are any units needing to retreat."""
        if not self.state:
            return False
        
        return len(self.state.dislodged_units) > 0
    
    def get_dislodged_units(self) -> List[Tuple[str, Unit]]:
        """Get list of dislodged units and their original locations."""
        if not self.state:
            return []
        
        return [(loc, unit) for loc, unit in self.state.dislodged_units.items()]
