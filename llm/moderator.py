"""
Game moderator for orchestrating LLM agent turns in Diplomacy.

The GameModerator connects LLM adapters to the game engine, collecting
orders from agents each turn and feeding them through the game manager.
"""

from typing import Callable, Optional

from game.game_manager import GameManager
from game.game_state import GameState, Phase
from game.orders import Order, OrderParser

from .adapters.base import BaseLLMAdapter


def format_turn_summary(
    turn_result: dict,
    state: GameState,
    game_manager: GameManager,
) -> str:
    """Format a human-readable summary of a completed turn.

    The output includes the turn identifier, the orders submitted by
    each power (with resolution results), unit positions after
    resolution, and supply-center counts per power.

    Args:
        turn_result: The dict returned by ``GameModerator.run_turn``
            or the winter-build dict produced internally by ``run_game``.
        state: The game state *after* the turn has been processed.
        game_manager: The game manager (used for territory name lookup).

    Returns:
        A multi-line string suitable for printing to the console.
    """
    lines: list[str] = []
    turn_label = turn_result["turn"]

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"  TURN: {turn_label}")
    lines.append("=" * 60)

    # --- Orders by power ---
    orders_by_power: dict[str, list[dict]] = {}
    for order_dict in turn_result.get("resolved_orders", []):
        power = order_dict.get("power", "Unknown")
        orders_by_power.setdefault(power, []).append(order_dict)

    if orders_by_power:
        lines.append("")
        lines.append("  Orders:")
        for power in sorted(orders_by_power):
            lines.append(f"    {power}:")
            for od in orders_by_power[power]:
                display = _format_order_with_names(od, game_manager)
                result = od.get("result", "pending")
                lines.append(f"      {display}  [{result}]")

    # --- Winter adjustments log ---
    winter_log = turn_result.get("winter_log")
    if winter_log:
        lines.append("")
        lines.append("  Winter adjustments:")
        for log_line in winter_log.splitlines():
            lines.append(f"    {log_line}")

    # --- Dislodged units ---
    dislodged = turn_result.get("dislodged", {})
    if dislodged:
        lines.append("")
        lines.append("  Dislodged units:")
        for loc, attacker_loc in dislodged.items():
            loc_name = game_manager.get_territory_name(loc)
            att_name = game_manager.get_territory_name(attacker_loc)
            lines.append(f"    {loc_name} (by {att_name})")

    # --- Board state: unit positions ---
    lines.append("")
    lines.append("  Unit positions:")
    units_by_power: dict[str, list[str]] = {}
    for loc, unit in state.units.items():
        t = "A" if unit.unit_type.value == "army" else "F"
        name = game_manager.get_territory_name(loc)
        units_by_power.setdefault(unit.power, []).append(f"{t} {name}")
    for power in sorted(units_by_power):
        unit_list = ", ".join(sorted(units_by_power[power]))
        lines.append(f"    {power}: {unit_list}")

    # --- Supply-center counts ---
    lines.append("")
    lines.append("  Supply centers:")
    for power in sorted(state.powers):
        sc = state.get_sc_count(power)
        units = state.get_unit_count(power)
        lines.append(f"    {power:20s} : {sc} SCs, {units} units")

    lines.append("-" * 60)

    return "\n".join(lines)


def _format_order_with_names(od: dict, game_manager: GameManager) -> str:
    """Build a display string using territory names instead of cell IDs."""
    ut = od.get("unit_type", "?")
    loc = od.get("location", "?")
    loc_name = game_manager.get_territory_name(loc)
    otype = od.get("order_type", "hold")

    if otype == "move":
        target = od.get("target", "?")
        target_name = game_manager.get_territory_name(target)
        return f"{ut} {{{loc_name}}} M {{{target_name}}}"
    elif otype == "support":
        s_ut = od.get("support_unit_type", "?")
        s_from = od.get("support_from", "?")
        s_from_name = game_manager.get_territory_name(s_from)
        s_to = od.get("support_to")
        if s_to:
            s_to_name = game_manager.get_territory_name(s_to)
            return f"{ut} {{{loc_name}}} S {s_ut} {{{s_from_name}}} M {{{s_to_name}}}"
        return f"{ut} {{{loc_name}}} S {s_ut} {{{s_from_name}}} H"
    elif otype == "convoy":
        s_ut = od.get("support_unit_type", "?")
        s_from = od.get("support_from", "?")
        s_from_name = game_manager.get_territory_name(s_from)
        target = od.get("target", "?")
        target_name = game_manager.get_territory_name(target)
        return f"{ut} {{{loc_name}}} C {s_ut} {{{s_from_name}}} M {{{target_name}}}"
    elif otype == "retreat":
        target = od.get("target", "?")
        target_name = game_manager.get_territory_name(target)
        return f"{ut} {{{loc_name}}} R {{{target_name}}}"
    elif otype == "disband":
        return f"{ut} {{{loc_name}}} D"
    elif otype == "build":
        return f"B {ut} {{{loc_name}}}"
    return f"{ut} {{{loc_name}}} H"


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
        all_orders: dict[str, list[Order]] = {}
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

    def run_game(
        self,
        max_turns: int = 50,
        turn_callback: Optional[Callable[[dict, "GameModerator", int], None]] = None,
    ) -> dict:
        """Run turns until victory, elimination, or *max_turns*.

        A "turn" is counted each time the ORDER phase is processed via
        ``run_turn``.  Between ORDER phases the moderator automatically
        handles RETREAT (auto-disband remaining dislodged units) and
        BUILD (submit empty winter orders) phases.

        Args:
            max_turns: Maximum number of ORDER-phase turns to process.
            turn_callback: Optional callable invoked after each ORDER
                turn and each BUILD phase with
                ``(turn_result, moderator, step_number)`` where
                *step_number* is a 1-based sequential counter across
                all reported phases.

        Returns:
            A dict with keys ``"turns_played"``, ``"winner"`` (or
            ``None``), ``"final_sc_counts"``, and ``"history"``.
        """
        history: list[dict] = []
        turns_played = 0
        step_number = 0
        winner: Optional[str] = None
        state = self.game_manager.state

        while turns_played < max_turns:
            if state.phase == Phase.ORDER:
                result = self.run_turn()
                history.append(result)
                turns_played += 1
                step_number += 1
                if turn_callback is not None:
                    turn_callback(result, self, step_number)
            elif state.phase == Phase.RETREAT:
                # Auto-disband any remaining dislodged units
                for loc in list(state.dislodged_units.keys()):
                    self.game_manager.disband_unit(loc)
                self.game_manager.advance_to_next_phase()
            elif state.phase == Phase.BUILD:
                winter_log = self.game_manager.process_winter_adjustments({})
                winter_result = {
                    "turn": f"Winter {state.year}",
                    "winter_log": winter_log,
                    "resolved_orders": [],
                    "dislodged": {},
                    "log": winter_log,
                }
                history.append(winter_result)
                step_number += 1
                if turn_callback is not None:
                    turn_callback(winter_result, self, step_number)
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
