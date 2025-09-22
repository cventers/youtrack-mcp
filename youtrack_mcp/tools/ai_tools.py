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
        try:
            # Try LLM-based analysis if available
            if self.ai_service:
                result = await self.ai_service.analyze_intent(intent, context)

                # Handle both dict and JSON string responses
                if isinstance(result, str):
                    result = json.loads(result)

                if 'error' not in result:
                    return result

        except Exception as e:
            logger.error(f"LLM analysis failed, falling back to rule-based: {e}")

        # Fallback to rule-based analysis
        return self._analyze_intent(intent, context)

    def _analyze_intent(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent and create execution plan."""
        intent_lower = intent.lower()
        plan = {
            "intent": intent,
            "context": context,
            "requires_confirmation": True,
            "plan": [],
            "explanations": [],
            "suggested_tools": [],
            "estimated_complexity": "low"
        }

        # Issue creation intents
        if any(word in intent_lower for word in ["create", "new", "add", "report"]):
            if any(word in intent_lower for word in ["issue", "bug", "task", "feature"]):
                plan["plan"].append({
                    "action": "create_issue",
                    "tool": "issues.create",
                    "description": "Create new issue based on description"
                })
                plan["suggested_tools"].append("issues.create")
                plan["explanations"].append("Detected intent to create a new issue")
                plan["estimated_complexity"] = "medium"

        # Search/query intents
        if any(word in intent_lower for word in ["find", "search", "show", "list", "get"]):
            if any(word in intent_lower for word in ["issue", "bug", "task"]):
                plan["plan"].append({
                    "action": "search_issues",
                    "tool": "search.autosearch",
                    "description": "Search for issues matching criteria"
                })
                plan["suggested_tools"].append("search.autosearch")
                plan["explanations"].append("Detected intent to search for issues")

        # Update/modify intents
        if any(word in intent_lower for word in ["update", "change", "modify", "edit", "fix"]):
            if any(word in intent_lower for word in ["issue", "bug", "task"]):
                plan["plan"].append({
                    "action": "update_issue",
                    "tool": "issues.patch",
                    "description": "Update existing issue properties"
                })
                plan["suggested_tools"].append("issues.patch")
                plan["explanations"].append("Detected intent to update an issue")
                plan["estimated_complexity"] = "medium"

        # Project management intents
        if any(word in intent_lower for word in ["project", "projects"]):
            if any(word in intent_lower for word in ["create", "new", "add"]):
                plan["plan"].append({
                    "action": "create_project",
                    "tool": "projects.create",
                    "description": "Create new project"
                })
                plan["suggested_tools"].append("projects.create")
                plan["explanations"].append("Detected intent to create a project")
                plan["estimated_complexity"] = "high"

        # User search intents
        if any(word in intent_lower for word in ["user", "users", "assignee", "assigned"]):
            if any(word in intent_lower for word in ["find", "search", "get"]):
                plan["plan"].append({
                    "action": "search_users",
                    "tool": "users.search",
                    "description": "Find users by name or criteria"
                })
                plan["suggested_tools"].append("users.search")
                plan["explanations"].append("Detected intent to search for users")

        # If no specific plan detected, suggest general search
        if not plan["plan"]:
            plan["plan"].append({
                "action": "general_search",
                "tool": "search.autosearch",
                "description": "Perform general search based on intent"
            })
            plan["suggested_tools"].append("search.autosearch")
            plan["explanations"].append("General intent detected, suggesting search")
            plan["estimated_complexity"] = "low"

        # Add context-aware suggestions
        if context.get("project"):
            plan["explanations"].append(f"Will use project context: {context['project']}")

        return plan

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
        try:
            if not self.ai_service:
                # No LLM available, return fallback
                return {
                    "error": "LLM service not available",
                    "fallback_query": f"text: {natural_language_query}"
                }

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
        except Exception as e:
            logger.exception(f"Error translating to YQL: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback_query": f"text: {natural_language_query}"
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