"""
Validators for Diplomacy game orders.

This module provides validation utilities for:
- Checking if territories exist
- Validating adjacency between territories
- Checking unit presence
- Validating order legality
"""

from typing import Dict, List, Optional, Set, Tuple
from .orders import Order, OrderType, OrderResult
from .units import Unit, UnitType
from .game_state import GameState


class OrderValidator:
    """
    Validates orders against the game state and map.
    
    Validates:
    - Unit exists at specified location
    - Target territories exist
    - Moves are to adjacent territories
    - Unit types match (armies on land, fleets on water/coast)
    - Convoy chains are valid
    """
    
    def __init__(self, game_state: GameState, adjacency: Dict[str, List[str]]):
        """
        Initialize the validator.
        
        Args:
            game_state: Current game state with units
            adjacency: Adjacency map from territory ID to list of adjacent territory IDs
        """
        self.state = game_state
        self.adjacency = adjacency
        
        # Build name-to-id mapping for territory lookup
        self.name_to_id = self._build_name_mapping()
        
        # Build territory type info
        self.territory_info = self._build_territory_info()
    
    def _build_name_mapping(self) -> Dict[str, str]:
        """Build mapping from territory names to IDs."""
        mapping = {}
        if not self.state.map_data:
            return mapping
        
        topology = self.state.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        for face_id, face_data in faces.items():
            name = face_data.get('name', '')
            if name:
                # Map both exact name and lowercase for case-insensitive lookup
                mapping[name] = face_id
                mapping[name.lower()] = face_id
            # Also map the ID itself
            mapping[face_id] = face_id
        
        return mapping
    
    def _build_territory_info(self) -> Dict[str, dict]:
        """Build territory information including type and coastal status."""
        info = {}
        if not self.state.map_data:
            return info
        
        topology = self.state.map_data.get('topology', {})
        faces = topology.get('faces', {})
        
        for face_id, face_data in faces.items():
            info[face_id] = {
                'type': face_data.get('type', 'land'),
                'coastal': face_data.get('coastal', False),
                'name': face_data.get('name', face_id)
            }
        
        return info
    
    def resolve_territory_name(self, name: str) -> Optional[str]:
        """
        Resolve a territory name to its ID.
        
        Args:
            name: Territory name or ID
            
        Returns:
            Territory ID if found, None otherwise
        """
        # Try exact match first
        if name in self.name_to_id:
            return self.name_to_id[name]
        
        # Try case-insensitive match
        if name.lower() in self.name_to_id:
            return self.name_to_id[name.lower()]
        
        return None
    
    def get_adjacent_territories(self, territory_id: str) -> List[str]:
        """Get territories adjacent to the given territory."""
        return self.adjacency.get(territory_id, [])
    
    def are_adjacent(self, territory1: str, territory2: str) -> bool:
        """Check if two territories are adjacent."""
        t1_id = self.resolve_territory_name(territory1)
        t2_id = self.resolve_territory_name(territory2)
        
        if not t1_id or not t2_id:
            return False
        
        return t2_id in self.get_adjacent_territories(t1_id)
    
    def validate_order(self, order: Order) -> Order:
        """
        Validate an order and update its result.
        
        Args:
            order: Order to validate
            
        Returns:
            The order with updated result and error_message
        """
        # Skip already invalid orders
        if order.result == OrderResult.INVALID_FORMAT:
            return order
        
        # Resolve location to ID
        location_id = self.resolve_territory_name(order.location)
        if not location_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.location}"
            return order
        
        # Update location to resolved ID
        order.location = location_id
        
        # Check if unit exists at location
        unit = self.state.get_unit_at(location_id)
        if not unit:
            order.result = OrderResult.INVALID_UNIT
            order.error_message = f"No unit at {order.location}"
            return order
        
        # Verify unit type matches
        expected_type = 'A' if unit.unit_type == UnitType.ARMY else 'F'
        if order.unit_type != expected_type:
            order.result = OrderResult.INVALID_UNIT_TYPE
            order.error_message = f"Unit at {order.location} is {expected_type}, not {order.unit_type}"
            return order
        
        # Set the power
        order.power = unit.power
        
        # Validate based on order type
        if order.order_type == OrderType.HOLD:
            return self._validate_hold(order, unit)
        elif order.order_type == OrderType.MOVE:
            return self._validate_move(order, unit)
        elif order.order_type == OrderType.SUPPORT:
            return self._validate_support(order, unit)
        elif order.order_type == OrderType.CONVOY:
            return self._validate_convoy(order, unit)
        elif order.order_type == OrderType.RETREAT:
            return self._validate_retreat(order, unit)
        
        return order
    
    def _validate_hold(self, order: Order, unit: Unit) -> Order:
        """Validate a hold order (always valid if unit exists)."""
        return order
    
    def _validate_move(self, order: Order, unit: Unit) -> Order:
        """Validate a move order."""
        if not order.target:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = "Move order requires target"
            return order
        
        # Resolve target
        target_id = self.resolve_territory_name(order.target)
        if not target_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.target}"
            return order
        
        order.target = target_id
        
        # Check adjacency
        if not self.are_adjacent(order.location, target_id):
            # Check if this could be a convoyed move (army moving to non-adjacent coast)
            if unit.unit_type == UnitType.ARMY:
                # Convoys are validated separately during resolution
                # For now, mark as potentially valid if target is coastal
                target_info = self.territory_info.get(target_id, {})
                if target_info.get('coastal', False) or target_info.get('type') == 'sea':
                    order.error_message = "Requires convoy"
                    return order
            
            order.result = OrderResult.INVALID_ADJACENT
            order.error_message = f"{order.location} is not adjacent to {order.target}"
            return order
        
        # Validate terrain compatibility
        target_info = self.territory_info.get(target_id, {})
        target_type = target_info.get('type', 'land')
        target_coastal = target_info.get('coastal', False)
        
        if unit.unit_type == UnitType.ARMY:
            if target_type == 'sea':
                order.result = OrderResult.INVALID_TARGET
                order.error_message = "Armies cannot move to sea territories"
                return order
        else:  # Fleet
            if target_type == 'land' and not target_coastal:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = "Fleets can only move to sea or coastal territories"
                return order
        
        return order
    
    def _validate_support(self, order: Order, unit: Unit) -> Order:
        """Validate a support order."""
        # Resolve support_from
        if not order.support_from:
            order.result = OrderResult.INVALID_FORMAT
            order.error_message = "Support order requires supported unit location"
            return order
        
        support_from_id = self.resolve_territory_name(order.support_from)
        if not support_from_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.support_from}"
            return order
        
        order.support_from = support_from_id
        
        # Check if supported unit exists
        supported_unit = self.state.get_unit_at(support_from_id)
        if not supported_unit:
            order.result = OrderResult.INVALID_UNIT
            order.error_message = f"No unit at {order.support_from} to support"
            return order
        
        if order.support_to:
            # Support move - validate target
            support_to_id = self.resolve_territory_name(order.support_to)
            if not support_to_id:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = f"Unknown territory: {order.support_to}"
                return order
            
            order.support_to = support_to_id
            
            # Supporting unit must be able to reach the target (if it could move there)
            if not self.are_adjacent(order.location, support_to_id):
                order.result = OrderResult.INVALID_ADJACENT
                order.error_message = f"Cannot support move to {order.support_to} - not adjacent"
                return order
        else:
            # Support hold - must be adjacent to supported unit
            if not self.are_adjacent(order.location, support_from_id):
                order.result = OrderResult.INVALID_ADJACENT
                order.error_message = f"Cannot support hold at {order.support_from} - not adjacent"
                return order
        
        return order
    
    def _validate_convoy(self, order: Order, unit: Unit) -> Order:
        """Validate a convoy order."""
        if unit.unit_type != UnitType.FLEET:
            order.result = OrderResult.INVALID_UNIT_TYPE
            order.error_message = "Only fleets can convoy"
            return order
        
        # Fleet must be at sea
        location_info = self.territory_info.get(order.location, {})
        if location_info.get('type') != 'sea':
            order.result = OrderResult.INVALID_TARGET
            order.error_message = "Fleet must be at sea to convoy"
            return order
        
        # Resolve convoy source and destination
        if not order.support_from:
            order.result = OrderResult.INVALID_FORMAT
            order.error_message = "Convoy order requires army location"
            return order
        
        convoy_from_id = self.resolve_territory_name(order.support_from)
        if not convoy_from_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.support_from}"
            return order
        
        order.support_from = convoy_from_id
        
        if not order.target:
            order.result = OrderResult.INVALID_FORMAT
            order.error_message = "Convoy order requires destination"
            return order
        
        convoy_to_id = self.resolve_territory_name(order.target)
        if not convoy_to_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.target}"
            return order
        
        order.target = convoy_to_id
        
        # Check that convoyed unit is an army
        convoyed_unit = self.state.get_unit_at(convoy_from_id)
        if not convoyed_unit:
            order.result = OrderResult.INVALID_UNIT
            order.error_message = f"No unit at {order.support_from} to convoy"
            return order
        
        if convoyed_unit.unit_type != UnitType.ARMY:
            order.result = OrderResult.INVALID_UNIT_TYPE
            order.error_message = "Only armies can be convoyed"
            return order
        
        return order
    
    def _validate_retreat(self, order: Order, unit: Unit) -> Order:
        """Validate a retreat order."""
        if not unit.dislodged:
            order.result = OrderResult.INVALID_UNIT
            order.error_message = "Unit is not dislodged"
            return order
        
        if not order.target:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = "Retreat order requires target"
            return order
        
        target_id = self.resolve_territory_name(order.target)
        if not target_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Unknown territory: {order.target}"
            return order
        
        order.target = target_id
        
        # Check adjacency
        if not self.are_adjacent(order.location, target_id):
            order.result = OrderResult.INVALID_ADJACENT
            order.error_message = f"{order.location} is not adjacent to {order.target}"
            return order
        
        # Check that target is unoccupied
        if self.state.get_unit_at(target_id):
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Cannot retreat to occupied territory: {order.target}"
            return order
        
        return order
    
    def validate_all_orders(self, orders: List[Order]) -> List[Order]:
        """
        Validate all orders in a list.
        
        Args:
            orders: List of orders to validate
            
        Returns:
            List of validated orders with results set
        """
        return [self.validate_order(order) for order in orders]


def build_adjacency_from_map(map_data: dict) -> Dict[str, List[str]]:
    """
    Build adjacency dictionary from map data.
    
    Args:
        map_data: Map data with adjacency information
        
    Returns:
        Dictionary mapping territory ID to list of adjacent territory IDs
    """
    adjacency = {}
    
    # Get face name to ID mapping
    topology = map_data.get('topology', {})
    faces = topology.get('faces', {})
    
    name_to_id = {}
    id_to_name = {}
    for face_id, face_data in faces.items():
        name = face_data.get('name', face_id)
        name_to_id[name] = face_id
        id_to_name[face_id] = name
    
    # First try the adjacency key if it exists
    if 'adjacency' in map_data:
        raw_adjacency = map_data['adjacency']
        
        # Convert from names to IDs if needed
        for key, neighbors in raw_adjacency.items():
            # Convert key to ID
            key_id = name_to_id.get(key, key)
            
            # Convert neighbors to IDs
            neighbor_ids = []
            for n in neighbors:
                n_id = name_to_id.get(n, n)
                neighbor_ids.append(n_id)
            
            adjacency[key_id] = neighbor_ids
        
        return adjacency
    
    # Otherwise build from topology
    borders = topology.get('borders', {})
    
    # Build adjacency from border data
    for border_id, border_data in borders.items():
        faces_list = border_data.get('faces', [])
        if len(faces_list) == 2:
            f1, f2 = faces_list
            
            # Check if both faces exist and aren't impassable
            f1_data = faces.get(f1, {})
            f2_data = faces.get(f2, {})
            
            # Skip if either face is impassable
            if f1_data.get('type') == 'impassable' or f2_data.get('type') == 'impassable':
                continue
            
            # Add adjacency both ways
            if f1 not in adjacency:
                adjacency[f1] = []
            if f2 not in adjacency:
                adjacency[f2] = []
            
            if f2 not in adjacency[f1]:
                adjacency[f1].append(f2)
            if f1 not in adjacency[f2]:
                adjacency[f2].append(f1)
    
    return adjacency
