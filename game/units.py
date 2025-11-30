"""
Unit classes for Diplomacy game.

Units represent military forces that players control on the map.
There are two types:
- Army: Moves on land, can be convoyed across water
- Fleet: Moves on water and coastal provinces
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class UnitType(Enum):
    """Types of units in Diplomacy."""
    ARMY = "army"
    FLEET = "fleet"


@dataclass
class Unit:
    """
    Represents a military unit in Diplomacy.
    
    Attributes:
        unit_type: Type of unit (ARMY or FLEET)
        power: The power (player) that controls this unit
        location: Province ID where the unit is located
        dislodged: Whether the unit has been dislodged and needs to retreat
    """
    unit_type: UnitType
    power: str
    location: str
    dislodged: bool = False
    
    def __post_init__(self):
        """Validate unit after initialization."""
        if isinstance(self.unit_type, str):
            self.unit_type = UnitType(self.unit_type)
    
    def to_dict(self) -> dict:
        """Convert unit to dictionary for JSON serialization."""
        return {
            "type": self.unit_type.value,
            "power": self.power,
            "location": self.location,
            "dislodged": self.dislodged
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Unit":
        """Create a Unit from a dictionary."""
        return cls(
            unit_type=UnitType(data["type"]),
            power=data["power"],
            location=data["location"],
            dislodged=data.get("dislodged", False)
        )
    
    def __str__(self) -> str:
        """String representation of the unit."""
        type_abbrev = "A" if self.unit_type == UnitType.ARMY else "F"
        return f"{type_abbrev} {self.location} ({self.power})"
    
    def __repr__(self) -> str:
        return f"Unit({self.unit_type.value}, {self.power!r}, {self.location!r})"
