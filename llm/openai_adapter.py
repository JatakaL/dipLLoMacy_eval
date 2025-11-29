"""
OpenAI API adapter for Diplomacy LLM integration.

This module provides an adapter for using OpenAI's GPT models
as Diplomacy players.
"""

import os
from typing import Optional

from .base import LLMInterface, LLMPlayer


class OpenAIAdapter(LLMPlayer):
    """
    Adapter for OpenAI's GPT models.
    
    Uses the OpenAI API to generate completions for Diplomacy game play.
    
    Environment Variables:
        OPENAI_API_KEY: Your OpenAI API key
    """
    
    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 1000):
        """
        Initialize the OpenAI adapter.
        
        Args:
            model: Model to use (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None
        
        # Initialize as LLMPlayer with self as the LLM interface
        super().__init__(llm=self)
    
    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. "
                    "Install with: pip install openai"
                )
        return self._client
    
    def complete(self, prompt: str, **kwargs) -> str:
        """
        Send a prompt to OpenAI and get a completion.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            The model's response text
        """
        client = self._get_client()
        
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert Diplomacy player."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        return f"openai/{self.model}"


class MockOpenAIAdapter(LLMPlayer):
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
        return "mock/openai"
