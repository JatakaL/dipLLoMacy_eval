"""
GameState class for tracking the current state of a Diplomacy game.

The GameState tracks:
- Turn information (year, season, phase)
- Unit positions
- Province ownership
- Supply center control
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from .units import Unit, UnitType


class Season(Enum):
    """Seasons in the Diplomacy game cycle."""
    SPRING = "spring"
    FALL = "fall"
    WINTER = "winter"


class Phase(Enum):
    """Phases within each season."""
    ORDER = "order"       # Players submit orders
    RETREAT = "retreat"   # Dislodged units retreat
    BUILD = "build"       # Winter adjustments (builds/disbands)


@dataclass
class GameState:
    """
    Represents the complete state of a Diplomacy game at a point in time.
    
    Attributes:
        turn: The turn number (1-indexed)
        year: The game year (starts at 1901)
        season: Current season (SPRING, FALL, or WINTER)
        phase: Current phase (ORDER, RETREAT, or BUILD)
        units: Dictionary mapping province_id -> Unit
        ownership: Dictionary mapping province_id -> power_id for owned provinces
        sc_control: Dictionary mapping SC province_id -> power_id
        powers: Set of power names in the game
        map_data: Reference to the underlying map data
    """
    turn: int = 1
    year: int = 1901
    season: Season = Season.SPRING
    phase: Phase = Phase.ORDER
    units: Dict[str, Unit] = field(default_factory=dict)
    ownership: Dict[str, str] = field(default_factory=dict)
    sc_control: Dict[str, str] = field(default_factory=dict)
    powers: Set[str] = field(default_factory=set)
    map_data: Optional[dict] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize mutable defaults and validate state."""
        # Ensure season and phase are enums
        if isinstance(self.season, str):
            self.season = Season(self.season)
        if isinstance(self.phase, str):
            self.phase = Phase(self.phase)
        # Convert powers to set if needed
        if not isinstance(self.powers, set):
            self.powers = set(self.powers)
    
    def get_unit_at(self, province_id: str) -> Optional[Unit]:
        """Get the unit at a province, if any."""
        return self.units.get(province_id)
    
    def get_units_for_power(self, power: str) -> List[Unit]:
        """Get all units belonging to a power."""
        return [u for u in self.units.values() if u.power == power]
    
    def get_unit_count(self, power: str) -> int:
        """Get the number of units a power controls."""
        return len(self.get_units_for_power(power))
    
    def get_sc_count(self, power: str) -> int:
        """Get the number of supply centers a power controls."""
        return sum(1 for p in self.sc_control.values() if p == power)
    
    def get_home_scs(self, power: str) -> List[str]:
        """Get the home supply centers for a power."""
        if not self.map_data:
            return []
        home_scs = self.map_data.get('supply_centers', {}).get('home', [])
        # Supply center data uses 'owner' key for the controlling power
        return [sc['cell_id'] for sc in home_scs if sc.get('owner') == power]
    
    def is_eliminated(self, power: str) -> bool:
        """Check if a power has been eliminated (0 supply centers)."""
        return self.get_sc_count(power) == 0
    
    def has_won(self, power: str, victory_threshold: int = 18) -> bool:
        """Check if a power has won (controls enough SCs)."""
        return self.get_sc_count(power) >= victory_threshold
    
    def advance_phase(self) -> None:
        """Advance to the next phase in the game cycle."""
        if self.season == Season.SPRING:
            if self.phase == Phase.ORDER:
                self.phase = Phase.RETREAT
            else:
                # After spring retreat, move to fall
                self.season = Season.FALL
                self.phase = Phase.ORDER
        elif self.season == Season.FALL:
            if self.phase == Phase.ORDER:
                self.phase = Phase.RETREAT
            else:
                # After fall retreat, move to winter
                self.season = Season.WINTER
                self.phase = Phase.BUILD
        else:  # WINTER
            # After winter build, move to next year's spring
            self.year += 1
            self.turn += 1
            self.season = Season.SPRING
            self.phase = Phase.ORDER
    
    def to_dict(self) -> dict:
        """Convert game state to dictionary for JSON serialization."""
        return {
            "turn": self.turn,
            "year": self.year,
            "season": self.season.value,
            "phase": self.phase.value,
            "units": {loc: unit.to_dict() for loc, unit in self.units.items()},
            "ownership": dict(self.ownership),
            "sc_control": dict(self.sc_control),
            "powers": list(self.powers)
        }
    
    @classmethod
    def from_dict(cls, data: dict, map_data: Optional[dict] = None) -> "GameState":
        """Create a GameState from a dictionary."""
        units = {}
        for loc, unit_data in data.get("units", {}).items():
            units[loc] = Unit.from_dict(unit_data)
        
        return cls(
            turn=data.get("turn", 1),
            year=data.get("year", 1901),
            season=Season(data.get("season", "spring")),
            phase=Phase(data.get("phase", "order")),
            units=units,
            ownership=dict(data.get("ownership", {})),
            sc_control=dict(data.get("sc_control", {})),
            powers=set(data.get("powers", [])),
            map_data=map_data
        )
    
    def get_turn_string(self) -> str:
        """Get a human-readable turn string like 'Spring 1901'."""
        return f"{self.season.value.capitalize()} {self.year}"
    
    def __str__(self) -> str:
        """String representation of the game state."""
        return f"GameState({self.get_turn_string()}, {self.phase.value}, {len(self.units)} units)"
