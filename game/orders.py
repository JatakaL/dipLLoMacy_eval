"""
Order Types for Diplomacy

This module defines the order types in Diplomacy:
- Hold: Unit stays in place
- Move: Unit attempts to move to adjacent province
- Support: Unit supports another unit's move or hold
- Convoy: Fleet convoys an army across sea
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .units import Unit


class OrderType(Enum):
    """Enumeration of order types in Diplomacy."""
    HOLD = "hold"
    MOVE = "move"
    SUPPORT = "support"
    CONVOY = "convoy"


class OrderResult(Enum):
    """Result of order resolution."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BOUNCED = "bounced"
    DISLODGED = "dislodged"
    CUT = "cut"
    VOID = "void"  # Invalid order


class Order:
    """
    Base class for Diplomacy orders.
    
    Attributes:
        unit_location: Location of the unit receiving the order
        power: The power issuing the order
        order_type: Type of order
        result: Result of order resolution
        strength: Effective strength of the order
    """
    
    def __init__(self, unit_location: str, power: str, order_type: OrderType):
        """
        Initialize an order.
        
        Args:
            unit_location: Location of the unit receiving the order
            power: The power issuing the order
            order_type: Type of order
        """
        self.unit_location = unit_location
        self.power = power
        self.order_type = order_type
        self.result = OrderResult.PENDING
        self.strength = 1  # Base strength, can be increased by supports
    
    def to_dict(self) -> dict:
        """Convert order to dictionary representation."""
        return {
            "unit_location": self.unit_location,
            "power": self.power,
            "order_type": self.order_type.value,
            "result": self.result.value,
            "strength": self.strength
        }
    
    def __repr__(self) -> str:
        return f"{self.unit_location} {self.order_type.value.upper()}"


class Hold(Order):
    """
    Hold order - unit stays in place.
    
    Syntax: UNIT holds
    Example: Paris holds
    """
    
    def __init__(self, unit_location: str, power: str):
        """
        Initialize a hold order.
        
        Args:
            unit_location: Location of the unit
            power: The power issuing the order
        """
        super().__init__(unit_location, power, OrderType.HOLD)
    
    def __repr__(self) -> str:
        return f"{self.unit_location} HOLD"


class Move(Order):
    """
    Move order - unit attempts to move to adjacent province.
    
    Syntax: UNIT -> DESTINATION
    Example: Paris -> Burgundy
    """
    
    def __init__(self, unit_location: str, power: str, destination: str,
                 destination_coast: Optional[str] = None):
        """
        Initialize a move order.
        
        Args:
            unit_location: Location of the unit
            power: The power issuing the order
            destination: Target province for the move
            destination_coast: Optional coast specification for fleets
        """
        super().__init__(unit_location, power, OrderType.MOVE)
        self.destination = destination
        self.destination_coast = destination_coast
        self.via_convoy = False  # Whether this move requires convoy
    
    def to_dict(self) -> dict:
        """Convert order to dictionary representation."""
        result = super().to_dict()
        result["destination"] = self.destination
        if self.destination_coast:
            result["destination_coast"] = self.destination_coast
        result["via_convoy"] = self.via_convoy
        return result
    
    def __repr__(self) -> str:
        coast = f"/{self.destination_coast}" if self.destination_coast else ""
        convoy = " (via convoy)" if self.via_convoy else ""
        return f"{self.unit_location} -> {self.destination}{coast}{convoy}"


class Support(Order):
    """
    Support order - unit supports another unit's move or hold.
    
    Syntax: UNIT supports SUPPORTED_UNIT [-> DESTINATION]
    Examples: 
        Paris supports Burgundy  (support to hold)
        Paris supports Burgundy -> Munich  (support to move)
    """
    
    def __init__(self, unit_location: str, power: str, 
                 supported_location: str, destination: Optional[str] = None):
        """
        Initialize a support order.
        
        Args:
            unit_location: Location of the supporting unit
            power: The power issuing the order
            supported_location: Location of the unit being supported
            destination: Destination of supported move (None for support hold)
        """
        super().__init__(unit_location, power, OrderType.SUPPORT)
        self.supported_location = supported_location
        self.destination = destination  # None means support to hold
    
    @property
    def is_support_hold(self) -> bool:
        """Check if this is a support to hold."""
        return self.destination is None
    
    @property
    def is_support_move(self) -> bool:
        """Check if this is a support to move."""
        return self.destination is not None
    
    def to_dict(self) -> dict:
        """Convert order to dictionary representation."""
        result = super().to_dict()
        result["supported_location"] = self.supported_location
        if self.destination:
            result["destination"] = self.destination
        return result
    
    def __repr__(self) -> str:
        if self.destination:
            return f"{self.unit_location} S {self.supported_location} -> {self.destination}"
        else:
            return f"{self.unit_location} S {self.supported_location}"


class Convoy(Order):
    """
    Convoy order - fleet convoys an army across sea.
    
    Syntax: FLEET convoys ARMY -> DESTINATION
    Example: North Sea convoys London -> Norway
    
    A chain of convoy orders allows an army to move across
    multiple sea provinces in a single turn.
    """
    
    def __init__(self, unit_location: str, power: str,
                 convoyed_army_location: str, destination: str):
        """
        Initialize a convoy order.
        
        Args:
            unit_location: Location of the convoying fleet
            power: The power issuing the order
            convoyed_army_location: Location of the army being convoyed
            destination: Destination of the convoyed army
        """
        super().__init__(unit_location, power, OrderType.CONVOY)
        self.convoyed_army_location = convoyed_army_location
        self.destination = destination
    
    def to_dict(self) -> dict:
        """Convert order to dictionary representation."""
        result = super().to_dict()
        result["convoyed_army_location"] = self.convoyed_army_location
        result["destination"] = self.destination
        return result
    
    def __repr__(self) -> str:
        return f"{self.unit_location} C {self.convoyed_army_location} -> {self.destination}"


def parse_order(order_str: str, power: str) -> Optional[Order]:
    """
    Parse an order from a string representation.
    
    Formats supported:
    - "Location HOLD" or "Location H"
    - "Location -> Destination" or "Location - Destination" or "Location M Destination"
    - "Location S TargetLocation" (support hold)
    - "Location S TargetLocation -> Destination" (support move)
    - "Location C Army -> Destination" (convoy)
    
    Args:
        order_str: String representation of the order
        power: The power issuing the order
        
    Returns:
        Parsed Order object or None if parsing fails
    """
    order_str = order_str.strip().upper()
    
    # Split by whitespace
    parts = order_str.split()
    if len(parts) < 2:
        return None
    
    unit_location = parts[0]
    
    # Hold order
    if parts[1] in ("HOLD", "H", "HOLDS"):
        return Hold(unit_location, power)
    
    # Move order
    if parts[1] in ("->", "-", "M", "MOVE", "MOVES"):
        if len(parts) >= 3:
            destination = parts[2]
            return Move(unit_location, power, destination)
        return None
    
    # Handle "Location -> Destination" format with -> as part of string
    if "->" in order_str or " - " in order_str:
        # Move order
        if " S " not in order_str and " C " not in order_str:
            if "->" in order_str:
                loc, dest = order_str.split("->", 1)
            else:
                loc, dest = order_str.split(" - ", 1)
            return Move(loc.strip(), power, dest.strip())
    
    # Support order
    if parts[1] in ("S", "SUPPORT", "SUPPORTS"):
        if len(parts) >= 3:
            supported_location = parts[2]
            # Check if it's support to move
            if len(parts) >= 5 and parts[3] in ("->", "-", "M"):
                destination = parts[4]
                return Support(unit_location, power, supported_location, destination)
            else:
                return Support(unit_location, power, supported_location)
        return None
    
    # Convoy order
    if parts[1] in ("C", "CONVOY", "CONVOYS"):
        if len(parts) >= 5 and parts[3] in ("->", "-"):
            army_location = parts[2]
            destination = parts[4]
            return Convoy(unit_location, power, army_location, destination)
        return None
    
    return None


def create_order(order_type: str, unit_location: str, power: str, 
                 destination: Optional[str] = None,
                 supported_location: Optional[str] = None,
                 convoyed_army_location: Optional[str] = None) -> Order:
    """
    Factory function to create an order of the specified type.
    
    Args:
        order_type: Type of order ("hold", "move", "support", "convoy")
        unit_location: Location of the unit receiving the order
        power: The power issuing the order
        destination: Target destination (for move/support move/convoy)
        supported_location: Unit being supported (for support orders)
        convoyed_army_location: Army being convoyed (for convoy orders)
        
    Returns:
        A new Order instance of the specified type
        
    Raises:
        ValueError: If order_type is invalid or required parameters are missing
    """
    order_type_lower = order_type.lower()
    
    if order_type_lower == "hold":
        return Hold(unit_location, power)
    
    elif order_type_lower == "move":
        if destination is None:
            raise ValueError("Move order requires destination")
        return Move(unit_location, power, destination)
    
    elif order_type_lower == "support":
        if supported_location is None:
            raise ValueError("Support order requires supported_location")
        return Support(unit_location, power, supported_location, destination)
    
    elif order_type_lower == "convoy":
        if convoyed_army_location is None or destination is None:
            raise ValueError("Convoy order requires convoyed_army_location and destination")
        return Convoy(unit_location, power, convoyed_army_location, destination)
    
    else:
        raise ValueError(f"Unknown order type: {order_type}")
