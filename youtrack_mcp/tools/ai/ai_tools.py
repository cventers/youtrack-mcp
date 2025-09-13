"""
YouTrack AI Tools Module.

This module provides MCP tool wrappers for AI functionality:
- Natural language query translation
- Error message enhancement
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from youtrack_mcp.mcp_wrappers import sync_wrapper
from youtrack_mcp.utils import format_json_response, ErrorHandler
from youtrack_mcp.ai.service import AIService
from youtrack_mcp.ai.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class AITools:
    """AI-powered tools for YouTrack operations."""

    def __init__(self):
        """Initialize AI tools with AIService."""
        # Initialize OpenAI client for NL to YQL (ai.plan, search autosearch)
        openai_client = None
        try:
            openai_client = OpenAIClient()
            logger.info("OpenAI client initialized for NL to YQL")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}. NL to YQL will be unavailable.")

        # AIService: NL to YQL requires LLM
        self.ai_service = AIService(openai_client=openai_client)

        # ErrorHandler: rule-based error enhancement
        self.error_handler = ErrorHandler()

        logger.info("AITools initialized (error enhancement: rule-based, NL to YQL: LLM required)")



    @sync_wrapper
    def translate_to_yql(self, natural_language_query: str, project_context: Optional[str] = None) -> str:
        """
        Translate natural language to YouTrack Query Language (YQL).

        FORMAT: translate_to_yql(natural_language_query="bugs assigned to me this week")

        Args:
            natural_language_query: Natural language description of the search
            project_context: Optional project ID for context-aware translation

        Returns:
            JSON string with YQL query and metadata
        """
        try:
            result = self.ai_service.translate_nl_to_yql(
                natural_language_query,
                project_context
            )

            return format_json_response({
                "original_query": result.original_input,
                "yql_query": result.yql_query,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "detected_entities": result.detected_entities,
                "suggestions": result.suggestions,
                "ai_provider": "llm" if self.ai_service.openai_client else "none"
            })
        except Exception as e:
            logger.exception(f"Error translating to YQL: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback_query": f"text: {natural_language_query}"
            })



    @sync_wrapper
    def enhance_error_message(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhance error messages with rule-based explanations and fixes.

        FORMAT: enhance_error_message(error_message="403 Forbidden", context={"operation": "update_state"})

        Args:
            error_message: The original error message
            context: Optional context about the operation

        Returns:
            JSON string with enhanced error information
        """
        try:
            result = self.error_handler.enhance_error(error_message, context or {})

            return format_json_response({
                "original_error": error_message,
                "enhanced_explanation": result.enhanced_explanation,
                "fix_suggestion": result.fix_suggestion,
                "example_correction": result.example_correction,
                "learning_tip": result.learning_tip,
                "confidence": result.confidence,
                "ai_provider": "rule_based"
            })
        except Exception as e:
            logger.exception(f"Error enhancing message: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "original_error": error_message
            })



    def close(self) -> None:
        """Clean up resources."""
        # Future: Clean up any AI model resources
        pass

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get tool definitions for this module."""
        return {
            "translate_to_yql": {
                "description": "Translate natural language to YouTrack Query Language",
                "category": "ai_assistance"
            },
            "enhance_error_message": {
                "description": "Enhance error messages with AI explanations",
                "category": "ai_assistance"
            }
        }


__all__ = ["AITools"]