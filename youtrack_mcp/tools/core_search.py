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
from youtrack_mcp.mcp_wrappers import sync_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class CoreSearchTools:
    """Minimal search tools with clean interfaces."""

    def __init__(self):
        """Initialize core search tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)

    @sync_wrapper
    def query(self, query: str, limit: int = 10) -> str:
        """
        Execute explicit YouTrack Query Language.

        FORMAT: search.query(query="project: DEMO #Unresolved", limit=10)

        Args:
            query: YouTrack Query Language expression
            limit: Maximum results to return (default: 10)

        Returns:
            JSON with search results
        """
        try:
            results = self.issues_api.search_issues(query=query, limit=limit)

            # Convert Issue objects to dicts for JSON response
            issues_data = []
            for issue in results:
                if hasattr(issue, "model_dump"):
                    issues_data.append(issue.model_dump())
                else:
                    issues_data.append(issue.__dict__ if hasattr(issue, "__dict__") else str(issue))

            return format_json_response({
                "query": query,
                "results": {"issues": issues_data},
                "metadata": {
                    "limit": limit,
                    "result_count": len(issues_data)
                }
            })

        except Exception as e:
            logger.exception(f"Error executing YQL query: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "query": query
            })

    @sync_wrapper
    def autosearch(self, natural_language_query: str, project_context: Optional[str] = None) -> str:
        """
        Natural language to YQL translation with confidence scoring.

        FORMAT: search.autosearch(natural_language_query="bugs assigned to me this week")

        Args:
            natural_language_query: Natural language search description
            project_context: Optional project ID for context

        Returns:
            JSON with YQL query, confidence, and results
        """
        try:
            # Simple rule-based translation (placeholder for AI integration)
            yql_query = self._simple_nl_to_yql(natural_language_query, project_context)
            confidence = self._calculate_confidence(natural_language_query)

            # Execute the query if confidence is reasonable
            results = None
            result_count = 0
            if confidence >= 0.6:
                try:
                    issues = self.issues_api.search_issues(yql_query, limit=10)
                    # Convert Issue objects to dicts
                    issues_data = []
                    for issue in issues:
                        if hasattr(issue, "model_dump"):
                            issues_data.append(issue.model_dump())
                        else:
                            issues_data.append(issue.__dict__ if hasattr(issue, "__dict__") else str(issue))
                    results = {"issues": issues_data}
                    result_count = len(issues_data)
                except Exception as e:
                    logger.warning(f"Query execution failed: {e}")
                    results = None

            response = {
                "yql": yql_query,
                "confidence": confidence,
                "results": results,
                "notes": [] if confidence >= 0.6 else ["Low confidence - review query manually"],
                "degraded": confidence < 0.6
            }

            if results:
                response["result_count"] = result_count

            return format_json_response(response)

        except Exception as e:
            logger.exception(f"Error in autosearch: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "query": natural_language_query
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
                "description": "Execute explicit YouTrack Query Language",
                "function": self.query
            },
            "search.autosearch": {
                "description": "Natural language to YQL translation",
                "function": self.autosearch
            }
        }


__all__ = ["CoreSearchTools"]