"""
Tests for the LLM adapter interface and mock implementation.

Tests the base adapter abstraction and the MockLLMAdapter's
deterministic order generation and message generation.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.adapters.base import BaseLLMAdapter
from llm.adapters.mock_adapter import MockLLMAdapter


def _make_game_state_dict(units: dict) -> dict:
    """Helper to build a minimal game_state_dict for testing."""
    return {
        "game_state": {
            "units": units,
            "turn": 1,
            "year": 1901,
            "season": "spring",
            "phase": "order",
        }
    }


class TestBaseLLMAdapter:
    """Tests for the abstract BaseLLMAdapter."""

    def test_cannot_instantiate_directly(self):
        """BaseLLMAdapter cannot be instantiated because it has abstract methods."""
        try:
            BaseLLMAdapter()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass


class TestMockLLMAdapterOrders:
    """Tests for MockLLMAdapter.generate_orders."""

    def test_returns_hold_orders_for_power(self):
        """generate_orders returns one hold order per unit of the given power."""
        units = {
            "C1": {"type": "army", "power": "Avalon", "location": "C1", "dislodged": False},
            "C2": {"type": "fleet", "power": "Avalon", "location": "C2", "dislodged": False},
            "C3": {"type": "army", "power": "Borealis", "location": "C3", "dislodged": False},
        }
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(_make_game_state_dict(units), "Avalon")
        assert len(orders) == 2
        assert "A C1 H" in orders
        assert "F C2 H" in orders

    def test_army_prefix(self):
        """Army units get 'A' prefix."""
        units = {"C5": {"type": "army", "power": "P1", "location": "C5", "dislodged": False}}
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(_make_game_state_dict(units), "P1")
        assert orders == ["A C5 H"]

    def test_fleet_prefix(self):
        """Fleet units get 'F' prefix."""
        units = {"C9": {"type": "fleet", "power": "P1", "location": "C9", "dislodged": False}}
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(_make_game_state_dict(units), "P1")
        assert orders == ["F C9 H"]

    def test_no_units_for_power(self):
        """Returns empty list when the power has no units."""
        units = {"C1": {"type": "army", "power": "Other", "location": "C1", "dislodged": False}}
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(_make_game_state_dict(units), "Avalon")
        assert orders == []

    def test_empty_units(self):
        """Returns empty list when there are no units at all."""
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(_make_game_state_dict({}), "Avalon")
        assert orders == []

    def test_board_image_path_accepted(self):
        """board_image_path parameter is accepted without error."""
        units = {"C1": {"type": "army", "power": "P1", "location": "C1", "dislodged": False}}
        adapter = MockLLMAdapter()
        orders = adapter.generate_orders(
            _make_game_state_dict(units), "P1", board_image_path="/tmp/board.jpg"
        )
        assert orders == ["A C1 H"]


class TestMockLLMAdapterDiplomacy:
    """Tests for MockLLMAdapter.generate_diplomacy_message."""

    def test_returns_non_empty_string(self):
        """generate_diplomacy_message returns a non-empty string."""
        adapter = MockLLMAdapter()
        msg = adapter.generate_diplomacy_message(
            _make_game_state_dict({}), "Avalon", "Borealis"
        )
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_returns_placeholder_message(self):
        """generate_diplomacy_message returns the expected placeholder text."""
        adapter = MockLLMAdapter()
        msg = adapter.generate_diplomacy_message(
            _make_game_state_dict({}), "Avalon", "Borealis"
        )
        assert msg == "I propose we work together this turn."
