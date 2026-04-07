"""
Game moderator for orchestrating LLM agent turns in Diplomacy.

The GameModerator connects LLM adapters to the game engine, collecting
orders from agents each turn and feeding them through the game manager.
"""

from typing import Optional

from game.game_manager import GameManager
from game.game_state import Phase
from game.orders import OrderParser

from .adapters.base import BaseLLMAdapter


class GameModerator:
    """Orchestrates LLM agent turns in a Diplomacy game.

    The moderator drives the game loop: each turn it asks every agent
    adapter for orders, parses them, submits them to the game manager,
    handles retreats, and advances the phase.

    Args:
        game_manager: An initialized ``GameManager`` (``initialize_game``
            must have been called).
        agents: Mapping of power name to its LLM adapter.
    """

    def __init__(
        self,
        game_manager: GameManager,
        agents: dict[str, BaseLLMAdapter],
    ) -> None:
        self.game_manager = game_manager
        self.agents = agents

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_turn(self) -> dict:
        """Execute one full game turn (ORDER phase).

        Steps:
        1. Call ``generate_orders`` on each agent adapter.
        2. Parse returned order strings via ``OrderParser.parse``.
        3. Submit orders to ``game_manager.process_turn``.
        4. Auto-disband dislodged units that have no retreat options.
        5. Advance the game phase.

        Returns:
            A dict with keys ``"turn"``, ``"resolved_orders"``,
            ``"dislodged"``, and ``"log"``.
        """
        state = self.game_manager.state
        turn_label = state.get_turn_string()

        # 1-2. Collect and parse orders from each agent
        all_orders: dict[str, list] = {}
        for power_name, adapter in self.agents.items():
            state_dict = self.game_manager.get_game_state()
            order_strings = adapter.generate_orders(state_dict, power_name)
            parsed = [OrderParser.parse(s) for s in order_strings]
            for order in parsed:
                order.power = power_name
            all_orders[power_name] = parsed

        # 3. Submit orders to game manager
        resolved_orders, dislodged, log = self.game_manager.process_turn(
            all_orders
        )

        # 4. Auto-disband dislodged units with no retreat options
        for loc in list(state.dislodged_units.keys()):
            retreat_options = self.game_manager.get_retreat_options(loc)
            if not retreat_options:
                self.game_manager.disband_unit(loc)

        # 5. Advance game phase
        self.game_manager.advance_to_next_phase()

        # 6. Return result dict
        return {
            "turn": turn_label,
            "resolved_orders": [o.to_dict() for o in resolved_orders],
            "dislodged": dislodged,
            "log": log,
        }

    def run_game(self, max_turns: int = 50) -> dict:
        """Run turns until victory, elimination, or *max_turns*.

        A "turn" is counted each time the ORDER phase is processed via
        ``run_turn``.  Between ORDER phases the moderator automatically
        handles RETREAT (auto-disband remaining dislodged units) and
        BUILD (submit empty winter orders) phases.

        Args:
            max_turns: Maximum number of ORDER-phase turns to process.

        Returns:
            A dict with keys ``"turns_played"``, ``"winner"`` (or
            ``None``), ``"final_sc_counts"``, and ``"history"``.
        """
        history: list[dict] = []
        turns_played = 0
        winner: Optional[str] = None
        state = self.game_manager.state

        while turns_played < max_turns:
            if state.phase == Phase.ORDER:
                result = self.run_turn()
                history.append(result)
                turns_played += 1
            elif state.phase == Phase.RETREAT:
                # Auto-disband any remaining dislodged units
                for loc in list(state.dislodged_units.keys()):
                    self.game_manager.disband_unit(loc)
                self.game_manager.advance_to_next_phase()
            elif state.phase == Phase.BUILD:
                self.game_manager.process_winter_adjustments({})
                self.game_manager.advance_to_next_phase()

            # Check victory conditions
            for power in state.powers:
                if state.has_won(power):
                    winner = power
                    break

            if winner:
                break

            # Check if all but one power eliminated
            active = [
                p for p in state.powers if not state.is_eliminated(p)
            ]
            if len(active) <= 1:
                winner = active[0] if active else None
                break

        return {
            "turns_played": turns_played,
            "winner": winner,
            "final_sc_counts": {
                p: state.get_sc_count(p) for p in state.powers
            },
            "history": history,
        }
