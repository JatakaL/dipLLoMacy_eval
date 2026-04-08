"""
LLM integration module for Diplomacy evaluation.

Provides adapter interfaces and implementations for connecting
Large Language Models to the Diplomacy game framework.
"""

from .adapters.base import BaseLLMAdapter
from .adapters.mock_adapter import MockLLMAdapter
from .adapters.random_adapter import RandomLLMAdapter
from .moderator import GameModerator, format_turn_summary

__all__ = [
    'BaseLLMAdapter',
    'MockLLMAdapter',
    'RandomLLMAdapter',
    'GameModerator',
    'format_turn_summary',
]
