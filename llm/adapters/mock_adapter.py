"""
Mock LLM adapter for testing without real API calls.

Returns deterministic responses: hold orders for all units of the
specified power and a fixed placeholder diplomacy message.
"""

from .base import BaseLLMAdapter


class MockLLMAdapter(BaseLLMAdapter):
    """Mock adapter that returns deterministic responses for testing."""

    def generate_orders(
        self,
        game_state_dict: dict,
        power: str,
        board_image_path: str | None = None,
    ) -> list[str]:
        """Return hold orders for every unit belonging to *power*.

        Units are read from ``game_state_dict["game_state"]["units"]``,
        which maps province IDs to unit dicts with ``"type"``, ``"power"``,
        and ``"location"`` keys.
        """
        units = game_state_dict.get("game_state", {}).get("units", {})
        orders: list[str] = []
        for _loc, unit in units.items():
            if unit.get("power") == power:
                unit_type = "A" if unit.get("type") == "army" else "F"
                location = unit.get("location", _loc)
                orders.append(f"{unit_type} {location} H")
        return orders

    def generate_diplomacy_message(
        self,
        game_state_dict: dict,
        sender: str,
        recipient: str,
    ) -> str:
        """Return a fixed placeholder diplomacy message."""
        return "I propose we work together this turn."
