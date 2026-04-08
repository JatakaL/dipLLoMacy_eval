"""
Tests for the GameModerator class.

Verifies that the moderator correctly orchestrates LLM agent turns
by collecting orders, parsing them, and driving the game loop.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager
from llm import GameModerator, MockLLMAdapter
from llm.adapters.base import BaseLLMAdapter


def _create_minimal_map_data():
    """Create minimal map data for testing (same as TestGameManager)."""
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


class TestRunTurn:
    """Tests for GameModerator.run_turn."""

    def test_returns_dict_with_expected_keys(self):
        """run_turn returns a dict with turn, resolved_orders, dislodged, log."""
        _gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        assert isinstance(result, dict)
        assert "turn" in result
        assert "resolved_orders" in result
        assert "dislodged" in result
        assert "log" in result

    def test_turn_label_is_string(self):
        """The 'turn' value should be a human-readable string."""
        _gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        assert isinstance(result["turn"], str)
        assert "1901" in result["turn"]

    def test_resolved_orders_is_list(self):
        """resolved_orders should be a list of order dicts."""
        _gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        assert isinstance(result["resolved_orders"], list)

    def test_log_is_string(self):
        """log should be a non-empty string."""
        _gm, moderator = _setup_game_and_moderator()
        result = moderator.run_turn()
        assert isinstance(result["log"], str)


class TestRunGame:
    """Tests for GameModerator.run_game."""

    def test_terminates_and_returns_turns_played(self):
        """run_game terminates and returns turns_played > 0."""
        _gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=2)
        assert isinstance(summary, dict)
        assert summary["turns_played"] > 0

    def test_returns_expected_keys(self):
        """run_game returns dict with turns_played, winner, final_sc_counts, history."""
        _gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=2)
        assert "turns_played" in summary
        assert "winner" in summary
        assert "final_sc_counts" in summary
        assert "history" in summary

    def test_final_sc_counts_has_all_powers(self):
        """final_sc_counts should contain an entry for every power."""
        gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=2)
        for power in gm.state.powers:
            assert power in summary["final_sc_counts"]

    def test_history_matches_turns_played(self):
        """history list length should be >= turns_played (winter entries add more)."""
        _gm, moderator = _setup_game_and_moderator()
        summary = moderator.run_game(max_turns=3)
        assert len(summary["history"]) >= summary["turns_played"]


class TestAgentCalls:
    """Tests verifying that all agents receive calls for each turn."""

    def test_all_agents_called_each_turn(self):
        """Every agent's generate_orders is called for each turn."""

        class TrackingAdapter(BaseLLMAdapter):
            """Adapter that records calls."""

            def __init__(self):
                self.calls: list[str] = []

            def generate_orders(self, game_state_dict, power, board_image_path=None):
                self.calls.append(power)
                return []

            def generate_diplomacy_message(self, game_state_dict, sender, recipient):
                return ""

        map_data = _create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()

        adapter1 = TrackingAdapter()
        adapter2 = TrackingAdapter()
        agents = {"Power1": adapter1, "Power2": adapter2}
        moderator = GameModerator(gm, agents)

        moderator.run_turn()

        assert len(adapter1.calls) == 1
        assert adapter1.calls[0] == "Power1"
        assert len(adapter2.calls) == 1
        assert adapter2.calls[0] == "Power2"

    def test_agents_called_every_turn_in_run_game(self):
        """Each agent is called once per ORDER-phase turn in run_game."""

        class CountingAdapter(BaseLLMAdapter):
            """Adapter that counts calls."""

            def __init__(self):
                self.call_count = 0

            def generate_orders(self, game_state_dict, power, board_image_path=None):
                self.call_count += 1
                return []

            def generate_diplomacy_message(self, game_state_dict, sender, recipient):
                return ""

        map_data = _create_minimal_map_data()
        gm = GameManager(map_data=map_data)
        gm.initialize_game()

        adapter1 = CountingAdapter()
        adapter2 = CountingAdapter()
        agents = {"Power1": adapter1, "Power2": adapter2}
        moderator = GameModerator(gm, agents)

        summary = moderator.run_game(max_turns=3)
        turns = summary["turns_played"]

        assert adapter1.call_count == turns
        assert adapter2.call_count == turns
