"""
Tests for the Game Viewer data loading and text summary output.

The GUI components themselves cannot be tested in a headless CI
environment, but we verify:
- load_game_output works correctly (covered more deeply in test_game_export)
- print_game_summary runs without error
- The viewer module can be imported without GUI dependencies
"""

import sys
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager
from game.game_export import create_game_output_dir, export_full_game
from llm import GameModerator, MockLLMAdapter


def _create_minimal_map_data():
    """Minimal map data for testing."""
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
            "neutral": [{"cell_id": "C5", "coastal": True}],
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
            "borders": {"b1": {"edges": ["e1", "e2", "e3", "e4"]}},
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


def _setup_and_export(tmp_path, max_turns=2):
    """Create a game, run it, and export to tmp_path."""
    gm = GameManager(map_data=_create_minimal_map_data())
    gm.initialize_game()
    agents = {
        "Power1": MockLLMAdapter(),
        "Power2": MockLLMAdapter(),
    }
    moderator = GameModerator(gm, agents)
    out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
    export_full_game(
        output_dir=out_dir,
        game_manager=gm,
        moderator=moderator,
        max_turns=max_turns,
    )
    return out_dir


class TestPrintGameSummary:
    """Test the text-mode (headless) game summary."""

    def test_prints_to_stdout(self, tmp_path, capsys):
        from game_viewer import print_game_summary

        out_dir = _setup_and_export(tmp_path)
        print_game_summary(out_dir)
        captured = capsys.readouterr()
        assert "DIPLOMACY GAME REPLAY" in captured.out
        assert "Powers:" in captured.out
        assert "Power1" in captured.out

    def test_shows_turn_list(self, tmp_path, capsys):
        from game_viewer import print_game_summary

        out_dir = _setup_and_export(tmp_path)
        print_game_summary(out_dir)
        captured = capsys.readouterr()
        assert "Turn list:" in captured.out

    def test_shows_result(self, tmp_path, capsys):
        from game_viewer import print_game_summary

        out_dir = _setup_and_export(tmp_path)
        print_game_summary(out_dir)
        captured = capsys.readouterr()
        # Either "No winner" or a power name
        assert "winner" in captured.out.lower() or "Winner" in captured.out


class TestGameViewerImport:
    """Verify the game_viewer module is importable."""

    def test_module_importable(self):
        import game_viewer
        assert hasattr(game_viewer, "load_game_output")
        assert hasattr(game_viewer, "print_game_summary")
        assert hasattr(game_viewer, "main")
