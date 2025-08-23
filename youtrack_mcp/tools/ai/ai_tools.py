"""
YouTrack AI Tools Module.

This module provides MCP tool wrappers for AI functionality:
- Natural language query translation
- Error message enhancement
- Intelligent suggestions
"""

import json
import logging
from typing import Any, Dict, Optional, List

from youtrack_mcp.mcp_wrappers import sync_wrapper
from youtrack_mcp.utils import format_json_response
from .ai_processor import AIProcessor
from .llm_client import LLMClient, LLMConfig, AIProvider

logger = logging.getLogger(__name__)


class AITools:
    """AI-powered tools for YouTrack operations."""

    def __init__(self):
        """Initialize AI tools with processor and LLM client."""
        # Initialize LLM configuration from environment or defaults
        self.llm_config = self._create_llm_config()
        self.llm_client = LLMClient(self.llm_config)
        self.ai_processor = AIProcessor(self.llm_client)
        logger.info("AITools initialized with AI processor and LLM client")

    def _create_llm_config(self) -> LLMConfig:
        """Create LLM configuration from environment variables."""
        import os
        
        # Check for AI provider configuration
        provider = os.getenv("YOUTRACK_AI_PROVIDER", "rule_based").lower()
        
        if provider == "openai":
            return LLMConfig(
                provider=AIProvider.OPENAI_COMPATIBLE,
                api_url="https://api.openai.com/v1",
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                enabled=bool(os.getenv("OPENAI_API_KEY"))
            )
        elif provider == "anthropic":
            return LLMConfig(
                provider=AIProvider.OPENAI_COMPATIBLE,
                api_url="https://api.anthropic.com/v1",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                enabled=bool(os.getenv("ANTHROPIC_API_KEY"))
            )
        elif provider == "google":
            # Google's API is not OpenAI-compatible, would need separate implementation
            logger.warning("Google AI provider not yet implemented, falling back to rule-based")
            return LLMConfig(provider=AIProvider.RULE_BASED)
        else:
            # Default to rule-based
            return LLMConfig(provider=AIProvider.RULE_BASED)

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
            result = self.ai_processor.translate_natural_language_to_yql(
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
                "ai_provider": self.llm_config.provider.value
            })
        except Exception as e:
            logger.exception(f"Error translating to YQL: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback_query": f"text: {natural_language_query}"
            })

    @sync_wrapper
    def suggest_ticket_attributes(self, title: str, description: str, project_id: Optional[str] = None) -> str:
        """
        Suggest ticket attributes based on title and description.
        
        FORMAT: suggest_ticket_attributes(title="Login button broken", description="Users can't login...")
        
        Args:
            title: Issue title/summary
            description: Issue description
            project_id: Optional project ID for context
            
        Returns:
            JSON string with suggested attributes
        """
        try:
            suggestions = self.ai_processor.suggest_ticket_attributes(
                title,
                description,
                project_id
            )
            
            return format_json_response({
                "title": title,
                "suggestions": suggestions,
                "ai_provider": self.llm_config.provider.value
            })
        except Exception as e:
            logger.exception(f"Error suggesting attributes: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "suggestions": {}
            })

    @sync_wrapper
    def enhance_error_message(self, error_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Enhance error messages with AI-powered explanations and fixes.
        
        FORMAT: enhance_error_message(error_message="403 Forbidden", context={"operation": "update_state"})
        
        Args:
            error_message: The original error message
            context: Optional context about the operation
            
        Returns:
            JSON string with enhanced error information
        """
        try:
            # Add context to error message if provided
            full_context = error_message
            if context:
                full_context = f"{error_message}\nContext: {json.dumps(context)}"
            
            result = self.ai_processor.enhance_error_message(full_context)
            
            return format_json_response({
                "original_error": error_message,
                "enhanced_explanation": result.enhanced_explanation,
                "fix_suggestion": result.fix_suggestion,
                "example_correction": result.example_correction,
                "learning_tip": result.learning_tip,
                "confidence": result.confidence,
                "ai_provider": self.llm_config.provider.value
            })
        except Exception as e:
            logger.exception(f"Error enhancing message: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "original_error": error_message
            })

    @sync_wrapper
    def analyze_activity_patterns(self, issues: List[Dict[str, Any]], time_range_days: int = 30) -> str:
        """
        Analyze activity patterns in issues using AI.
        
        FORMAT: analyze_activity_patterns(issues=[...], time_range_days=30)
        
        Args:
            issues: List of issue data to analyze
            time_range_days: Number of days to analyze
            
        Returns:
            JSON string with pattern analysis
        """
        try:
            result = self.ai_processor.analyze_activity_patterns(issues, time_range_days)
            
            return format_json_response({
                "patterns": result.patterns,
                "insights": result.insights,
                "recommendations": result.recommendations,
                "confidence": result.confidence,
                "time_range_days": time_range_days,
                "issues_analyzed": len(issues),
                "ai_provider": self.llm_config.provider.value
            })
        except Exception as e:
            logger.exception(f"Error analyzing patterns: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "issues_analyzed": len(issues) if issues else 0
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
            "suggest_ticket_attributes": {
                "description": "AI-powered ticket attribute suggestions",
                "category": "ai_assistance"
            },
            "enhance_error_message": {
                "description": "Enhance error messages with AI explanations",
                "category": "ai_assistance"
            },
            "analyze_activity_patterns": {
                "description": "Analyze activity patterns using AI",
                "category": "ai_assistance"
            }
        }


__all__ = ["AITools"]