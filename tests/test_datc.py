"""
DATC-derived adjudication tests for the Diplomacy engine.

These tests construct minimal game states directly so the resolver can be
validated without running the full map generation pipeline.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game import GameManager, GameState, OrderResolver, OrderValidator, Unit, UnitType
from game.orders import Order, OrderParser, OrderResult, OrderType
from game.validators import build_adjacency_from_map


def land(*, coastal: bool = False, coasts: dict | None = None) -> dict:
    """Create a land face."""
    face = {"type": "land", "coastal": coastal}
    if coasts:
        face["coasts"] = coasts
        face["coastal"] = True
    return face


def sea() -> dict:
    """Create a sea face."""
    return {"type": "sea", "coastal": False}


def army(power: str, *, dislodged: bool = False) -> dict:
    """Create an army unit spec."""
    return {"unit_type": UnitType.ARMY, "power": power, "dislodged": dislodged}


def fleet(power: str, *, coast: str | None = None, dislodged: bool = False) -> dict:
    """Create a fleet unit spec."""
    return {
        "unit_type": UnitType.FLEET,
        "power": power,
        "coast": coast,
        "dislodged": dislodged,
    }


def make_map(faces: dict[str, dict], adjacency: dict[str, list[str]]) -> dict:
    """Build minimal map data for adjudication tests."""
    topology_faces = {}
    for face_id, face_data in faces.items():
        topology_faces[face_id] = {
            "name": face_id,
            "type": face_data["type"],
            "coastal": face_data.get("coastal", False),
            "borders": [],
            "center": [0.0, 0.0],
        }
        if "coasts" in face_data:
            topology_faces[face_id]["coasts"] = face_data["coasts"]

    return {
        "topology": {
            "vertices": {},
            "edges": {},
            "borders": {},
            "faces": topology_faces,
        },
        "adjacency": adjacency,
    }


def make_state(map_data: dict, units: dict[str, dict]) -> GameState:
    """Build a minimal GameState from unit specs."""
    state = GameState(map_data=map_data, powers={spec["power"] for spec in units.values()})
    for location, spec in units.items():
        state.units[location] = Unit(
            unit_type=spec["unit_type"],
            power=spec["power"],
            location=location,
            coast=spec.get("coast"),
            dislodged=spec.get("dislodged", False),
        )
    return state


def adjudicate(
    faces: dict[str, dict],
    adjacency: dict[str, list[str]],
    units: dict[str, dict],
    order_strings: list[str],
) -> tuple[GameState, dict[str, object], dict[str, str], dict]:
    """Validate and resolve a set of orders."""
    map_data = make_map(faces, adjacency)
    state = make_state(map_data, units)
    built_adjacency = build_adjacency_from_map(map_data)
    validator = OrderValidator(state, built_adjacency)
    orders = [validator.validate_order(OrderParser.parse(order)) for order in order_strings]
    resolver = OrderResolver(state, built_adjacency)
    resolved_orders, dislodged = resolver.resolve(orders)
    resolver.apply_moves()
    return state, {order.raw_order: order for order in resolved_orders}, dislodged, map_data


@pytest.mark.parametrize(
    ("faces", "adjacency", "units", "order_string", "destination"),
    [
        (
            {"A": land(), "B": land()},
            {"A": ["B"], "B": ["A"]},
            {"A": army("P1")},
            "A {A} M {B}",
            "B",
        ),
        (
            {"SEA": sea(), "COAST": land(coastal=True)},
            {"SEA": ["COAST"], "COAST": ["SEA"]},
            {"SEA": fleet("P1")},
            "F {SEA} M {COAST}",
            "COAST",
        ),
    ],
)
def test_datc_basic_movement(faces, adjacency, units, order_string, destination):
    """DATC: basic army and fleet movement."""
    state, orders, _, _ = adjudicate(faces, adjacency, units, [order_string])

    assert orders[order_string].result == OrderResult.SUCCESS
    assert destination in state.units


def test_datc_bounce_on_equal_strength_standoff():
    """DATC: equal-strength attacks on an empty province bounce."""
    faces = {"A": land(), "B": land(), "C": land()}
    adjacency = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    units = {"A": army("P1"), "C": army("P2")}
    orders_in = ["A {A} M {B}", "A {C} M {B}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {B}"].result == OrderResult.FAILED_BOUNCE
    assert orders["A {C} M {B}"].result == OrderResult.FAILED_BOUNCE
    assert "B" not in state.units


def test_datc_support_hold_prevents_dislodgement():
    """DATC: support hold adds defensive strength."""
    faces = {"A": land(), "B": land(), "C": land()}
    adjacency = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    units = {"A": army("P1"), "B": army("P2"), "C": army("P3")}
    orders_in = ["A {B} H", "A {A} S A {B} H", "A {C} M {B}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {C} M {B}"].result == OrderResult.FAILED_BOUNCE
    assert state.units["B"].power == "P2"


def test_datc_support_move_overpowers_defender():
    """DATC: support move can dislodge a holding defender."""
    faces = {"A": land(), "B": land(coastal=True), "C": land()}
    adjacency = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    units = {"A": army("P1"), "B": army("P2"), "C": army("P1")}
    orders_in = ["A {A} M {B}", "A {C} S A {A} M {B}", "A {B} H"]

    state, orders, dislodged, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {B}"].result == OrderResult.SUCCESS
    assert orders["A {B} H"].result == OrderResult.FAILED_DISLODGED
    assert dislodged == {"B": "A"}
    assert state.units["B"].power == "P1"


def test_datc_support_is_cut_by_attack():
    """DATC: attacks on a supporter cut support even if the attack fails."""
    faces = {"A": land(), "B": land(), "C": land(), "D": land()}
    adjacency = {
        "A": ["B"],
        "B": ["A", "C"],
        "C": ["B", "D"],
        "D": ["C"],
    }
    units = {"A": army("P1"), "B": army("P2"), "C": army("P1"), "D": army("P3")}
    orders_in = ["A {A} M {B}", "A {C} S A {A} M {B}", "A {B} H", "A {D} M {C}"]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {C} S A {A} M {B}"].result == OrderResult.CUT
    assert orders["A {A} M {B}"].result == OrderResult.FAILED_BOUNCE
    assert orders["A {D} M {C}"].result == OrderResult.FAILED_BOUNCE


def test_datc_support_is_not_cut_when_supporting_against_the_attacker():
    """DATC: support is not cut by the unit against which support is given."""
    faces = {"A": land(), "B": land(), "C": land()}
    adjacency = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    units = {"A": army("P1"), "B": army("P2"), "C": army("P1")}
    orders_in = ["A {A} M {B}", "A {C} S A {A} M {B}", "A {B} M {C}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {C} S A {A} M {B}"].result == OrderResult.PENDING
    assert orders["A {A} M {B}"].result == OrderResult.SUCCESS
    assert state.units["B"].power == "P1"


def test_datc_head_to_head_equal_strength_bounces():
    """DATC: equal head-to-head attacks bounce."""
    faces = {"A": land(), "B": land()}
    adjacency = {"A": ["B"], "B": ["A"]}
    units = {"A": army("P1"), "B": army("P2")}
    orders_in = ["A {A} M {B}", "A {B} M {A}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {B}"].result == OrderResult.FAILED_BOUNCE
    assert orders["A {B} M {A}"].result == OrderResult.FAILED_BOUNCE
    assert state.units["A"].power == "P1"
    assert state.units["B"].power == "P2"


def test_datc_head_to_head_stronger_attack_dislodges():
    """DATC: support decides head-to-head battles."""
    faces = {"A": land(), "B": land(), "C": land()}
    adjacency = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}
    units = {"A": army("P1"), "B": army("P2"), "C": army("P1")}
    orders_in = ["A {A} M {B}", "A {C} S A {A} M {B}", "A {B} M {A}"]

    state, orders, dislodged, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {B}"].result == OrderResult.SUCCESS
    assert orders["A {B} M {A}"].result == OrderResult.FAILED_DISLODGED
    assert dislodged == {"B": "A"}
    assert state.units["B"].power == "P1"


def test_datc_single_fleet_convoy_succeeds():
    """DATC: a single convoying fleet can transport an army."""
    faces = {"A": land(coastal=True), "SEA": sea(), "C": land(coastal=True)}
    adjacency = {"A": ["SEA"], "SEA": ["A", "C"], "C": ["SEA"]}
    units = {"A": army("P1"), "SEA": fleet("P1")}
    orders_in = ["A {A} M {C}", "F {SEA} C A {A} M {C}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {C}"].result == OrderResult.SUCCESS
    assert state.units["C"].power == "P1"


def test_datc_multi_fleet_convoy_chain_succeeds():
    """DATC: a chain of convoying fleets can transport an army."""
    faces = {"A": land(coastal=True), "S1": sea(), "S2": sea(), "C": land(coastal=True)}
    adjacency = {"A": ["S1"], "S1": ["A", "S2"], "S2": ["S1", "C"], "C": ["S2"]}
    units = {"A": army("P1"), "S1": fleet("P1"), "S2": fleet("P1")}
    orders_in = ["A {A} M {C}", "F {S1} C A {A} M {C}", "F {S2} C A {A} M {C}"]

    state, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {C}"].result == OrderResult.SUCCESS
    assert state.units["C"].power == "P1"


def test_datc_convoy_disruption_when_convoying_fleet_is_dislodged():
    """DATC: dislodging the convoying fleet breaks the convoy."""
    faces = {
        "A": land(coastal=True),
        "S": sea(),
        "C": land(coastal=True),
        "X": sea(),
        "Y": sea(),
    }
    adjacency = {
        "A": ["S"],
        "S": ["A", "C", "X", "Y"],
        "C": ["S"],
        "X": ["S", "Y"],
        "Y": ["S", "X"],
    }
    units = {"A": army("P1"), "S": fleet("P1"), "X": fleet("P2"), "Y": fleet("P2")}
    orders_in = [
        "A {A} M {C}",
        "F {S} C A {A} M {C}",
        "F {X} M {S}",
        "F {Y} S F {X} M {S}",
    ]

    _, orders, dislodged, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["F {S} C A {A} M {C}"].result == OrderResult.FAILED_DISLODGED
    assert orders["A {A} M {C}"].result == OrderResult.FAILED_NO_PATH
    assert dislodged == {"S": "X"}


def test_datc_dislodgement_and_retreat_eligibility():
    """DATC: a dislodged unit gets retreat options excluding the attack source."""
    faces = {"A": land(), "B": land(), "C": land(), "D": land()}
    adjacency = {"A": ["B"], "B": ["A", "C", "D"], "C": ["B"], "D": ["B"]}
    units = {"A": army("P1"), "B": army("P2"), "C": army("P1")}
    orders_in = ["A {A} M {B}", "A {C} S A {A} M {B}", "A {B} H"]

    state, orders, dislodged, map_data = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {B} H"].result == OrderResult.FAILED_DISLODGED
    assert dislodged == {"B": "A"}
    assert "B" in state.dislodged_units

    manager = GameManager(map_data=map_data)
    manager.state = state
    assert manager.get_retreat_options("B") == ["D"]


def test_datc_fleet_move_to_split_coast_requires_named_coast():
    """DATC: a fleet must specify which non-contiguous coast it is moving to."""
    faces = {
        "NSEA": sea(),
        "SSEA": sea(),
        "CAPE": land(
            coasts={
                "north": {"adjacent": ["NSEA"], "aliases": ["nc"]},
                "south": {"adjacent": ["SSEA"], "aliases": ["sc"]},
            }
        ),
    }
    adjacency = {"NSEA": ["CAPE"], "SSEA": ["CAPE"], "CAPE": ["NSEA", "SSEA"]}
    units = {"NSEA": fleet("P1")}
    orders_in = ["F {NSEA} M {CAPE}"]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["F {NSEA} M {CAPE}"].result == OrderResult.INVALID_TARGET
    assert "specify a coast" in orders["F {NSEA} M {CAPE}"].error_message.lower()


@pytest.mark.parametrize(
    ("order_string", "expected_result"),
    [
        ("F {NSEA} M {CAPE/north}", OrderResult.SUCCESS),
        ("F {NSEA} M {CAPE/south}", OrderResult.INVALID_ADJACENT),
    ],
)
def test_datc_split_coast_target_respects_named_coast(order_string, expected_result):
    """DATC: named coasts only allow fleets from matching adjacent seas."""
    faces = {
        "NSEA": sea(),
        "SSEA": sea(),
        "CAPE": land(
            coasts={
                "north": {"adjacent": ["NSEA"], "aliases": ["nc"]},
                "south": {"adjacent": ["SSEA"], "aliases": ["sc"]},
            }
        ),
    }
    adjacency = {"NSEA": ["CAPE"], "SSEA": ["CAPE"], "CAPE": ["NSEA", "SSEA"]}
    units = {"NSEA": fleet("P1")}

    state, orders, _, _ = adjudicate(faces, adjacency, units, [order_string])

    assert orders[order_string].result == expected_result
    if expected_result == OrderResult.SUCCESS:
        assert state.units["CAPE"].coast == "north"


def test_datc_split_coast_source_coast_restricts_outgoing_fleet_move():
    """DATC: a fleet on one coast cannot move out via a different coast."""
    faces = {
        "NSEA": sea(),
        "SSEA": sea(),
        "CAPE": land(
            coasts={
                "north": {"adjacent": ["NSEA"], "aliases": ["nc"]},
                "south": {"adjacent": ["SSEA"], "aliases": ["sc"]},
            }
        ),
    }
    adjacency = {"NSEA": ["CAPE"], "SSEA": ["CAPE"], "CAPE": ["NSEA", "SSEA"]}
    units = {"CAPE": fleet("P1", coast="north")}
    orders_in = ["F {CAPE} M {SSEA}"]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["F {CAPE} M {SSEA}"].result == OrderResult.INVALID_ADJACENT


def test_datc_three_coast_topology_uses_the_requested_coast():
    """DATC-inspired unusual topology: three non-contiguous coasts still honor coast selection."""
    faces = {
        "WEST": sea(),
        "EAST": sea(),
        "SOUTH": sea(),
        "TRI": land(
            coasts={
                "west": {"adjacent": ["WEST"]},
                "east": {"adjacent": ["EAST"]},
                "south": {"adjacent": ["SOUTH"]},
            }
        ),
    }
    adjacency = {
        "WEST": ["TRI"],
        "EAST": ["TRI"],
        "SOUTH": ["TRI"],
        "TRI": ["WEST", "EAST", "SOUTH"],
    }
    units = {"WEST": fleet("P1")}
    orders_in = ["F {WEST} M {TRI/east}"]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["F {WEST} M {TRI/east}"].result == OrderResult.INVALID_ADJACENT


def test_datc_convoy_path_requires_matching_destination_coast():
    """DATC: convoy paths must match the move's named destination coast."""
    faces = {
        "A": land(coastal=True),
        "SSEA": sea(),
        "NSEA": sea(),
        "CAPE": land(
            coasts={
                "north": {"adjacent": ["NSEA"]},
                "south": {"adjacent": ["SSEA"]},
            }
        ),
    }
    adjacency = {
        "A": ["SSEA"],
        "SSEA": ["A", "CAPE", "NSEA"],
        "NSEA": ["SSEA", "CAPE"],
        "CAPE": ["SSEA", "NSEA"],
    }
    units = {"A": army("P1"), "SSEA": fleet("P1")}
    orders_in = ["A {A} M {CAPE/north}", "F {SSEA} C A {A} M {CAPE/south}"]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["A {A} M {CAPE/north}"].result == OrderResult.FAILED_NO_PATH


def test_datc_support_move_requires_matching_supported_fleet_coast():
    """DATC: support does not apply when the named source coast doesn't match the moving fleet."""
    faces = {
        "CAPE": land(
            coasts={
                "north": {"adjacent": ["NSEA"]},
                "south": {"adjacent": ["SSEA"]},
            }
        ),
        "NSEA": sea(),
        "SSEA": sea(),
    }
    adjacency = {
        "CAPE": ["NSEA", "SSEA"],
        "NSEA": ["CAPE", "SSEA"],
        "SSEA": ["CAPE", "NSEA"],
    }
    units = {
        "CAPE": fleet("P1", coast="north"),
        "NSEA": fleet("P2"),
        "SSEA": fleet("P1"),
    }
    orders_in = [
        "F {CAPE} M {NSEA}",
        "F {SSEA} S F {CAPE/south} M {NSEA}",
        "F {NSEA} H",
    ]

    _, orders, _, _ = adjudicate(faces, adjacency, units, orders_in)

    assert orders["F {CAPE} M {NSEA}"].result == OrderResult.FAILED_BOUNCE


def test_datc_split_coast_retreat_options_are_coast_qualified():
    """DATC: retreat options expose only the reachable split coast."""
    map_data = make_map(
        {
            "SEA": sea(),
            "BLOCK": sea(),
            "CAPE": land(
                coasts={
                    "north": {"adjacent": ["SEA"]},
                    "south": {"adjacent": ["BLOCK"]},
                }
            ),
        },
        {
            "SEA": ["BLOCK", "CAPE"],
            "BLOCK": ["SEA", "CAPE"],
            "CAPE": ["SEA", "BLOCK"],
        },
    )
    manager = GameManager(map_data=map_data)
    manager.state = GameState(map_data=map_data, powers={"P1"})
    dislodged = Unit(UnitType.FLEET, "P1", "SEA", dislodged=True)
    manager.state.dislodged_units["SEA"] = dislodged
    manager.state.dislodged_from["SEA"] = "BLOCK"

    assert manager.get_retreat_options("SEA") == ["CAPE/north"]
    assert manager.process_retreat("SEA", "CAPE/north") is True
    assert manager.state.units["CAPE"].coast == "north"


def test_datc_initial_split_coast_fleet_gets_default_coast():
    """DATC: initial fleet placement in a split-coast home center records a coast."""
    map_data = {
        "powers": {"P1": {"name": "P1", "home_centers": ["CAPE"]}},
        "supply_centers": {"home": [{"cell_id": "CAPE", "owner": "P1", "coastal": True}]},
        "topology": {
            "vertices": {},
            "edges": {},
            "borders": {},
            "faces": {
                "CAPE": {
                    "name": "CAPE",
                    "type": "land",
                    "coastal": True,
                    "coasts": {
                        "north": {"adjacent": ["NSEA"]},
                        "south": {"adjacent": ["SSEA"]},
                    },
                    "center": [0.0, 0.0],
                    "borders": [],
                    "owner": "P1",
                    "is_supply_center": True,
                },
                "NSEA": {"name": "NSEA", "type": "sea", "coastal": False, "center": [0.0, 0.0], "borders": []},
                "SSEA": {"name": "SSEA", "type": "sea", "coastal": False, "center": [0.0, 0.0], "borders": []},
            },
        },
        "adjacency": {"CAPE": ["NSEA", "SSEA"], "NSEA": ["CAPE"], "SSEA": ["CAPE"]},
    }

    manager = GameManager(map_data=map_data)
    state = manager.initialize_game()

    assert state.units["CAPE"].unit_type == UnitType.FLEET
    assert state.units["CAPE"].coast in {"north", "south"}


def test_datc_split_coast_fleet_build_records_coast():
    """DATC: winter fleet builds in split-coast provinces keep coast information."""
    map_data = {
        "powers": {"P1": {"name": "P1", "home_centers": ["CAPE"]}},
        "supply_centers": {"home": [{"cell_id": "CAPE", "owner": "P1", "coastal": True}]},
        "topology": {
            "vertices": {},
            "edges": {},
            "borders": {},
            "faces": {
                "CAPE": {
                    "name": "CAPE",
                    "type": "land",
                    "coastal": True,
                    "coasts": {
                        "north": {"adjacent": ["NSEA"]},
                        "south": {"adjacent": ["SSEA"]},
                    },
                    "center": [0.0, 0.0],
                    "borders": [],
                    "owner": "P1",
                    "is_supply_center": True,
                },
                "NSEA": {"name": "NSEA", "type": "sea", "coastal": False, "center": [0.0, 0.0], "borders": []},
                "SSEA": {"name": "SSEA", "type": "sea", "coastal": False, "center": [0.0, 0.0], "borders": []},
            },
        },
        "adjacency": {"CAPE": ["NSEA", "SSEA"], "NSEA": ["CAPE"], "SSEA": ["CAPE"]},
    }

    manager = GameManager(map_data=map_data)
    manager.state = GameState(map_data=map_data, powers={"P1"})
    manager.state.sc_control["CAPE"] = "P1"

    build_order = Order(
        unit_type="F",
        location="CAPE",
        location_coast="south",
        order_type=OrderType.BUILD,
        power="P1",
    )

    manager.process_winter_adjustments({"P1": [build_order]})

    assert manager.state.units["CAPE"].coast == "south"
