"""
Prompt templates for LLM Diplomacy players.

This module contains:
- Default prompts for order generation, diplomacy, and analysis
- GameStateFormatter for converting game state to text
- Customizable prompt templates
"""

from typing import Dict, List, Any


# Default prompt for getting orders
DEFAULT_ORDER_PROMPT = """You are playing as {power} in a game of Diplomacy.

CURRENT GAME STATE:
{game_state}

VALID ORDERS:
{valid_orders}

Based on the game state and your strategic objectives, provide your orders for this turn.

INSTRUCTIONS:
1. Analyze the current position and threats
2. Consider which territories to attack, defend, or support
3. Issue one order per unit you control

OUTPUT FORMAT:
Provide each order on a separate line in this format:
LOCATION: ORDER

Examples:
Paris: HOLD
Munich: MOVE Berlin
London: SUPPORT Paris
Marseilles: SUPPORT Paris -> Burgundy
North Sea: CONVOY London -> Norway

YOUR ORDERS:"""


# Default prompt for diplomatic messages
DEFAULT_DIPLOMACY_PROMPT = """You are playing as {power} in a game of Diplomacy.

CURRENT GAME STATE:
{game_state}

You need to send a diplomatic message to {recipient}.

{context}

Write a message that:
1. Is strategic and advances your position
2. Sounds genuine and builds trust (if appropriate)
3. May include proposals for coordination or alliance
4. Is appropriately brief (2-4 sentences)

YOUR MESSAGE TO {recipient}:"""


# Default prompt for position analysis
DEFAULT_ANALYSIS_PROMPT = """You are playing as {power} in a game of Diplomacy.

CURRENT GAME STATE:
{game_state}

Analyze your current position and provide:
1. Your strategic strengths and weaknesses
2. The most significant threats you face
3. Opportunities for expansion or alliance
4. Recommended short-term and long-term strategies

ANALYSIS:"""


class GameStateFormatter:
    """
    Formats game state dictionaries into human-readable text for LLM prompts.
    """
    
    def format_game_state(self, state: dict) -> str:
        """
        Format a complete game state for LLM consumption.
        
        Args:
            state: Game state dictionary from GameEngine.get_game_state_for_llm()
            
        Returns:
            Formatted text representation
        """
        lines = []
        
        # Basic info
        lines.append(f"Year: {state.get('year', 'Unknown')}")
        lines.append(f"Phase: {state.get('phase', 'Unknown')}")
        lines.append("")
        
        # Your power's info
        power = state.get("power", "Unknown")
        lines.append(f"YOU ARE: {power}")
        lines.append("")
        
        # Your units
        your_units = state.get("your_units", [])
        lines.append("YOUR UNITS:")
        if your_units:
            for unit in your_units:
                unit_type = unit.get("type", "?").upper()
                location = unit.get("location", "?")
                prov_name = self._get_province_name(state, location)
                lines.append(f"  - {unit_type} at {prov_name} ({location})")
        else:
            lines.append("  None")
        lines.append("")
        
        # Your supply centers
        your_scs = state.get("your_supply_centers", [])
        lines.append(f"YOUR SUPPLY CENTERS ({len(your_scs)}):")
        if your_scs:
            for sc in your_scs:
                prov_name = self._get_province_name(state, sc)
                lines.append(f"  - {prov_name} ({sc})")
        else:
            lines.append("  None")
        lines.append("")
        
        # Other units on the board
        all_units = state.get("all_units", [])
        other_units = [u for u in all_units if u.get("power") != power]
        
        lines.append("OTHER POWERS' UNITS:")
        if other_units:
            by_power = {}
            for unit in other_units:
                unit_power = unit.get("power", "Unknown")
                if unit_power not in by_power:
                    by_power[unit_power] = []
                by_power[unit_power].append(unit)
            
            for other_power, units in sorted(by_power.items()):
                lines.append(f"  {other_power}:")
                for unit in units:
                    unit_type = unit.get("type", "?").upper()
                    location = unit.get("location", "?")
                    prov_name = self._get_province_name(state, location)
                    lines.append(f"    - {unit_type} at {prov_name} ({location})")
        else:
            lines.append("  None visible")
        lines.append("")
        
        # Supply center ownership
        supply_centers = state.get("supply_centers", {})
        lines.append("SUPPLY CENTER OWNERSHIP:")
        sc_by_power = {"Neutral": []}
        for sc_loc, owner in supply_centers.items():
            if owner is None:
                sc_by_power["Neutral"].append(sc_loc)
            else:
                if owner not in sc_by_power:
                    sc_by_power[owner] = []
                sc_by_power[owner].append(sc_loc)
        
        for sc_power, scs in sorted(sc_by_power.items()):
            if scs:
                sc_names = [f"{self._get_province_name(state, sc)} ({sc})" for sc in scs]
                lines.append(f"  {sc_power} ({len(scs)}): {', '.join(sc_names)}")
        lines.append("")
        
        # Adjacent provinces for your units
        lines.append("YOUR UNITS' ADJACENCIES:")
        adjacency = state.get("adjacency", {})
        for unit in your_units:
            location = unit.get("location", "")
            adj = adjacency.get(location, [])
            adj_names = [f"{self._get_province_name(state, a)}" for a in adj]
            prov_name = self._get_province_name(state, location)
            lines.append(f"  {prov_name} ({location}) borders: {', '.join(adj_names)}")
        
        return "\n".join(lines)
    
    def _get_province_name(self, state: dict, location: str) -> str:
        """Get the human-readable name for a province."""
        provinces = state.get("provinces", {})
        if location in provinces:
            return provinces[location].get("name", location)
        return location
    
    def format_orders_for_review(self, orders: List[dict]) -> str:
        """
        Format a list of orders for review/confirmation.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            Formatted text
        """
        if not orders:
            return "No orders submitted."
        
        lines = ["Orders:"]
        for order in orders:
            lines.append(f"  - {order.get('description', str(order))}")
        return "\n".join(lines)


class PromptLibrary:
    """
    A library of prompt templates for different scenarios.
    """
    
    # Strategic prompts
    AGGRESSIVE = """You are playing as {power} in a game of Diplomacy.
You prefer aggressive, expansionist strategies.

{game_state}

Focus on:
1. Identifying weak neighbors to attack
2. Building strength quickly
3. Taking calculated risks for expansion

YOUR ORDERS:"""

    DEFENSIVE = """You are playing as {power} in a game of Diplomacy.
You prefer careful, defensive strategies.

{game_state}

Focus on:
1. Protecting your supply centers
2. Building stable alliances
3. Avoiding overextension

YOUR ORDERS:"""

    DIPLOMATIC = """You are playing as {power} in a game of Diplomacy.
You excel at negotiation and alliance building.

{game_state}

Focus on:
1. Coordinating with potential allies
2. Avoiding unnecessary conflicts
3. Building trust through reliable moves

YOUR ORDERS:"""

    @classmethod
    def get_template(cls, style: str) -> str:
        """Get a prompt template by style name."""
        templates = {
            "aggressive": cls.AGGRESSIVE,
            "defensive": cls.DEFENSIVE,
            "diplomatic": cls.DIPLOMATIC,
            "default": DEFAULT_ORDER_PROMPT
        }
        return templates.get(style.lower(), DEFAULT_ORDER_PROMPT)
