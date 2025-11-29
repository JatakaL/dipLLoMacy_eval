"""
LLM Integration Module for Diplomacy Evaluation

This module provides:
- Abstract LLM interface for different providers
- Concrete adapters for OpenAI and Anthropic
- Prompt templates for game state analysis
- Evaluation harness for testing LLM decision-making

Usage:
    from llm import OpenAIAdapter, create_player
    
    # Create an LLM player
    player = create_player("openai", model="gpt-4")
    
    # Get orders for a game state
    orders = player.get_orders(game_state, power="Power1")
"""

from .base import LLMInterface, LLMPlayer
from .prompts import PromptTemplate, GameStateFormatter
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter

__all__ = [
    'LLMInterface',
    'LLMPlayer',
    'PromptTemplate',
    'GameStateFormatter',
    'OpenAIAdapter',
    'AnthropicAdapter',
]


def create_player(provider: str, **kwargs) -> 'LLMPlayer':
    """
    Factory function to create an LLM player.
    
    Args:
        provider: LLM provider ("openai" or "anthropic")
        **kwargs: Provider-specific configuration
        
    Returns:
        LLMPlayer instance
        
    Raises:
        ValueError: If provider is not supported
    """
    if provider.lower() == "openai":
        return OpenAIAdapter(**kwargs)
    elif provider.lower() == "anthropic":
        return AnthropicAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
