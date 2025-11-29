"""
Game Engine for Diplomacy

This module implements the main game engine that:
- Manages game flow and turn structure
- Validates orders
- Resolves orders according to Diplomacy rules
- Handles retreats and builds
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from .units import Unit, Army, Fleet, UnitType
from .orders import Order, OrderType, OrderResult, Hold, Move, Support, Convoy
from .game_state import GameState, Phase


class GameEngine:
    """
    Main game engine for Diplomacy.
    
    Handles the complete game loop including:
    - Order submission and validation
    - Order resolution
    - Retreat processing
    - Build/disband processing
    - Victory checking
    """
    
    def __init__(self, map_data: dict):
        """
        Initialize the game engine with a map.
        
        Args:
            map_data: Map JSON from the generation pipeline
        """
        self.state = GameState(map_data)
        self.pending_orders: Dict[str, List[Order]] = {}  # power -> orders
        self.resolution_log: List[str] = []
    
    @property
    def year(self) -> int:
        return self.state.year
    
    @property
    def phase(self) -> Phase:
        return self.state.phase
    
    def setup_starting_positions(self):
        """Place starting units for all powers."""
        self.state.setup_starting_positions()
    
    # Order Validation
    
    def validate_order(self, order: Order) -> Tuple[bool, str]:
        """
        Validate an order.
        
        Args:
            order: The order to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if unit exists at the location
        unit = self.state.get_unit(order.unit_location)
        if not unit:
            return False, f"No unit at {order.unit_location}"
        
        # Check if power owns the unit
        if unit.power != order.power:
            return False, f"Unit at {order.unit_location} belongs to {unit.power}, not {order.power}"
        
        # Validate specific order types
        if isinstance(order, Move):
            return self._validate_move(order, unit)
        elif isinstance(order, Support):
            return self._validate_support(order, unit)
        elif isinstance(order, Convoy):
            return self._validate_convoy(order, unit)
        elif isinstance(order, Hold):
            return True, ""
        
        return False, f"Unknown order type: {order.order_type}"
    
    def _validate_move(self, order: Move, unit: Unit) -> Tuple[bool, str]:
        """Validate a move order."""
        # Check adjacency (unless via convoy)
        if not order.via_convoy:
            if not self.state.are_adjacent(order.unit_location, order.destination):
                return False, f"{order.destination} is not adjacent to {order.unit_location}"
        
        # Check if unit can enter destination
        dest_type = self.state.get_province_type(order.destination)
        dest_coastal = self.state.is_coastal(order.destination)
        
        if dest_type == "impassable":
            return False, f"Cannot move to impassable province {order.destination}"
        
        if not unit.can_occupy(dest_type, dest_coastal):
            return False, f"{unit.unit_type.value} cannot occupy {dest_type} province {order.destination}"
        
        return True, ""
    
    def _validate_support(self, order: Support, unit: Unit) -> Tuple[bool, str]:
        """Validate a support order."""
        # Check if supporting unit can reach the destination (if support move)
        if order.is_support_move:
            dest_type = self.state.get_province_type(order.destination)
            dest_coastal = self.state.is_coastal(order.destination)
            
            # Supporting unit must be able to move to destination (not actually move)
            if not self.state.are_adjacent(order.unit_location, order.destination):
                return False, f"Cannot support into {order.destination}: not adjacent to {order.unit_location}"
            
            if not unit.can_occupy(dest_type, dest_coastal):
                return False, f"{unit.unit_type.value} cannot support into {dest_type} province"
        
        else:
            # Support hold - must be adjacent to supported unit
            if not self.state.are_adjacent(order.unit_location, order.supported_location):
                return False, f"Cannot support hold at {order.supported_location}: not adjacent"
        
        return True, ""
    
    def _validate_convoy(self, order: Convoy, unit: Unit) -> Tuple[bool, str]:
        """Validate a convoy order."""
        # Must be a fleet
        if unit.unit_type != UnitType.FLEET:
            return False, "Only fleets can convoy"
        
        # Must be in a sea province
        prov_type = self.state.get_province_type(order.unit_location)
        if prov_type != "sea":
            return False, "Fleet must be in a sea province to convoy"
        
        # Check if army exists at the source
        army = self.state.get_unit(order.convoyed_army_location)
        if not army:
            return False, f"No army at {order.convoyed_army_location}"
        if army.unit_type != UnitType.ARMY:
            return False, f"Unit at {order.convoyed_army_location} is not an army"
        
        return True, ""
    
    # Order Submission
    
    def submit_orders(self, power: str, orders: List[Order]) -> List[Tuple[Order, bool, str]]:
        """
        Submit orders for a power.
        
        Args:
            power: The power submitting orders
            orders: List of orders
            
        Returns:
            List of (order, is_valid, error_message) tuples
        """
        results = []
        valid_orders = []
        
        for order in orders:
            is_valid, error = self.validate_order(order)
            results.append((order, is_valid, error))
            if is_valid:
                valid_orders.append(order)
        
        self.pending_orders[power] = valid_orders
        return results
    
    def get_valid_orders(self, power: str) -> List[dict]:
        """
        Get all valid orders a power can issue.
        
        Args:
            power: The power to get orders for
            
        Returns:
            List of valid order descriptions
        """
        valid_orders = []
        units = self.state.get_power_units(power)
        
        for unit in units:
            # Hold is always valid
            valid_orders.append({
                "type": "hold",
                "unit_location": unit.location,
                "description": f"{unit.location} HOLD"
            })
            
            # Find valid moves
            for adjacent in self.state.get_adjacent(unit.location):
                adj_type = self.state.get_province_type(adjacent)
                adj_coastal = self.state.is_coastal(adjacent)
                
                if adj_type != "impassable" and unit.can_occupy(adj_type, adj_coastal):
                    valid_orders.append({
                        "type": "move",
                        "unit_location": unit.location,
                        "destination": adjacent,
                        "description": f"{unit.location} -> {adjacent}"
                    })
            
            # Find valid supports
            for adjacent in self.state.get_adjacent(unit.location):
                # Support hold for any unit in adjacent province
                other_unit = self.state.get_unit(adjacent)
                if other_unit:
                    valid_orders.append({
                        "type": "support_hold",
                        "unit_location": unit.location,
                        "supported_location": adjacent,
                        "description": f"{unit.location} S {adjacent}"
                    })
                
                # Support moves into any province the supporting unit could reach
                for dest in self.state.get_adjacent(unit.location):
                    if dest != adjacent:
                        dest_type = self.state.get_province_type(dest)
                        dest_coastal = self.state.is_coastal(dest)
                        if dest_type != "impassable" and unit.can_occupy(dest_type, dest_coastal):
                            valid_orders.append({
                                "type": "support_move",
                                "unit_location": unit.location,
                                "supported_location": adjacent,
                                "destination": dest,
                                "description": f"{unit.location} S {adjacent} -> {dest}"
                            })
        
        return valid_orders
    
    # Order Resolution
    
    def resolve_turn(self) -> dict:
        """
        Resolve all orders for the current phase.
        
        Returns:
            Dictionary with resolution results
        """
        self.resolution_log = []
        
        if self.phase in (Phase.SPRING_MOVES, Phase.FALL_MOVES):
            results = self._resolve_movement_phase()
        elif self.phase in (Phase.SPRING_RETREATS, Phase.FALL_RETREATS):
            results = self._resolve_retreat_phase()
        elif self.phase == Phase.WINTER_BUILDS:
            results = self._resolve_build_phase()
        else:
            results = {"error": f"Unknown phase: {self.phase}"}
        
        # Update supply center ownership after fall moves
        if self.phase == Phase.FALL_MOVES:
            self.state.update_supply_center_ownership()
        
        # Advance phase
        self.state.advance_phase()
        self.state.skip_retreats_if_none()
        
        # Check for eliminations and victory
        self.state.check_elimination()
        winner = self.state.check_victory()
        if winner:
            results["winner"] = winner
        
        # Clear pending orders
        self.pending_orders = {}
        
        results["log"] = self.resolution_log
        return results
    
    def _resolve_movement_phase(self) -> dict:
        """Resolve a movement phase (Spring or Fall moves)."""
        # Collect all orders
        all_orders: List[Order] = []
        for power, orders in self.pending_orders.items():
            all_orders.extend(orders)
        
        # Units without orders hold by default
        units_with_orders = {o.unit_location for o in all_orders}
        for unit in self.state.units.values():
            if unit.location not in units_with_orders:
                all_orders.append(Hold(unit.location, unit.power))
        
        # Build order index by location
        order_by_location = {o.unit_location: o for o in all_orders}
        
        # Calculate strengths and resolve conflicts
        move_orders = [o for o in all_orders if isinstance(o, Move)]
        support_orders = [o for o in all_orders if isinstance(o, Support)]
        
        # Apply supports
        for support in support_orders:
            self._apply_support(support, order_by_location)
        
        # Group moves by destination
        moves_by_dest = defaultdict(list)
        for move in move_orders:
            moves_by_dest[move.destination].append(move)
        
        # Resolve each destination
        successful_moves = []
        for dest, moves in moves_by_dest.items():
            winner = self._resolve_destination(dest, moves, order_by_location)
            if winner:
                successful_moves.append(winner)
        
        # Execute successful moves
        for move in successful_moves:
            self.state.move_unit(move.unit_location, move.destination)
            move.result = OrderResult.SUCCEEDED
            self._log(f"{move} - SUCCEEDED")
        
        return {
            "phase": self.phase.value,
            "moves_attempted": len(move_orders),
            "moves_succeeded": len(successful_moves),
            "orders": [o.to_dict() for o in all_orders]
        }
    
    def _apply_support(self, support: Support, order_by_location: Dict[str, Order]):
        """Apply a support order to increase strength."""
        # Find the order being supported
        if support.is_support_hold:
            # Support hold - look for hold or unit at supported location
            supported = order_by_location.get(support.supported_location)
            if supported and isinstance(supported, Hold):
                supported.strength += 1
                self._log(f"{support} gives +1 strength to {supported}")
        else:
            # Support move - find move from supported location to destination
            supported = order_by_location.get(support.supported_location)
            if supported and isinstance(supported, Move):
                if supported.destination == support.destination:
                    supported.strength += 1
                    self._log(f"{support} gives +1 strength to {supported}")
    
    def _resolve_destination(self, dest: str, moves: List[Move], 
                            order_by_location: Dict[str, Order]) -> Optional[Move]:
        """
        Resolve competing moves to a destination.
        
        Returns the winning move order, or None if all bounce.
        """
        if len(moves) == 0:
            return None
        
        if len(moves) == 1:
            move = moves[0]
            # Check if destination is occupied by a unit not moving
            defender = self.state.get_unit(dest)
            if defender:
                defender_order = order_by_location.get(dest)
                if not isinstance(defender_order, Move):
                    # Compare strengths
                    defender_strength = defender_order.strength if defender_order else 1
                    if move.strength > defender_strength:
                        # Attacker wins, defender dislodged
                        defender.dislodged = True
                        self._find_retreat_options(defender)
                        self._log(f"{dest} dislodged by {move}")
                        return move
                    else:
                        # Attack fails
                        move.result = OrderResult.FAILED
                        self._log(f"{move} - FAILED (defender held)")
                        return None
                else:
                    # Defender is moving out - check if swap
                    if defender_order.destination == move.unit_location:
                        # Head-to-head battle
                        if move.strength > defender_order.strength:
                            defender.dislodged = True
                            self._find_retreat_options(defender)
                            return move
                        elif defender_order.strength > move.strength:
                            move.result = OrderResult.FAILED
                            return None
                        else:
                            # Equal strength - both bounce
                            move.result = OrderResult.BOUNCED
                            defender_order.result = OrderResult.BOUNCED
                            self._log(f"{move} and {defender_order} BOUNCED")
                            return None
                    else:
                        # Defender moving elsewhere - check if their move succeeds
                        # For simplicity, assume vacant if defender has valid move
                        return move
            else:
                # Destination is vacant
                return move
        
        # Multiple moves to same destination - find strongest
        max_strength = max(m.strength for m in moves)
        strongest = [m for m in moves if m.strength == max_strength]
        
        if len(strongest) > 1:
            # Tie - all bounce
            for m in moves:
                m.result = OrderResult.BOUNCED
            self._log(f"Multiple units bounced at {dest}")
            return None
        
        # Single strongest - check against defender
        winner = strongest[0]
        defender = self.state.get_unit(dest)
        if defender:
            defender_order = order_by_location.get(dest)
            defender_strength = defender_order.strength if defender_order else 1
            if winner.strength > defender_strength:
                defender.dislodged = True
                self._find_retreat_options(defender)
                for m in moves:
                    if m != winner:
                        m.result = OrderResult.BOUNCED
                return winner
            else:
                for m in moves:
                    m.result = OrderResult.BOUNCED
                return None
        
        for m in moves:
            if m != winner:
                m.result = OrderResult.BOUNCED
        return winner
    
    def _find_retreat_options(self, unit: Unit):
        """Find valid retreat options for a dislodged unit."""
        options = []
        for adjacent in self.state.get_adjacent(unit.location):
            adj_type = self.state.get_province_type(adjacent)
            adj_coastal = self.state.is_coastal(adjacent)
            
            # Can retreat if: not occupied, unit can enter, wasn't contested
            if (adjacent not in self.state.units and 
                adj_type != "impassable" and
                unit.can_occupy(adj_type, adj_coastal)):
                options.append(adjacent)
        
        unit.retreat_options = options
    
    def _resolve_retreat_phase(self) -> dict:
        """Resolve retreat phase."""
        # For now, units with no retreat options are destroyed
        retreated = []
        destroyed = []
        
        dislodged = [u for u in self.state.units.values() if u.dislodged]
        
        for unit in dislodged:
            if unit.retreat_options:
                # For now, auto-retreat to first option
                dest = unit.retreat_options[0]
                self.state.move_unit(unit.location, dest)
                unit.dislodged = False
                unit.retreat_options = []
                retreated.append(f"{unit} -> {dest}")
                self._log(f"{unit} retreated to {dest}")
            else:
                # Destroyed
                self.state.remove_unit(unit.location)
                destroyed.append(str(unit))
                self._log(f"{unit} destroyed (no retreat options)")
        
        return {
            "phase": self.phase.value,
            "retreated": retreated,
            "destroyed": destroyed
        }
    
    def _resolve_build_phase(self) -> dict:
        """Resolve winter build phase."""
        builds = []
        disbands = []
        
        for power in self.state.power_names:
            if power in self.state.eliminated_powers:
                continue
            
            sc_count = len(self.state.get_power_supply_centers(power))
            unit_count = len(self.state.get_power_units(power))
            diff = sc_count - unit_count
            
            if diff > 0:
                # Can build units
                home_centers = self.state.get_power_home_centers(power)
                vacant_homes = [hc for hc in home_centers 
                               if hc not in self.state.units and
                               self.state.supply_centers.get(hc) == power]
                
                for _ in range(min(diff, len(vacant_homes))):
                    if vacant_homes:
                        loc = vacant_homes.pop(0)
                        unit = Army(
                            unit_id=f"unit_{len(self.state.units)}",
                            power=power,
                            location=loc
                        )
                        self.state.add_unit(unit)
                        builds.append(f"{power} builds {unit} at {loc}")
                        self._log(f"{power} builds {unit} at {loc}")
            
            elif diff < 0:
                # Must disband units
                units = self.state.get_power_units(power)
                for _ in range(abs(diff)):
                    if units:
                        unit = units.pop()  # Remove last unit
                        self.state.remove_unit(unit.location)
                        disbands.append(f"{power} disbands {unit}")
                        self._log(f"{power} disbands {unit}")
        
        return {
            "phase": self.phase.value,
            "builds": builds,
            "disbands": disbands
        }
    
    def _log(self, message: str):
        """Add a message to the resolution log."""
        self.resolution_log.append(message)
    
    # Game Control
    
    def run_phase(self, orders_by_power: Dict[str, List[Order]]) -> dict:
        """
        Run a complete phase with submitted orders.
        
        Args:
            orders_by_power: Dictionary mapping power names to order lists
            
        Returns:
            Resolution results
        """
        for power, orders in orders_by_power.items():
            self.submit_orders(power, orders)
        
        return self.resolve_turn()
    
    def get_game_state_for_llm(self, power: str) -> dict:
        """
        Get a view of the game state suitable for an LLM player.
        
        Args:
            power: The power requesting the view
            
        Returns:
            Dictionary with game state visible to that power
        """
        return {
            "year": self.year,
            "phase": self.phase.value,
            "power": power,
            "your_units": [u.to_dict() for u in self.state.get_power_units(power)],
            "your_supply_centers": self.state.get_power_supply_centers(power),
            "all_units": [u.to_dict() for u in self.state.units.values()],
            "supply_centers": self.state.supply_centers,
            "valid_orders": self.get_valid_orders(power),
            "adjacency": dict(self.state.adjacency),
            "provinces": {fid: {
                "name": f.get("name", fid),
                "type": f.get("type"),
                "coastal": f.get("coastal", False)
            } for fid, f in self.state.faces.items()}
        }
