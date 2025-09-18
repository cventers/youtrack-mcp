"""
OpenAI Client for YouTrack MCP Server.

Minimal OpenAI SDK adapter supporting configurable backends.
"""

import logging
import os
from typing import Any, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Minimal OpenAI SDK client with configurable backend support.

    Supports OpenAI-compatible APIs via base_url override.
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.7,
                 timeout: float = 30.0,
                 max_tokens: int = 1000):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for OpenAI-compatible API (defaults to OPENAI_BASE_URL env var)
            model: Model name (defaults to OPENAI_MODEL env var)
            temperature: Temperature for responses (defaults to OPENAI_TEMPERATURE env var)
            timeout: Request timeout in seconds (defaults to OPENAI_TIMEOUT env var)
            max_tokens: Maximum tokens for completion (defaults to OPENAI_MAX_TOKENS env var or 1000)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY)")

        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        temp_env = os.getenv("OPENAI_TEMPERATURE")
        if temp_env:
            try:
                self.temperature = float(temp_env)
            except ValueError:
                pass

        self.timeout = timeout
        timeout_env = os.getenv("OPENAI_TIMEOUT")
        if timeout_env:
            try:
                self.timeout = float(timeout_env)
            except ValueError:
                pass
        
        self.max_tokens = max_tokens
        max_tokens_env = os.getenv("OPENAI_MAX_TOKENS")
        if max_tokens_env:
            try:
                self.max_tokens = int(max_tokens_env)
            except ValueError:
                pass

        # Initialize client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        logger.info(f"OpenAIClient initialized with model {self.model}, max_tokens {self.max_tokens}")

    def complete(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> str:
        """
        Complete a prompt using the OpenAI API.

        Args:
            prompt: The user prompt
            system: Optional system message
            max_tokens: Maximum tokens in response (defaults to instance max_tokens)
            temperature: Temperature override

        Returns:
            The completion text
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
            
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                timeout=self.timeout
            )

            content = response.choices[0].message.content if response.choices else ""

            return content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")