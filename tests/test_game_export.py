"""
Tests for the standardized game output export (game/game_export.py).

Verifies that:
- create_game_output_dir creates the expected folder structure
- write_game_metadata writes valid JSON with expected keys
- write_map_data writes the map data
- write_turn_data creates per-turn artifacts
- write_game_result writes final result JSON
- build_turn_callback produces a working callback
- export_full_game runs end-to-end
- load_game_output correctly loads all artifacts back
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager
from game.game_export import (
    create_game_output_dir,
    write_game_metadata,
    write_map_data,
    write_turn_data,
    write_game_result,
    build_turn_callback,
    export_full_game,
    load_game_output,
)
from game.game_state import GameState
from llm import GameModerator, MockLLMAdapter, format_turn_summary


def _create_minimal_map_data():
    """Reuse the minimal map data from test_turn_output."""
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


def _setup_game():
    """Create a game manager + moderator pair for testing."""
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
# create_game_output_dir
# ------------------------------------------------------------------

class TestCreateGameOutputDir:
    def test_creates_directory(self, tmp_path):
        out = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        assert out.exists()
        assert out.is_dir()
        assert out.name == "game_20260408_120000"

    def test_creates_turns_subdirectory(self, tmp_path):
        out = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        assert (out / "turns").is_dir()

    def test_auto_timestamp(self, tmp_path):
        out = create_game_output_dir(base_dir=tmp_path)
        assert out.name.startswith("game_")
        assert len(out.name) > len("game_")


# ------------------------------------------------------------------
# write_game_metadata
# ------------------------------------------------------------------

class TestWriteGameMetadata:
    def test_creates_file(self, tmp_path):
        gm, _ = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        path = write_game_metadata(out_dir, gm)
        assert path.exists()
        assert path.name == "game_metadata.json"

    def test_contains_powers(self, tmp_path):
        gm, _ = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        write_game_metadata(out_dir, gm)
        with open(out_dir / "game_metadata.json") as f:
            data = json.load(f)
        assert "powers" in data
        assert "Power1" in data["powers"]
        assert "Power2" in data["powers"]

    def test_stores_config(self, tmp_path):
        gm, _ = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        write_game_metadata(out_dir, gm, config={"seed": 42})
        with open(out_dir / "game_metadata.json") as f:
            data = json.load(f)
        assert data["generation_config"]["seed"] == 42


# ------------------------------------------------------------------
# write_map_data
# ------------------------------------------------------------------

class TestWriteMapData:
    def test_creates_map_json(self, tmp_path):
        gm, _ = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        path = write_map_data(out_dir, gm)
        assert path.exists()
        assert path.name == "map.json"

    def test_map_json_contains_topology(self, tmp_path):
        gm, _ = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        write_map_data(out_dir, gm)
        with open(out_dir / "map.json") as f:
            data = json.load(f)
        assert "topology" in data


# ------------------------------------------------------------------
# write_turn_data
# ------------------------------------------------------------------

class TestWriteTurnData:
    def test_creates_turn_directory(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        result = moderator.run_turn()
        summary = format_turn_summary(result, gm.state, gm)
        turn_dir = write_turn_data(out_dir, 1, result, gm.state, gm, summary)
        assert turn_dir.is_dir()
        assert "turn_01_" in turn_dir.name

    def test_creates_orders_json(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        result = moderator.run_turn()
        summary = format_turn_summary(result, gm.state, gm)
        turn_dir = write_turn_data(out_dir, 1, result, gm.state, gm, summary)
        assert (turn_dir / "orders.json").exists()
        with open(turn_dir / "orders.json") as f:
            data = json.load(f)
        assert "turn" in data
        assert "resolved_orders" in data

    def test_creates_state_json(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        result = moderator.run_turn()
        summary = format_turn_summary(result, gm.state, gm)
        turn_dir = write_turn_data(out_dir, 1, result, gm.state, gm, summary)
        assert (turn_dir / "state.json").exists()

    def test_creates_summary_txt(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        result = moderator.run_turn()
        summary = format_turn_summary(result, gm.state, gm)
        turn_dir = write_turn_data(out_dir, 1, result, gm.state, gm, summary)
        assert (turn_dir / "summary.txt").exists()
        text = (turn_dir / "summary.txt").read_text()
        assert "Spring 1901" in text


# ------------------------------------------------------------------
# write_game_result
# ------------------------------------------------------------------

class TestWriteGameResult:
    def test_creates_result_json(self, tmp_path):
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        summary = {
            "turns_played": 3,
            "winner": "Power1",
            "final_sc_counts": {"Power1": 5, "Power2": 3},
            "history": [],
        }
        path = write_game_result(out_dir, summary)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["winner"] == "Power1"
        assert data["turns_played"] == 3
        # History should NOT be in result.json (it's large)
        assert "history" not in data


# ------------------------------------------------------------------
# build_turn_callback
# ------------------------------------------------------------------

class TestBuildTurnCallback:
    def test_callback_creates_turn_dirs(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        cb = build_turn_callback(out_dir)
        result = moderator.run_turn()
        cb(result, moderator, 1)
        turns_dir = out_dir / "turns"
        turn_dirs = list(turns_dir.iterdir())
        assert len(turn_dirs) == 1
        assert (turn_dirs[0] / "orders.json").exists()


# ------------------------------------------------------------------
# export_full_game (end-to-end)
# ------------------------------------------------------------------

class TestExportFullGame:
    def test_end_to_end(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        summary = export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=2,
        )
        assert (out_dir / "game_metadata.json").exists()
        assert (out_dir / "map.json").exists()
        assert (out_dir / "result.json").exists()
        assert summary["turns_played"] > 0

        turns_dir = out_dir / "turns"
        turn_dirs = sorted(turns_dir.iterdir())
        assert len(turn_dirs) >= 1
        # Each turn dir has orders.json, state.json, summary.txt
        for td in turn_dirs:
            assert (td / "orders.json").exists()
            assert (td / "state.json").exists()
            assert (td / "summary.txt").exists()


# ------------------------------------------------------------------
# load_game_output
# ------------------------------------------------------------------

class TestLoadGameOutput:
    def test_loads_exported_game(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=2,
        )

        loaded = load_game_output(out_dir)
        assert "metadata" in loaded
        assert "map_data" in loaded
        assert "turns" in loaded
        assert "result" in loaded

    def test_turns_are_sorted(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=3,
        )

        loaded = load_game_output(out_dir)
        steps = [t["step"] for t in loaded["turns"]]
        assert steps == sorted(steps)

    def test_turn_has_expected_keys(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=1,
        )

        loaded = load_game_output(out_dir)
        assert len(loaded["turns"]) >= 1
        turn = loaded["turns"][0]
        assert "step" in turn
        assert "label" in turn
        assert "orders" in turn
        assert "state" in turn
        assert "summary" in turn

    def test_missing_dir_raises(self, tmp_path):
        import pytest
        with pytest.raises(FileNotFoundError):
            load_game_output(tmp_path / "nonexistent")

    def test_missing_metadata_raises(self, tmp_path):
        import pytest
        empty_dir = tmp_path / "empty_game"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="game_metadata.json"):
            load_game_output(empty_dir)

    def test_metadata_has_powers(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=1,
        )

        loaded = load_game_output(out_dir)
        assert "Power1" in loaded["metadata"]["powers"]
        assert "Power2" in loaded["metadata"]["powers"]

    def test_result_has_winner_key(self, tmp_path):
        gm, moderator = _setup_game()
        out_dir = create_game_output_dir(base_dir=tmp_path, timestamp="20260408_120000")
        export_full_game(
            output_dir=out_dir,
            game_manager=gm,
            moderator=moderator,
            max_turns=1,
        )

        loaded = load_game_output(out_dir)
        assert "winner" in loaded["result"]
        assert "turns_played" in loaded["result"]
