"""
Anthropic API adapter for Diplomacy LLM integration.

This module provides an adapter for using Anthropic's Claude models
as Diplomacy players.
"""

import os
from typing import Optional

from .base import LLMInterface, LLMPlayer


class AnthropicAdapter(LLMPlayer):
    """
    Adapter for Anthropic's Claude models.
    
    Uses the Anthropic API to generate completions for Diplomacy game play.
    
    Environment Variables:
        ANTHROPIC_API_KEY: Your Anthropic API key
    """
    
    def __init__(self, model: str = "claude-3-sonnet-20240229", 
                 api_key: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 1000):
        """
        Initialize the Anthropic adapter.
        
        Args:
            model: Model to use (e.g., "claude-3-opus-20240229", "claude-3-sonnet-20240229")
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        
        # Initialize as LLMPlayer with self as the LLM interface
        super().__init__(llm=self)
    
    def _get_client(self):
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client
    
    def complete(self, prompt: str, **kwargs) -> str:
        """
        Send a prompt to Anthropic and get a completion.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            The model's response text
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are an expert Diplomacy player.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        return f"anthropic/{self.model}"


class MockAnthropicAdapter(LLMPlayer):
    """
    Mock adapter for testing without API calls.
    
    Returns predefined responses for testing purposes.
    """
    
    def __init__(self, responses: Optional[dict] = None):
        """
        Initialize the mock adapter.
        
        Args:
            responses: Dictionary mapping prompt patterns to responses
        """
        self.responses = responses or {}
        self.call_history = []
        super().__init__(llm=self)
    
    def complete(self, prompt: str, **kwargs) -> str:
        """Return a mock response."""
        self.call_history.append(prompt)
        
        # Check for matching response
        for pattern, response in self.responses.items():
            if pattern.lower() in prompt.lower():
                return response
        
        # Default: return hold orders for any units mentioned
        return self._generate_default_orders(prompt)
    
    def _generate_default_orders(self, prompt: str) -> str:
        """Generate default hold orders based on the prompt."""
        lines = []
        # Look for unit locations in the prompt
        if "YOUR UNITS:" in prompt:
            start = prompt.find("YOUR UNITS:")
            end = prompt.find("\n\n", start)
            unit_section = prompt[start:end] if end > 0 else prompt[start:]
            
            for line in unit_section.split("\n"):
                if " at " in line:
                    # Extract location
                    parts = line.split(" at ")
                    if len(parts) >= 2:
                        location = parts[1].split()[0].strip("()")
                        lines.append(f"{location}: HOLD")
        
        return "\n".join(lines) if lines else "No orders"
    
    def get_model_name(self) -> str:
        """Get the name of the mock model."""
        return "mock/anthropic"
