"""
Tests for the game module.

Tests the core game functionality including:
- GameState initialization
- Unit creation
- GameManager initialization and export
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager, GameState, Unit, UnitType
from game.game_state import Season, Phase
from game.orders import Order, OrderType, OrderResult


class TestUnit:
    """Tests for the Unit class."""
    
    def test_unit_creation(self):
        """Test creating a unit."""
        unit = Unit(UnitType.ARMY, "Power1", "C1")
        assert unit.unit_type == UnitType.ARMY
        assert unit.power == "Power1"
        assert unit.location == "C1"
        assert unit.dislodged is False
    
    def test_unit_from_string_type(self):
        """Test creating a unit with string type."""
        unit = Unit("army", "Power1", "C1")
        assert unit.unit_type == UnitType.ARMY
    
    def test_unit_to_dict(self):
        """Test unit serialization."""
        unit = Unit(UnitType.FLEET, "Power2", "C5")
        d = unit.to_dict()
        assert d["type"] == "fleet"
        assert d["power"] == "Power2"
        assert d["location"] == "C5"
        assert d["dislodged"] is False
    
    def test_unit_from_dict(self):
        """Test unit deserialization."""
        data = {"type": "army", "power": "Power3", "location": "C10", "dislodged": True}
        unit = Unit.from_dict(data)
        assert unit.unit_type == UnitType.ARMY
        assert unit.power == "Power3"
        assert unit.location == "C10"
        assert unit.dislodged is True
    
    def test_unit_str(self):
        """Test unit string representation."""
        army = Unit(UnitType.ARMY, "Power1", "C1")
        assert str(army) == "A C1 (Power1)"
        
        fleet = Unit(UnitType.FLEET, "Power2", "C2")
        assert str(fleet) == "F C2 (Power2)"


class TestGameState:
    """Tests for the GameState class."""
    
    def test_initial_state(self):
        """Test default game state initialization."""
        state = GameState()
        assert state.turn == 1
        assert state.year == 1901
        assert state.season == Season.SPRING
        assert state.phase == Phase.ORDER
        assert len(state.units) == 0
        assert len(state.powers) == 0
    
    def test_get_turn_string(self):
        """Test turn string generation."""
        state = GameState(year=1901, season=Season.SPRING)
        assert state.get_turn_string() == "Spring 1901"
        
        state.season = Season.FALL
        assert state.get_turn_string() == "Fall 1901"
    
    def test_advance_phase_spring(self):
        """Test advancing from spring order to spring retreat."""
        state = GameState(season=Season.SPRING, phase=Phase.ORDER)
        state.advance_phase()
        assert state.season == Season.SPRING
        assert state.phase == Phase.RETREAT
    
    def test_advance_phase_spring_to_fall(self):
        """Test advancing from spring retreat to fall order."""
        state = GameState(season=Season.SPRING, phase=Phase.RETREAT)
        state.advance_phase()
        assert state.season == Season.FALL
        assert state.phase == Phase.ORDER
    
    def test_advance_phase_to_winter(self):
        """Test advancing to winter build phase."""
        state = GameState(season=Season.FALL, phase=Phase.RETREAT)
        state.advance_phase()
        assert state.season == Season.WINTER
        assert state.phase == Phase.BUILD
    
    def test_advance_phase_new_year(self):
        """Test advancing from winter to next year's spring."""
        state = GameState(turn=1, year=1901, season=Season.WINTER, phase=Phase.BUILD)
        state.advance_phase()
        assert state.turn == 2
        assert state.year == 1902
        assert state.season == Season.SPRING
        assert state.phase == Phase.ORDER
    
    def test_unit_operations(self):
        """Test unit counting operations."""
        state = GameState(powers={"Power1", "Power2"})
        state.units = {
            "C1": Unit(UnitType.ARMY, "Power1", "C1"),
            "C2": Unit(UnitType.FLEET, "Power1", "C2"),
            "C3": Unit(UnitType.ARMY, "Power2", "C3"),
        }
        
        assert state.get_unit_count("Power1") == 2
        assert state.get_unit_count("Power2") == 1
        assert state.get_unit_count("Power3") == 0
        
        p1_units = state.get_units_for_power("Power1")
        assert len(p1_units) == 2
    
    def test_sc_operations(self):
        """Test supply center operations."""
        state = GameState(powers={"Power1", "Power2"})
        state.sc_control = {
            "C1": "Power1",
            "C2": "Power1",
            "C3": "Power1",
            "C4": "Power2",
        }
        
        assert state.get_sc_count("Power1") == 3
        assert state.get_sc_count("Power2") == 1
        assert state.is_eliminated("Power3") is True
        assert state.is_eliminated("Power1") is False
    
    def test_victory_check(self):
        """Test victory condition check."""
        state = GameState()
        state.sc_control = {f"C{i}": "Power1" for i in range(18)}
        assert state.has_won("Power1") is True
        assert state.has_won("Power1", victory_threshold=20) is False
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        state = GameState(
            turn=2,
            year=1902,
            season=Season.FALL,
            phase=Phase.RETREAT,
            powers={"Power1", "Power2"}
        )
        state.units = {"C1": Unit(UnitType.ARMY, "Power1", "C1")}
        state.sc_control = {"C1": "Power1"}
        
        d = state.to_dict()
        restored = GameState.from_dict(d)
        
        assert restored.turn == 2
        assert restored.year == 1902
        assert restored.season == Season.FALL
        assert restored.phase == Phase.RETREAT
        assert "Power1" in restored.powers
        assert "C1" in restored.units
        assert restored.units["C1"].power == "Power1"


class TestGameManager:
    """Tests for the GameManager class."""
    
    @staticmethod
    def _create_minimal_map_data():
        """Create minimal map data for testing."""
        return {
            "powers": {
                "Power1": {"name": "Power1", "home_centers": ["C1", "C2"]},
                "Power2": {"name": "Power2", "home_centers": ["C3", "C4"]},
            },
            "supply_centers": {
                "home": [
                    {"cell_id": "C1", "owner": "Power1", "coastal": True},
                    {"cell_id": "C2", "owner": "Power1", "coastal": False},
                    {"cell_id": "C3", "owner": "Power2", "coastal": True},
                    {"cell_id": "C4", "owner": "Power2", "coastal": False},
                ],
                "neutral": [
                    {"cell_id": "C5", "coastal": True},
                ]
            },
            "topology": {
                "vertices": [
                    {"id": "v1", "coords": [0, 0]},
                    {"id": "v2", "coords": [1, 0]},
                    {"id": "v3", "coords": [1, 1]},
                    {"id": "v4", "coords": [0, 1]},
                ],
                "edges": {
                    "e1": {"v1": "v1", "v2": "v2"},
                    "e2": {"v1": "v2", "v2": "v3"},
                    "e3": {"v1": "v3", "v2": "v4"},
                    "e4": {"v1": "v4", "v2": "v1"},
                },
                "borders": {
                    "b1": {"edges": ["e1", "e2", "e3", "e4"]},
                },
                "faces": {
                    "C1": {"type": "land", "coastal": True, "owner": "Power1", 
                           "is_supply_center": True, "center": [0.5, 0.5], "borders": ["b1"],
                           "name": "Province1"},
                    "C2": {"type": "land", "coastal": False, "owner": "Power1",
                           "is_supply_center": True, "center": [0.5, 0.5], "borders": ["b1"],
                           "name": "Province2"},
                    "C3": {"type": "land", "coastal": True, "owner": "Power2",
                           "is_supply_center": True, "center": [0.5, 0.5], "borders": ["b1"],
                           "name": "Province3"},
                    "C4": {"type": "land", "coastal": False, "owner": "Power2",
                           "is_supply_center": True, "center": [0.5, 0.5], "borders": ["b1"],
                           "name": "Province4"},
                    "C5": {"type": "land", "coastal": True, "is_supply_center": True,
                           "center": [0.5, 0.5], "borders": ["b1"], "name": "Neutral1"},
                    "Sea1": {"type": "sea", "center": [0.5, 0.5], "borders": ["b1"],
                             "name": "Sea Zone"},
                }
            }
        }
    
    def test_init_with_map_data(self):
        """Test initializing GameManager with map data dictionary."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        assert gm.map_data == map_data
        assert gm.state is None
    
    def test_init_requires_map(self):
        """Test that GameManager requires map data."""
        import pytest
        with pytest.raises(ValueError) as exc_info:
            GameManager()
        assert "map_path or map_data" in str(exc_info.value)
    
    def test_initialize_game(self):
        """Test game initialization."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        state = gm.initialize_game()
        
        assert state is not None
        assert state.turn == 1
        assert state.year == 1901
        assert state.season == Season.SPRING
        assert state.phase == Phase.ORDER
        assert "Power1" in state.powers
        assert "Power2" in state.powers
    
    def test_initial_units_placed(self):
        """Test that initial units are placed at home supply centers."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        state = gm.initialize_game()
        
        # Should have 4 units (one per home SC)
        assert len(state.units) == 4
        
        # Each power should have 2 units
        assert state.get_unit_count("Power1") == 2
        assert state.get_unit_count("Power2") == 2
    
    def test_export_json(self):
        """Test JSON export."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name
        
        try:
            result_path = gm.export_game_state_json(output_path)
            assert os.path.exists(result_path)
            
            with open(result_path, 'r') as f:
                data = json.load(f)
            
            assert "game_state" in data
            assert "map_data" in data
            assert data["game_state"]["year"] == 1901
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_get_game_state(self):
        """Test getting game state as dictionary."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()
        
        state_dict = gm.get_game_state()
        assert "game_state" in state_dict
        assert "map_info" in state_dict
        assert state_dict["game_state"]["year"] == 1901
    
    def test_get_province_info(self):
        """Test getting province information."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()
        
        info = gm.get_province_info("C1")
        assert info is not None
        assert info["id"] == "C1"
        assert info["type"] == "land"
        assert info["coastal"] is True
        assert info["owner"] == "Power1"
    
    def test_get_all_units(self):
        """Test getting all units."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()
        
        units = gm.get_all_units()
        assert len(units) == 4
        assert all("type" in u for u in units)
        assert all("power" in u for u in units)
        assert all("location" in u for u in units)


class TestWinterAdjustments:
    """Tests for winter adjustment phase (builds and disbands)."""

    @staticmethod
    def _create_minimal_map_data():
        """Create minimal map data for testing winter adjustments."""
        return {
            "powers": {
                "Power1": {"name": "Power1", "home_centers": ["C1", "C2"]},
                "Power2": {"name": "Power2", "home_centers": ["C3", "C4"]},
            },
            "supply_centers": {
                "home": [
                    {"cell_id": "C1", "owner": "Power1", "coastal": True},
                    {"cell_id": "C2", "owner": "Power1", "coastal": False},
                    {"cell_id": "C3", "owner": "Power2", "coastal": True},
                    {"cell_id": "C4", "owner": "Power2", "coastal": False},
                ],
                "neutral": [
                    {"cell_id": "C5", "coastal": True},
                ]
            },
            "topology": {
                "vertices": [
                    {"id": "v1", "coords": [0, 0]},
                    {"id": "v2", "coords": [1, 0]},
                    {"id": "v3", "coords": [1, 1]},
                    {"id": "v4", "coords": [0, 1]},
                ],
                "edges": {
                    "e1": {"v1": "v1", "v2": "v2"},
                    "e2": {"v1": "v2", "v2": "v3"},
                    "e3": {"v1": "v3", "v2": "v4"},
                    "e4": {"v1": "v4", "v2": "v1"},
                },
                "borders": {
                    "b1": {"edges": ["e1", "e2", "e3", "e4"]},
                },
                "faces": {
                    "C1": {"type": "land", "coastal": True, "owner": "Power1",
                           "is_supply_center": True, "center": [0.5, 0.5],
                           "borders": ["b1"], "name": "Province1"},
                    "C2": {"type": "land", "coastal": False, "owner": "Power1",
                           "is_supply_center": True, "center": [0.5, 0.5],
                           "borders": ["b1"], "name": "Province2"},
                    "C3": {"type": "land", "coastal": True, "owner": "Power2",
                           "is_supply_center": True, "center": [0.5, 0.5],
                           "borders": ["b1"], "name": "Province3"},
                    "C4": {"type": "land", "coastal": False, "owner": "Power2",
                           "is_supply_center": True, "center": [0.5, 0.5],
                           "borders": ["b1"], "name": "Province4"},
                    "C5": {"type": "land", "coastal": True,
                           "is_supply_center": True, "center": [0.5, 0.5],
                           "borders": ["b1"], "name": "Neutral1"},
                    "Sea1": {"type": "sea", "center": [0.5, 0.5],
                             "borders": ["b1"], "name": "Sea Zone"},
                }
            }
        }

    def _setup_game_for_winter(self, sc_control, units):
        """Helper to set up a game manager in winter BUILD phase."""
        map_data = self._create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()
        # Override SC control and units for test scenario
        gm.state.sc_control = dict(sc_control)
        gm.state.units = dict(units)
        gm.state.season = Season.WINTER
        gm.state.phase = Phase.BUILD
        return gm

    def test_build_with_more_scs_than_units(self):
        """Power with more SCs than units can build at unoccupied home SC."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C2": "Power1", "C3": "Power2"},
            units={
                "C1": Unit(UnitType.ARMY, "Power1", "C1"),
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
            },
        )
        # Power1 has 2 SCs, 1 unit -> can build 1
        build_orders = {
            "Power1": [
                Order(unit_type="A", location="C2",
                      order_type=OrderType.BUILD, power="Power1"),
            ],
        }
        log = gm.process_winter_adjustments(build_orders)
        assert "BUILD A at C2" in log
        # Unit should now exist at C2
        assert gm.state.get_unit_at("C2") is not None
        assert gm.state.get_unit_at("C2").power == "Power1"
        assert gm.state.get_unit_count("Power1") == 2

    def test_disband_with_more_units_than_scs(self):
        """Power with more units than SCs must disband."""
        gm = self._setup_game_for_winter(
            sc_control={"C3": "Power2"},
            units={
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
                "C4": Unit(UnitType.ARMY, "Power2", "C4"),
            },
        )
        # Power2 has 1 SC, 2 units -> must disband 1
        disband_orders = {
            "Power2": [
                Order(unit_type="A", location="C4",
                      order_type=OrderType.DISBAND, power="Power2"),
            ],
        }
        log = gm.process_winter_adjustments(disband_orders)
        assert "DISBAND A at C4" in log
        assert gm.state.get_unit_at("C4") is None
        assert gm.state.get_unit_count("Power2") == 1

    def test_build_rejected_at_occupied_home_sc(self):
        """Build at an occupied home SC should be rejected."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C2": "Power1"},
            units={
                "C2": Unit(UnitType.ARMY, "Power1", "C2"),
            },
        )
        # Power1 has 2 SCs, 1 unit -> can build 1, but C2 is occupied
        build_orders = {
            "Power1": [
                Order(unit_type="A", location="C2",
                      order_type=OrderType.BUILD, power="Power1"),
            ],
        }
        log = gm.process_winter_adjustments(build_orders)
        assert "REJECTED" in log
        assert "occupied" in log
        # Still only 1 unit
        assert gm.state.get_unit_count("Power1") == 1

    def test_build_rejected_at_non_home_sc(self):
        """Build at a non-home SC should be rejected."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C5": "Power1"},
            units={
                "C1": Unit(UnitType.ARMY, "Power1", "C1"),
            },
        )
        # Power1 has 2 SCs, 1 unit -> can build 1
        # C5 is a neutral SC (not a home SC for Power1)
        build_orders = {
            "Power1": [
                Order(unit_type="A", location="C5",
                      order_type=OrderType.BUILD, power="Power1"),
            ],
        }
        log = gm.process_winter_adjustments(build_orders)
        assert "REJECTED" in log
        assert "not a home supply center" in log
        assert gm.state.get_unit_count("Power1") == 1

    def test_no_adjustment_when_equal(self):
        """Power with equal SCs and units needs no adjustment."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C3": "Power2"},
            units={
                "C1": Unit(UnitType.ARMY, "Power1", "C1"),
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
            },
        )
        log = gm.process_winter_adjustments({})
        assert "no adjustment needed" in log
        assert gm.state.get_unit_count("Power1") == 1
        assert gm.state.get_unit_count("Power2") == 1

    def test_write_winter_order_files_builds(self):
        """Test writing winter order files when builds are available."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C2": "Power1", "C3": "Power2"},
            units={
                "C1": Unit(UnitType.ARMY, "Power1", "C1"),
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
            },
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            files = gm.write_winter_order_files(tmpdir)
            assert "Power1" in files
            with open(files["Power1"], 'r') as f:
                content = f.read()
            assert "BUILD 1 unit(s)" in content
            assert "(available)" in content

    def test_write_winter_order_files_disbands(self):
        """Test writing winter order files when disbands are required."""
        gm = self._setup_game_for_winter(
            sc_control={"C3": "Power2"},
            units={
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
                "C4": Unit(UnitType.ARMY, "Power2", "C4"),
            },
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            files = gm.write_winter_order_files(tmpdir)
            assert "Power2" in files
            with open(files["Power2"], 'r') as f:
                content = f.read()
            assert "DISBAND 1 unit(s)" in content

    def test_read_winter_order_files_build(self):
        """Test reading winter order files with build orders."""
        gm = self._setup_game_for_winter(
            sc_control={"C1": "Power1", "C2": "Power1"},
            units={
                "C1": Unit(UnitType.ARMY, "Power1", "C1"),
            },
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "Power1_winter_orders.txt")
            with open(filepath, 'w') as f:
                f.write("# Winter Orders for Power1\n")
                f.write("B A {Province2}\n")
            order_files = {"Power1": filepath}
            orders = gm.read_winter_order_files(order_files)
            assert len(orders["Power1"]) == 1
            order = orders["Power1"][0]
            assert order.order_type == OrderType.BUILD
            assert order.unit_type == "A"
            assert order.location == "C2"  # resolved from name
            assert order.power == "Power1"

    def test_read_winter_order_files_disband(self):
        """Test reading winter order files with disband orders."""
        gm = self._setup_game_for_winter(
            sc_control={"C3": "Power2"},
            units={
                "C3": Unit(UnitType.ARMY, "Power2", "C3"),
                "C4": Unit(UnitType.ARMY, "Power2", "C4"),
            },
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "Power2_winter_orders.txt")
            with open(filepath, 'w') as f:
                f.write("# Winter Orders for Power2\n")
                f.write("A {Province4} D\n")
            order_files = {"Power2": filepath}
            orders = gm.read_winter_order_files(order_files)
            assert len(orders["Power2"]) == 1
            order = orders["Power2"][0]
            assert order.order_type == OrderType.DISBAND
            assert order.location == "C4"  # resolved from name
            assert order.power == "Power2"


def run_tests():
    """Run all tests and report results."""
    test_classes = [TestUnit, TestGameState, TestGameManager, TestWinterAdjustments]
    
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
