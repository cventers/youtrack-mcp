"""
AI Service Registry - Singleton Pattern for Shared AI Components.

Prevents duplicate initialization of AI services across tool modules.
Provides centralized access to OpenAIClient, AIService, and ErrorHandler instances.
"""

import logging
from typing import Optional

from .openai_client import OpenAIClient, OutputMode
from .service import AIService
from ..utils import ErrorHandler
from ..config import config, Settings

logger = logging.getLogger(__name__)


class AIServiceRegistry:
    """
    Singleton registry for AI services.

    Ensures only one instance of each AI component is created and shared
    across all tool modules, eliminating duplicate initialization.
    """

    _instance: Optional['AIServiceRegistry'] = None
    _openai_client: Optional[OpenAIClient] = None
    _ai_service: Optional[AIService] = None
    _error_handler: Optional[ErrorHandler] = None

    def __new__(cls) -> 'AIServiceRegistry':
        """Singleton pattern - return existing instance or create new one."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def openai_client(self) -> Optional[OpenAIClient]:
        """Get shared OpenAI client instance."""
        if self._openai_client is None:
            self._initialize_openai_client()
        return self._openai_client

    @property
    def ai_service(self) -> AIService:
        """Get shared AI service instance."""
        if self._ai_service is None:
            self._initialize_ai_service()
        assert self._ai_service is not None  # Should be initialized above
        return self._ai_service

    @property
    def error_handler(self) -> ErrorHandler:
        """Get shared error handler instance."""
        if self._error_handler is None:
            self._initialize_error_handler()
        assert self._error_handler is not None  # Should be initialized above
        return self._error_handler

    def _initialize_openai_client(self):
        """Initialize OpenAI client if configured."""
        try:
            # Try to get settings from the new config system
            settings = None
            try:
                settings = Settings()
            except Exception:
                # Fall back to legacy config
                pass

            if settings and settings.openai.api_key.get_secret_value() and settings.openai.enabled:
                # Use new config system
                try:
                    output_mode = OutputMode(settings.llm.output_mode)
                except ValueError:
                    output_mode = OutputMode.JSON_SCHEMA

                self._openai_client = OpenAIClient(
                    api_key=settings.openai.api_key.get_secret_value(),
                    base_url=settings.openai.base_url,
                    model=settings.openai.model,
                    temperature=settings.openai.temperature,
                    timeout=settings.openai.timeout,
                    max_tokens=settings.openai.max_tokens,
                    mode=output_mode,
                    max_retries=settings.llm.max_retries,
                    initial_backoff=settings.llm.initial_backoff,
                    backoff_multiplier=settings.llm.backoff_multiplier
                )
                logger.info(f"OpenAI client initialized with mode {output_mode}")
            elif config.OPENAI_API_KEY and config.LLM_ENABLED:
                # Fall back to legacy config
                self._openai_client = OpenAIClient(
                    api_key=config.OPENAI_API_KEY,
                    base_url=config.OPENAI_BASE_URL,
                    model=config.OPENAI_MODEL,
                    temperature=config.OPENAI_TEMPERATURE,
                    timeout=config.OPENAI_TIMEOUT,
                    max_tokens=config.OPENAI_MAX_TOKENS
                )
                logger.info("OpenAI client initialized successfully (legacy config)")
            else:
                logger.info("OpenAI client not initialized (missing API key or LLM disabled)")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}. NL to YQL will be unavailable.")

    def _initialize_ai_service(self) -> None:
        """Initialize AI service once."""
        self._ai_service = AIService(
            openai_client=self.openai_client,
            error_handler=self.error_handler
        )
        logger.info("AIService initialized (NL to YQL: LLM required)")

    def _initialize_error_handler(self) -> None:
        """Initialize error handler once."""
        self._error_handler = ErrorHandler()
        logger.info("ErrorHandler initialized with error patterns")


# Global singleton instance
ai_registry = AIServiceRegistry()


__all__ = ["AIServiceRegistry", "ai_registry"]