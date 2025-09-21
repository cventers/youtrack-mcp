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

logger = logging.getLogger(__name__)


class SearchTools:
    """Minimal search tools with clean interfaces."""

    def __init__(self, ai_tools=None):
        """Initialize core search tools.

        Args:
            ai_tools: Optional AITools instance to use for NL to YQL translation
        """
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)
        self.ai_tools = ai_tools  # Will be None if not provided

    def _detect_date_syntax_errors(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Detect incorrect date syntax patterns and provide suggestions.

        Detects incorrect patterns like:
        - "-6m .. *" (should be "{minus 6m} .. *")
        - "{6 months ago .. Today}" (should be "{minus 6m} .. Today")

        Args:
            query: The original query string

        Returns:
            Dict with error details and suggestions if incorrect syntax found, None if syntax is correct
        """
        import re

        # Helper to convert word units to single letters
        def unit_to_short(unit: str) -> str:
            unit = unit.lower()
            if unit in ['days', 'day']:
                return 'd'
            elif unit in ['weeks', 'week']:
                return 'w'
            elif unit in ['months', 'month']:
                return 'm'
            elif unit in ['years', 'year']:
                return 'y'
            else:
                return unit[0] if unit else 'd'  # fallback

        errors = []
        suggestions = []

        # Pattern 1: Detect "-Nm .. *" format
        pattern1_matches = re.findall(r'-(\d+)([dwm])\s*\.\.\s*\*', query)
        if pattern1_matches:
            for match in pattern1_matches:
                num, unit = match
                incorrect = f"-{num}{unit} .. *"
                correct = f"{{minus {num}{unit}}} .. *"
                errors.append(f"Incorrect date range syntax: '{incorrect}'")
                suggestions.append(f"Use: '{correct}' instead of '{incorrect}'")

        # Pattern 2: Detect "{N units ago .. Today}" format
        pattern2_matches = re.findall(r'\{(\d+)\s+(\w+)\s+ago\s*\.\.\s*Today\}', query)
        if pattern2_matches:
            for match in pattern2_matches:
                num, unit_word = match
                unit = unit_to_short(unit_word)
                incorrect = f"{{{num} {unit_word} ago .. Today}}"
                correct = f"{{minus {num}{unit}}} .. Today"
                errors.append(f"Incorrect date range syntax: '{incorrect}'")
                suggestions.append(f"Use: '{correct}' instead of '{incorrect}'")

        # Pattern 3: Detect "{N units ago .. *}" format
        pattern3_matches = re.findall(r'\{(\d+)\s+(\w+)\s+ago\s*\.\.\s*\*\}', query)
        if pattern3_matches:
            for match in pattern3_matches:
                num, unit_word = match
                unit = unit_to_short(unit_word)
                incorrect = f"{{{num} {unit_word} ago .. *}}"
                correct = f"{{minus {num}{unit}}} .. *"
                errors.append(f"Incorrect date range syntax: '{incorrect}'")
                suggestions.append(f"Use: '{correct}' instead of '{incorrect}'")

        if errors:
            return {
                "error": "Invalid date range syntax detected",
                "explanation": "YouTrack requires specific date range syntax. " + " ".join(errors),
                "suggestions": suggestions,
                "learn_from_this": "Use {minus Nd} format for relative dates. Examples: {minus 7d}, {minus 30d}, {minus 6m}",
                "examples": [
                    "created: {minus 7d} .. Today",
                    "updated: {minus 30d} .. *",
                    "created: 2025-01-01 .. 2025-12-31"
                ]
            }

        return None

    async def query(self, query: str, limit: int = 10, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> dict:
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
            # Check for date syntax errors
            syntax_error = self._detect_date_syntax_errors(query)
            if syntax_error:
                return {
                    "query": query,
                    "error": syntax_error["error"],
                    "explanation": syntax_error["explanation"],
                    "suggestions": syntax_error["suggestions"],
                    "learn_from_this": syntax_error["learn_from_this"],
                    "examples": syntax_error["examples"],
                    "results": [],
                    "count": 0,
                    "limit": limit,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                }

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

            return {
                "query": query,
                "results": result,
                "count": len(result) if isinstance(result, list) else len(result.get("issues", [])),
                "limit": limit,
                "sort_by": sort_by,
                "sort_order": sort_order
            }

        except Exception as e:
            logger.exception(f"Error in search query: {query}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "query": query
            }

    async def autosearch(self, natural_language_query: str, project_context: Optional[str] = None) -> dict:
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
            # AI tools are required for autosearch
            if not self.ai_tools:
                raise RuntimeError("AI translation service not available - autosearch requires LLM configuration")

            translation_result = await self.ai_tools.translate_to_yql(
                natural_language_query,
                project_context
            )

            # Parse the AI result
            ai_response = translation_result
            yql_query = ai_response.get("yql_query", "")
            confidence = ai_response.get("confidence", 0.0)

            # If confidence is low, return with degraded flag
            if confidence < 0.7:
                return {
                    "yql": yql_query,
                    "confidence": confidence,
                    "results": [],
                    "notes": ai_response.get("reasoning", ""),
                    "degraded": True,
                    "suggestions": ai_response.get("suggestions", [])
                }

            # Execute the translated query
            search_response = await self.query(yql_query, limit=10)

            # Check if the query execution returned an error due to date syntax
            if "error" in search_response and "date" in search_response.get("explanation", "").lower():
                return {
                    "yql": yql_query,
                    "confidence": confidence,
                    "results": [],
                    "notes": f"Query contains date syntax error: {search_response.get('explanation', '')}",
                    "degraded": True,
                    "suggestions": search_response.get("suggestions", []),
                    "examples": search_response.get("examples", []),
                    "detected_entities": ai_response.get("detected_entities", [])
                }

            return {
                "yql": yql_query,
                "confidence": confidence,
                "results": search_response.get("results", []),
                "notes": ai_response.get("reasoning", ""),
                "degraded": False,
                "detected_entities": ai_response.get("detected_entities", [])
            }

        except Exception as e:
            logger.exception(f"Error in autosearch: {natural_language_query}")
            # Fallback to simple text search
            fallback_query = f"text: {natural_language_query}"
            try:
                fallback_response = await self.query(fallback_query, limit=10)

                return {
                    "yql": fallback_query,
                    "confidence": 0.0,
                    "results": fallback_response.get("results", []),
                    "notes": f"Fallback to text search due to error: {str(e)}",
                    "degraded": True
                }
            except Exception as fallback_error:
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "fallback_error": str(fallback_error),
                    "natural_language_query": natural_language_query
                }





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