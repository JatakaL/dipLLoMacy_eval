"""
Evaluation metrics for LLM Diplomacy performance assessment.

Provides metric classes for three categories of evaluation:
- PerformanceMetrics: game outcomes, supply center counts, longevity
- StrategicMetrics: order validity, tactical soundness, support utilization
- DiplomaticMetrics: alliance formation, promise keeping, communication quality

Each class collects per-game data and computes aggregate summaries.
"""

from __future__ import annotations


class PerformanceMetrics:
    """Tracks game-outcome metrics across multiple evaluation games.

    Records wins, survivals, supply center counts, and game length
    for each completed game, then computes aggregate statistics.
    """

    def __init__(self) -> None:
        self.games_played: int = 0
        self.wins: int = 0
        self.survivals: int = 0
        self.sc_counts: list[int] = []
        self.turns_survived: list[int] = []

    def add_game_result(self, result: dict) -> None:
        """Record metrics from a completed game.

        Args:
            result: Dictionary with keys ``"won"`` (bool),
                ``"survived"`` (bool), ``"final_sc_count"`` (int),
                and ``"turns"`` (int).
        """
        self.games_played += 1
        if result.get("won", False):
            self.wins += 1
        if result.get("survived", False):
            self.survivals += 1
        self.sc_counts.append(result.get("final_sc_count", 0))
        self.turns_survived.append(result.get("turns", 0))

    def compute_summary(self) -> dict:
        """Return aggregate performance statistics.

        Returns:
            Dictionary containing win_rate, survival_rate,
            avg_sc_count, and avg_turns_survived.  Returns zeroes
            when no games have been recorded.
        """
        if self.games_played == 0:
            return {
                "games_played": 0,
                "win_rate": 0.0,
                "survival_rate": 0.0,
                "avg_sc_count": 0.0,
                "avg_turns_survived": 0.0,
            }
        return {
            "games_played": self.games_played,
            "win_rate": self.wins / self.games_played,
            "survival_rate": self.survivals / self.games_played,
            "avg_sc_count": sum(self.sc_counts) / len(self.sc_counts),
            "avg_turns_survived": (
                sum(self.turns_survived) / len(self.turns_survived)
            ),
        }


class StrategicMetrics:
    """Tracks strategic quality metrics for order evaluation.

    Measures order validity rates, support utilization, and
    offensive/defensive effectiveness across games.
    """

    def __init__(self) -> None:
        self.total_orders: int = 0
        self.valid_orders: int = 0
        self.support_orders: int = 0
        self.successful_supports: int = 0
        self.attacks: int = 0
        self.successful_attacks: int = 0

    def record_orders(self, orders: list[dict]) -> None:
        """Record order outcomes for a single turn.

        Args:
            orders: List of order dictionaries, each containing
                ``"valid"`` (bool), ``"type"`` (str), and
                ``"success"`` (bool).
        """
        for order in orders:
            self.total_orders += 1
            if order.get("valid", False):
                self.valid_orders += 1
            order_type = order.get("type", "")
            if order_type == "support":
                self.support_orders += 1
                if order.get("success", False):
                    self.successful_supports += 1
            elif order_type == "move":
                self.attacks += 1
                if order.get("success", False):
                    self.successful_attacks += 1

    def compute_summary(self) -> dict:
        """Return aggregate strategic quality statistics.

        Returns:
            Dictionary containing order_validity_rate,
            support_success_rate, and attack_success_rate.
            Returns zeroes when no data has been recorded.
        """
        return {
            "total_orders": self.total_orders,
            "order_validity_rate": (
                self.valid_orders / self.total_orders
                if self.total_orders > 0
                else 0.0
            ),
            "support_success_rate": (
                self.successful_supports / self.support_orders
                if self.support_orders > 0
                else 0.0
            ),
            "attack_success_rate": (
                self.successful_attacks / self.attacks
                if self.attacks > 0
                else 0.0
            ),
        }


class DiplomaticMetrics:
    """Tracks diplomatic and negotiation quality metrics.

    Measures alliance formation success, promise keeping rates,
    and communication quality scores for press-game evaluations.
    """

    def __init__(self) -> None:
        self.messages_sent: int = 0
        self.alliances_proposed: int = 0
        self.alliances_formed: int = 0
        self.promises_made: int = 0
        self.promises_kept: int = 0

    def record_message(self, message_info: dict) -> None:
        """Record metadata about a diplomatic message.

        Args:
            message_info: Dictionary with optional keys
                ``"alliance_proposed"`` (bool),
                ``"alliance_formed"`` (bool),
                ``"promise_made"`` (bool), and
                ``"promise_kept"`` (bool).
        """
        self.messages_sent += 1
        if message_info.get("alliance_proposed", False):
            self.alliances_proposed += 1
        if message_info.get("alliance_formed", False):
            self.alliances_formed += 1
        if message_info.get("promise_made", False):
            self.promises_made += 1
        if message_info.get("promise_kept", False):
            self.promises_kept += 1

    def compute_summary(self) -> dict:
        """Return aggregate diplomatic quality statistics.

        Returns:
            Dictionary containing messages_sent,
            alliance_formation_rate, and promise_keeping_rate.
            Returns zeroes when no data has been recorded.
        """
        return {
            "messages_sent": self.messages_sent,
            "alliance_formation_rate": (
                self.alliances_formed / self.alliances_proposed
                if self.alliances_proposed > 0
                else 0.0
            ),
            "promise_keeping_rate": (
                self.promises_kept / self.promises_made
                if self.promises_made > 0
                else 0.0
            ),
        }
