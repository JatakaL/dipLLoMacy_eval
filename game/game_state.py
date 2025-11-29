"""
Game State Management for Diplomacy

This module manages the complete game state including:
- Map topology and adjacency
- Unit positions
- Supply center ownership
- Turn and phase tracking
- Victory conditions
"""

from typing import Dict, List, Optional, Set
from enum import Enum
import copy

from .units import Unit, Army, Fleet, UnitType, create_unit


class Phase(Enum):
    """Game phases in Diplomacy."""
    SPRING_MOVES = "spring_moves"
    SPRING_RETREATS = "spring_retreats"
    FALL_MOVES = "fall_moves"
    FALL_RETREATS = "fall_retreats"
    WINTER_BUILDS = "winter_builds"


class GameState:
    """
    Manages the complete state of a Diplomacy game.
    
    Attributes:
        map_data: The map configuration from the generator
        year: Current game year (starts at 1901)
        phase: Current phase of the turn
        units: Dictionary mapping location to Unit
        supply_centers: Dictionary mapping SC location to owning power
        power_names: List of all power names in the game
        eliminated_powers: Set of powers that have been eliminated
    """
    
    def __init__(self, map_data: dict):
        """
        Initialize game state from map data.
        
        Args:
            map_data: Map JSON from the generation pipeline
        """
        self.map_data = map_data
        self.year = 1901
        self.phase = Phase.SPRING_MOVES
        
        # Unit tracking
        self.units: Dict[str, Unit] = {}  # location -> unit
        
        # Build adjacency and topology lookups
        self._build_lookups()
        
        # Supply center ownership
        self.supply_centers: Dict[str, Optional[str]] = {}
        self._init_supply_centers()
        
        # Power tracking
        self.power_names = list(map_data.get("powers", {}).keys())
        self.eliminated_powers: Set[str] = set()
        
        # History for undo/replay
        self.history: List[dict] = []
    
    def _build_lookups(self):
        """Build efficient lookup structures from map data."""
        # Get topology or fall back to cells
        topology = self.map_data.get("topology", {})
        
        if topology:
            self.faces = topology.get("faces", {})
            self.adjacency = self.map_data.get("adjacency", {})
        else:
            # Legacy: use cells directly
            self.faces = self.map_data.get("cells", {})
            self.adjacency = {}
            for cell_id, cell in self.faces.items():
                self.adjacency[cell_id] = cell.get("neighbors", [])
        
        # Create reverse lookup: name -> cell_id
        self.name_to_id: Dict[str, str] = {}
        for face_id, face_data in self.faces.items():
            name = face_data.get("name", face_id)
            self.name_to_id[name] = face_id
    
    def _init_supply_centers(self):
        """Initialize supply center ownership from map data."""
        sc_data = self.map_data.get("supply_centers", {})
        
        # Home supply centers
        for sc in sc_data.get("home", []):
            location = sc.get("cell_id")
            power = sc.get("owner")
            if location:
                self.supply_centers[location] = power
        
        # Neutral supply centers
        for sc in sc_data.get("neutral", []):
            location = sc.get("cell_id")
            if location:
                self.supply_centers[location] = None  # Neutral
    
    def get_province_info(self, location: str) -> Optional[dict]:
        """
        Get information about a province.
        
        Args:
            location: Province ID or name
            
        Returns:
            Province data dictionary or None
        """
        # Try direct lookup first
        if location in self.faces:
            return self.faces[location]
        
        # Try name lookup
        if location in self.name_to_id:
            return self.faces.get(self.name_to_id[location])
        
        return None
    
    def get_province_type(self, location: str) -> Optional[str]:
        """Get the type of a province (land, sea, impassable)."""
        info = self.get_province_info(location)
        return info.get("type") if info else None
    
    def is_coastal(self, location: str) -> bool:
        """Check if a province is coastal."""
        info = self.get_province_info(location)
        return info.get("coastal", False) if info else False
    
    def is_supply_center(self, location: str) -> bool:
        """Check if a location is a supply center."""
        return location in self.supply_centers
    
    def get_adjacent(self, location: str) -> List[str]:
        """Get list of adjacent provinces."""
        # Direct lookup in adjacency
        if location in self.adjacency:
            return self.adjacency[location]
        
        # Try name-based lookup
        if location in self.name_to_id:
            cell_id = self.name_to_id[location]
            return self.adjacency.get(cell_id, [])
        
        return []
    
    def are_adjacent(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are adjacent."""
        adjacent = self.get_adjacent(loc1)
        return loc2 in adjacent
    
    # Unit Management
    
    def add_unit(self, unit: Unit) -> bool:
        """
        Add a unit to the game.
        
        Args:
            unit: The unit to add
            
        Returns:
            True if successful, False if location occupied
        """
        if unit.location in self.units:
            return False
        self.units[unit.location] = unit
        return True
    
    def remove_unit(self, location: str) -> Optional[Unit]:
        """
        Remove a unit from a location.
        
        Args:
            location: The location to remove unit from
            
        Returns:
            The removed unit or None
        """
        return self.units.pop(location, None)
    
    def move_unit(self, from_location: str, to_location: str) -> bool:
        """
        Move a unit from one location to another.
        
        Args:
            from_location: Current location
            to_location: Target location
            
        Returns:
            True if successful
        """
        if from_location not in self.units:
            return False
        if to_location in self.units:
            return False
        
        unit = self.units.pop(from_location)
        unit.location = to_location
        self.units[to_location] = unit
        return True
    
    def get_unit(self, location: str) -> Optional[Unit]:
        """Get unit at a location."""
        return self.units.get(location)
    
    def get_power_units(self, power: str) -> List[Unit]:
        """Get all units belonging to a power."""
        return [u for u in self.units.values() if u.power == power]
    
    def get_power_supply_centers(self, power: str) -> List[str]:
        """Get all supply centers owned by a power."""
        return [loc for loc, owner in self.supply_centers.items() if owner == power]
    
    def get_power_home_centers(self, power: str) -> List[str]:
        """Get the home supply centers for a power."""
        power_data = self.map_data.get("powers", {}).get(power, {})
        home_territories = power_data.get("home_territories", [])
        return [t.get("cell_id") for t in home_territories if t.get("is_supply_center")]
    
    # Phase Management
    
    def advance_phase(self):
        """Advance to the next phase."""
        phase_order = [
            Phase.SPRING_MOVES,
            Phase.SPRING_RETREATS,
            Phase.FALL_MOVES,
            Phase.FALL_RETREATS,
            Phase.WINTER_BUILDS
        ]
        
        current_idx = phase_order.index(self.phase)
        next_idx = (current_idx + 1) % len(phase_order)
        
        self.phase = phase_order[next_idx]
        
        # New year after winter builds
        if self.phase == Phase.SPRING_MOVES:
            self.year += 1
    
    def skip_retreats_if_none(self) -> bool:
        """
        Skip retreat phase if no units need to retreat.
        
        Returns:
            True if phase was skipped
        """
        if self.phase in (Phase.SPRING_RETREATS, Phase.FALL_RETREATS):
            if not any(u.dislodged for u in self.units.values()):
                self.advance_phase()
                return True
        return False
    
    # Supply Center Control
    
    def update_supply_center_ownership(self):
        """
        Update supply center ownership based on unit positions.
        Called at the end of fall moves.
        """
        for location in self.supply_centers:
            if location in self.units:
                unit = self.units[location]
                self.supply_centers[location] = unit.power
    
    # Victory Conditions
    
    def check_victory(self) -> Optional[str]:
        """
        Check if any power has won the game.
        
        Victory requires controlling 18 supply centers (half + 1 of 34).
        
        Returns:
            Name of winning power or None
        """
        total_scs = len(self.supply_centers)
        victory_requirement = (total_scs // 2) + 1
        
        sc_counts = {}
        for owner in self.supply_centers.values():
            if owner:
                sc_counts[owner] = sc_counts.get(owner, 0) + 1
        
        for power, count in sc_counts.items():
            if count >= victory_requirement:
                return power
        
        return None
    
    def check_elimination(self):
        """Check if any powers have been eliminated."""
        for power in self.power_names:
            if power in self.eliminated_powers:
                continue
            
            # Check if power has any SCs or units
            sc_count = len(self.get_power_supply_centers(power))
            unit_count = len(self.get_power_units(power))
            
            if sc_count == 0 and unit_count == 0:
                self.eliminated_powers.add(power)
    
    # Setup
    
    def setup_starting_positions(self):
        """
        Place starting units for all powers based on map configuration.
        
        Default: One army on each home supply center.
        For coastal centers, can optionally place fleets.
        """
        unit_counter = 0
        
        for power_name, power_data in self.map_data.get("powers", {}).items():
            home_territories = power_data.get("home_territories", [])
            
            for territory in home_territories:
                cell_id = territory.get("cell_id")
                is_coastal = territory.get("coastal", False)
                
                # Create unit - default to army, use fleet for some coastal
                # For now, just use armies for simplicity
                unit = Army(
                    unit_id=f"unit_{unit_counter}",
                    power=power_name,
                    location=cell_id
                )
                unit_counter += 1
                
                self.add_unit(unit)
    
    # Serialization
    
    def to_dict(self) -> dict:
        """Convert game state to dictionary for serialization."""
        return {
            "year": self.year,
            "phase": self.phase.value,
            "units": {loc: u.to_dict() for loc, u in self.units.items()},
            "supply_centers": self.supply_centers,
            "eliminated_powers": list(self.eliminated_powers),
            "map_data": self.map_data
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        """Create game state from dictionary."""
        state = cls(data["map_data"])
        state.year = data.get("year", 1901)
        state.phase = Phase(data.get("phase", "spring_moves"))
        state.eliminated_powers = set(data.get("eliminated_powers", []))
        state.supply_centers = data.get("supply_centers", {})
        
        # Recreate units
        state.units = {}
        for loc, unit_data in data.get("units", {}).items():
            state.units[loc] = Unit.from_dict(unit_data)
        
        return state
    
    def clone(self) -> 'GameState':
        """Create a deep copy of the game state."""
        return GameState.from_dict(self.to_dict())
    
    # Display
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the game state."""
        lines = []
        lines.append(f"Year: {self.year}")
        lines.append(f"Phase: {self.phase.value}")
        lines.append("")
        
        for power in self.power_names:
            if power in self.eliminated_powers:
                lines.append(f"{power}: ELIMINATED")
                continue
            
            units = self.get_power_units(power)
            scs = self.get_power_supply_centers(power)
            
            lines.append(f"{power}:")
            lines.append(f"  Supply Centers: {len(scs)} - {', '.join(scs)}")
            lines.append(f"  Units: {len(units)}")
            for unit in units:
                lines.append(f"    {unit}")
        
        winner = self.check_victory()
        if winner:
            lines.append(f"\n*** {winner} WINS! ***")
        
        return "\n".join(lines)
