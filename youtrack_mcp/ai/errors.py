"""
Structured output error classes for YouTrack MCP AI module.

Provides specialized exception types for LLM output validation and generation failures.
"""

from typing import Any, Dict, List, Optional, Union


class StructuredOutputError(Exception):
    """Structured output validation or generation failure."""

    def __init__(
        self,
        fields: Union[Dict, List],      # Failed fields/constraints
        message: str,                   # Human-readable error
        last_raw: Optional[str] = None, # Last raw response
        attempt_count: int = 0,         # Number of attempts made
        request_id: Optional[str] = None # OpenAI request ID
    ):
        """
        Initialize structured output error.

        Args:
            fields: Failed fields or constraints
            message: Human-readable error message
            last_raw: Last raw response from LLM
            attempt_count: Number of attempts made
            request_id: OpenAI request ID for debugging
        """
        self.fields = fields
        self.message = message
        self.last_raw = last_raw
        self.attempt_count = attempt_count
        self.request_id = request_id
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_type": "structured_output_error",
            "message": self.message,
            "fields": self.fields,
            "attempt_count": self.attempt_count,
            "request_id": self.request_id,
            "last_raw": self.last_raw[:500] if self.last_raw else None  # Truncate for logs
        }


class ProviderError(Exception):
    """Provider API error (OpenAI or compatible service)."""

    def __init__(
        self,
        message: str,
        request_id: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        """
        Initialize provider error.

        Args:
            message: Error message from provider
            request_id: Request ID from provider
            status_code: HTTP status code if applicable
        """
        self.message = message
        self.request_id = request_id
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_type": "provider_error",
            "message": self.message,
            "request_id": self.request_id,
            "status_code": self.status_code
        }