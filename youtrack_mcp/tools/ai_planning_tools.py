"""
Core AI Tools for YouTrack MCP - Minimal Implementation.

Implements the 1 core AI tool:
- ai.plan: Plan-only translator
"""

import logging
from typing import Any, Dict, Optional

from youtrack_mcp.mcp_wrappers import async_wrapper
from youtrack_mcp.utils import format_json_response
logger = logging.getLogger(__name__)


class AIPlanningTools:
    """Minimal AI tools with clean interfaces."""

    def __init__(self):
        """Initialize AI planning tools."""

    @async_wrapper
    async def plan(self, intent: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Plan-only intent translator.

        FORMAT: ai.plan(intent="Create a bug report for login issues", context={"project": "DEMO"})

        Args:
            intent: Natural language description of desired action
            context: Optional context dictionary

        Returns:
            JSON with plan, explanations[], requires_confirmation: true
        """
        try:
            # Analyze intent to determine appropriate tools and actions
            plan_result = self._analyze_intent(intent, context or {})

            return format_json_response(plan_result)

        except Exception as e:
            logger.exception(f"Error planning intent: {intent}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "intent": intent,
                "requires_confirmation": True
            })

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

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core AI tool definitions."""
        return {
            "ai.plan": {
                "description": "Plan user intent actions",
                "function": self.plan
            }
        }


__all__ = ["AIPlanningTools"]