"""
Tests for the order_viewer module.

Verifies:
- Text turn-summary parsing into order dicts
- JSON turn-result loading
- Rendering produces an image file without errors
- Result color mapping
- Name-to-ID resolution
- Winter (build/disband) order parsing and rendering
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from order_viewer import (
    parse_turn_summary_text,
    load_orders,
    render_order_view,
    _result_color,
    _is_failed,
    _build_name_to_id_map,
    RESULT_COLORS,
)


# ------------------------------------------------------------------
# Shared fixtures
# ------------------------------------------------------------------

def _minimal_map_data():
    """Minimal map data with topology for rendering tests."""
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
            "neutral": [],
        },
        "topology": {
            "vertices": [
                {"id": "v1", "coords": [0.0, 0.0]},
                {"id": "v2", "coords": [0.2, 0.0]},
                {"id": "v3", "coords": [0.2, 0.2]},
                {"id": "v4", "coords": [0.0, 0.2]},
                {"id": "v5", "coords": [0.4, 0.0]},
                {"id": "v6", "coords": [0.4, 0.2]},
                {"id": "v7", "coords": [0.2, 0.4]},
                {"id": "v8", "coords": [0.0, 0.4]},
                {"id": "v9", "coords": [0.4, 0.4]},
            ],
            "edges": {
                "e1": {"v1": "v1", "v2": "v2"},
                "e2": {"v1": "v2", "v2": "v3"},
                "e3": {"v1": "v3", "v2": "v4"},
                "e4": {"v1": "v4", "v2": "v1"},
                "e5": {"v1": "v2", "v2": "v5"},
                "e6": {"v1": "v5", "v2": "v6"},
                "e7": {"v1": "v6", "v2": "v3"},
                "e8": {"v1": "v4", "v2": "v8"},
                "e9": {"v1": "v8", "v2": "v7"},
                "e10": {"v1": "v7", "v2": "v3"},
                "e11": {"v1": "v6", "v2": "v9"},
                "e12": {"v1": "v9", "v2": "v7"},
            },
            "borders": {
                "b1": {"edges": ["e1", "e2", "e3", "e4"]},
                "b2": {"edges": ["e5", "e6", "e7", "e2"]},
                "b3": {"edges": ["e3", "e10", "e9", "e8"]},
                "b4": {"edges": ["e7", "e11", "e12", "e10"]},
            },
            "faces": {
                "C1": {
                    "type": "land", "coastal": True, "owner": "Power1",
                    "is_supply_center": True,
                    "center": [0.1, 0.1],
                    "borders": ["b1"],
                    "name": "Ethwood",
                },
                "C2": {
                    "type": "land", "coastal": False, "owner": "Power1",
                    "is_supply_center": True,
                    "center": [0.3, 0.1],
                    "borders": ["b2"],
                    "name": "Calm Sound",
                },
                "C3": {
                    "type": "land", "coastal": True, "owner": "Power2",
                    "is_supply_center": True,
                    "center": [0.1, 0.3],
                    "borders": ["b3"],
                    "name": "North Strait",
                },
                "C4": {
                    "type": "land", "coastal": False, "owner": "Power2",
                    "is_supply_center": True,
                    "center": [0.3, 0.3],
                    "borders": ["b4"],
                    "name": "Falmere",
                },
            },
        },
    }


def _sample_orders():
    """Sample resolved orders list."""
    return [
        {
            "unit_type": "A",
            "location": "Ethwood",
            "order_type": "hold",
            "target": None,
            "support_unit_type": None,
            "support_from": None,
            "support_to": None,
            "result": "success",
            "power": "Power1",
            "raw_order": "A {Ethwood} H",
        },
        {
            "unit_type": "F",
            "location": "Calm Sound",
            "order_type": "move",
            "target": "North Strait",
            "support_unit_type": None,
            "support_from": None,
            "support_to": None,
            "result": "success",
            "power": "Power1",
            "raw_order": "F {Calm Sound} M {North Strait}",
        },
        {
            "unit_type": "A",
            "location": "North Strait",
            "order_type": "move",
            "target": "Falmere",
            "support_unit_type": None,
            "support_from": None,
            "support_to": None,
            "result": "bounce",
            "power": "Power2",
            "raw_order": "A {North Strait} M {Falmere}",
        },
        {
            "unit_type": "A",
            "location": "Falmere",
            "order_type": "support",
            "target": None,
            "support_unit_type": "A",
            "support_from": "North Strait",
            "support_to": None,
            "result": "success",
            "power": "Power2",
            "raw_order": "A {Falmere} S A {North Strait} H",
        },
    ]


SAMPLE_TURN_TEXT = """\
============================================================
  TURN: Spring 1901
============================================================

  Orders:
    Power1:
      A {Ethwood} H  [success]
      F {Calm Sound} M {North Strait}  [success]
    Power2:
      A {North Strait} M {Falmere}  [bounce]
      A {Falmere} S A {North Strait} H  [success]

  Unit positions:
    Power1: A Ethwood, F North Strait
    Power2: A North Strait, A Falmere

  Supply centers:
    Power1               : 2 SCs, 2 units
    Power2               : 2 SCs, 2 units
------------------------------------------------------------
"""


SAMPLE_WINTER_TEXT = """\
============================================================
  TURN: Winter 1901
============================================================

  Orders:
    Power1:
      B A {Ethwood}  [success]
    Power2:
      A {North Strait} D  [success]

  Winter adjustments:
    Power1: 1 build, Power2: 1 disband

  Unit positions:
    Power1: A Ethwood, A Calm Sound
    Power2: A Falmere

  Supply centers:
    Power1               : 3 SCs, 3 units
    Power2               : 1 SCs, 1 units
------------------------------------------------------------
"""


# ------------------------------------------------------------------
# Tests: parse_turn_summary_text
# ------------------------------------------------------------------

class TestParseTurnSummaryText:
    """Tests for text turn-summary parsing."""

    def test_parses_hold_order(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        hold = [o for o in orders if o["order_type"] == "hold"]
        assert len(hold) >= 1
        assert hold[0]["location"] == "Ethwood"
        assert hold[0]["result"] == "success"

    def test_parses_move_order(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        moves = [o for o in orders if o["order_type"] == "move"]
        assert len(moves) >= 1
        first_move = moves[0]
        assert first_move["location"] == "Calm Sound"
        assert first_move["target"] == "North Strait"
        assert first_move["result"] == "success"

    def test_parses_bounce_result(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        bounced = [o for o in orders if o["result"] == "bounce"]
        assert len(bounced) == 1
        assert bounced[0]["target"] == "Falmere"

    def test_parses_support_order(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        supports = [o for o in orders if o["order_type"] == "support"]
        assert len(supports) == 1
        assert supports[0]["support_from"] == "North Strait"

    def test_parses_power_names(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        powers = {o["power"] for o in orders}
        assert "Power1" in powers
        assert "Power2" in powers

    def test_total_order_count(self):
        orders = parse_turn_summary_text(SAMPLE_TURN_TEXT)
        assert len(orders) == 4

    def test_parses_build_order(self):
        orders = parse_turn_summary_text(SAMPLE_WINTER_TEXT)
        builds = [o for o in orders if o["order_type"] == "build"]
        assert len(builds) == 1
        assert builds[0]["location"] == "Ethwood"
        assert builds[0]["unit_type"] == "A"

    def test_parses_disband_order(self):
        orders = parse_turn_summary_text(SAMPLE_WINTER_TEXT)
        disbands = [o for o in orders if o["order_type"] == "disband"]
        assert len(disbands) == 1
        assert disbands[0]["location"] == "North Strait"


# ------------------------------------------------------------------
# Tests: load_orders (JSON)
# ------------------------------------------------------------------

class TestLoadOrdersJSON:
    """Tests for JSON loading."""

    def test_loads_json_turn_result(self):
        data = {"turn": "Fall 1901", "resolved_orders": _sample_orders()}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            orders, label = load_orders(path)
            assert label == "Fall 1901"
            assert len(orders) == 4
        finally:
            os.unlink(path)

    def test_loads_text_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(SAMPLE_TURN_TEXT)
            path = f.name
        try:
            orders, label = load_orders(path)
            assert len(orders) == 4
            assert "Spring 1901" in label
        finally:
            os.unlink(path)


# ------------------------------------------------------------------
# Tests: result color helpers
# ------------------------------------------------------------------

class TestResultColors:
    """Tests for result color mapping."""

    def test_success_is_green(self):
        assert _result_color("success") == "#2ca02c"

    def test_bounce_is_red(self):
        assert _result_color("bounce") == "#d62728"

    def test_pending_is_gray(self):
        assert _result_color("pending") == "#7f7f7f"

    def test_unknown_defaults_to_gray(self):
        assert _result_color("unknown_value") == "#7f7f7f"

    def test_is_failed_bounce(self):
        assert _is_failed("bounce") is True

    def test_is_failed_success(self):
        assert _is_failed("success") is False

    def test_is_failed_pending(self):
        assert _is_failed("pending") is False


# ------------------------------------------------------------------
# Tests: name-to-ID mapping
# ------------------------------------------------------------------

class TestNameToIdMap:
    """Tests for _build_name_to_id_map."""

    def test_maps_name_to_id(self):
        faces = {"C1": {"name": "Ethwood"}, "C2": {"name": "Calm Sound"}}
        m = _build_name_to_id_map(faces)
        assert m["Ethwood"] == "C1"
        assert m["Calm Sound"] == "C2"

    def test_maps_id_to_itself(self):
        faces = {"C1": {"name": "Ethwood"}}
        m = _build_name_to_id_map(faces)
        assert m["C1"] == "C1"


# ------------------------------------------------------------------
# Tests: render_order_view (integration)
# ------------------------------------------------------------------

class TestRenderOrderView:
    """Integration tests for the rendering function."""

    def test_produces_png_file(self):
        map_data = _minimal_map_data()
        orders = _sample_orders()
        with tempfile.TemporaryDirectory() as td:
            out = render_order_view(map_data, orders, turn_label="Spring 1901",
                                    output_path=os.path.join(td, "test.png"))
            assert os.path.isfile(out)
            assert out.endswith(".png")
            # File should have non-trivial size
            assert os.path.getsize(out) > 1000

    def test_renders_with_empty_orders(self):
        """Rendering with no orders should still produce a valid image."""
        map_data = _minimal_map_data()
        with tempfile.TemporaryDirectory() as td:
            out = render_order_view(map_data, [], turn_label="Spring 1901",
                                    output_path=os.path.join(td, "empty.png"))
            assert os.path.isfile(out)

    def test_renders_winter_orders(self):
        """Rendering build and disband orders should not crash."""
        map_data = _minimal_map_data()
        winter_orders = [
            {
                "unit_type": "A",
                "location": "Ethwood",
                "order_type": "build",
                "target": None,
                "support_unit_type": None,
                "support_from": None,
                "support_to": None,
                "result": "success",
                "power": "Power1",
                "raw_order": "B A {Ethwood}",
            },
            {
                "unit_type": "A",
                "location": "North Strait",
                "order_type": "disband",
                "target": None,
                "support_unit_type": None,
                "support_from": None,
                "support_to": None,
                "result": "success",
                "power": "Power2",
                "raw_order": "A {North Strait} D",
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            out = render_order_view(map_data, winter_orders,
                                    turn_label="Winter 1901",
                                    output_path=os.path.join(td, "winter.png"))
            assert os.path.isfile(out)
            assert os.path.getsize(out) > 1000

    def test_renders_convoy_order(self):
        """Rendering a convoy order should not crash."""
        map_data = _minimal_map_data()
        convoy_orders = [
            {
                "unit_type": "F",
                "location": "Calm Sound",
                "order_type": "convoy",
                "target": "Falmere",
                "support_unit_type": "A",
                "support_from": "Ethwood",
                "support_to": None,
                "result": "success",
                "power": "Power1",
                "raw_order": "F {Calm Sound} C A {Ethwood} M {Falmere}",
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            out = render_order_view(map_data, convoy_orders,
                                    turn_label="Fall 1901",
                                    output_path=os.path.join(td, "convoy.png"))
            assert os.path.isfile(out)


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestParseTurnSummaryText,
        TestLoadOrdersJSON,
        TestResultColors,
        TestNameToIdMap,
        TestRenderOrderView,
    ]

    total = 0
    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()

        for method_name in sorted(dir(instance)):
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
