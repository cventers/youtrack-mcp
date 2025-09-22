"""
Core AI Tools for YouTrack MCP.

Provides AI-powered functionality:
- MCP Tool: ai.plan - Plan user intent actions
- Internal: translate_to_yql - Natural language to YQL translation (used by SearchTools)
- Internal: enhance_error_message - Error message enhancement
"""

import json
import logging
from typing import Any, Dict, Optional

from youtrack_mcp.ai.registry import ai_registry
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class AITools:
    """AI-powered tools for YouTrack operations."""

    def __init__(self):
        """Initialize AI tools using shared registry."""
        # Use shared AI service instance from registry
        self.ai_service = ai_registry.ai_service
        self.error_handler = ai_registry.error_handler
        logger.info("AITools initialized using shared AI registry")

    async def plan(self, intent: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        LLM-powered intent planning and analysis.

        FORMAT: ai.plan(intent="Create a bug report for login issues", context={"project": "DEMO"})

        Args:
            intent: Natural language description of desired action
            context: Optional context dictionary

        Returns:
            JSON string with plan, explanations[], requires_confirmation: true
        """
        try:
            # Use LLM to analyze intent and create execution plan
            plan_result = await self._analyze_intent_with_llm(intent, context or {})
            return json.dumps(plan_result)

        except Exception as e:
            logger.exception(f"Error planning intent: {intent}")
            return json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "intent": intent,
                "requires_confirmation": True
            })

    async def _analyze_intent_with_llm(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze intent and create execution plan."""
        if not self.ai_service:
            raise ValueError("AI service not available - LLM features require proper API configuration")
        
        result = await self.ai_service.analyze_intent(intent, context)
        
        # Handle both dict and JSON string responses
        if isinstance(result, str):
            result = json.loads(result)
        
        if 'error' in result:
            raise ValueError(f"LLM analysis failed: {result.get('error')}")
        
        return result



    async def translate_to_yql(self, natural_language_query: str, project_context: Optional[str] = None) -> dict:
        """
        Translate natural language to YouTrack Query Language (YQL).
        Internal method used by SearchTools.

        Args:
            natural_language_query: Natural language description of the search
            project_context: Optional project ID for context-aware translation

        Returns:
            Dict with YQL query and metadata
        """
        if not self.ai_service:
            raise ValueError("AI service not available - LLM features require proper API configuration")
        
        result = await self.ai_service.translate_nl_to_yql(
            natural_language_query,
            project_context
        )

        return {
            "original_query": result.original_input,
            "yql_query": result.yql_query,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "detected_entities": result.detected_entities,
            "suggestions": result.suggestions,
            "ai_provider": "llm"
        }

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core AI tool definitions."""
        return {
            "ai.plan": {
                "description": "Plan user intent actions",
                "function": self.plan
            }
        }


__all__ = ["AITools"]