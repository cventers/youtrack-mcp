"""
AI Service Registry - Singleton Pattern for Shared AI Components.

Prevents duplicate initialization of AI services across tool modules.
Provides centralized access to OpenAIClient, AIService, and ErrorHandler instances.
"""

import logging
from typing import Optional

from .openai_client import OpenAIClient
from .service import AIService
from ..utils import ErrorHandler
from ..config import config

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

    def _initialize_openai_client(self) -> None:
        """Initialize OpenAI client once."""
        try:
            if config.OPENAI_API_KEY and config.LLM_ENABLED:
                self._openai_client = OpenAIClient(
                    api_key=config.OPENAI_API_KEY,
                    base_url=config.OPENAI_BASE_URL,
                    model=config.OPENAI_MODEL,
                    temperature=config.OPENAI_TEMPERATURE,
                    timeout=config.OPENAI_TIMEOUT
                )
                logger.info("OpenAI client initialized for NL to YQL using config values")
            else:
                logger.warning("LLM not enabled or API key not configured. NL to YQL will be unavailable.")
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