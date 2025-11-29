"""
Tests for the game module.
"""

import pytest
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from game.units import Unit, Army, Fleet, UnitType, create_unit
from game.orders import (
    Order, OrderType, OrderResult, Hold, Move, Support, Convoy,
    parse_order, create_order
)


class TestUnits:
    """Tests for unit classes."""
    
    def test_army_creation(self):
        """Test creating an army."""
        army = Army("unit_1", "Power1", "C23")
        assert army.unit_type == UnitType.ARMY
        assert army.power == "Power1"
        assert army.location == "C23"
        assert not army.dislodged
    
    def test_fleet_creation(self):
        """Test creating a fleet."""
        fleet = Fleet("unit_2", "Power2", "C10", coast="nc")
        assert fleet.unit_type == UnitType.FLEET
        assert fleet.power == "Power2"
        assert fleet.location == "C10"
        assert fleet.coast == "nc"
    
    def test_army_can_occupy(self):
        """Test army movement restrictions."""
        army = Army("unit_1", "Power1", "C23")
        
        # Army can occupy land
        assert army.can_occupy("land", is_coastal=False)
        assert army.can_occupy("land", is_coastal=True)
        
        # Army cannot occupy sea
        assert not army.can_occupy("sea")
        
        # Army cannot occupy impassable
        assert not army.can_occupy("impassable")
    
    def test_fleet_can_occupy(self):
        """Test fleet movement restrictions."""
        fleet = Fleet("unit_1", "Power1", "C10")
        
        # Fleet can occupy sea
        assert fleet.can_occupy("sea")
        
        # Fleet can occupy coastal land
        assert fleet.can_occupy("land", is_coastal=True)
        
        # Fleet cannot occupy inland land
        assert not fleet.can_occupy("land", is_coastal=False)
        
        # Fleet cannot occupy impassable
        assert not fleet.can_occupy("impassable")
    
    def test_unit_serialization(self):
        """Test unit to_dict and from_dict."""
        army = Army("unit_1", "Power1", "C23")
        army.dislodged = True
        army.retreat_options = ["C24", "C25"]
        
        data = army.to_dict()
        assert data["type"] == "army"
        assert data["power"] == "Power1"
        assert data["dislodged"] == True
        
        # Reconstruct
        restored = Unit.from_dict(data)
        assert restored.unit_type == UnitType.ARMY
        assert restored.dislodged == True
        assert restored.retreat_options == ["C24", "C25"]
    
    def test_create_unit_factory(self):
        """Test the create_unit factory function."""
        army = create_unit("army", "unit_1", "Power1", "C23")
        assert isinstance(army, Army)
        
        fleet = create_unit("fleet", "unit_2", "Power2", "C10", coast="sc")
        assert isinstance(fleet, Fleet)
        assert fleet.coast == "sc"
        
        with pytest.raises(ValueError):
            create_unit("tank", "unit_3", "Power1", "C23")


class TestOrders:
    """Tests for order classes."""
    
    def test_hold_order(self):
        """Test hold order creation."""
        hold = Hold("C23", "Power1")
        assert hold.order_type == OrderType.HOLD
        assert hold.unit_location == "C23"
        assert hold.power == "Power1"
        assert hold.result == OrderResult.PENDING
    
    def test_move_order(self):
        """Test move order creation."""
        move = Move("C23", "Power1", "C24")
        assert move.order_type == OrderType.MOVE
        assert move.destination == "C24"
        assert not move.via_convoy
    
    def test_support_hold_order(self):
        """Test support hold order."""
        support = Support("C23", "Power1", "C24")
        assert support.order_type == OrderType.SUPPORT
        assert support.is_support_hold
        assert not support.is_support_move
    
    def test_support_move_order(self):
        """Test support move order."""
        support = Support("C23", "Power1", "C24", "C25")
        assert support.order_type == OrderType.SUPPORT
        assert support.is_support_move
        assert not support.is_support_hold
        assert support.destination == "C25"
    
    def test_convoy_order(self):
        """Test convoy order creation."""
        convoy = Convoy("NorthSea", "Power1", "London", "Norway")
        assert convoy.order_type == OrderType.CONVOY
        assert convoy.convoyed_army_location == "London"
        assert convoy.destination == "Norway"
    
    def test_parse_hold_order(self):
        """Test parsing hold orders."""
        order = parse_order("C23 HOLD", "Power1")
        assert isinstance(order, Hold)
        assert order.unit_location == "C23"
        
        order = parse_order("C23 H", "Power1")
        assert isinstance(order, Hold)
    
    def test_parse_move_order(self):
        """Test parsing move orders."""
        order = parse_order("C23 -> C24", "Power1")
        assert isinstance(order, Move)
        assert order.destination == "C24"
        
        order = parse_order("C23 M C24", "Power1")
        assert isinstance(order, Move)
    
    def test_parse_support_order(self):
        """Test parsing support orders."""
        # Support hold
        order = parse_order("C23 S C24", "Power1")
        assert isinstance(order, Support)
        assert order.is_support_hold
        
        # Support move
        order = parse_order("C23 S C24 -> C25", "Power1")
        assert isinstance(order, Support)
        assert order.is_support_move
        assert order.destination == "C25"
    
    def test_parse_convoy_order(self):
        """Test parsing convoy orders."""
        order = parse_order("NorthSea C London -> Norway", "Power1")
        assert isinstance(order, Convoy)
        assert order.convoyed_army_location == "LONDON"
        assert order.destination == "NORWAY"
    
    def test_create_order_factory(self):
        """Test create_order factory function."""
        hold = create_order("hold", "C23", "Power1")
        assert isinstance(hold, Hold)
        
        move = create_order("move", "C23", "Power1", destination="C24")
        assert isinstance(move, Move)
        
        support = create_order("support", "C23", "Power1", 
                              supported_location="C24", destination="C25")
        assert isinstance(support, Support)
        
        with pytest.raises(ValueError):
            create_order("move", "C23", "Power1")  # Missing destination


class TestOrderSerialization:
    """Tests for order serialization."""
    
    def test_hold_to_dict(self):
        """Test hold order serialization."""
        hold = Hold("C23", "Power1")
        data = hold.to_dict()
        assert data["order_type"] == "hold"
        assert data["unit_location"] == "C23"
    
    def test_move_to_dict(self):
        """Test move order serialization."""
        move = Move("C23", "Power1", "C24", destination_coast="nc")
        move.via_convoy = True
        data = move.to_dict()
        assert data["destination"] == "C24"
        assert data["destination_coast"] == "nc"
        assert data["via_convoy"] == True
    
    def test_support_to_dict(self):
        """Test support order serialization."""
        support = Support("C23", "Power1", "C24", "C25")
        data = support.to_dict()
        assert data["supported_location"] == "C24"
        assert data["destination"] == "C25"
    
    def test_convoy_to_dict(self):
        """Test convoy order serialization."""
        convoy = Convoy("NorthSea", "Power1", "London", "Norway")
        data = convoy.to_dict()
        assert data["convoyed_army_location"] == "London"
        assert data["destination"] == "Norway"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
