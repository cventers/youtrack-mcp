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
                 timeout: float = 30.0):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for OpenAI-compatible API (defaults to OPENAI_BASE_URL env var)
            model: Model name (defaults to OPENAI_MODEL env var)
            temperature: Temperature for responses (defaults to OPENAI_TEMPERATURE env var)
            timeout: Request timeout in seconds (defaults to OPENAI_TIMEOUT env var)
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

        # Initialize client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        logger.info(f"OpenAIClient initialized with model {self.model}")

    def complete(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Complete a prompt using OpenAI API.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Temperature override

        Returns:
            Dict with 'content', 'usage', 'confidence' keys
        """
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature or self.temperature,
                timeout=self.timeout
            )

            content = response.choices[0].message.content if response.choices else ""

            return {
                "content": content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "confidence": 0.8  # Default confidence for successful responses
            }

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API call failed: {str(e)}")