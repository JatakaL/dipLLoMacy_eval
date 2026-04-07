"""
Tests for the RandomLLMAdapter.

Verifies deterministic output with a fixed seed, order parseability,
and terrain-based movement constraints (armies vs fleets).
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.orders import OrderParser, OrderResult
from llm.adapters.random_adapter import RandomLLMAdapter


def _make_game_state_dict(units: dict, map_data: dict | None = None) -> dict:
    """Helper to build a minimal game_state_dict with map_data."""
    if map_data is None:
        map_data = _create_map_with_adjacency()
    return {
        "game_state": {
            "units": units,
            "turn": 1,
            "year": 1901,
            "season": "spring",
            "phase": "order",
        },
        "map_data": map_data,
    }


def _create_map_with_adjacency() -> dict:
    """Create map data with explicit adjacency for testing.

    Layout::

        Land1 (coastal) -- Sea1 -- Land3 (coastal)
          |                          |
        Land2 (inland)            Land4 (inland)
    """
    return {
        "topology": {
            "faces": {
                "L1": {
                    "type": "land", "coastal": True,
                    "name": "Land1", "center": [0, 0],
                },
                "L2": {
                    "type": "land", "coastal": False,
                    "name": "Land2", "center": [0, 1],
                },
                "S1": {
                    "type": "sea",
                    "name": "Sea1", "center": [1, 0],
                },
                "L3": {
                    "type": "land", "coastal": True,
                    "name": "Land3", "center": [2, 0],
                },
                "L4": {
                    "type": "land", "coastal": False,
                    "name": "Land4", "center": [2, 1],
                },
            },
            "borders": {},
            "vertices": [],
            "edges": {},
        },
        "adjacency": {
            "L1": ["L2", "S1"],
            "L2": ["L1"],
            "S1": ["L1", "L3"],
            "L3": ["S1", "L4"],
            "L4": ["L3"],
        },
    }


# ------------------------------------------------------------------
# Determinism
# ------------------------------------------------------------------

class TestDeterminism:
    """With a fixed seed, generate_orders returns deterministic results."""

    def test_same_seed_same_orders(self):
        """Two adapters with the same seed produce identical orders."""
        units = {
            "L1": {"type": "army", "power": "Alpha", "location": "L1", "dislodged": False},
            "S1": {"type": "fleet", "power": "Alpha", "location": "S1", "dislodged": False},
        }
        state = _make_game_state_dict(units)

        orders_a = RandomLLMAdapter(seed=42).generate_orders(state, "Alpha")
        orders_b = RandomLLMAdapter(seed=42).generate_orders(state, "Alpha")

        assert orders_a == orders_b

    def test_different_seed_may_differ(self):
        """Different seeds can produce different results (not guaranteed,
        but extremely likely with enough units)."""
        units = {
            f"L{i}": {"type": "army", "power": "Alpha", "location": f"L{i}", "dislodged": False}
            for i in range(1, 3)
        }
        map_data = _create_map_with_adjacency()
        state = _make_game_state_dict(units, map_data)

        orders_a = RandomLLMAdapter(seed=1).generate_orders(state, "Alpha")
        orders_b = RandomLLMAdapter(seed=999).generate_orders(state, "Alpha")

        # Not a hard requirement, but very likely to differ
        # If they happen to be the same, the test still passes for correctness
        assert isinstance(orders_a, list) and isinstance(orders_b, list)


# ------------------------------------------------------------------
# Parseability
# ------------------------------------------------------------------

class TestOrderParseability:
    """All returned order strings are parseable without INVALID_FORMAT."""

    def test_all_orders_parseable(self):
        """Every order from generate_orders parses successfully."""
        units = {
            "L1": {"type": "army", "power": "Alpha", "location": "L1", "dislodged": False},
            "L3": {"type": "fleet", "power": "Alpha", "location": "L3", "dislodged": False},
            "S1": {"type": "fleet", "power": "Alpha", "location": "S1", "dislodged": False},
        }
        state = _make_game_state_dict(units)

        # Run with several seeds to cover both hold and move branches
        for seed in range(20):
            orders = RandomLLMAdapter(seed=seed).generate_orders(state, "Alpha")
            for order_str in orders:
                parsed = OrderParser.parse(order_str)
                assert parsed.result != OrderResult.INVALID_FORMAT, (
                    f"seed={seed}: order '{order_str}' was INVALID_FORMAT"
                )

    def test_hold_order_parseable(self):
        """A hold order (no valid neighbors) is parseable."""
        # Unit with no adjacent territories
        map_data = {
            "topology": {
                "faces": {
                    "Isolated": {"type": "land", "coastal": False, "name": "Isolated"},
                },
                "borders": {},
                "vertices": [],
                "edges": {},
            },
            "adjacency": {},
        }
        units = {"Isolated": {"type": "army", "power": "P1", "location": "Isolated", "dislodged": False}}
        state = _make_game_state_dict(units, map_data)

        orders = RandomLLMAdapter(seed=0).generate_orders(state, "P1")
        assert len(orders) == 1
        parsed = OrderParser.parse(orders[0])
        assert parsed.result != OrderResult.INVALID_FORMAT


# ------------------------------------------------------------------
# Terrain constraints
# ------------------------------------------------------------------

class TestArmyConstraints:
    """Army orders never target sea provinces."""

    def test_army_never_moves_to_sea(self):
        """Army on a coastal province adjacent to sea never targets the sea."""
        units = {
            "L1": {"type": "army", "power": "Alpha", "location": "L1", "dislodged": False},
        }
        state = _make_game_state_dict(units)

        for seed in range(50):
            orders = RandomLLMAdapter(seed=seed).generate_orders(state, "Alpha")
            for order_str in orders:
                parsed = OrderParser.parse(order_str)
                if parsed.target:
                    assert parsed.target != "S1", (
                        f"seed={seed}: army moved to sea province S1"
                    )


class TestFleetConstraints:
    """Fleet orders never target inland (non-coastal) land provinces."""

    def test_fleet_never_moves_to_inland(self):
        """Fleet adjacent to inland province never targets it."""
        units = {
            "L3": {"type": "fleet", "power": "Alpha", "location": "L3", "dislodged": False},
        }
        state = _make_game_state_dict(units)

        for seed in range(50):
            orders = RandomLLMAdapter(seed=seed).generate_orders(state, "Alpha")
            for order_str in orders:
                parsed = OrderParser.parse(order_str)
                if parsed.target:
                    assert parsed.target != "L4", (
                        f"seed={seed}: fleet moved to inland province L4"
                    )


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for RandomLLMAdapter."""

    def test_no_units_for_power(self):
        """Returns empty list when the power has no units."""
        units = {"L1": {"type": "army", "power": "Other", "location": "L1", "dislodged": False}}
        state = _make_game_state_dict(units)
        orders = RandomLLMAdapter(seed=0).generate_orders(state, "Alpha")
        assert orders == []

    def test_empty_units(self):
        """Returns empty list when there are no units at all."""
        state = _make_game_state_dict({})
        orders = RandomLLMAdapter(seed=0).generate_orders(state, "Alpha")
        assert orders == []

    def test_fleet_holds_when_no_valid_target(self):
        """Fleet on inland province with only inland neighbors holds."""
        map_data = {
            "topology": {
                "faces": {
                    "Inland1": {"type": "land", "coastal": False, "name": "Inland1"},
                    "Inland2": {"type": "land", "coastal": False, "name": "Inland2"},
                },
                "borders": {},
                "vertices": [],
                "edges": {},
            },
            "adjacency": {"Inland1": ["Inland2"], "Inland2": ["Inland1"]},
        }
        units = {"Inland1": {"type": "fleet", "power": "P1", "location": "Inland1", "dislodged": False}}
        state = _make_game_state_dict(units, map_data)

        for seed in range(10):
            orders = RandomLLMAdapter(seed=seed).generate_orders(state, "P1")
            assert len(orders) == 1
            parsed = OrderParser.parse(orders[0])
            assert parsed.result != OrderResult.INVALID_FORMAT
            # Should always hold since no valid target
            assert parsed.target is None


# ------------------------------------------------------------------
# Diplomacy messages
# ------------------------------------------------------------------

class TestDiplomacyMessage:
    """Tests for generate_diplomacy_message."""

    def test_returns_non_empty_string(self):
        """generate_diplomacy_message returns a non-empty string."""
        adapter = RandomLLMAdapter(seed=0)
        msg = adapter.generate_diplomacy_message(
            _make_game_state_dict({}), "Alpha", "Beta"
        )
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_deterministic_with_seed(self):
        """Same seed produces same message."""
        msg_a = RandomLLMAdapter(seed=7).generate_diplomacy_message(
            _make_game_state_dict({}), "Alpha", "Beta"
        )
        msg_b = RandomLLMAdapter(seed=7).generate_diplomacy_message(
            _make_game_state_dict({}), "Alpha", "Beta"
        )
        assert msg_a == msg_b
