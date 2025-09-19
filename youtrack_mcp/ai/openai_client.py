"""
OpenAI Client for YouTrack MCP Server.

Enhanced OpenAI SDK adapter with structured output support and three enforcement modes.
"""

import asyncio
import json
import logging
import os
import re
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .errors import StructuredOutputError, ProviderError

logger = logging.getLogger(__name__)


class OutputMode(str, Enum):
    """Output mode for structured responses."""
    JSON_SCHEMA = "json_schema"  # Strict server-side enforcement - JSON always required
    JSON_OBJECT = "json_object"  # Provider JSON + local validation - JSON always required
    INLINE = "inline"            # Schema in prompt - JSON always required


T = TypeVar('T', bound=BaseModel)


class OpenAIClient:
    """
    Enhanced OpenAI SDK client with structured output support.

    Supports three output modes for JSON enforcement:
    - JSON_SCHEMA: OpenAI enforces both JSON format and schema server-side
    - JSON_OBJECT: OpenAI enforces JSON format, we validate schema locally
    - INLINE: We extract JSON and validate schema locally, retry if either fails
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 temperature: float = 0.7,
                 timeout: float = 30.0,
                 max_tokens: int = 1000,
                 mode: OutputMode = OutputMode.JSON_SCHEMA,
                 max_retries: int = 3,
                 initial_backoff: float = 1.0,
                 backoff_multiplier: float = 2.0):
        """
        Initialize OpenAI client with structured output support.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for OpenAI-compatible API (defaults to OPENAI_BASE_URL env var)
            model: Model name (defaults to OPENAI_MODEL env var)
            temperature: Temperature for responses (defaults to OPENAI_TEMPERATURE env var)
            timeout: Request timeout in seconds (defaults to OPENAI_TIMEOUT env var)
            max_tokens: Maximum tokens for completion (defaults to OPENAI_MAX_TOKENS env var or 1000)
            mode: Output mode for structured responses (defaults to LLM_OUTPUT_MODE env var)
            max_retries: Maximum retry attempts (defaults to LLM_MAX_RETRIES env var)
            initial_backoff: Initial backoff delay in seconds
            backoff_multiplier: Backoff multiplier for exponential backoff
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

        # Structured output configuration
        mode_env = os.getenv("LLM_OUTPUT_MODE", "json_schema")
        try:
            self.mode = OutputMode(mode_env.lower())
        except ValueError:
            logger.warning(f"Invalid LLM_OUTPUT_MODE '{mode_env}', using JSON_SCHEMA")
            self.mode = OutputMode.JSON_SCHEMA

        self.max_retries = max_retries
        retries_env = os.getenv("LLM_MAX_RETRIES")
        if retries_env:
            try:
                self.max_retries = int(retries_env)
            except ValueError:
                pass

        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier

        # Initialize client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

        logger.info(f"OpenAIClient initialized with model {self.model}, mode {self.mode}, max_tokens {self.max_tokens}")

    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> T:
        """
        Generate structured output with mode-based enforcement.

        JSON is always required and validated, enforcement method varies by OutputMode:
        - JSON_SCHEMA: OpenAI enforces both JSON format and schema server-side
        - JSON_OBJECT: OpenAI enforces JSON format, we validate schema locally
        - INLINE: We extract JSON and validate schema locally, retry if either fails

        Args:
            prompt: The user prompt
            response_model: Pydantic model class for response validation
            system: Optional system message
            max_tokens: Maximum tokens in response (defaults to instance max_tokens)
            temperature: Temperature override

        Returns:
            Validated instance of response_model

        Raises:
            StructuredOutputError: If validation fails after retries
            ProviderError: If provider API fails
        """
        if max_tokens is None:
            max_tokens = self.max_tokens

        if temperature is None:
            temperature = self.temperature

        if self.mode == OutputMode.JSON_SCHEMA:
            return await self._json_schema_mode(prompt, response_model, system, max_tokens, temperature)
        elif self.mode == OutputMode.JSON_OBJECT:
            return await self._json_object_mode(prompt, response_model, system, max_tokens, temperature)
        else:  # INLINE
            return await self._inline_mode(prompt, response_model, system, max_tokens, temperature)

    async def _json_schema_mode(
        self,
        prompt: str,
        model: Type[T],
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> T:
        """Use OpenAI's strict json_schema enforcement."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system or "Output only the JSON object."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": model.__name__,
                        "strict": True,
                        "schema": model.model_json_schema()
                    }
                },
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Log warning if approaching or exceeding token limits
            if hasattr(response, 'usage'):
                if response.usage.total_tokens > 4000:
                    logger.warning(f"High token usage: {response.usage.total_tokens} total tokens")
                if response.usage.completion_tokens >= max_tokens * 0.95:
                    logger.warning(f"Response near max_tokens limit: {response.usage.completion_tokens}/{max_tokens}")

            content = response.choices[0].message.content
            return model.model_validate_json(content)

        except ValidationError as e:
            raise StructuredOutputError(
                fields=e.errors(),
                message="JSON schema validation failed",
                last_raw=content if 'content' in locals() else None,
                attempt_count=1,
                request_id=response.id if 'response' in locals() else None
            )
        except Exception as e:
            logger.error(f"OpenAI API error in json_schema mode: {e}")
            raise ProviderError(
                message=str(e),
                request_id=response.id if 'response' in locals() else None
            )

    async def _json_object_mode(
        self,
        prompt: str,
        model: Type[T],
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> T:
        """Use json_object with local validation and retries."""
        last_error = None
        last_content = None

        for attempt in range(self.max_retries):
            try:
                # Add retry context to prompt if not first attempt
                retry_prompt = prompt
                if attempt > 0 and last_error:
                    retry_prompt += f"\n\nFix these validation errors: {last_error}"

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system or f"Return JSON matching: {model.model_json_schema()}"},
                        {"role": "user", "content": retry_prompt}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                last_content = response.choices[0].message.content

                try:
                    return model.model_validate_json(last_content)
                except ValidationError as e:
                    last_error = e.errors()
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.initial_backoff * (self.backoff_multiplier ** attempt))
                    else:
                        raise StructuredOutputError(
                            fields=last_error,
                            message="Validation failed after retries",
                            last_raw=last_content,
                            attempt_count=attempt + 1,
                            request_id=response.id
                        )

            except StructuredOutputError:
                raise
            except Exception as e:
                logger.error(f"OpenAI API error in json_object mode: {e}")
                raise ProviderError(
                    message=str(e),
                    request_id=response.id if 'response' in locals() else None
                )

    async def _inline_mode(
        self,
        prompt: str,
        model: Type[T],
        system: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> T:
        """Include schema in prompt with validation and retries."""
        schema_str = self._compact_schema(model)
        enhanced_prompt = f"{prompt}\n\nOutput JSON matching: {schema_str}"
        last_content = None

        for attempt in range(self.max_retries):
            try:
                # Add retry context if not first attempt
                if attempt > 0:
                    enhanced_prompt += f"\n\nIMPORTANT: You MUST return valid JSON. Previous attempt failed."

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system or "Output valid JSON only."},
                        {"role": "user", "content": enhanced_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                last_content = response.choices[0].message.content

                # Extract JSON from response
                json_data = self._extract_json(last_content)
                if json_data is None:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.initial_backoff * (self.backoff_multiplier ** attempt))
                        continue
                    else:
                        raise StructuredOutputError(
                            fields={"json_extraction": "No valid JSON found in response"},
                            message="Failed to extract JSON from response",
                            last_raw=last_content,
                            attempt_count=attempt + 1,
                            request_id=response.id
                        )

                # Validate against model
                try:
                    return model.model_validate(json_data)
                except ValidationError as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.initial_backoff * (self.backoff_multiplier ** attempt))
                        enhanced_prompt += f"\n\nFix validation errors: {e.errors()}"
                    else:
                        raise StructuredOutputError(
                            fields=e.errors(),
                            message="Schema validation failed after retries",
                            last_raw=last_content,
                            attempt_count=attempt + 1,
                            request_id=response.id
                        )

            except StructuredOutputError:
                raise
            except Exception as e:
                logger.error(f"OpenAI API error in inline mode: {e}")
                raise ProviderError(
                    message=str(e),
                    request_id=response.id if 'response' in locals() else None
                )

    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response content."""
        # Try direct parsing first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        if "```json" in content:
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        # Try generic code block
        if "```" in content:
            match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object in text
        json_start = content.find('{')
        json_end = content.rfind('}')
        if json_start != -1 and json_end != -1:
            try:
                return json.loads(content[json_start:json_end + 1])
            except json.JSONDecodeError:
                pass

        return None

    def _compact_schema(self, model: Type[BaseModel]) -> str:
        """Generate compact schema representation for inline mode."""
        schema = model.model_json_schema()
        # Remove unnecessary fields for compactness
        if 'title' in schema:
            del schema['title']
        if 'description' in schema:
            del schema['description']
        return json.dumps(schema, separators=(',', ':'))

    def complete(self,
                 prompt: str,
                 system: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> str:
        """
        Complete a prompt using the OpenAI API (backward compatibility).

        This method is kept for backward compatibility. For new code,
        use complete_structured with a Pydantic model.

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