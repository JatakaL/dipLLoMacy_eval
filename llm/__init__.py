"""
LLM integration module for Diplomacy evaluation.

Provides adapter interfaces and implementations for connecting
Large Language Models to the Diplomacy game framework.
"""

from .adapters.base import BaseLLMAdapter
from .adapters.mock_adapter import MockLLMAdapter

__all__ = [
    'BaseLLMAdapter',
    'MockLLMAdapter',
]
