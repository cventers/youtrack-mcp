"""
Core Search Tools for YouTrack MCP - Minimal Implementation.

Implements the 2 core search tools:
- search.query: Execute explicit YouTrack Query Language
- search.autosearch: Natural language to YQL translation
"""

import json
import logging
from typing import Any, Dict, Optional

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.mcp_wrappers import async_wrapper
from youtrack_mcp.utils import format_json_response
from youtrack_mcp.tools.ai.ai_tools import AITools

logger = logging.getLogger(__name__)


class SearchTools:
    """Minimal search tools with clean interfaces."""

    def __init__(self):
        """Initialize core search tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)
        self.ai_tools = AITools()

    @async_wrapper
    async def query(self, query: str, limit: int = 10, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> str:
        """
        Execute explicit YouTrack Query Language.

        FORMAT: search.query(query="project: DEMO #Unresolved", limit=5, sort_by="created", sort_order="desc")

        Args:
            query: YouTrack Query Language string
            limit: Maximum number of results to return
            sort_by: Field to sort by (created, updated, priority, etc.)
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            JSON with search results
        """
        try:
            # Build sort parameter if provided
            sort_param = None
            if sort_by:
                if sort_order and sort_order.lower() in ["asc", "desc"]:
                    sort_param = f"{sort_by} {sort_order}"
                else:
                    sort_param = f"{sort_by} desc"  # Default to desc

            # Perform the search
            issues = await self.issues_api.search_issues(query=query, limit=limit)

            # Handle response format
            if isinstance(issues, dict):
                result = issues
            else:
                # Convert list of issues to JSON
                result = []
                for issue in issues:
                    if hasattr(issue, "model_dump"):
                        result.append(issue.model_dump())
                    else:
                        result.append(issue)

            return format_json_response({
                "query": query,
                "results": result,
                "count": len(result) if isinstance(result, list) else len(result.get("issues", [])),
                "limit": limit,
                "sort_by": sort_by,
                "sort_order": sort_order
            })

        except Exception as e:
            logger.exception(f"Error in search query: {query}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "query": query
            })

    @async_wrapper
    async def autosearch(self, natural_language_query: str, project_context: Optional[str] = None) -> str:
        """
        Natural language to YQL translation.

        FORMAT: search.autosearch(natural_language_query="bugs assigned to me this week")

        Args:
            natural_language_query: Natural language description of the search
            project_context: Optional project ID for context-aware translation

        Returns:
            JSON with YQL query, confidence, results, notes, degraded?
        """
        try:
            # Use AI to translate natural language to YQL
            translation_result = self.ai_tools.translate_to_yql(
                natural_language_query,
                project_context
            )

            # Parse the AI result
            ai_response = json.loads(translation_result)
            yql_query = ai_response.get("yql_query", "")
            confidence = ai_response.get("confidence", 0.0)

            # If confidence is low, return with degraded flag
            if confidence < 0.7:
                return format_json_response({
                    "yql": yql_query,
                    "confidence": confidence,
                    "results": [],
                    "notes": ai_response.get("reasoning", ""),
                    "degraded": True,
                    "suggestions": ai_response.get("suggestions", [])
                })

            # Execute the translated query
            search_result = await self.query(yql_query, limit=10)
            search_response = json.loads(search_result)

            return format_json_response({
                "yql": yql_query,
                "confidence": confidence,
                "results": search_response.get("results", []),
                "notes": ai_response.get("reasoning", ""),
                "degraded": False,
                "detected_entities": ai_response.get("detected_entities", [])
            })

        except Exception as e:
            logger.exception(f"Error in autosearch: {natural_language_query}")
            # Fallback to simple text search
            fallback_query = f"text: {natural_language_query}"
            try:
                fallback_result = await self.query(fallback_query, limit=10)
                fallback_response = json.loads(fallback_result)

                return format_json_response({
                    "yql": fallback_query,
                    "confidence": 0.0,
                    "results": fallback_response.get("results", []),
                    "notes": f"Fallback to text search due to error: {str(e)}",
                    "degraded": True
                })
            except Exception as fallback_error:
                return format_json_response({
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "fallback_error": str(fallback_error),
                    "natural_language_query": natural_language_query
                })

    def _simple_nl_to_yql(self, query: str, project_context: Optional[str] = None) -> str:
        """Simple rule-based natural language to YQL conversion."""
        yql_parts = []

        # Add project context if provided
        if project_context:
            yql_parts.append(f"project: {project_context}")

        query_lower = query.lower()

        # Time-based patterns
        if "last week" in query_lower:
            yql_parts.append("created: -7d .. *")
        elif "this week" in query_lower:
            yql_parts.append("created: {This week}")
        elif "today" in query_lower:
            yql_parts.append("created: {Today}")
        elif "yesterday" in query_lower:
            yql_parts.append("created: {Yesterday}")

        # Assignment patterns
        if "assigned to me" in query_lower or "my" in query_lower:
            yql_parts.append("assignee: me")

        # State patterns
        if "open" in query_lower:
            yql_parts.append("state: Open")
        elif "resolved" in query_lower or "closed" in query_lower:
            yql_parts.append("#Resolved")

        # Priority patterns
        if "critical" in query_lower or "high priority" in query_lower:
            yql_parts.append("priority: Critical")

        # Type patterns
        if "bug" in query_lower:
            yql_parts.append("type: Bug")
        elif "feature" in query_lower:
            yql_parts.append("type: Feature")

        # Free text search for remaining content
        remaining = query
        for pattern in ["last week", "this week", "today", "yesterday", "assigned to me", "my",
                       "open", "resolved", "closed", "critical", "high priority", "bug", "feature"]:
            remaining = remaining.replace(pattern, "")

        remaining = remaining.strip()
        if remaining and len(remaining) > 2:
            yql_parts.append(f"text: {remaining}")

        return " ".join(yql_parts) if yql_parts else "*"

    def _calculate_confidence(self, query: str) -> float:
        """Calculate confidence score for the translation."""
        score = 0.5  # Base score

        # Increase for recognized patterns
        recognized_patterns = [
            "last week", "this week", "today", "yesterday",
            "assigned to me", "my", "open", "resolved", "closed",
            "critical", "high priority", "bug", "feature"
        ]

        for pattern in recognized_patterns:
            if pattern in query.lower():
                score += 0.1

        # Cap at 0.9 for rule-based approach
        return min(score, 0.9)

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core search tool definitions."""
        return {
            "search.query": {
                "description": "Execute YouTrack Query Language",
                "function": self.query
            },
            "search.autosearch": {
                "description": "Translate natural language to YQL",
                "function": self.autosearch
            }
        }


__all__ = ["SearchTools"]