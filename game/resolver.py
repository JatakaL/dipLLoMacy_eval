"""
Order resolution for Diplomacy game.

This module implements the Diplomacy order resolution algorithm:
1. Validate all orders
2. Calculate support strengths  
3. Resolve conflicts (head-to-head battles, standoffs)
4. Apply successful moves
5. Mark dislodged units

The resolution follows standard Diplomacy rules.
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from .orders import Order, OrderType, OrderResult
from .units import Unit, UnitType
from .game_state import GameState


class OrderResolver:
    """
    Resolves orders for a Diplomacy turn.
    
    Implements the standard Diplomacy adjudication algorithm:
    - Orders are resolved simultaneously
    - Support can be cut by attacks
    - Equal strength results in standoffs
    - Successful attacks dislodge defenders
    """
    
    def __init__(self, game_state: GameState, adjacency: Dict[str, List[str]]):
        """
        Initialize the resolver.
        
        Args:
            game_state: Current game state
            adjacency: Adjacency mapping
        """
        self.state = game_state
        self.adjacency = adjacency
        
        # Resolution tracking
        self.orders_by_location: Dict[str, Order] = {}
        self.orders_by_target: Dict[str, List[Order]] = defaultdict(list)
        self.support_orders: List[Order] = []
        self.convoy_orders: List[Order] = []
        
        # Resolution results
        self.successful_moves: List[Order] = []
        self.failed_moves: List[Order] = []
        self.dislodged_units: Dict[str, str] = {}  # location -> attacker location (for retreat)
        self.contested_territories: Set[str] = set()
    
    def resolve(self, orders: List[Order]) -> Tuple[List[Order], Dict[str, str]]:
        """
        Resolve all orders for the turn.
        
        Args:
            orders: List of validated orders
            
        Returns:
            Tuple of (all orders with results, dislodged units mapping)
        """
        # Reset tracking
        self.orders_by_location.clear()
        self.orders_by_target.clear()
        self.support_orders.clear()
        self.convoy_orders.clear()
        self.successful_moves.clear()
        self.failed_moves.clear()
        self.dislodged_units.clear()
        self.contested_territories.clear()
        
        # Filter out invalid orders
        valid_orders = [o for o in orders if o.result == OrderResult.PENDING]
        
        # Organize orders by type and location
        self._organize_orders(valid_orders)
        
        # Step 1: Check for convoy paths
        self._validate_convoy_paths()
        
        # Step 2: Calculate initial support (before cuts)
        strengths = self._calculate_initial_strengths()
        
        # Step 3: Cut support from attacked units
        self._cut_support(strengths)
        
        # Step 4: Resolve head-to-head battles
        self._resolve_head_to_head(strengths)
        
        # Step 5: Resolve remaining moves
        self._resolve_moves(strengths)
        
        # Step 6: Mark dislodged units
        self._mark_dislodged()
        
        return orders, self.dislodged_units
    
    def _organize_orders(self, orders: List[Order]) -> None:
        """Organize orders into lookup structures."""
        for order in orders:
            # Skip invalid orders
            if order.result != OrderResult.PENDING:
                continue
                
            self.orders_by_location[order.location] = order
            
            if order.order_type == OrderType.MOVE:
                self.orders_by_target[order.target].append(order)
            elif order.order_type == OrderType.SUPPORT:
                self.support_orders.append(order)
            elif order.order_type == OrderType.CONVOY:
                self.convoy_orders.append(order)
    
    def _validate_convoy_paths(self) -> None:
        """
        Validate that convoyed moves have valid convoy chains.
        
        A convoy is valid if there's a chain of fleets with convoy orders
        connecting the army's location to its destination.
        """
        for location, order in list(self.orders_by_location.items()):
            if order.order_type != OrderType.MOVE:
                continue
            
            if order.error_message == "Requires convoy":
                # Check if there's a valid convoy chain
                if self._has_convoy_path(order.location, order.target):
                    order.error_message = None  # Clear the warning
                else:
                    order.result = OrderResult.FAILED_NO_PATH
                    order.error_message = "No valid convoy path"
    
    def _has_convoy_path(self, start: str, end: str) -> bool:
        """
        Check if there's a convoy chain from start to end.
        
        Uses BFS to find a path through convoying fleets from the army's
        start location to the destination. The path must go:
        start (army location) -> convoying fleet(s) -> end (destination)
        
        A valid convoy path requires:
        1. The start must be adjacent to at least one convoying fleet
        2. The convoying fleets must form a connected chain
        3. The end must be adjacent to at least one convoying fleet in the chain
        """
        # Find all fleets convoying this army
        convoying_fleets = set()
        for convoy in self.convoy_orders:
            if convoy.support_from == start and convoy.target == end:
                convoying_fleets.add(convoy.location)
        
        if not convoying_fleets:
            return False
        
        # Check that start is adjacent to at least one convoying fleet
        start_adjacent_fleets = [f for f in convoying_fleets if f in self.adjacency.get(start, [])]
        if not start_adjacent_fleets:
            return False
        
        # Check that end is adjacent to at least one convoying fleet
        end_adjacent_fleets = [f for f in convoying_fleets if f in self.adjacency.get(end, [])]
        if not end_adjacent_fleets:
            return False
        
        # BFS through convoying fleets to check if there's a connected chain
        # from a fleet adjacent to start to a fleet adjacent to end
        visited = set()
        queue = list(start_adjacent_fleets)
        
        while queue:
            current = queue.pop(0)
            
            if current in visited:
                continue
            visited.add(current)
            
            # Check if we've reached a fleet adjacent to the destination
            if current in end_adjacent_fleets:
                return True
            
            # Add adjacent convoying fleets to queue
            for adj in self.adjacency.get(current, []):
                if adj in convoying_fleets and adj not in visited:
                    queue.append(adj)
        
        return False
    
    def _calculate_initial_strengths(self) -> Dict[str, int]:
        """
        Calculate initial attack/defense strengths.
        
        Returns:
            Dictionary mapping location/target to strength
        """
        strengths = defaultdict(int)
        
        # Each unit has base strength of 1
        for location, order in self.orders_by_location.items():
            if order.order_type == OrderType.MOVE:
                strengths[(order.location, order.target)] = 1
            elif order.order_type == OrderType.HOLD:
                strengths[(order.location, order.location)] = 1
        
        # Add support (not cut yet)
        for support in self.support_orders:
            if support.result != OrderResult.PENDING:
                continue
            
            if support.support_to:
                # Support move
                key = (support.support_from, support.support_to)
                strengths[key] = strengths.get(key, 0) + 1
            else:
                # Support hold
                key = (support.support_from, support.support_from)
                strengths[key] = strengths.get(key, 0) + 1
        
        return strengths
    
    def _cut_support(self, strengths: Dict[str, int]) -> None:
        """
        Cut support from units that are attacked.
        
        Support is cut if the supporting unit is attacked, unless:
        - The attacker is the unit being supported against
        - The attack is from the same power as the supporter
        """
        for support in self.support_orders:
            if support.result != OrderResult.PENDING:
                continue
            
            # Check if support is attacked
            for attacker in self.orders_by_target.get(support.location, []):
                if attacker.result != OrderResult.PENDING:
                    continue
                
                # Don't cut support from same power
                if attacker.power == support.power:
                    continue
                
                # Don't cut support if supporting against the attacker
                if support.support_to == attacker.location:
                    continue
                
                # Cut the support
                support.result = OrderResult.CUT
                support.error_message = f"Support cut by attack from {attacker.location}"
                
                # Reduce strength
                if support.support_to:
                    key = (support.support_from, support.support_to)
                else:
                    key = (support.support_from, support.support_from)
                
                if key in strengths:
                    strengths[key] -= 1
                break
    
    def _resolve_head_to_head(self, strengths: Dict[str, int]) -> None:
        """
        Resolve head-to-head battles (units attacking each other).
        """
        processed = set()
        
        for location, order in list(self.orders_by_location.items()):
            if order.order_type != OrderType.MOVE:
                continue
            if order.result != OrderResult.PENDING:
                continue
            if location in processed:
                continue
            
            target = order.target
            
            # Check for head-to-head
            target_order = self.orders_by_location.get(target)
            if not target_order:
                continue
            if target_order.order_type != OrderType.MOVE:
                continue
            if target_order.target != location:
                continue
            
            # Head-to-head battle!
            processed.add(location)
            processed.add(target)
            
            strength1 = strengths.get((location, target), 1)
            strength2 = strengths.get((target, location), 1)
            
            if strength1 > strength2:
                # Order 1 wins
                order.result = OrderResult.SUCCESS
                target_order.result = OrderResult.FAILED_DISLODGED
                self.successful_moves.append(order)
                self.dislodged_units[target] = location
            elif strength2 > strength1:
                # Order 2 wins
                target_order.result = OrderResult.SUCCESS
                order.result = OrderResult.FAILED_DISLODGED
                self.successful_moves.append(target_order)
                self.dislodged_units[location] = target
            else:
                # Standoff - both fail
                order.result = OrderResult.FAILED_BOUNCE
                target_order.result = OrderResult.FAILED_BOUNCE
                order.error_message = f"Bounced with {target} (strength {strength1})"
                target_order.error_message = f"Bounced with {location} (strength {strength2})"
                self.contested_territories.add(target)
                self.contested_territories.add(location)
    
    def _resolve_moves(self, strengths: Dict[str, int]) -> None:
        """
        Resolve remaining moves (not head-to-head).
        """
        # Group moves by target
        for target, attackers in self.orders_by_target.items():
            pending_attackers = [a for a in attackers if a.result == OrderResult.PENDING]
            
            if not pending_attackers:
                continue
            
            # Get defender strength (if any unit is holding there)
            defender = self.state.get_unit_at(target)
            defender_order = self.orders_by_location.get(target)
            
            # Calculate defender strength
            defender_strength = 0
            if defender:
                if defender_order and defender_order.order_type == OrderType.MOVE:
                    # Defender is moving out - no defense strength
                    defender_strength = 0
                else:
                    defender_strength = strengths.get((target, target), 1)
            
            # Get attacker strengths
            attacker_strengths = []
            for attacker in pending_attackers:
                strength = strengths.get((attacker.location, target), 1)
                attacker_strengths.append((attacker, strength))
            
            # Sort by strength (highest first)
            attacker_strengths.sort(key=lambda x: x[1], reverse=True)
            
            if len(attacker_strengths) == 1:
                # Single attacker
                attacker, strength = attacker_strengths[0]
                
                if strength > defender_strength:
                    # Attack succeeds
                    attacker.result = OrderResult.SUCCESS
                    self.successful_moves.append(attacker)
                    
                    if defender and defender_order and defender_order.result == OrderResult.PENDING:
                        if defender_order.order_type == OrderType.HOLD:
                            defender_order.result = OrderResult.FAILED_DISLODGED
                            self.dislodged_units[target] = attacker.location
                        elif defender_order.order_type == OrderType.MOVE:
                            # Defender was trying to move - check if it succeeds
                            pass  # Will be resolved in their own turn
                elif strength == defender_strength and not defender:
                    # No defender and strength at least 1
                    attacker.result = OrderResult.SUCCESS
                    self.successful_moves.append(attacker)
                else:
                    # Attack fails
                    attacker.result = OrderResult.FAILED_BOUNCE
                    attacker.error_message = f"Bounced against defender (strength {defender_strength})"
            else:
                # Multiple attackers - check for standoffs
                top_strength = attacker_strengths[0][1]
                second_strength = attacker_strengths[1][1] if len(attacker_strengths) > 1 else 0
                
                if top_strength > second_strength and top_strength > defender_strength:
                    # Top attacker wins
                    winner = attacker_strengths[0][0]
                    winner.result = OrderResult.SUCCESS
                    self.successful_moves.append(winner)
                    
                    if defender:
                        defender_order = self.orders_by_location.get(target)
                        if defender_order and defender_order.result == OrderResult.PENDING:
                            if defender_order.order_type != OrderType.MOVE:
                                defender_order.result = OrderResult.FAILED_DISLODGED
                                self.dislodged_units[target] = winner.location
                    
                    # Others fail
                    for attacker, _ in attacker_strengths[1:]:
                        attacker.result = OrderResult.FAILED_BOUNCE
                        attacker.error_message = f"Lost to stronger attack (strength {top_strength})"
                else:
                    # Standoff - all fail
                    for attacker, strength in attacker_strengths:
                        attacker.result = OrderResult.FAILED_BOUNCE
                        attacker.error_message = f"Standoff at {target} (strength {strength})"
                    self.contested_territories.add(target)
    
    def _mark_dislodged(self) -> None:
        """Mark dislodged units in the game state."""
        for location in self.dislodged_units:
            unit = self.state.get_unit_at(location)
            if unit:
                unit.dislodged = True
    
    def apply_moves(self) -> None:
        """
        Apply successful moves to the game state.
        
        Call this after resolution to update unit positions.
        Dislodged units are moved to the dislodged_units dictionary.
        """
        # First, move all dislodged units to the dislodged_units dictionary
        for location, attacker_location in self.dislodged_units.items():
            if location in self.state.units:
                dislodged_unit = self.state.units.pop(location)
                dislodged_unit.dislodged = True
                # Store with original location as key
                self.state.dislodged_units[location] = dislodged_unit
                # Track where the attack came from (for retreat restrictions)
                self.state.dislodged_from[location] = attacker_location
        
        # Process successful moves
        moves_to_apply = []
        for order in self.successful_moves:
            if order.order_type == OrderType.MOVE:
                moves_to_apply.append((order.location, order.target))
        
        # Apply moves
        for from_loc, to_loc in moves_to_apply:
            if from_loc in self.state.units:
                unit = self.state.units.pop(from_loc)
                unit.location = to_loc
                self.state.units[to_loc] = unit
    
    def get_resolution_log(self, orders: List[Order]) -> str:
        """
        Generate a human-readable log of the resolution.
        
        Args:
            orders: All orders that were resolved
            
        Returns:
            String containing the resolution log
        """
        lines = []
        lines.append("=" * 60)
        lines.append("ORDER RESOLUTION LOG")
        lines.append("=" * 60)
        
        # Successful moves
        successful = [o for o in orders if o.result == OrderResult.SUCCESS]
        if successful:
            lines.append("\nSUCCESSFUL ORDERS:")
            for order in successful:
                lines.append(f"  ✓ {order}")
        
        # Failed due to gameplay (bounce, cut, dislodged)
        gameplay_failed = [o for o in orders if o.result in (
            OrderResult.FAILED_BOUNCE, OrderResult.CUT, 
            OrderResult.FAILED_DISLODGED, OrderResult.FAILED_NO_PATH)]
        if gameplay_failed:
            lines.append("\nFAILED DUE TO GAMEPLAY:")
            for order in gameplay_failed:
                lines.append(f"  ✗ {order} - {order.result.value}: {order.error_message}")
        
        # Invalid format
        invalid_format = [o for o in orders if o.result == OrderResult.INVALID_FORMAT]
        if invalid_format:
            lines.append("\nINVALID FORMAT:")
            for order in invalid_format:
                lines.append(f"  ! {order.raw_order} - {order.error_message}")
        
        # Invalid (impossible orders)
        invalid = [o for o in orders if o.result in (
            OrderResult.INVALID_UNIT, OrderResult.INVALID_TARGET,
            OrderResult.INVALID_ADJACENT, OrderResult.INVALID_UNIT_TYPE)]
        if invalid:
            lines.append("\nIMPOSSIBLE ORDERS:")
            for order in invalid:
                lines.append(f"  ! {order.raw_order or order} - {order.result.value}: {order.error_message}")
        
        # Holds (default if no explicit result)
        holds = [o for o in orders if o.order_type == OrderType.HOLD and o.result == OrderResult.PENDING]
        if holds:
            lines.append("\nHOLDS:")
            for order in holds:
                lines.append(f"  - {order}")
        
        # Dislodged units
        if self.dislodged_units:
            lines.append("\nDISLODGED UNITS (require retreat):")
            for location, attacker_loc in self.dislodged_units.items():
                unit = self.state.get_unit_at(location)
                if unit:
                    lines.append(f"  ! {unit} - dislodged by attack from {attacker_loc}")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
