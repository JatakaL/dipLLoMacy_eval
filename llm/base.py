"""
Base classes for LLM integration.

This module defines the abstract interface that all LLM adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.orders import Order, parse_order


class LLMInterface(ABC):
    """
    Abstract base class for LLM interfaces.
    
    All LLM adapters (OpenAI, Anthropic, etc.) must implement this interface.
    """
    
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """
        Send a prompt to the LLM and get a completion.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional provider-specific parameters
            
        Returns:
            The LLM's response text
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name/identifier of the model being used."""
        pass


class LLMPlayer:
    """
    An LLM-based Diplomacy player.
    
    Wraps an LLM interface and provides methods for:
    - Getting orders for a game state
    - Generating diplomatic messages
    - Analyzing game positions
    """
    
    def __init__(self, llm: LLMInterface, prompt_template: Optional['PromptTemplate'] = None):
        """
        Initialize an LLM player.
        
        Args:
            llm: The LLM interface to use
            prompt_template: Optional custom prompt template
        """
        self.llm = llm
        self.prompt_template = prompt_template
    
    def get_orders(self, game_state: dict, power: str) -> List[Order]:
        """
        Get orders from the LLM for a power.
        
        Args:
            game_state: Current game state (from GameEngine.get_game_state_for_llm)
            power: The power to get orders for
            
        Returns:
            List of Order objects
        """
        from .prompts import GameStateFormatter, DEFAULT_ORDER_PROMPT
        
        # Format game state
        formatter = GameStateFormatter()
        state_text = formatter.format_game_state(game_state)
        
        # Build prompt
        prompt = DEFAULT_ORDER_PROMPT.format(
            power=power,
            game_state=state_text,
            valid_orders=self._format_valid_orders(game_state.get("valid_orders", []))
        )
        
        # Get LLM response
        response = self.llm.complete(prompt)
        
        # Parse orders from response
        orders = self._parse_orders(response, power)
        
        return orders
    
    def get_diplomatic_message(self, game_state: dict, power: str, 
                               recipient: str, context: str = "") -> str:
        """
        Get a diplomatic message from the LLM.
        
        Args:
            game_state: Current game state
            power: The power sending the message
            recipient: The power receiving the message
            context: Optional context for the message
            
        Returns:
            The diplomatic message
        """
        from .prompts import GameStateFormatter, DEFAULT_DIPLOMACY_PROMPT
        
        formatter = GameStateFormatter()
        state_text = formatter.format_game_state(game_state)
        
        prompt = DEFAULT_DIPLOMACY_PROMPT.format(
            power=power,
            recipient=recipient,
            game_state=state_text,
            context=context
        )
        
        response = self.llm.complete(prompt)
        return response.strip()
    
    def analyze_position(self, game_state: dict, power: str) -> str:
        """
        Get an analysis of the current position.
        
        Args:
            game_state: Current game state
            power: The power to analyze for
            
        Returns:
            Position analysis text
        """
        from .prompts import GameStateFormatter, DEFAULT_ANALYSIS_PROMPT
        
        formatter = GameStateFormatter()
        state_text = formatter.format_game_state(game_state)
        
        prompt = DEFAULT_ANALYSIS_PROMPT.format(
            power=power,
            game_state=state_text
        )
        
        response = self.llm.complete(prompt)
        return response.strip()
    
    def _format_valid_orders(self, valid_orders: List[dict]) -> str:
        """Format valid orders for the prompt."""
        if not valid_orders:
            return "No valid orders available."
        
        lines = []
        for order in valid_orders:
            lines.append(f"  - {order.get('description', str(order))}")
        return "\n".join(lines)
    
    def _parse_orders(self, response: str, power: str) -> List[Order]:
        """
        Parse orders from LLM response.
        
        Expected format (one per line):
        LOCATION: ORDER_TYPE [TARGET]
        
        Examples:
        Paris: HOLD
        Munich: MOVE Berlin
        London: SUPPORT Paris -> Burgundy
        """
        orders = []
        
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Try to parse the line
            order = parse_order(line, power)
            if order:
                orders.append(order)
            else:
                # Try alternate format: "Location: OrderType Target"
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        location = parts[0].strip()
                        order_text = f"{location} {parts[1].strip()}"
                        order = parse_order(order_text, power)
                        if order:
                            orders.append(order)
        
        return orders


class PromptTemplate:
    """
    Base class for prompt templates.
    
    Allows customization of prompts for different LLM models or play styles.
    """
    
    def __init__(self, template: str, name: str = "custom"):
        """
        Initialize a prompt template.
        
        Args:
            template: The template string with {placeholders}
            name: Name identifier for this template
        """
        self.template = template
        self.name = name
    
    def format(self, **kwargs) -> str:
        """Format the template with provided values."""
        return self.template.format(**kwargs)
