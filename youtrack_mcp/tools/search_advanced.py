"""
Advanced Search Tools for YouTrack MCP.

This module extends the basic search functionality with:
- Intelligent query building with natural language support
- Result caching and performance optimization
- Search analytics and pattern tracking
- Query suggestions and auto-completion
"""

import json
from youtrack_mcp.logging import get_logger
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from functools import lru_cache

from cachetools import TTLCache, LRUCache

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.api.projects import ProjectsClient

logger = get_logger(__name__)


class SearchOperator(str, Enum):
    """YouTrack search operators."""
    EQUALS = ":"
    NOT_EQUALS = "!:"
    CONTAINS = "~"
    NOT_CONTAINS = "!~"
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not in"
    HAS = "has"
    NOT_HAS = "!has"


@dataclass
class SearchCondition:
    """Represents a single search condition."""
    field: str
    operator: SearchOperator
    value: Any
    negated: bool = False
    
    def to_query_string(self) -> dict:
        """Convert condition to YouTrack query string."""
        # Handle negation
        op = f"!{self.operator.value}" if self.negated and self.operator != SearchOperator.NOT_EQUALS else self.operator.value
        
        # Format value based on type
        if isinstance(self.value, (list, tuple)):
            if self.operator in [SearchOperator.IN, SearchOperator.NOT_IN]:
                values = ", ".join([f'"{v}"' if isinstance(v, str) else str(v) for v in self.value])
                return f"{self.field} {op} ({values})"
            else:
                # For multiple values with other operators, create OR conditions
                conditions = [f"{self.field} {op} \"{v}\"" if isinstance(v, str) else f"{self.field} {op} {v}" 
                             for v in self.value]
                return f"({' or '.join(conditions)})"
        elif isinstance(self.value, str):
            # Handle special string values
            if self.value.lower() in ["unassigned", "me", "*"]:
                return f"{self.field} {op} {self.value}"
            else:
                return f"{self.field} {op} \"{self.value}\""
        else:
            return f"{self.field} {op} {self.value}"


@dataclass
class SearchStats:
    """Search performance and usage statistics."""
    total_searches: int = 0
    total_results: int = 0
    total_execution_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    popular_queries: Dict[str, int] = field(default_factory=dict)
    field_usage: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    last_reset: datetime = field(default_factory=datetime.now)


class AdvancedSearchTools:
    """Enhanced search tools with intelligent features."""
    
    def __init__(self):
        """Initialize advanced search tools."""
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)
        self.projects_api = ProjectsClient(self.client)
        
        # Initialize caches
        self.query_cache = TTLCache(maxsize=100, ttl=300)  # 5 minute TTL
        self.suggestion_cache = LRUCache(maxsize=50)
        
        # Initialize analytics
        self.stats = SearchStats()
        
        logger.info("AdvancedSearchTools initialized with caching and analytics")
    async def intelligent_search(
        self,
        natural_query: str,
        project: Optional[str] = None,
        limit: int = 10,
        include_suggestions: bool = True
    ) -> dict:
        """
        Perform intelligent search with natural language-like queries.
        
        FORMAT: intelligent_search(natural_query="bugs assigned to me last week")
        
        Args:
            natural_query: Natural language search query
            project: Optional project to scope search
            limit: Maximum results to return
            include_suggestions: Whether to include query suggestions
            
        Returns:
            JSON string with search results and metadata
        """
        start_time = time.time()
        
        try:
            # Convert natural language to YQL
            yql_query = self._natural_to_yql(natural_query, project)
            
            # Check cache
            cache_key = f"{yql_query}:{limit}"
            if cache_key in self.query_cache:
                self.stats.cache_hits += 1
                cached_result = self.query_cache[cache_key]
                cached_result["from_cache"] = True
                return cached_result
            
            self.stats.cache_misses += 1
            
            # Execute search
            issues = await self.issues_api.search_issues(yql_query, limit=limit)

            # Wrap results in expected format
            results = {"issues": [issue.model_dump() if hasattr(issue, 'model_dump') else issue for issue in issues]}

            # Process results
            execution_time = time.time() - start_time

            # Update stats
            self.stats.total_searches += 1
            self.stats.total_results += len(results.get("issues", []))
            self.stats.total_execution_time += execution_time
            self.stats.popular_queries[natural_query] = self.stats.popular_queries.get(natural_query, 0) + 1

            # Extract field usage
            for field in self._extract_fields_from_query(yql_query):
                self.stats.field_usage[field] = self.stats.field_usage.get(field, 0) + 1

            # Build response
            response = {
                "query": {
                    "natural": natural_query,
                    "yql": yql_query
                },
                "results": results,
                "metadata": {
                    "execution_time": execution_time,
                    "result_count": len(results.get("issues", [])),
                    "from_cache": False
                }
            }

            # Add suggestions if requested
            if include_suggestions:
                response["suggestions"] = self._generate_suggestions(natural_query, results)
            
            # Cache the result
            self.query_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            self.stats.error_count += 1
            logger.exception(f"Error in intelligent search: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "query": natural_query
            }

    async def search_by_query_builder(
        self,
        conditions: List[Dict[str, Any]],
        text_search: Optional[str] = None,
        projects: Optional[List[str]] = None,
        limit: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> dict:
        """
        Build and execute complex searches using structured conditions.
        
        FORMAT: search_by_query_builder(conditions=[{"field": "state", "operator": ":", "value": "Open"}])
        
        Args:
            conditions: List of search conditions with field, operator, value
            text_search: Optional free text search
            projects: Optional list of projects to search in
            limit: Maximum results
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            JSON string with search results
        """
        try:
            # Build query from conditions
            query_parts = []
            
            # Add project scope if specified
            if projects:
                project_query = f"project: ({', '.join(projects)})"
                query_parts.append(project_query)
            
            # Add conditions
            for cond in conditions:
                condition = SearchCondition(
                    field=cond["field"],
                    operator=SearchOperator(cond.get("operator", ":")),
                    value=cond["value"],
                    negated=cond.get("negated", False)
                )
                query_parts.append(condition.to_query_string())
            
            # Add text search if specified
            if text_search:
                query_parts.append(f"text: \"{text_search}\"")
            
            # Combine query parts
            final_query = " AND ".join(query_parts) if query_parts else "*"
            
            # Execute search with sorting
            sort_param = None
            if sort_by:
                order_prefix = "-" if sort_order.lower() == "desc" else ""
                sort_param = f"{order_prefix}{sort_by}"
            
            results = await self.issues_api.search_issues(
                query=final_query,
                limit=limit
            )
            
            return {
                "query": final_query,
                "conditions": conditions,
                "results": results,
                "metadata": {
                    "total_conditions": len(conditions),
                    "projects": projects,
                    "sort": {"field": sort_by, "order": sort_order} if sort_by else None
                }
            }
            
        except Exception as e:
            logger.exception(f"Error in query builder search: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "conditions": conditions
            }

    async def search_suggestions(self, partial_query: str, context: Optional[str] = None) -> dict:
        """
        Get search suggestions and auto-completions.
        
        FORMAT: search_suggestions(partial_query="state: ", context="project: DEMO")
        
        Args:
            partial_query: Partial query for suggestions
            context: Optional context (e.g., current project)
            
        Returns:
            JSON string with suggestions
        """
        try:
            # Check cache
            cache_key = f"{partial_query}:{context}"
            if cache_key in self.suggestion_cache:
                return self.suggestion_cache[cache_key]
            
            suggestions = []
            
            # Detect what user is typing
            if partial_query.endswith(": ") or partial_query.endswith(":"):
                # User typed a field, suggest values
                field = partial_query.rstrip(": ").split()[-1]
                suggestions = self._suggest_field_values(field, context)
            elif " " not in partial_query or partial_query.endswith(" "):
                # Suggest fields
                suggestions = self._suggest_fields(partial_query.strip())
            else:
                # Suggest operators or values
                parts = partial_query.split()
                if len(parts) >= 2 and not any(op in parts[-1] for op in [":", "!:", "~", ">", "<"]):
                    # Suggest operators
                    suggestions = [
                        {"value": ":", "description": "equals"},
                        {"value": "!:", "description": "not equals"},
                        {"value": "~", "description": "contains"},
                        {"value": ">", "description": "greater than"},
                        {"value": "<", "description": "less than"}
                    ]
            
            result = {
                "query": partial_query,
                "suggestions": suggestions,
                "context": context
            }
            
            # Cache result
            self.suggestion_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating suggestions: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "query": partial_query
            }

    async def search_analytics(self) -> dict:
        """
        Get search analytics and performance metrics.
        
        FORMAT: search_analytics()
        
        Returns:
            JSON string with analytics data
        """
        try:
            # Calculate metrics
            avg_execution_time = (
                self.stats.total_execution_time / self.stats.total_searches
                if self.stats.total_searches > 0 else 0
            )
            
            cache_hit_rate = (
                self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses)
                if (self.stats.cache_hits + self.stats.cache_misses) > 0 else 0
            )
            
            # Get top queries
            top_queries = sorted(
                self.stats.popular_queries.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Get top fields
            top_fields = sorted(
                self.stats.field_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "performance": {
                    "total_searches": self.stats.total_searches,
                    "total_results": self.stats.total_results,
                    "average_execution_time": avg_execution_time,
                    "total_errors": self.stats.error_count
                },
                "cache": {
                    "hits": self.stats.cache_hits,
                    "misses": self.stats.cache_misses,
                    "hit_rate": cache_hit_rate,
                    "current_size": len(self.query_cache)
                },
                "usage": {
                    "top_queries": [{"query": q, "count": c} for q, c in top_queries],
                    "top_fields": [{"field": f, "count": c} for f, c in top_fields]
                },
                "period": {
                    "start": self.stats.last_reset.isoformat(),
                    "duration_hours": (datetime.now() - self.stats.last_reset).total_seconds() / 3600
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting analytics: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__
            }

    async def clear_search_cache(self) -> dict:
        """
        Clear search caches and optionally reset analytics.
        
        FORMAT: clear_search_cache()
        
        Returns:
            JSON string with cache clear results
        """
        try:
            query_cache_size = len(self.query_cache)
            suggestion_cache_size = len(self.suggestion_cache)
            
            self.query_cache.clear()
            self.suggestion_cache.clear()
            
            return {
                "cleared": {
                    "query_cache": query_cache_size,
                    "suggestion_cache": suggestion_cache_size
                },
                "status": "success"
            }
            
        except Exception as e:
            logger.exception(f"Error clearing cache: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _natural_to_yql(self, natural_query: str, project: Optional[str] = None) -> dict:
        """Convert natural language to YouTrack Query Language."""
        query = natural_query.lower()
        parts = []
        
        # Add project scope if specified
        if project:
            parts.append(f"project: {project}")
        
        # Parse time ranges
        time_patterns = {
            r"(last|past) week": "created: -7d .. *",
            r"(last|past) month": "created: -30d .. *",
            r"(last|past) (\d+) days?": lambda m: f"created: -{m.group(2)}d .. *",
            r"today": "created: Today",
            r"yesterday": "created: Yesterday"
        }
        
        for pattern, replacement in time_patterns.items():
            match = re.search(pattern, query)
            if match:
                if callable(replacement):
                    parts.append(replacement(match))
                else:
                    parts.append(replacement)
                query = re.sub(pattern, "", query)
        
        # Parse assignment
        if "assigned to me" in query or "my" in query:
            parts.append("assignee: me")
            query = query.replace("assigned to me", "").replace("my", "")
        elif match := re.search(r"assigned to (\w+)", query):
            parts.append(f"assignee: {match.group(1)}")
            query = re.sub(r"assigned to \w+", "", query)
        
        # Parse states
        state_mappings = {
            "open": "state: Open",
            "closed": "state: Closed",
            "resolved": "state: Resolved",
            "in progress": "state: {In Progress}",
            "unresolved": "#Unresolved"
        }
        
        for keyword, yql in state_mappings.items():
            if keyword in query:
                parts.append(yql)
                query = query.replace(keyword, "")
        
        # Parse types
        type_mappings = {
            "bugs?": "type: Bug",
            "features?": "type: Feature",
            "tasks?": "type: Task",
            "issues?": ""  # Generic, no type filter
        }
        
        for keyword, yql in type_mappings.items():
            if re.search(keyword, query):
                if yql:
                    parts.append(yql)
                query = re.sub(keyword, "", query)
        
        # Parse priority
        if "high priority" in query:
            parts.append("priority: High")
            query = query.replace("high priority", "")
        elif "critical" in query:
            parts.append("priority: Critical")
            query = query.replace("critical", "")
        
        # Any remaining text as text search
        remaining = query.strip()
        if remaining and remaining not in ["the", "all", "show", "find", "get"]:
            parts.append(f"text: \"{remaining}\"")
        
        return " ".join(parts) if parts else "*"
    
    def _extract_fields_from_query(self, query: str) -> List[str]:
        """Extract field names from a YQL query."""
        # Simple regex to find field names
        fields = re.findall(r"(\w+):\s*", query)
        return list(set(fields))
    
    def _generate_suggestions(self, query: str, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate query refinement suggestions based on results."""
        suggestions = []
        
        # Suggest adding project filter if not present
        if "project:" not in query and results.get("issues"):
            projects = set()
            for issue in results.get("issues", [])[:10]:
                if project := issue.get("project", {}).get("shortName"):
                    projects.add(project)
            
            if len(projects) > 1:
                for project in list(projects)[:3]:
                    suggestions.append({
                        "type": "refinement",
                        "suggestion": f"{query} project: {project}",
                        "description": f"Filter by {project} project"
                    })
        
        # Suggest state filters if not present
        if not any(state in query.lower() for state in ["state:", "resolved", "unresolved", "#"]):
            suggestions.append({
                "type": "refinement", 
                "suggestion": f"{query} #Unresolved",
                "description": "Show only unresolved issues"
            })
        
        return suggestions
    
    def _suggest_fields(self, partial: str) -> List[Dict[str, str]]:
        """Suggest field names."""
        common_fields = [
            {"value": "project", "description": "Filter by project"},
            {"value": "assignee", "description": "Filter by assignee"},
            {"value": "state", "description": "Filter by state"},
            {"value": "type", "description": "Filter by issue type"},
            {"value": "priority", "description": "Filter by priority"},
            {"value": "created", "description": "Filter by creation date"},
            {"value": "updated", "description": "Filter by update date"},
            {"value": "reporter", "description": "Filter by reporter"},
            {"value": "tag", "description": "Filter by tag"},
            {"value": "text", "description": "Search in text"}
        ]
        
        if partial:
            return [f for f in common_fields if f["value"].startswith(partial.lower())]
        return common_fields[:5]
    
    def _suggest_field_values(self, field: str, context: Optional[str] = None) -> List[Dict[str, str]]:
        """Suggest values for a specific field."""
        suggestions = []
        
        if field == "state":
            suggestions = [
                {"value": "Open", "description": "Open issues"},
                {"value": "In Progress", "description": "Work in progress"},
                {"value": "Resolved", "description": "Resolved issues"},
                {"value": "Closed", "description": "Closed issues"}
            ]
        elif field == "type":
            suggestions = [
                {"value": "Bug", "description": "Bug reports"},
                {"value": "Feature", "description": "Feature requests"},
                {"value": "Task", "description": "Tasks"},
                {"value": "Epic", "description": "Epics"}
            ]
        elif field == "priority":
            suggestions = [
                {"value": "Critical", "description": "Critical priority"},
                {"value": "High", "description": "High priority"},
                {"value": "Normal", "description": "Normal priority"},
                {"value": "Low", "description": "Low priority"}
            ]
        elif field == "assignee":
            suggestions = [
                {"value": "me", "description": "Assigned to me"},
                {"value": "Unassigned", "description": "Not assigned"}
            ]
        
        return suggestions
    
    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get tool definitions for this module."""
        return {
            "intelligent_search": {
                "description": "Natural language search with intelligent query conversion",
                "category": "search"
            },
            "search_by_query_builder": {
                "description": "Build complex searches with structured conditions",
                "category": "search"
            },
            "search_suggestions": {
                "description": "Get search suggestions and auto-completions",
                "category": "search"
            },
            "search_analytics": {
                "description": "View search performance metrics and usage analytics",
                "category": "search"
            },
            "clear_search_cache": {
                "description": "Clear search result caches",
                "category": "search"
            }
        }


__all__ = ["AdvancedSearchTools"]