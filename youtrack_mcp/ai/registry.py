"""
AI Service Registry v3 - Singleton pattern for AI components.

Provides centralized, lazy initialization of AI services with LiteLLM/Instructor.
"""

import logging
import json
from typing import Optional
from pathlib import Path
import structlog

from .llm_client import LLMClient
from .template_manager import TemplateManager
from .service_v3 import AIService
from ..config_v3 import Settings
from ..utils import ErrorHandler

logger = structlog.get_logger(__name__)


class AIServiceRegistry:
    """Singleton registry for AI components with lazy initialization."""

    _instance = None
    _llm_client: Optional[LLMClient] = None
    _template_manager: Optional[TemplateManager] = None
    _ai_service: Optional[AIService] = None
    _error_handler: Optional[ErrorHandler] = None
    _settings: Optional[Settings] = None
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _initialize_settings(self):
        """Initialize settings if not already done."""
        if self._settings is None:
            self._settings = Settings()
            logger.info(
                "Initialized settings",
                llm_enabled=self._settings.llm.enabled,
                provider=self._settings.llm.provider
            )

    def _initialize_llm_client(self):
        """Initialize LiteLLM + Instructor client with logging."""
        if self._llm_client is not None:
            return

        self._initialize_settings()
        settings = self._settings

        # Skip if LLM is disabled
        if not settings.llm.enabled:
            logger.info("LLM features disabled in configuration")
            return

        # Check for API key
        if not settings.llm.api_key:
            logger.warning("No LLM API key configured, LLM features will be limited")
            return

        try:
            # Configure LiteLLM logging if enabled
            if settings.llm.log_conversations:
                self._setup_conversation_logger(settings.llm)

            # Create LLM client
            self._llm_client = LLMClient(
                model=settings.llm.full_model_name,
                api_key=settings.llm.api_key.get_secret_value() if settings.llm.api_key else None,
                api_base=settings.llm.api_base,
                max_retries=settings.llm.max_retries,
                retry_on_validation_error=settings.llm.retry_on_validation_error,
                timeout=settings.llm.timeout,
                temperature=settings.llm.temperature
            )

            logger.info(
                "Initialized LLM client",
                provider=settings.llm.provider,
                model=settings.llm.model
            )
        except Exception as e:
            logger.error(
                "Failed to initialize LLM client",
                error=str(e),
                provider=settings.llm.provider
            )
            # Don't raise - allow service to run without LLM features

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

            # Set litellm verbosity
            litellm.set_verbose = (llm_config.log_level == "DEBUG")

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

        self._initialize_settings()

        # Use configured template dir or default
        template_dir = self._settings.llm.template_dir
        if template_dir is None:
            # Default to ai/templates relative to this file
            template_dir = Path(__file__).parent / "templates"

        try:
            self._template_manager = TemplateManager(template_dir)
            logger.info("Initialized template manager", template_dir=str(template_dir))
        except Exception as e:
            logger.error("Failed to initialize template manager", error=str(e))
            # Create a minimal template manager with defaults
            self._template_manager = None

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

        logger.info("Initialized AI service v3")

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

    @property
    def settings(self) -> Settings:
        """Get or create settings."""
        if self._settings is None:
            self._initialize_settings()
        return self._settings

    def reset(self):
        """Reset all components (mainly for testing)."""
        self._llm_client = None
        self._template_manager = None
        self._ai_service = None
        self._error_handler = None
        self._settings = None
        self._initialized = False
        logger.info("Reset AI service registry")


# Global singleton instance
ai_registry = AIServiceRegistry()

# Export for convenience
__all__ = ['ai_registry', 'AIServiceRegistry']