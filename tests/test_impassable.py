"""
Tests for impassable territory validation.

Ensures that units cannot move, support, convoy, or retreat into
impassable territories (e.g. 'Impassable Peaks').
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "map_gen" / "phases"))

from game.game_state import GameState, Season, Phase
from game.units import Unit, UnitType
from game.orders import (
    Order, OrderType, OrderResult, OrderParser,
    create_move_order, create_hold_order,
    create_support_move_order,
)
from game.validators import OrderValidator, build_adjacency_from_map


def _create_map_with_impassable():
    """Create minimal map data that includes an impassable territory."""
    return {
        "topology": {
            "vertices": {},
            "edges": {},
            "borders": {
                "b_L1_IMP": {
                    "left_face": "L1", "right_face": "IMP",
                    "type": "impassable", "faces": ["L1", "IMP"],
                    "edges": []
                },
                "b_L1_L2": {
                    "left_face": "L1", "right_face": "L2",
                    "type": "land", "faces": ["L1", "L2"],
                    "edges": []
                },
                "b_L2_IMP": {
                    "left_face": "L2", "right_face": "IMP",
                    "type": "impassable", "faces": ["L2", "IMP"],
                    "edges": []
                },
                "b_L2_SEA": {
                    "left_face": "L2", "right_face": "SEA",
                    "type": "coast", "faces": ["L2", "SEA"],
                    "edges": []
                },
            },
            "faces": {
                "L1": {
                    "type": "land", "coastal": False,
                    "name": "Lowlands", "center": [0.2, 0.5],
                    "borders": ["b_L1_IMP", "b_L1_L2"],
                },
                "L2": {
                    "type": "land", "coastal": True,
                    "name": "Coastville", "center": [0.5, 0.5],
                    "borders": ["b_L1_L2", "b_L2_IMP", "b_L2_SEA"],
                },
                "IMP": {
                    "type": "impassable", "coastal": False,
                    "name": "Impassable Peaks", "center": [0.8, 0.5],
                    "borders": ["b_L1_IMP", "b_L2_IMP"],
                },
                "SEA": {
                    "type": "sea", "coastal": False,
                    "name": "Open Sea", "center": [0.5, 0.9],
                    "borders": ["b_L2_SEA"],
                },
            },
        },
    }


def _make_state_and_validator(map_data, units_dict):
    """Build a GameState and OrderValidator from map data and unit dict."""
    state = GameState()
    state.map_data = map_data
    for loc, unit in units_dict.items():
        state.units[loc] = unit
    adjacency = build_adjacency_from_map(map_data)
    validator = OrderValidator(state, adjacency)
    return state, validator


class TestBuildAdjacencyFiltersImpassable:
    """Tests that build_adjacency_from_map excludes impassable territories."""

    def test_topology_path_excludes_impassable(self):
        """When adjacency is built from topology borders, impassable faces are excluded."""
        map_data = _create_map_with_impassable()
        adjacency = build_adjacency_from_map(map_data)

        # Impassable territory should NOT appear as a key
        assert "IMP" not in adjacency

        # Impassable territory should NOT appear as a neighbor of any territory
        for neighbors in adjacency.values():
            assert "IMP" not in neighbors

    def test_adjacency_key_path_excludes_impassable(self):
        """When map_data has a pre-built 'adjacency' key, impassable faces are filtered."""
        map_data = _create_map_with_impassable()
        # Simulate a pre-built adjacency that incorrectly includes the impassable
        map_data["adjacency"] = {
            "Lowlands": ["Coastville", "Impassable Peaks"],
            "Coastville": ["Lowlands", "Impassable Peaks", "Open Sea"],
            "Impassable Peaks": ["Lowlands", "Coastville"],
            "Open Sea": ["Coastville"],
        }
        adjacency = build_adjacency_from_map(map_data)

        # Impassable territory should NOT appear as a key (neither by name nor ID)
        for key in adjacency:
            face_data = map_data["topology"]["faces"].get(key, {})
            assert face_data.get("type") != "impassable", (
                f"Impassable territory {key} should not be in adjacency"
            )

        # Impassable territory should NOT appear as a neighbor
        for key, neighbors in adjacency.items():
            for n in neighbors:
                face_data = map_data["topology"]["faces"].get(n, {})
                assert face_data.get("type") != "impassable", (
                    f"Impassable neighbor {n} found for {key}"
                )


class TestMoveIntoImpassable:
    """Tests that move orders targeting impassable territories are rejected."""

    def test_army_move_to_impassable_rejected(self):
        """An army cannot move to an impassable territory."""
        map_data = _create_map_with_impassable()
        units = {"L1": Unit(UnitType.ARMY, "Power1", "L1")}
        _, validator = _make_state_and_validator(map_data, units)

        order = create_move_order("A", "L1", "IMP")
        result = validator.validate_order(order)

        assert result.result == OrderResult.INVALID_TARGET
        assert "impassable" in result.error_message.lower()

    def test_army_move_to_impassable_by_name_rejected(self):
        """An army cannot move to impassable even when using territory name."""
        map_data = _create_map_with_impassable()
        units = {"L1": Unit(UnitType.ARMY, "Power1", "L1")}
        _, validator = _make_state_and_validator(map_data, units)

        order = create_move_order("A", "L1", "Impassable Peaks")
        result = validator.validate_order(order)

        assert result.result == OrderResult.INVALID_TARGET
        assert "impassable" in result.error_message.lower()


class TestSupportIntoImpassable:
    """Tests that support orders targeting impassable territories are rejected."""

    def test_support_move_to_impassable_rejected(self):
        """Cannot support a move into an impassable territory."""
        map_data = _create_map_with_impassable()
        units = {
            "L1": Unit(UnitType.ARMY, "Power1", "L1"),
            "L2": Unit(UnitType.ARMY, "Power1", "L2"),
        }
        _, validator = _make_state_and_validator(map_data, units)

        order = create_support_move_order("A", "L2", "A", "L1", "IMP")
        result = validator.validate_order(order)

        assert result.result == OrderResult.INVALID_TARGET
        assert "impassable" in result.error_message.lower()


class TestRetreatIntoImpassable:
    """Tests that retreat orders targeting impassable territories are rejected."""

    def test_retreat_to_impassable_rejected(self):
        """A dislodged unit cannot retreat to an impassable territory."""
        map_data = _create_map_with_impassable()
        dislodged_unit = Unit(UnitType.ARMY, "Power1", "L1")
        dislodged_unit.dislodged = True
        units = {"L1": dislodged_unit}
        _, validator = _make_state_and_validator(map_data, units)

        order = Order(
            unit_type="A",
            location="L1",
            order_type=OrderType.RETREAT,
            target="IMP",
        )
        result = validator.validate_order(order)

        assert result.result == OrderResult.INVALID_TARGET
        assert "impassable" in result.error_message.lower()


class TestIsImpassableHelper:
    """Tests for the _is_impassable helper method."""

    def test_impassable_territory_detected(self):
        """_is_impassable returns True for impassable territories."""
        map_data = _create_map_with_impassable()
        units = {"L1": Unit(UnitType.ARMY, "Power1", "L1")}
        _, validator = _make_state_and_validator(map_data, units)

        assert validator._is_impassable("IMP") is True

    def test_land_territory_not_impassable(self):
        """_is_impassable returns False for land territories."""
        map_data = _create_map_with_impassable()
        units = {"L1": Unit(UnitType.ARMY, "Power1", "L1")}
        _, validator = _make_state_and_validator(map_data, units)

        assert validator._is_impassable("L1") is False

    def test_unknown_territory_not_impassable(self):
        """_is_impassable returns False for unknown territory IDs."""
        map_data = _create_map_with_impassable()
        units = {"L1": Unit(UnitType.ARMY, "Power1", "L1")}
        _, validator = _make_state_and_validator(map_data, units)

        assert validator._is_impassable("NONEXISTENT") is False


class TestNamingNoSwitzerland:
    """Ensure 'Switzerland' no longer appears in impassable name generation."""

    def test_impassable_name_not_switzerland(self):
        """The first impassable name should be 'Impassable Peaks', not 'Switzerland'."""
        from phase7_naming import RegionNamer

        namer = RegionNamer(seed=0)
        name = namer.generate_impassable_name()
        assert name == "Impassable Peaks"
        assert name != "Switzerland"


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestBuildAdjacencyFiltersImpassable,
        TestMoveIntoImpassable,
        TestSupportIntoImpassable,
        TestRetreatIntoImpassable,
        TestIsImpassableHelper,
        TestNamingNoSwitzerland,
    ]

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
