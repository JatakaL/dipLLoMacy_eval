"""
Base LLM adapter interface for Diplomacy evaluation.

Defines the abstract interface that all LLM adapters must implement,
including order generation and diplomatic message generation.
"""

from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    """Abstract base class for LLM adapters.

    All LLM provider adapters must inherit from this class and implement
    the abstract methods for generating orders and diplomacy messages.
    """

    @abstractmethod
    def generate_orders(
        self,
        game_state_dict: dict,
        power: str,
        board_image_path: str | None = None,
    ) -> list[str]:
        """Generate orders for a power given the current game state.

        Args:
            game_state_dict: Complete game state dictionary as returned by
                GameManager.get_game_state(), containing a "game_state" key
                with unit positions, supply centers, etc.
            power: Name of the power to generate orders for.
            board_image_path: Optional path to a board image for multimodal
                models.

        Returns:
            A list of order strings (e.g. ["A Paris H", "F Brest H"]).
        """

    @abstractmethod
    def generate_diplomacy_message(
        self,
        game_state_dict: dict,
        sender: str,
        recipient: str,
    ) -> str:
        """Generate a diplomacy message from one power to another.

        Args:
            game_state_dict: Complete game state dictionary as returned by
                GameManager.get_game_state().
            sender: Name of the power sending the message.
            recipient: Name of the power receiving the message.

        Returns:
            A diplomatic message string.
        """
