"""
Random-order LLM adapter for baseline evaluation.

Picks random valid moves from adjacency data, providing a comparison
point for smarter strategies. Supports an optional random seed for
reproducibility.
"""

import random

from .base import BaseLLMAdapter
from game.validators import build_adjacency_from_map


class RandomLLMAdapter(BaseLLMAdapter):
    """Adapter that generates random valid orders for baseline evaluation.

    For each unit belonging to the given power, randomly chooses between
    hold and move to a random valid adjacent territory.  Armies cannot
    move to sea; fleets can only move to sea or coastal provinces.  Falls
    back to hold if no valid move target exists.

    Args:
        seed: Optional random seed for reproducibility.
    """

    _GENERIC_MESSAGES = [
        "I think we should work together this turn.",
        "Let's coordinate our efforts.",
        "I have no hostile intentions toward you.",
        "Perhaps an alliance would benefit us both.",
        "I suggest we focus on other fronts.",
    ]

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def generate_orders(
        self,
        game_state_dict: dict,
        power: str,
        board_image_path: str | None = None,
    ) -> list[str]:
        """Generate random valid orders for every unit of *power*.

        For each unit the adapter randomly holds or moves to a valid
        adjacent territory.  Territory validity respects unit type
        constraints (armies cannot enter sea, fleets cannot enter
        non-coastal land).
        """
        units = game_state_dict.get("game_state", {}).get("units", {})
        map_data = game_state_dict.get("map_data", {})

        adjacency = build_adjacency_from_map(map_data)
        faces = map_data.get("topology", {}).get("faces", {})

        orders: list[str] = []
        for _loc, unit in units.items():
            if unit.get("power") != power:
                continue

            unit_type = "A" if unit.get("type") == "army" else "F"
            location = unit.get("location", _loc)

            # Determine valid move targets based on unit type
            neighbors = adjacency.get(location, [])
            valid_targets: list[str] = []
            for neighbor_id in neighbors:
                face_data = faces.get(neighbor_id, {})
                territory_type = face_data.get("type", "land")
                is_coastal = face_data.get("coastal", False)

                if unit_type == "A":
                    # Armies cannot move to sea
                    if territory_type != "sea":
                        valid_targets.append(neighbor_id)
                else:
                    # Fleets can only move to sea or coastal land
                    if territory_type == "sea" or is_coastal:
                        valid_targets.append(neighbor_id)

            if valid_targets and self._rng.random() >= 0.5:
                target = self._rng.choice(valid_targets)
                orders.append(f"{unit_type} {{{location}}} M {{{target}}}")
            else:
                orders.append(f"{unit_type} {{{location}}} H")

        return orders

    def generate_diplomacy_message(
        self,
        game_state_dict: dict,
        sender: str,
        recipient: str,
    ) -> str:
        """Return a random pick from a small set of generic messages."""
        return self._rng.choice(self._GENERIC_MESSAGES)
