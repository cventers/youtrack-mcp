"""LiteLLM + Instructor client for provider-agnostic structured outputs."""

import instructor
from litellm import acompletion
from typing import Type, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel
import structlog

T = TypeVar('T', bound=BaseModel)

logger = structlog.get_logger(__name__)


class LLMClient:
    """Provider-agnostic LLM client using LiteLLM and Instructor."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_retries: int = 3,
        retry_on_validation_error: bool = True,
        timeout: float = 60.0,
        temperature: float = 0.3,
        **kwargs
    ):
        """Initialize the LLM client with LiteLLM and Instructor.

        Args:
            model: Model name with optional provider prefix (e.g., "openai/gpt-4o-mini")
            api_key: API key for the provider
            api_base: Optional custom API base URL
            max_retries: Maximum number of retries for validation errors
            retry_on_validation_error: Whether to retry on Pydantic validation errors
            timeout: Request timeout in seconds
            temperature: Temperature for responses (0.0-2.0)
            **kwargs: Additional provider-specific parameters
        """
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.temperature = temperature
        self.timeout = timeout

        # Create instructor client from litellm's async completion
        self.client = instructor.from_litellm(
            acompletion,
            max_retries=max_retries,
            retry_on_validation_error=retry_on_validation_error
        )

        # Store additional kwargs for provider-specific settings
        self.kwargs = kwargs

        logger.info(
            "Initialized LLM client",
            model=model,
            has_api_key=bool(api_key),
            api_base=api_base
        )

    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> T:
        """Get a structured response from the LLM.

        Args:
            prompt: User prompt (ignored if messages provided)
            response_model: Pydantic model for structured output
            system: System message (ignored if messages provided)
            messages: Pre-formatted messages list (overrides prompt/system)
            **kwargs: Additional parameters to pass to LiteLLM

        Returns:
            Instance of response_model with validated data
        """
        # Build messages if not provided
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        # Merge kwargs with instance defaults
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "response_model": response_model,
            "temperature": self.temperature,
            "timeout": self.timeout,
            **self.kwargs
        }

        # Add API key and base if provided
        if self.api_key:
            call_kwargs["api_key"] = self.api_key
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        # Override with call-specific kwargs
        call_kwargs.update(kwargs)

        logger.debug(
            "Making LLM completion request",
            model=self.model,
            response_model=response_model.__name__,
            message_count=len(messages)
        )

        try:
            response = await self.client.create(**call_kwargs)
            logger.debug(
                "Received structured response",
                model=self.model,
                response_type=type(response).__name__
            )
            return response
        except Exception as e:
            logger.error(
                "LLM completion failed",
                model=self.model,
                error=str(e),
                response_model=response_model.__name__
            )
            raise

    async def complete_text(
        self,
        prompt: str,
        system: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """Get a text response from the LLM without structured output.

        Args:
            prompt: User prompt (ignored if messages provided)
            system: System message (ignored if messages provided)
            messages: Pre-formatted messages list (overrides prompt/system)
            **kwargs: Additional parameters to pass to LiteLLM

        Returns:
            Text response from the model
        """
        # Build messages if not provided
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        # Merge kwargs with instance defaults
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "timeout": self.timeout,
            **self.kwargs
        }

        # Add API key and base if provided
        if self.api_key:
            call_kwargs["api_key"] = self.api_key
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        # Override with call-specific kwargs
        call_kwargs.update(kwargs)

        logger.debug(
            "Making LLM text completion request",
            model=self.model,
            message_count=len(messages)
        )

        try:
            # Use direct litellm for text completion (no instructor)
            response = await acompletion(**call_kwargs)
            content = response.choices[0].message.content
            logger.debug(
                "Received text response",
                model=self.model,
                response_length=len(content) if content else 0
            )
            return content
        except Exception as e:
            logger.error(
                "LLM text completion failed",
                model=self.model,
                error=str(e)
            )
            raise