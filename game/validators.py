"""
Validators for Diplomacy game orders.

This module provides validation utilities for:
- Checking if territories exist
- Validating adjacency between territories
- Checking unit presence
- Validating order legality
"""

import re
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
    COAST_REFERENCE_PATTERN = re.compile(
        r"^(?P<territory>.+?)\s*(?:/\s*(?P<slash>[^/()]+)|\((?P<paren>[^)]+)\))\s*$"
    )
    
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
            coast_entries = {}
            raw_coasts = face_data.get('coasts', {})
            for coast_id, coast_data in raw_coasts.items():
                coast_name = coast_data.get('name', coast_id)
                aliases = {self._normalize_coast_label(coast_id), self._normalize_coast_label(coast_name)}
                for alias in coast_data.get('aliases', []):
                    aliases.add(self._normalize_coast_label(alias))

                coast_entries[coast_id] = {
                    'name': coast_name,
                    'adjacent': list(coast_data.get('adjacent', coast_data.get('adjacent_to', []))),
                    'aliases': {alias for alias in aliases if alias},
                }

            info[face_id] = {
                'type': face_data.get('type', 'land'),
                'coastal': face_data.get('coastal', False) or bool(coast_entries),
                'name': face_data.get('name', face_id),
                'coasts': coast_entries,
            }
        
        return info

    @staticmethod
    def _normalize_coast_label(label: Optional[str]) -> Optional[str]:
        """Normalize a coast label for case-insensitive matching."""
        if label is None:
            return None
        normalized = re.sub(r'[^a-z0-9]+', '', label.lower())
        return normalized or None

    def _split_territory_reference(self, reference: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Split a territory reference into territory name and optional coast."""
        if reference is None:
            return None, None

        reference = reference.strip()
        match = self.COAST_REFERENCE_PATTERN.match(reference)
        if not match:
            return reference, None

        territory = match.group('territory').strip()
        coast = (match.group('slash') or match.group('paren') or '').strip()
        if not territory or not coast:
            return reference, None

        if territory in self.name_to_id or territory.lower() in self.name_to_id:
            return territory, coast

        return reference, None

    def _resolve_coast_name(self, territory_id: str, coast_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a coast label to a canonical coast identifier."""
        if coast_name is None:
            return None, None

        territory_info = self.territory_info.get(territory_id, {})
        coasts = territory_info.get('coasts', {})
        if not coasts:
            territory_name = territory_info.get('name', territory_id)
            return None, f"{territory_name} does not have named coasts"

        normalized = self._normalize_coast_label(coast_name)
        for coast_id, coast_info in coasts.items():
            if normalized in coast_info.get('aliases', set()):
                return coast_id, None

        territory_name = territory_info.get('name', territory_id)
        return None, f"Unknown coast '{coast_name}' for {territory_name}"

    def _resolve_territory_reference(self, reference: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve a territory reference with an optional coast."""
        territory_name, coast_name = self._split_territory_reference(reference)
        territory_id = self.resolve_territory_name(territory_name) if territory_name else None
        if not territory_id:
            return None, None, f"Unknown territory: {reference}"

        coast_id, coast_error = self._resolve_coast_name(territory_id, coast_name)
        if coast_error:
            return None, None, coast_error

        return territory_id, coast_id, None

    def _get_coast_data(self, territory_id: str) -> Dict[str, dict]:
        """Get named coast data for a territory."""
        return self.territory_info.get(territory_id, {}).get('coasts', {})

    def _requires_coast_specification(self, territory_id: str) -> bool:
        """Return True when a territory has multiple non-contiguous coasts."""
        return len(self._get_coast_data(territory_id)) > 1

    def _default_coast(self, territory_id: str) -> Optional[str]:
        """Return the only named coast for a territory, if one exists."""
        coasts = self._get_coast_data(territory_id)
        if len(coasts) == 1:
            return next(iter(coasts))
        return None

    def _get_reachable_neighbors(self, territory_id: str, coast_id: Optional[str] = None) -> Set[str]:
        """Get reachable neighboring territories, optionally constrained to a coast."""
        coasts = self._get_coast_data(territory_id)
        if coast_id and coast_id in coasts:
            return set(coasts[coast_id].get('adjacent', []))
        if len(coasts) == 1:
            return set(next(iter(coasts.values())).get('adjacent', []))
        return set(self.get_adjacent_territories(territory_id))

    def _resolve_source_coast(self, unit: Unit, order: Order) -> Tuple[Optional[str], Optional[str]]:
        """Resolve the current coast for a fleet in a split-coast province."""
        territory_id = order.location
        coasts = self._get_coast_data(territory_id)
        if not coasts:
            return None, None

        requested_coast = order.location_coast
        unit_coast = unit.coast

        if requested_coast and unit_coast and requested_coast != unit_coast:
            territory_name = self.territory_info.get(territory_id, {}).get('name', territory_id)
            return None, f"Fleet at {territory_name} is on coast {unit_coast}, not {requested_coast}"

        coast_id = unit_coast or requested_coast or self._default_coast(territory_id)
        if coast_id:
            return coast_id, None

        territory_name = self.territory_info.get(territory_id, {}).get('name', territory_id)
        return None, f"Fleet at {territory_name} must specify which coast it occupies"

    def _resolve_target_coast(self, territory_id: str, requested_coast: Optional[str], *, required: bool) -> Tuple[Optional[str], Optional[str]]:
        """Resolve the coast for a target territory when needed."""
        coasts = self._get_coast_data(territory_id)
        if not coasts:
            return None, None

        if requested_coast:
            return requested_coast, None

        default_coast = self._default_coast(territory_id)
        if default_coast:
            return default_coast, None

        if required:
            territory_name = self.territory_info.get(territory_id, {}).get('name', territory_id)
            return None, f"Fleet moves to {territory_name} must specify a coast"

        return None, None

    def _fleet_can_reach(self, source_id: str, target_id: str, source_coast: Optional[str], target_coast: Optional[str]) -> bool:
        """Check whether a fleet can move between two territories with coast constraints."""
        source_neighbors = self._get_reachable_neighbors(source_id, source_coast)
        if target_id not in source_neighbors:
            return False

        target_neighbors = self._get_reachable_neighbors(target_id, target_coast)
        if source_coast or target_coast or self._get_coast_data(source_id) or self._get_coast_data(target_id):
            return source_id in target_neighbors

        return source_id in target_neighbors or self.are_adjacent(source_id, target_id)
    
    def resolve_territory_name(self, name: str) -> Optional[str]:
        """
        Resolve a territory name to its ID.
        
        Args:
            name: Territory name or ID
            
        Returns:
            Territory ID if found, None otherwise
        """
        territory_name, _ = self._split_territory_reference(name)
        if territory_name is None:
            return None

        # Try exact match first
        if territory_name in self.name_to_id:
            return self.name_to_id[territory_name]
        
        # Try case-insensitive match
        if territory_name.lower() in self.name_to_id:
            return self.name_to_id[territory_name.lower()]
        
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
        location_id, location_coast, location_error = self._resolve_territory_reference(order.location)
        if location_error or not location_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = location_error or f"Unknown territory: {order.location}"
            return order
        
        # Update location to resolved ID
        order.location = location_id
        order.location_coast = location_coast
        
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
    
    def _is_impassable(self, territory_id: str) -> bool:
        """
        Check if a territory is impassable.
        
        Looks up the territory's type in territory_info. Returns False if the
        territory_id is not found (unknown territories are not impassable).
        """
        info = self.territory_info.get(territory_id, {})
        return info.get('type') == 'impassable'

    def _validate_move(self, order: Order, unit: Unit) -> Order:
        """Validate a move order."""
        if not order.target:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = "Move order requires target"
            return order
        
        # Resolve target
        target_id, target_coast, target_error = self._resolve_territory_reference(order.target)
        if target_error or not target_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = target_error or f"Unknown territory: {order.target}"
            return order
        
        order.target = target_id
        order.target_coast = target_coast
        
        # Reject moves into impassable territories
        if self._is_impassable(target_id):
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Cannot move to impassable territory: {order.target}"
            return order
        
        # Validate terrain compatibility
        target_info = self.territory_info.get(target_id, {})
        target_type = target_info.get('type', 'land')
        target_coastal = target_info.get('coastal', False)
        
        if unit.unit_type == UnitType.ARMY:
            # Check adjacency
            if not self.are_adjacent(order.location, target_id):
                # Check if this could be a convoyed move (army moving to non-adjacent coast)
                if target_info.get('coastal', False) or target_info.get('type') == 'sea':
                    order.via_convoy = True
                    order.error_message = "Requires convoy"
                    return order

                order.result = OrderResult.INVALID_ADJACENT
                order.error_message = f"{order.location} is not adjacent to {order.target}"
                return order

            if target_type == 'sea':
                order.result = OrderResult.INVALID_TARGET
                order.error_message = "Armies cannot move to sea territories"
                return order
        else:  # Fleet
            source_coast, source_error = self._resolve_source_coast(unit, order)
            if source_error:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = source_error
                return order
            order.location_coast = source_coast

            if target_type == 'land' and not target_coastal:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = "Fleets can only move to sea or coastal territories"
                return order

            required_target_coast = target_type == 'land' and self._requires_coast_specification(target_id)
            resolved_target_coast, target_coast_error = self._resolve_target_coast(
                target_id,
                order.target_coast,
                required=required_target_coast,
            )
            if target_coast_error:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = target_coast_error
                return order
            order.target_coast = resolved_target_coast

            if not self._fleet_can_reach(order.location, target_id, source_coast, order.target_coast):
                order.result = OrderResult.INVALID_ADJACENT
                order.error_message = f"{order.location} is not adjacent to {order.target}"
                return order
        
        return order
    
    def _validate_support(self, order: Order, unit: Unit) -> Order:
        """Validate a support order."""
        # Resolve support_from
        if not order.support_from:
            order.result = OrderResult.INVALID_FORMAT
            order.error_message = "Support order requires supported unit location"
            return order
        
        support_from_id, support_from_coast, support_from_error = self._resolve_territory_reference(order.support_from)
        if support_from_error or not support_from_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = support_from_error or f"Unknown territory: {order.support_from}"
            return order
        
        order.support_from = support_from_id
        order.support_from_coast = support_from_coast
        
        # Check if supported unit exists
        supported_unit = self.state.get_unit_at(support_from_id)
        if not supported_unit:
            order.result = OrderResult.INVALID_UNIT
            order.error_message = f"No unit at {order.support_from} to support"
            return order
        
        if order.support_to:
            # Support move - validate target
            support_to_id, support_to_coast, support_to_error = self._resolve_territory_reference(order.support_to)
            if support_to_error or not support_to_id:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = support_to_error or f"Unknown territory: {order.support_to}"
                return order
            
            order.support_to = support_to_id
            order.support_to_coast = support_to_coast
            
            # Reject support into impassable territories
            if self._is_impassable(support_to_id):
                order.result = OrderResult.INVALID_TARGET
                order.error_message = f"Cannot support move to impassable territory: {order.support_to}"
                return order
            
            # Supporting unit must be able to reach the target (if it could move there)
            if unit.unit_type == UnitType.FLEET:
                source_coast, source_error = self._resolve_source_coast(unit, order)
                if source_error:
                    order.result = OrderResult.INVALID_TARGET
                    order.error_message = source_error
                    return order
                order.location_coast = source_coast

                required_target_coast = (
                    self.territory_info.get(support_to_id, {}).get('type') == 'land'
                    and self._requires_coast_specification(support_to_id)
                )
                resolved_support_to_coast, target_coast_error = self._resolve_target_coast(
                    support_to_id,
                    order.support_to_coast,
                    required=required_target_coast,
                )
                if target_coast_error:
                    order.result = OrderResult.INVALID_TARGET
                    order.error_message = target_coast_error
                    return order
                order.support_to_coast = resolved_support_to_coast

                if not self._fleet_can_reach(order.location, support_to_id, source_coast, order.support_to_coast):
                    order.result = OrderResult.INVALID_ADJACENT
                    order.error_message = f"Cannot support move to {order.support_to} - not adjacent"
                    return order
            else:
                if not self.are_adjacent(order.location, support_to_id):
                    order.result = OrderResult.INVALID_ADJACENT
                    order.error_message = f"Cannot support move to {order.support_to} - not adjacent"
                    return order
        else:
            # Support hold - must be adjacent to supported unit
            if unit.unit_type == UnitType.FLEET:
                source_coast, source_error = self._resolve_source_coast(unit, order)
                if source_error:
                    order.result = OrderResult.INVALID_TARGET
                    order.error_message = source_error
                    return order
                order.location_coast = source_coast

                target_coast = order.support_from_coast
                if supported_unit.unit_type == UnitType.FLEET and supported_unit.coast:
                    target_coast = supported_unit.coast

                if not self._fleet_can_reach(order.location, support_from_id, source_coast, target_coast):
                    order.result = OrderResult.INVALID_ADJACENT
                    order.error_message = f"Cannot support hold at {order.support_from} - not adjacent"
                    return order
            else:
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
        
        convoy_from_id, convoy_from_coast, convoy_from_error = self._resolve_territory_reference(order.support_from)
        if convoy_from_error or not convoy_from_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = convoy_from_error or f"Unknown territory: {order.support_from}"
            return order
        
        order.support_from = convoy_from_id
        order.support_from_coast = convoy_from_coast
        
        if not order.target:
            order.result = OrderResult.INVALID_FORMAT
            order.error_message = "Convoy order requires destination"
            return order
        
        convoy_to_id, convoy_to_coast, convoy_to_error = self._resolve_territory_reference(order.target)
        if convoy_to_error or not convoy_to_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = convoy_to_error or f"Unknown territory: {order.target}"
            return order
        
        order.target = convoy_to_id
        order.target_coast = convoy_to_coast
        
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
        
        target_id, target_coast, target_error = self._resolve_territory_reference(order.target)
        if target_error or not target_id:
            order.result = OrderResult.INVALID_TARGET
            order.error_message = target_error or f"Unknown territory: {order.target}"
            return order
        
        order.target = target_id
        order.target_coast = target_coast
        
        # Reject retreats into impassable territories
        if self._is_impassable(target_id):
            order.result = OrderResult.INVALID_TARGET
            order.error_message = f"Cannot retreat to impassable territory: {order.target}"
            return order
        
        # Check adjacency
        if unit.unit_type == UnitType.FLEET:
            source_coast, source_error = self._resolve_source_coast(unit, order)
            if source_error:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = source_error
                return order
            order.location_coast = source_coast

            required_target_coast = (
                self.territory_info.get(target_id, {}).get('type') == 'land'
                and self._requires_coast_specification(target_id)
            )
            resolved_target_coast, target_coast_error = self._resolve_target_coast(
                target_id,
                order.target_coast,
                required=required_target_coast,
            )
            if target_coast_error:
                order.result = OrderResult.INVALID_TARGET
                order.error_message = target_coast_error
                return order
            order.target_coast = resolved_target_coast

            if not self._fleet_can_reach(order.location, target_id, source_coast, order.target_coast):
                order.result = OrderResult.INVALID_ADJACENT
                order.error_message = f"{order.location} is not adjacent to {order.target}"
                return order
        else:
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
        
        # Build set of impassable territory names and IDs for filtering
        impassable_ids = set()
        for face_id, face_data in faces.items():
            if face_data.get('type') == 'impassable':
                impassable_ids.add(face_id)
                name = face_data.get('name', '')
                if name:
                    impassable_ids.add(name)
        
        # Convert from names to IDs if needed, filtering out impassable
        for key, neighbors in raw_adjacency.items():
            # Skip impassable territories
            if key in impassable_ids:
                continue
            
            # Convert key to ID
            key_id = name_to_id.get(key, key)
            
            # Skip if the resolved ID is impassable
            if key_id in impassable_ids:
                continue
            
            # Convert neighbors to IDs, filtering out impassable
            neighbor_ids = []
            for n in neighbors:
                if n in impassable_ids:
                    continue
                n_id = name_to_id.get(n, n)
                if n_id not in impassable_ids:
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
