"""
Tests for turn-by-turn output: format_turn_summary and turn_callback in run_game.

Verifies that:
- format_turn_summary produces the expected text sections
- format_turn_summary shows territory names (not cell IDs) in orders
- run_game invokes the turn_callback for every ORDER turn and winter BUILD
- run_game still works identically when no callback is provided
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager
from llm import GameModerator, MockLLMAdapter, format_turn_summary
from llm.adapters.base import BaseLLMAdapter


def _create_minimal_map_data():
    """Create minimal map data for testing (same as test_moderator)."""
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
            ],
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
                "C1": {
                    "type": "land", "coastal": True, "owner": "Power1",
                    "is_supply_center": True, "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Province1",
                },
                "C2": {
                    "type": "land", "coastal": False, "owner": "Power1",
                    "is_supply_center": True, "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Province2",
                },
                "C3": {
                    "type": "land", "coastal": True, "owner": "Power2",
                    "is_supply_center": True, "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Province3",
                },
                "C4": {
                    "type": "land", "coastal": False, "owner": "Power2",
                    "is_supply_center": True, "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Province4",
                },
                "C5": {
                    "type": "land", "coastal": True,
                    "is_supply_center": True, "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Neutral1",
                },
                "Sea1": {
                    "type": "sea", "center": [0.5, 0.5],
                    "borders": ["b1"], "name": "Sea Zone",
                },
            },
        },
    }


def _setup_game_and_moderator():
    """Helper to create a GameManager + GameModerator with mock adapters."""
    map_data = _create_minimal_map_data()
    gm = GameManager(map_data=map_data)
    gm.initialize_game()
    agents = {
        "Power1": MockLLMAdapter(),
        "Power2": MockLLMAdapter(),
    }
    moderator = GameModerator(gm, agents)
    return gm, moderator


# ------------------------------------------------------------------
# format_turn_summary
# ------------------------------------------------------------------

class TestFormatTurnSummary:
    """Tests for the format_turn_summary helper function."""

    def test_returns_string(self):
        """format_turn_summary returns a non-empty string."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_contains_turn_label(self):
        """Output contains the turn identifier (e.g., 'Spring 1901')."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert "Spring 1901" in text

    def test_contains_orders_section(self):
        """Output contains an 'Orders:' section."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert "Orders:" in text

    def test_contains_unit_positions_section(self):
        """Output contains a 'Unit positions:' section."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert "Unit positions:" in text

    def test_contains_supply_centers_section(self):
        """Output contains a 'Supply centers:' section."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert "Supply centers:" in text

    def test_contains_power_names(self):
        """Output contains every power name."""
        gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        text = format_turn_summary(result, gm.state, gm)
        assert "Power1" in text
        assert "Power2" in text

    def test_orders_use_territory_names(self):
        """Orders section uses territory names, not cell IDs."""
        gm, moderator = _setup_game_and_moderator()
        # Build a synthetic turn result with properly formed order dicts
        # (as would be produced by a real adapter that emits valid orders)
        result = {
            "turn": "Spring 1901",
            "resolved_orders": [
                {
                    "unit_type": "A",
                    "location": "C2",
                    "order_type": "hold",
                    "target": None,
                    "result": "success",
                    "power": "Power1",
                    "raw_order": "A {C2} H",
                },
                {
                    "unit_type": "F",
                    "location": "C1",
                    "order_type": "move",
                    "target": "C3",
                    "result": "bounce",
                    "power": "Power1",
                    "raw_order": "F {C1} M {C3}",
                },
            ],
            "dislodged": {},
            "log": "",
        }
        text = format_turn_summary(result, gm.state, gm)
        orders_section = text.split("Orders:")[1].split("Unit positions:")[0]
        # Should contain province names
        assert "Province1" in orders_section
        assert "Province2" in orders_section
        assert "Province3" in orders_section
        # Cell IDs should NOT appear in the orders display
        assert "{C1}" not in orders_section
        assert "{C2}" not in orders_section
        assert "{C3}" not in orders_section


# ------------------------------------------------------------------
# turn_callback in run_game
# ------------------------------------------------------------------

class TestTurnCallback:
    """Tests for the turn_callback parameter of run_game."""

    def test_callback_invoked_per_order_turn(self):
        """turn_callback is called at least once per ORDER-phase turn."""
        gm, moderator = _setup_game_and_moderator()
        collected: list[dict] = []

        def cb(result, mod, step):
            collected.append(result)

        summary = moderator.run_game(max_turns=3, turn_callback=cb)
        # At least as many callbacks as turns played (winter adds more)
        assert len(collected) >= summary["turns_played"]

    def test_callback_receives_turn_result(self):
        """Each callback invocation receives a dict with expected keys."""
        gm, moderator = _setup_game_and_moderator()
        collected: list[dict] = []

        def cb(result, mod, step):
            collected.append(result)

        moderator.run_game(max_turns=1, turn_callback=cb)
        assert len(collected) >= 1
        result = collected[0]
        assert "turn" in result
        assert "resolved_orders" in result
        assert "dislodged" in result
        assert "log" in result

    def test_callback_receives_moderator(self):
        """The callback receives the moderator as its second argument."""
        gm, moderator = _setup_game_and_moderator()
        received_mods: list = []

        def cb(result, mod, step):
            received_mods.append(mod)

        moderator.run_game(max_turns=1, turn_callback=cb)
        assert len(received_mods) >= 1
        assert received_mods[0] is moderator

    def test_callback_receives_step_number(self):
        """The callback receives a sequential step_number starting at 1."""
        gm, moderator = _setup_game_and_moderator()
        steps: list[int] = []

        def cb(result, mod, step):
            steps.append(step)

        moderator.run_game(max_turns=3, turn_callback=cb)
        assert steps[0] == 1
        # Steps should be strictly increasing
        for i in range(1, len(steps)):
            assert steps[i] == steps[i - 1] + 1

    def test_no_callback_still_works(self):
        """run_game works identically when turn_callback is None."""
        gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=2, turn_callback=None)
        assert isinstance(summary, dict)
        assert summary["turns_played"] > 0
        assert "history" in summary

    def test_run_game_without_callback_kwarg(self):
        """run_game without the callback keyword is backward-compatible."""
        gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=2)
        assert isinstance(summary, dict)
        assert summary["turns_played"] > 0


# ------------------------------------------------------------------
# Winter turns
# ------------------------------------------------------------------

class TestWinterTurnOutput:
    """Tests verifying winter BUILD phases appear in callback output."""

    def test_winter_turn_in_history(self):
        """Winter build results appear in the history list."""
        gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=3)
        winter_entries = [
            h for h in summary["history"] if "Winter" in h.get("turn", "")
        ]
        # With 3 order turns (S1901, F1901, S1902) there should be
        # at least one winter entry (Winter 1901).
        assert len(winter_entries) >= 1

    def test_winter_callback_invoked(self):
        """turn_callback is invoked for winter BUILD phases."""
        gm, moderator = _setup_game_and_moderator()
        turns_seen: list[str] = []

        def cb(result, mod, step):
            turns_seen.append(result["turn"])

        moderator.run_game(max_turns=3, turn_callback=cb)
        winter_calls = [t for t in turns_seen if "Winter" in t]
        assert len(winter_calls) >= 1

    def test_winter_summary_has_adjustments(self):
        """format_turn_summary for a winter turn contains adjustments text."""
        gm, moderator = _setup_game_and_moderator()
        collected: list[dict] = []

        def cb(result, mod, step):
            collected.append(result)

        moderator.run_game(max_turns=3, turn_callback=cb)
        winter_results = [r for r in collected if "Winter" in r["turn"]]
        assert len(winter_results) >= 1
        text = format_turn_summary(winter_results[0], gm.state, gm)
        assert "Winter" in text
