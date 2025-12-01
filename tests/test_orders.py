"""
Tests for the orders module.

Tests for:
- Order parsing
- Order validation
- Order resolution
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.orders import (
    Order, OrderType, OrderResult, OrderParser,
    create_hold_order, create_move_order, create_support_hold_order,
    create_support_move_order, create_convoy_order
)


class TestOrderParser:
    """Tests for the OrderParser class."""
    
    def test_parse_hold_order(self):
        """Test parsing a hold order."""
        order = OrderParser.parse("A {Karwyn} H")
        assert order.unit_type == 'A'
        assert order.location == 'Karwyn'
        assert order.order_type == OrderType.HOLD
        assert order.result == OrderResult.PENDING
    
    def test_parse_fleet_hold(self):
        """Test parsing a fleet hold order."""
        order = OrderParser.parse("F {Dark Narrows} H")
        assert order.unit_type == 'F'
        assert order.location == 'Dark Narrows'
        assert order.order_type == OrderType.HOLD
    
    def test_parse_move_order(self):
        """Test parsing a move order."""
        order = OrderParser.parse("A {Karwyn} M {Falmere}")
        assert order.unit_type == 'A'
        assert order.location == 'Karwyn'
        assert order.order_type == OrderType.MOVE
        assert order.target == 'Falmere'
    
    def test_parse_support_move_order(self):
        """Test parsing a support move order."""
        order = OrderParser.parse("A {Harell} S A {Karwyn} M {Falmere}")
        assert order.unit_type == 'A'
        assert order.location == 'Harell'
        assert order.order_type == OrderType.SUPPORT
        assert order.support_unit_type == 'A'
        assert order.support_from == 'Karwyn'
        assert order.support_to == 'Falmere'
    
    def test_parse_support_hold_order(self):
        """Test parsing a support hold order."""
        order = OrderParser.parse("A {Harell} S A {Karwyn} H")
        assert order.unit_type == 'A'
        assert order.location == 'Harell'
        assert order.order_type == OrderType.SUPPORT
        assert order.support_unit_type == 'A'
        assert order.support_from == 'Karwyn'
        assert order.support_to is None
    
    def test_parse_convoy_order(self):
        """Test parsing a convoy order."""
        order = OrderParser.parse("F {Narrow Passage} C A {Derpeak} M {Karwyn}")
        assert order.unit_type == 'F'
        assert order.location == 'Narrow Passage'
        assert order.order_type == OrderType.CONVOY
        assert order.support_unit_type == 'A'
        assert order.support_from == 'Derpeak'
        assert order.target == 'Karwyn'
    
    def test_parse_invalid_no_braces(self):
        """Test parsing order without braces."""
        order = OrderParser.parse("A Karwyn H")
        assert order.result == OrderResult.INVALID_FORMAT
    
    def test_parse_invalid_empty(self):
        """Test parsing empty order."""
        order = OrderParser.parse("")
        assert order.result == OrderResult.INVALID_FORMAT
    
    def test_parse_invalid_no_unit_type(self):
        """Test parsing order without unit type."""
        order = OrderParser.parse("{Karwyn} H")
        assert order.result == OrderResult.INVALID_FORMAT
    
    def test_parse_invalid_unknown_order_type(self):
        """Test parsing order with unknown order type."""
        order = OrderParser.parse("A {Karwyn} X")
        assert order.result == OrderResult.INVALID_FORMAT
    
    def test_parse_with_spaces_in_name(self):
        """Test parsing order with spaces in territory name."""
        order = OrderParser.parse("A {North Atlantic Ocean} M {Mid Atlantic Ocean}")
        assert order.location == 'North Atlantic Ocean'
        assert order.target == 'Mid Atlantic Ocean'
    
    def test_order_to_string(self):
        """Test order string representation."""
        order = create_hold_order('A', 'Paris')
        assert str(order) == "A {Paris} H"
        
        order = create_move_order('F', 'London', 'North Sea')
        assert str(order) == "F {London} M {North Sea}"
    
    def test_support_move_string(self):
        """Test support move order string representation."""
        order = create_support_move_order('A', 'Paris', 'A', 'Burgundy', 'Munich')
        assert str(order) == "A {Paris} S A {Burgundy} M {Munich}"
    
    def test_support_hold_string(self):
        """Test support hold order string representation."""
        order = create_support_hold_order('A', 'Paris', 'A', 'Burgundy')
        assert str(order) == "A {Paris} S A {Burgundy} H"


class TestOrderHelpers:
    """Tests for order creation helper functions."""
    
    def test_create_hold_order(self):
        """Test creating a hold order."""
        order = create_hold_order('A', 'Paris')
        assert order.unit_type == 'A'
        assert order.location == 'Paris'
        assert order.order_type == OrderType.HOLD
    
    def test_create_move_order(self):
        """Test creating a move order."""
        order = create_move_order('F', 'London', 'North Sea')
        assert order.unit_type == 'F'
        assert order.location == 'London'
        assert order.order_type == OrderType.MOVE
        assert order.target == 'North Sea'
    
    def test_create_convoy_order(self):
        """Test creating a convoy order."""
        order = create_convoy_order('North Sea', 'London', 'Norway')
        assert order.unit_type == 'F'
        assert order.location == 'North Sea'
        assert order.order_type == OrderType.CONVOY
        assert order.support_from == 'London'
        assert order.target == 'Norway'


class TestOrderSerialization:
    """Tests for order serialization."""
    
    def test_order_to_dict(self):
        """Test order serialization to dictionary."""
        order = create_move_order('A', 'Paris', 'Burgundy')
        order.power = 'France'
        d = order.to_dict()
        
        assert d['unit_type'] == 'A'
        assert d['location'] == 'Paris'
        assert d['order_type'] == 'move'
        assert d['target'] == 'Burgundy'
        assert d['power'] == 'France'


def run_tests():
    """Run all tests and report results."""
    test_classes = [TestOrderParser, TestOrderHelpers, TestOrderSerialization]
    
    total = 0
    passed = 0
    failed = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
