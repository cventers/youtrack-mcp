"""
AI Service Registry - Singleton pattern for AI components.

Provides centralized, lazy initialization of AI services with LiteLLM/Instructor.
"""

import logging
import json
from typing import Optional
from pathlib import Path
import structlog

from .llm_client import LLMClient
from .template_manager import TemplateManager
from .service import AIService
from ..config import Config, config
from ..utils import ErrorHandler

logger = structlog.get_logger(__name__)


class AIServiceRegistry:
    """Singleton registry for AI components with lazy initialization."""

    _instance = None
    _llm_client: Optional[LLMClient] = None
    _template_manager: Optional[TemplateManager] = None
    _ai_service: Optional[AIService] = None
    _error_handler: Optional[ErrorHandler] = None
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _initialize_llm_client(self):
        """Initialize LiteLLM + Instructor client with logging."""
        if self._llm_client is not None:
            return

        # Skip if LLM is disabled
        if not config.llm.enabled:
            logger.info("LLM features disabled in configuration")
            return

        # Check for API key
        if not config.llm.api_key:
            logger.warning("No LLM API key configured, LLM features will be limited")
            return

        # Configure LiteLLM logging if enabled
        if config.llm.log_conversations:
            self._setup_conversation_logger(config.llm)

        # Create LLM client
        self._llm_client = LLMClient(
            model=config.llm.full_model_name,
            api_key=config.llm.api_key.get_secret_value(),
            api_base=config.llm.api_base,
            max_retries=config.llm.max_retries,
            timeout=config.llm.timeout,
            temperature=config.llm.temperature
        )

    def _setup_conversation_logger(self, llm_config):
        """Setup conversation logging with configurable format."""
        import logging as stdlib_logging

        # Create a separate logger for conversations
        conv_logger = stdlib_logging.getLogger("llm.conversations")
        conv_logger.setLevel(getattr(stdlib_logging, llm_config.log_level))

        # Clear existing handlers
        conv_logger.handlers.clear()

        # Create formatter based on config
        if llm_config.log_format == "json":
            formatter = stdlib_logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"message": %(message)s}'  # message will be JSON string
            )
        else:
            formatter = stdlib_logging.Formatter(
                '%(asctime)s - LLM - %(levelname)s - %(message)s'
            )

        # Add handler
        handler = stdlib_logging.StreamHandler()
        handler.setFormatter(formatter)
        conv_logger.addHandler(handler)

        # Configure litellm logging
        try:
            import litellm
            import os

            # Set litellm verbosity using environment variable (set_verbose is deprecated)
            if llm_config.log_level == "DEBUG":
                os.environ['LITELLM_LOG'] = 'DEBUG'
            else:
                # Remove the env var if not debugging to avoid verbose logs
                os.environ.pop('LITELLM_LOG', None)

            # Custom success callback for conversation logging
            def log_success(kwargs, response, start_time, end_time):
                """Log successful LLM calls."""
                try:
                    conversation = {
                        "status": "success",
                        "model": kwargs.get("model"),
                        "messages": kwargs.get("messages", []),
                        "response": response.model_dump() if hasattr(response, 'model_dump') else str(response),
                        "duration": end_time - start_time if start_time and end_time else None
                    }

                    if llm_config.redact_api_keys:
                        conversation = self._redact_sensitive_data(conversation)

                    if llm_config.log_format == "json":
                        conv_logger.info(json.dumps(conversation))
                    else:
                        conv_logger.info(f"Success: {conversation}")
                except Exception as e:
                    conv_logger.error(f"Error logging success: {e}")

            # Custom failure callback
            def log_failure(kwargs, response, start_time, end_time):
                """Log failed LLM calls."""
                try:
                    conversation = {
                        "status": "failure",
                        "model": kwargs.get("model"),
                        "messages": kwargs.get("messages", []),
                        "error": str(response),
                        "duration": end_time - start_time if start_time and end_time else None
                    }

                    if llm_config.redact_api_keys:
                        conversation = self._redact_sensitive_data(conversation)

                    if llm_config.log_format == "json":
                        conv_logger.error(json.dumps(conversation))
                    else:
                        conv_logger.error(f"Failure: {conversation}")
                except Exception as e:
                    conv_logger.error(f"Error logging failure: {e}")

            # Register callbacks
            litellm.success_callback = [log_success]
            litellm.failure_callback = [log_failure]

            logger.info(
                "Configured LiteLLM conversation logging",
                level=llm_config.log_level,
                format=llm_config.log_format
            )
        except ImportError:
            logger.warning("LiteLLM not available for conversation logging")

    def _redact_sensitive_data(self, data):
        """Redact sensitive information from logged data."""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ['api_key', 'token', 'secret', 'password']):
                    redacted[key] = "***REDACTED***"
                elif isinstance(value, (dict, list)):
                    redacted[key] = self._redact_sensitive_data(value)
                else:
                    redacted[key] = value
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data

    def _initialize_template_manager(self):
        """Initialize template manager."""
        if self._template_manager is not None:
            return

        # Use configured template dir or default
        template_dir = config.llm.template_dir
        if template_dir is None:
            # Default to ai/templates relative to this file
            template_dir = Path(__file__).parent / "templates"

        self._template_manager = TemplateManager(template_dir)

    def _initialize_error_handler(self):
        """Initialize error handler."""
        if self._error_handler is None:
            self._error_handler = ErrorHandler()
            logger.info("Initialized error handler")

    def _initialize_ai_service(self):
        """Initialize AI service with all components."""
        if self._ai_service is not None:
            return

        # Initialize dependencies
        self._initialize_llm_client()
        self._initialize_template_manager()
        self._initialize_error_handler()

        # Skip if no LLM client available
        if self._llm_client is None:
            logger.warning("AI service not initialized - no LLM client available")
            return

        self._ai_service = AIService(
            llm_client=self._llm_client,
            template_manager=self._template_manager,
            error_handler=self._error_handler
        )

        logger.info("Initialized AI service")

    @property
    def llm_client(self) -> Optional[LLMClient]:
        """Get or create LLM client."""
        if self._llm_client is None:
            self._initialize_llm_client()
        return self._llm_client

    @property
    def template_manager(self) -> Optional[TemplateManager]:
        """Get or create template manager."""
        if self._template_manager is None:
            self._initialize_template_manager()
        return self._template_manager

    @property
    def error_handler(self) -> ErrorHandler:
        """Get or create error handler."""
        if self._error_handler is None:
            self._initialize_error_handler()
        return self._error_handler

    @property
    def ai_service(self) -> Optional[AIService]:
        """Get or create AI service."""
        if self._ai_service is None:
            self._initialize_ai_service()
        return self._ai_service


# Global singleton instance
ai_registry = AIServiceRegistry()

# Export for convenience
__all__ = ['ai_registry', 'AIServiceRegistry']
