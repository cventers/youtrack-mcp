"""LiteLLM + Instructor client for provider-agnostic structured outputs."""

import instructor
from litellm import acompletion
from typing import Type, TypeVar, Optional, List, Dict, Any, Callable
from pydantic import BaseModel
import structlog
import asyncio

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
        timeout: float = 60.0,
        temperature: float = 0.3,
        **kwargs
    ):
        """Initialize the LLM client with LiteLLM and Instructor.

        Args:
            model: Model name with optional provider prefix (e.g., "openai/gpt-4o-mini")
            api_key: API key for the provider
            api_base: Optional custom API base URL
            max_retries: Maximum number of retries for validation errors (0 disables retries)
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
        # Note: max_retries should NOT be passed here as it causes conflicts
        # It should only be passed in the create() call
        self.client = instructor.from_litellm(acompletion)

        # Store retry settings for use in create() calls
        # When max_retries > 0, Instructor automatically retries on validation errors
        self.max_retries = max_retries

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
        response_model: Type[T],
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> T:
        """Get a structured response from the LLM.

        Args:
            response_model: Pydantic model for structured output
            messages: Pre-formatted messages list (if provided, overrides prompt/system)
            prompt: User prompt (only used if messages not provided)
            system: System message (only used if messages not provided)
            **kwargs: Additional parameters to pass to LiteLLM

        Returns:
            Instance of response_model with validated data
        """
        # Build messages if not provided
        if messages is None:
            if prompt is None:
                raise ValueError("Either messages or prompt must be provided")
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
            response = await self.client.chat.completions.create(
                max_retries=self.max_retries,
                **call_kwargs
            )
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

    async def complete_with_tools(
        self,
        response_model: Type[T],
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_handler: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        **kwargs
    ) -> T:
        """Get a structured response from the LLM with optional tool calling support.

        Args:
            response_model: Pydantic model for structured output
            messages: Pre-formatted messages list
            tools: Optional list of tool definitions for the LLM to use
            tool_handler: Optional async function to execute tool calls (name, args) -> result
            **kwargs: Additional parameters to pass to LiteLLM

        Returns:
            Instance of response_model with validated data
        """
        # If no tools provided, use regular structured completion
        if not tools or not tool_handler:
            return await self.complete_structured(
                response_model=response_model,
                messages=messages,
                **kwargs
            )

        # First, make a call with tools to see if the LLM wants to use any
        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
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
            "Making LLM completion request with tools",
            model=self.model,
            tool_count=len(tools) if tools else 0,
            message_count=len(messages)
        )

        try:
            # Use litellm directly for tool calling
            import litellm
            response = await litellm.acompletion(**call_kwargs)
            
            # Check if the model wants to use tools
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    # Execute tool calls
                    tool_messages = messages.copy()
                    tool_messages.append(choice.message.model_dump())
                    
                    for tool_call in choice.message.tool_calls:
                        logger.debug(
                            "Executing tool call",
                            tool_name=tool_call.function.name,
                            tool_args=tool_call.function.arguments
                        )
                        
                        # Parse arguments
                        import json
                        args = json.loads(tool_call.function.arguments)
                        
                        # Execute the tool
                        if asyncio.iscoroutinefunction(tool_handler):
                            result = await tool_handler(tool_call.function.name, args)
                        else:
                            result = tool_handler(tool_call.function.name, args)
                        
                        # Add tool response to messages
                        tool_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result) if not isinstance(result, str) else result
                        })
                    
                    # Now get the final structured response with tool results
                    return await self.complete_structured(
                        response_model=response_model,
                        messages=tool_messages,
                        **kwargs
                    )
            
            # No tool calls, get structured response from the initial response
            # Extract content and use it to create structured response
            content = choice.message.content if hasattr(choice.message, 'content') else str(choice.message)
            
            # Parse the content into the response model
            if content:
                import json
                try:
                    data = json.loads(content)
                    return response_model(**data)
                except:
                    # Fallback to regular structured completion
                    return await self.complete_structured(
                        response_model=response_model,
                        messages=messages,
                        **kwargs
                    )
            else:
                # Fallback to regular structured completion
                return await self.complete_structured(
                    response_model=response_model,
                    messages=messages,
                    **kwargs
                )
                
        except Exception as e:
            logger.error(
                "LLM completion with tools failed",
                model=self.model,
                error=str(e)
            )
            raise