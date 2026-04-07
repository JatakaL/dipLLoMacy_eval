"""
LLM adapter implementations for various providers.

Contains the base adapter interface and provider-specific implementations.
"""

from .base import BaseLLMAdapter
from .mock_adapter import MockLLMAdapter

__all__ = [
    'BaseLLMAdapter',
    'MockLLMAdapter',
]
