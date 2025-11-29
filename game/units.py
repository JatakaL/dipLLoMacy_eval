"""
Unit Types for Diplomacy

This module defines the two unit types in Diplomacy:
- Army: Can move on land, can be convoyed across sea
- Fleet: Can move on sea and coastal provinces
"""

from enum import Enum
from typing import Optional


class UnitType(Enum):
    """Enumeration of unit types in Diplomacy."""
    ARMY = "army"
    FLEET = "fleet"


class Unit:
    """
    Base class for Diplomacy units.
    
    Attributes:
        unit_id: Unique identifier for this unit
        unit_type: Type of unit (army or fleet)
        power: The power that controls this unit
        location: The province where the unit is located (face/cell ID)
        coast: Optional coast specification for fleets (e.g., "nc", "sc")
        dislodged: Whether the unit was dislodged this turn
        retreat_options: List of valid retreat locations if dislodged
    """
    
    def __init__(self, unit_id: str, unit_type: UnitType, power: str, 
                 location: str, coast: Optional[str] = None):
        """
        Initialize a unit.
        
        Args:
            unit_id: Unique identifier for this unit
            unit_type: Type of unit (army or fleet)
            power: The power that controls this unit
            location: The province where the unit is located
            coast: Optional coast specification for fleets
        """
        self.unit_id = unit_id
        self.unit_type = unit_type
        self.power = power
        self.location = location
        self.coast = coast
        self.dislodged = False
        self.retreat_options: list[str] = []
    
    def can_occupy(self, province_type: str, is_coastal: bool = False) -> bool:
        """
        Check if this unit can occupy a given province type.
        
        Args:
            province_type: Type of province ("land", "sea", "impassable")
            is_coastal: Whether the province is coastal
            
        Returns:
            True if the unit can occupy this province
        """
        raise NotImplementedError("Subclasses must implement can_occupy")
    
    def to_dict(self) -> dict:
        """Convert unit to dictionary representation."""
        result = {
            "unit_id": self.unit_id,
            "type": self.unit_type.value,
            "power": self.power,
            "location": self.location,
        }
        if self.coast:
            result["coast"] = self.coast
        if self.dislodged:
            result["dislodged"] = True
            result["retreat_options"] = self.retreat_options
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Unit':
        """Create a unit from dictionary representation."""
        unit_type = UnitType(data["type"])
        if unit_type == UnitType.ARMY:
            unit = Army(
                unit_id=data["unit_id"],
                power=data["power"],
                location=data["location"]
            )
        else:
            unit = Fleet(
                unit_id=data["unit_id"],
                power=data["power"],
                location=data["location"],
                coast=data.get("coast")
            )
        unit.dislodged = data.get("dislodged", False)
        unit.retreat_options = data.get("retreat_options", [])
        return unit
    
    def __repr__(self) -> str:
        coast_str = f"/{self.coast}" if self.coast else ""
        return f"{self.unit_type.value.upper()}({self.power}:{self.location}{coast_str})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Unit):
            return False
        return self.unit_id == other.unit_id
    
    def __hash__(self) -> int:
        return hash(self.unit_id)


class Army(Unit):
    """
    Army unit in Diplomacy.
    
    Armies can:
    - Move on land provinces
    - Be convoyed across sea by fleets
    - Cannot move on sea provinces directly
    """
    
    def __init__(self, unit_id: str, power: str, location: str):
        """
        Initialize an army.
        
        Args:
            unit_id: Unique identifier for this unit
            power: The power that controls this unit
            location: The province where the unit is located
        """
        super().__init__(unit_id, UnitType.ARMY, power, location)
    
    def can_occupy(self, province_type: str, is_coastal: bool = False) -> bool:
        """
        Check if this army can occupy a given province type.
        
        Armies can only occupy land provinces (coastal or inland).
        
        Args:
            province_type: Type of province ("land", "sea", "impassable")
            is_coastal: Whether the province is coastal (ignored for armies)
            
        Returns:
            True if the army can occupy this province
        """
        return province_type == "land"


class Fleet(Unit):
    """
    Fleet unit in Diplomacy.
    
    Fleets can:
    - Move on sea provinces
    - Move on coastal land provinces
    - Cannot move on inland land provinces
    - Convoy armies across sea
    """
    
    def __init__(self, unit_id: str, power: str, location: str, 
                 coast: Optional[str] = None):
        """
        Initialize a fleet.
        
        Args:
            unit_id: Unique identifier for this unit
            power: The power that controls this unit
            location: The province where the unit is located
            coast: Optional coast specification (e.g., "nc", "sc")
        """
        super().__init__(unit_id, UnitType.FLEET, power, location, coast)
    
    def can_occupy(self, province_type: str, is_coastal: bool = False) -> bool:
        """
        Check if this fleet can occupy a given province type.
        
        Fleets can occupy sea provinces or coastal land provinces.
        
        Args:
            province_type: Type of province ("land", "sea", "impassable")
            is_coastal: Whether the province is coastal
            
        Returns:
            True if the fleet can occupy this province
        """
        if province_type == "sea":
            return True
        if province_type == "land" and is_coastal:
            return True
        return False


def create_unit(unit_type: str, unit_id: str, power: str, location: str,
                coast: Optional[str] = None) -> Unit:
    """
    Factory function to create a unit of the specified type.
    
    Args:
        unit_type: Type of unit ("army" or "fleet")
        unit_id: Unique identifier for this unit
        power: The power that controls this unit
        location: The province where the unit is located
        coast: Optional coast specification for fleets
        
    Returns:
        A new Unit instance of the specified type
        
    Raises:
        ValueError: If unit_type is invalid
    """
    if unit_type.lower() == "army":
        return Army(unit_id, power, location)
    elif unit_type.lower() == "fleet":
        return Fleet(unit_id, power, location, coast)
    else:
        raise ValueError(f"Unknown unit type: {unit_type}")
