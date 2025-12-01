"""
Order classes for Diplomacy game.

Orders represent the commands players give to their units. The supported order types are:
- Hold: Unit stays in place
- Move: Unit attempts to move to an adjacent province
- Support: Unit supports another unit's hold or move
- Convoy: Fleet transports army across water

Order format (as specified in the issue):
- `A {Karwyn} M {Falmere}` (Army in Karwyn moves to Falmere)
- `F {Dark Narrows} H` (Fleet in Dark Narrows holds)
- `A {Harell} S A {Karwyn} M {Falmere}` (Army in Harell supports army in Karwyn moving to Falmere)
- `F {Narrow Passage} C A {Derpeak} M {Karwyn}` (Fleet in Narrow Passage convoys army in Derpeak to Karwyn)

Territory names are enclosed in `{}` and must match exactly.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


class OrderType(Enum):
    """Types of orders in Diplomacy."""
    HOLD = "hold"
    MOVE = "move"
    SUPPORT = "support"
    CONVOY = "convoy"
    RETREAT = "retreat"
    DISBAND = "disband"
    BUILD = "build"


class OrderResult(Enum):
    """Result of an order after resolution."""
    PENDING = "pending"         # Not yet resolved
    SUCCESS = "success"         # Order succeeded
    FAILED_BOUNCE = "bounce"    # Move failed due to equal strength
    FAILED_DISLODGED = "dislodged"  # Unit was dislodged
    FAILED_NO_PATH = "no_path"  # Convoy had no valid path
    INVALID_FORMAT = "invalid_format"  # Order string was malformed
    INVALID_UNIT = "invalid_unit"  # No unit at specified location
    INVALID_TARGET = "invalid_target"  # Target territory doesn't exist
    INVALID_ADJACENT = "invalid_adjacent"  # Target not adjacent
    INVALID_UNIT_TYPE = "invalid_unit_type"  # Wrong unit type for order
    CUT = "cut"  # Support was cut


@dataclass
class Order:
    """
    Represents an order given to a unit.
    
    Attributes:
        unit_type: Type of unit ('A' for army, 'F' for fleet)
        location: Province where the unit is located
        order_type: Type of order (HOLD, MOVE, SUPPORT, CONVOY)
        target: Target province for MOVE orders
        support_unit_type: Unit type being supported (for SUPPORT orders)
        support_from: Location of supported unit (for SUPPORT orders)
        support_to: Target of supported unit's move (for SUPPORT orders, None if support hold)
        result: Result of the order after resolution
        power: The power that issued this order (set during validation)
        raw_order: The original order string
    """
    unit_type: str  # 'A' or 'F'
    location: str
    order_type: OrderType
    target: Optional[str] = None
    support_unit_type: Optional[str] = None
    support_from: Optional[str] = None
    support_to: Optional[str] = None
    result: OrderResult = OrderResult.PENDING
    power: Optional[str] = None
    raw_order: Optional[str] = None
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the order."""
        if self.order_type == OrderType.HOLD:
            return f"{self.unit_type} {{{self.location}}} H"
        elif self.order_type == OrderType.MOVE:
            return f"{self.unit_type} {{{self.location}}} M {{{self.target}}}"
        elif self.order_type == OrderType.SUPPORT:
            if self.support_to:
                return f"{self.unit_type} {{{self.location}}} S {self.support_unit_type} {{{self.support_from}}} M {{{self.support_to}}}"
            else:
                return f"{self.unit_type} {{{self.location}}} S {self.support_unit_type} {{{self.support_from}}} H"
        elif self.order_type == OrderType.CONVOY:
            return f"{self.unit_type} {{{self.location}}} C {self.support_unit_type} {{{self.support_from}}} M {{{self.target}}}"
        elif self.order_type == OrderType.RETREAT:
            return f"{self.unit_type} {{{self.location}}} R {{{self.target}}}"
        elif self.order_type == OrderType.DISBAND:
            return f"{self.unit_type} {{{self.location}}} D"
        elif self.order_type == OrderType.BUILD:
            return f"B {self.unit_type} {{{self.location}}}"
        return f"{self.unit_type} {self.location} ???"
    
    def to_dict(self) -> dict:
        """Convert order to dictionary for JSON serialization."""
        return {
            "unit_type": self.unit_type,
            "location": self.location,
            "order_type": self.order_type.value,
            "target": self.target,
            "support_unit_type": self.support_unit_type,
            "support_from": self.support_from,
            "support_to": self.support_to,
            "result": self.result.value,
            "power": self.power,
            "raw_order": self.raw_order,
            "error_message": self.error_message
        }


class OrderParser:
    """
    Parses order strings into Order objects.
    
    Supports the format specified in the issue:
    - `A {Territory} H` - Hold
    - `A {Territory} M {Target}` - Move
    - `A {Territory} S A {From} M {To}` - Support move
    - `A {Territory} S A {From} H` - Support hold
    - `F {Territory} C A {From} M {To}` - Convoy
    """
    
    # Regex patterns for parsing
    # Matches territory names in braces: {Territory Name}
    TERRITORY_PATTERN = r'\{([^}]+)\}'
    
    # Pattern for unit type: A or F
    UNIT_TYPE_PATTERN = r'^(A|F)\s+'
    
    @classmethod
    def parse(cls, order_str: str) -> Order:
        """
        Parse an order string into an Order object.
        
        Args:
            order_str: Order string in the format specified
            
        Returns:
            Order object (may have INVALID_FORMAT result if parsing fails)
        """
        order_str = order_str.strip()
        
        if not order_str:
            return cls._invalid_order(order_str, "Empty order string")
        
        # Extract unit type
        unit_match = re.match(cls.UNIT_TYPE_PATTERN, order_str)
        if not unit_match:
            return cls._invalid_order(order_str, "Order must start with 'A' or 'F' for unit type")
        
        unit_type = unit_match.group(1)
        rest = order_str[unit_match.end():].strip()
        
        # Extract all territories in braces
        territories = re.findall(cls.TERRITORY_PATTERN, rest)
        
        if not territories:
            return cls._invalid_order(order_str, "No territory found in braces {}")
        
        location = territories[0]
        
        # Determine order type based on command letter after first territory
        # Remove the first territory from rest to find the command
        after_location = re.sub(r'^\{[^}]+\}\s*', '', rest).strip()
        
        if not after_location:
            return cls._invalid_order(order_str, "No order type specified after territory")
        
        command = after_location[0].upper()
        
        if command == 'H':
            # Hold order: A {Location} H
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.HOLD,
                raw_order=order_str
            )
        
        elif command == 'M':
            # Move order: A {Location} M {Target}
            if len(territories) < 2:
                return cls._invalid_order(order_str, "Move order requires target territory")
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.MOVE,
                target=territories[1],
                raw_order=order_str
            )
        
        elif command == 'S':
            # Support order: A {Location} S A {From} M {To} OR A {Location} S A {From} H
            return cls._parse_support(order_str, unit_type, location, after_location, territories)
        
        elif command == 'C':
            # Convoy order: F {Location} C A {From} M {To}
            return cls._parse_convoy(order_str, unit_type, location, after_location, territories)
        
        elif command == 'R':
            # Retreat order: A {Location} R {Target}
            if len(territories) < 2:
                return cls._invalid_order(order_str, "Retreat order requires target territory")
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.RETREAT,
                target=territories[1],
                raw_order=order_str
            )
        
        elif command == 'D':
            # Disband order: A {Location} D
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.DISBAND,
                raw_order=order_str
            )
        
        else:
            return cls._invalid_order(order_str, f"Unknown order type: {command}")
    
    @classmethod
    def _parse_support(cls, order_str: str, unit_type: str, location: str, 
                       after_location: str, territories: List[str]) -> Order:
        """Parse a support order."""
        # After 'S' we expect: A {From} M {To} or A {From} H
        # Find the supported unit type
        support_match = re.search(r'S\s+(A|F)\s+\{([^}]+)\}\s*(M|H)', after_location)
        
        if not support_match:
            return cls._invalid_order(order_str, "Invalid support order format. Expected: S A/F {Location} M/H ...")
        
        support_unit_type = support_match.group(1)
        support_from = support_match.group(2)
        support_action = support_match.group(3).upper()
        
        if support_action == 'H':
            # Support hold: A {Location} S A {From} H
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.SUPPORT,
                support_unit_type=support_unit_type,
                support_from=support_from,
                support_to=None,
                raw_order=order_str
            )
        else:
            # Support move: A {Location} S A {From} M {To}
            if len(territories) < 3:
                return cls._invalid_order(order_str, "Support move order requires target territory")
            
            # The third territory is the target of the supported move
            support_to = territories[2]
            
            return Order(
                unit_type=unit_type,
                location=location,
                order_type=OrderType.SUPPORT,
                support_unit_type=support_unit_type,
                support_from=support_from,
                support_to=support_to,
                raw_order=order_str
            )
    
    @classmethod
    def _parse_convoy(cls, order_str: str, unit_type: str, location: str,
                      after_location: str, territories: List[str]) -> Order:
        """Parse a convoy order."""
        # Convoy: F {Location} C A {From} M {To}
        convoy_match = re.search(r'C\s+(A)\s+\{([^}]+)\}\s*M', after_location)
        
        if not convoy_match:
            return cls._invalid_order(order_str, "Invalid convoy order format. Expected: C A {From} M {To}")
        
        if unit_type != 'F':
            return cls._invalid_order(order_str, "Only fleets can convoy")
        
        convoy_unit_type = convoy_match.group(1)
        convoy_from = convoy_match.group(2)
        
        if len(territories) < 3:
            return cls._invalid_order(order_str, "Convoy order requires destination territory")
        
        convoy_to = territories[2]
        
        return Order(
            unit_type=unit_type,
            location=location,
            order_type=OrderType.CONVOY,
            support_unit_type=convoy_unit_type,
            support_from=convoy_from,
            target=convoy_to,
            raw_order=order_str
        )
    
    @classmethod
    def _invalid_order(cls, order_str: str, message: str) -> Order:
        """Create an invalid order with error information."""
        return Order(
            unit_type='?',
            location='?',
            order_type=OrderType.HOLD,  # Default
            result=OrderResult.INVALID_FORMAT,
            raw_order=order_str,
            error_message=message
        )
    
    @classmethod
    def parse_file(cls, file_path: str) -> List[Order]:
        """
        Parse all orders from a file.
        
        Args:
            file_path: Path to the order file
            
        Returns:
            List of Order objects
        """
        orders = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    orders.append(cls.parse(line))
        return orders


def create_hold_order(unit_type: str, location: str) -> Order:
    """Create a hold order for a unit."""
    return Order(
        unit_type=unit_type,
        location=location,
        order_type=OrderType.HOLD
    )


def create_move_order(unit_type: str, location: str, target: str) -> Order:
    """Create a move order for a unit."""
    return Order(
        unit_type=unit_type,
        location=location,
        order_type=OrderType.MOVE,
        target=target
    )


def create_support_hold_order(unit_type: str, location: str, 
                               support_unit_type: str, support_from: str) -> Order:
    """Create a support hold order."""
    return Order(
        unit_type=unit_type,
        location=location,
        order_type=OrderType.SUPPORT,
        support_unit_type=support_unit_type,
        support_from=support_from
    )


def create_support_move_order(unit_type: str, location: str,
                               support_unit_type: str, support_from: str, support_to: str) -> Order:
    """Create a support move order."""
    return Order(
        unit_type=unit_type,
        location=location,
        order_type=OrderType.SUPPORT,
        support_unit_type=support_unit_type,
        support_from=support_from,
        support_to=support_to
    )


def create_convoy_order(location: str, army_from: str, army_to: str) -> Order:
    """Create a convoy order for a fleet."""
    return Order(
        unit_type='F',
        location=location,
        order_type=OrderType.CONVOY,
        support_unit_type='A',
        support_from=army_from,
        target=army_to
    )
