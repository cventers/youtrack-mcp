"""
Advanced Search Engine for YouTrack MCP Server.

Provides sophisticated search capabilities including query building, 
result caching, search optimization, and analytics.
"""
import asyncio
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator
from youtrack_mcp.api.client import YouTrackClient, YouTrackModel

logger = logging.getLogger(__name__)


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


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class SearchScope(str, Enum):
    """Search scope options."""
    ALL = "all"
    CURRENT_PROJECT = "current_project"
    VISIBLE_PROJECTS = "visible_projects"
    SPECIFIC_PROJECTS = "specific_projects"


@dataclass
class SearchCondition:
    """Represents a single search condition."""
    field: str
    operator: SearchOperator
    value: Any
    negated: bool = False
    
    def to_query_string(self) -> str:
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


class SearchQuery(YouTrackModel):
    """Advanced search query builder with validation."""
    
    conditions: List[SearchCondition] = Field(default_factory=list, description="Search conditions")
    text_search: Optional[str] = Field(None, description="Free text search")
    project_scope: SearchScope = Field(SearchScope.ALL, description="Project search scope")
    specific_projects: List[str] = Field(default_factory=list, description="Specific projects for scope")
    
    # Pagination and sorting
    limit: int = Field(50, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")
    sort_field: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    
    # Field selection
    include_fields: List[str] = Field(default_factory=list, description="Specific fields to include")
    exclude_fields: List[str] = Field(default_factory=list, description="Fields to exclude")
    include_custom_fields: bool = Field(True, description="Include custom fields in results")
    
    # Advanced options
    include_archived: bool = Field(False, description="Include archived projects")
    include_resolved: bool = Field(True, description="Include resolved issues")
    date_range_field: Optional[str] = Field(None, description="Field for date range filtering")
    date_from: Optional[datetime] = Field(None, description="Start date for filtering")
    date_to: Optional[datetime] = Field(None, description="End date for filtering")
    
    @field_validator('specific_projects')
    @classmethod
    def validate_specific_projects(cls, v, values):
        """Validate specific projects are provided when scope requires them."""
        if values.get('project_scope') == SearchScope.SPECIFIC_PROJECTS and not v:
            raise ValueError("specific_projects must be provided when project_scope is SPECIFIC_PROJECTS")
        return v
    
    def add_condition(self, field: str, operator: SearchOperator, value: Any, negated: bool = False) -> 'SearchQuery':
        """Add a search condition."""
        condition = SearchCondition(field=field, operator=operator, value=value, negated=negated)
        self.conditions.append(condition)
        return self
    
    def add_text_search(self, text: str) -> 'SearchQuery':
        """Add free text search."""
        self.text_search = text
        return self
    
    def add_date_range(self, field: str, from_date: Optional[datetime] = None, 
                      to_date: Optional[datetime] = None) -> 'SearchQuery':
        """Add date range filtering."""
        self.date_range_field = field
        self.date_from = from_date
        self.date_to = to_date
        return self
    
    def set_pagination(self, limit: int, offset: int = 0) -> 'SearchQuery':
        """Set pagination parameters."""
        self.limit = limit
        self.offset = offset
        return self
    
    def set_sorting(self, field: str, order: SortOrder = SortOrder.DESC) -> 'SearchQuery':
        """Set sorting parameters."""
        self.sort_field = field
        self.sort_order = order
        return self
    
    def to_youtrack_query(self) -> str:
        """Convert to YouTrack query string."""
        query_parts = []
        
        # Add conditions
        for condition in self.conditions:
            query_parts.append(condition.to_query_string())
        
        # Add project scope
        if self.project_scope == SearchScope.SPECIFIC_PROJECTS:
            if len(self.specific_projects) == 1:
                query_parts.append(f'project: "{self.specific_projects[0]}"')
            else:
                projects = ", ".join([f'"{p}"' for p in self.specific_projects])
                query_parts.append(f"project: ({projects})")
        
        # Add text search
        if self.text_search:
            # Search in summary and description
            text_query = f'(summary: "{self.text_search}" or description: "{self.text_search}")'
            query_parts.append(text_query)
        
        # Add date range
        if self.date_range_field and (self.date_from or self.date_to):
            if self.date_from and self.date_to:
                from_str = self.date_from.strftime("%Y-%m-%d")
                to_str = self.date_to.strftime("%Y-%m-%d")
                query_parts.append(f"{self.date_range_field}: {from_str} .. {to_str}")
            elif self.date_from:
                from_str = self.date_from.strftime("%Y-%m-%d")
                query_parts.append(f"{self.date_range_field}: {from_str} .. *")
            elif self.date_to:
                to_str = self.date_to.strftime("%Y-%m-%d")
                query_parts.append(f"{self.date_range_field}: * .. {to_str}")
        
        # Add archived filter
        if not self.include_archived:
            query_parts.append("project.archived: false")
        
        # Add resolved filter
        if not self.include_resolved:
            query_parts.append("resolved: Unresolved")
        
        return " and ".join(query_parts) if query_parts else "*"


@dataclass
class SearchResult:
    """Search result with metadata."""
    issues: List[Dict[str, Any]]
    total_count: int
    execution_time: float
    query_used: str
    cache_hit: bool = False
    suggested_queries: List[str] = field(default_factory=list)
    facets: Dict[str, Dict[str, int]] = field(default_factory=dict)


class SearchCache:
    """In-memory cache for search results."""
    
    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 300):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[SearchResult, float]] = {}
        self._access_times: Dict[str, float] = {}
    
    def _cleanup_expired(self):
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def _cleanup_lru(self):
        """Remove least recently used entries if cache is full."""
        if len(self._cache) >= self.max_entries:
            # Remove 20% of least recently used entries
            remove_count = max(1, self.max_entries // 5)
            lru_keys = sorted(self._access_times.keys(), key=lambda k: self._access_times[k])[:remove_count]
            for key in lru_keys:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
    
    def get(self, query_hash: str) -> Optional[SearchResult]:
        """Get cached search result."""
        self._cleanup_expired()
        
        if query_hash in self._cache:
            result, _ = self._cache[query_hash]
            self._access_times[query_hash] = time.time()
            result.cache_hit = True
            return result
        
        return None
    
    def put(self, query_hash: str, result: SearchResult):
        """Cache search result."""
        self._cleanup_expired()
        self._cleanup_lru()
        
        current_time = time.time()
        self._cache[query_hash] = (result, current_time)
        self._access_times[query_hash] = current_time
    
    def clear(self):
        """Clear all cached results."""
        self._cache.clear()
        self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
            "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_request_count', 1), 1)
        }


class SearchAnalytics:
    """Search analytics and performance monitoring."""
    
    def __init__(self):
        self.query_counts: Dict[str, int] = defaultdict(int)
        self.execution_times: List[float] = []
        self.popular_fields: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.start_time = time.time()
    
    def record_search(self, query: str, execution_time: float, result_count: int, 
                     fields_used: List[str], error: Optional[str] = None):
        """Record search analytics."""
        # Normalize query for counting
        normalized_query = re.sub(r'\d+', 'N', query.lower())
        self.query_counts[normalized_query] += 1
        
        if error:
            self.error_counts[error] += 1
        else:
            self.execution_times.append(execution_time)
            for field in fields_used:
                self.popular_fields[field] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analytics statistics."""
        total_searches = sum(self.query_counts.values())
        avg_execution_time = sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0
        
        return {
            "total_searches": total_searches,
            "unique_query_patterns": len(self.query_counts),
            "average_execution_time": avg_execution_time,
            "max_execution_time": max(self.execution_times) if self.execution_times else 0,
            "popular_queries": dict(sorted(self.query_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "popular_fields": dict(sorted(self.popular_fields.items(), key=lambda x: x[1], reverse=True)[:10]),
            "error_counts": dict(self.error_counts),
            "uptime_seconds": time.time() - self.start_time
        }


class AdvancedSearchEngine:
    """Advanced search engine with caching, analytics, and optimization."""
    
    def __init__(self, client: YouTrackClient, enable_cache: bool = True, enable_analytics: bool = True):
        self.client = client
        self.enable_cache = enable_cache
        self.enable_analytics = enable_analytics
        
        self.cache = SearchCache() if enable_cache else None
        self.analytics = SearchAnalytics() if enable_analytics else None
        
        # Field mappings for optimization
        self._field_mappings = {
            "id": "idReadable",
            "created_by": "reporter",
            "assigned_to": "assignee",
            "created_date": "created",
            "updated_date": "updated",
            "resolved_date": "resolved"
        }
    
    def create_query(self) -> SearchQuery:
        """Create a new search query builder."""
        return SearchQuery()
    
    async def search(self, query: Union[str, SearchQuery], **kwargs) -> SearchResult:
        """
        Execute advanced search with caching and analytics.
        
        Args:
            query: Search query (string or SearchQuery object)
            **kwargs: Additional search parameters
            
        Returns:
            SearchResult with issues and metadata
        """
        start_time = time.time()
        
        # Convert string query to SearchQuery if needed
        if isinstance(query, str):
            search_query = SearchQuery()
            search_query.text_search = query
            # Apply kwargs
            for key, value in kwargs.items():
                if hasattr(search_query, key):
                    setattr(search_query, key, value)
        else:
            search_query = query
        
        # Generate cache key
        query_string = search_query.to_youtrack_query()
        cache_key = self._generate_cache_key(search_query)
        
        # Check cache
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                if self.analytics:
                    self.analytics.record_search(
                        query_string, 
                        time.time() - start_time,
                        len(cached_result.issues),
                        self._extract_fields_from_query(query_string)
                    )
                return cached_result
        
        try:
            # Execute search
            result = await self._execute_search(search_query)
            result.execution_time = time.time() - start_time
            result.query_used = query_string
            
            # Cache result
            if self.cache:
                self.cache.put(cache_key, result)
            
            # Record analytics
            if self.analytics:
                self.analytics.record_search(
                    query_string,
                    result.execution_time,
                    len(result.issues),
                    self._extract_fields_from_query(query_string)
                )
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            if self.analytics:
                self.analytics.record_search(
                    query_string,
                    time.time() - start_time,
                    0,
                    [],
                    error_msg
                )
            raise
    
    async def _execute_search(self, query: SearchQuery) -> SearchResult:
        """Execute the actual search against YouTrack API."""
        # Build API parameters
        params = {
            "query": query.to_youtrack_query(),
            "$top": query.limit,
            "$skip": query.offset
        }
        
        # Add sorting
        if query.sort_field:
            params["$orderBy"] = f"{query.sort_field} {query.sort_order.value}"
        
        # Build fields parameter
        fields = self._build_fields_parameter(query)
        if fields:
            params["fields"] = fields
        
        # Execute API call
        issues = await self.client.get("issues", params=params)
        
        # Get total count (if needed)
        total_count = len(issues)
        if len(issues) == query.limit:
            # There might be more results, do a count query
            count_params = {"query": params["query"], "$top": 0}
            count_result = await self.client.get("issues", params=count_params)
            # YouTrack doesn't return count directly, so we estimate
            total_count = query.offset + len(issues) + (1 if len(issues) == query.limit else 0)
        
        # Generate facets if requested
        facets = await self._generate_facets(query) if query.limit <= 100 else {}
        
        # Generate suggested queries
        suggested_queries = self._generate_suggestions(query.to_youtrack_query())
        
        return SearchResult(
            issues=issues,
            total_count=total_count,
            execution_time=0.0,  # Will be set by caller
            query_used="",  # Will be set by caller
            facets=facets,
            suggested_queries=suggested_queries
        )
    
    def _build_fields_parameter(self, query: SearchQuery) -> str:
        """Build the fields parameter for the API request."""
        base_fields = [
            "id", "idReadable", "summary", "description", "created", "updated", "resolved",
            "project(id,name,shortName)", "reporter(id,login,name)", "assignee(id,login,name)"
        ]
        
        # Add custom fields if requested
        if query.include_custom_fields:
            base_fields.append("customFields(id,name,value(id,name,$type,text,presentation))")
        
        # Add specific fields
        if query.include_fields:
            base_fields.extend(query.include_fields)
        
        # Remove excluded fields
        if query.exclude_fields:
            base_fields = [f for f in base_fields if not any(excl in f for excl in query.exclude_fields)]
        
        return ",".join(base_fields)
    
    async def _generate_facets(self, query: SearchQuery) -> Dict[str, Dict[str, int]]:
        """Generate facets for search results."""
        facets = {}
        
        # Common facet fields
        facet_fields = ["project", "assignee", "State", "Priority", "Type"]
        
        for field in facet_fields:
            try:
                # Get unique values for this field
                facet_query = f"{query.to_youtrack_query()} #{{{field}}}"
                facet_params = {
                    "query": facet_query,
                    "$top": 0,
                    "fields": f"{field}(name)"
                }
                
                # This is a simplified facet implementation
                # In a real implementation, you'd need to aggregate the results
                facets[field] = {"All": 0}  # Placeholder
                
            except Exception as e:
                logger.warning(f"Failed to generate facets for field {field}: {e}")
        
        return facets
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate query suggestions based on the current query."""
        suggestions = []
        
        # Add common refinements
        if "state:" not in query.lower():
            suggestions.append(f"{query} State: Open")
        
        if "assignee:" not in query.lower():
            suggestions.append(f"{query} Assignee: Unassigned")
        
        if "created:" not in query.lower():
            suggestions.append(f"{query} created: -7d .. *")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _generate_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for the query."""
        import hashlib
        
        # Include all relevant query parameters
        key_data = {
            "query": query.to_youtrack_query(),
            "limit": query.limit,
            "offset": query.offset,
            "sort_field": query.sort_field,
            "sort_order": query.sort_order.value,
            "include_fields": sorted(query.include_fields),
            "exclude_fields": sorted(query.exclude_fields),
            "include_custom_fields": query.include_custom_fields
        }
        
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _extract_fields_from_query(self, query: str) -> List[str]:
        """Extract field names used in the query."""
        # Simple regex to extract field names
        pattern = r'(\w+):\s*'
        matches = re.findall(pattern, query)
        return list(set(matches))
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = []
        
        # Field name suggestions
        common_fields = [
            "project", "assignee", "reporter", "state", "priority", "type",
            "created", "updated", "resolved", "summary", "description"
        ]
        
        # If the partial query ends with a field name being typed
        words = partial_query.split()
        if words:
            last_word = words[-1].lower()
            for field in common_fields:
                if field.startswith(last_word) and field not in partial_query.lower():
                    suggested_query = " ".join(words[:-1] + [f"{field}:"])
                    suggestions.append(suggested_query.strip())
        
        # Value suggestions based on analytics
        if self.analytics and ":" in partial_query:
            # Extract field being completed
            field_match = re.search(r'(\w+):\s*$', partial_query)
            if field_match:
                field_name = field_match.group(1)
                # Add common values for this field
                common_values = {
                    "state": ["Open", "Fixed", "Verified", "Closed"],
                    "priority": ["Critical", "High", "Normal", "Low"],
                    "assignee": ["Unassigned", "me"]
                }
                
                if field_name.lower() in common_values:
                    for value in common_values[field_name.lower()]:
                        suggestions.append(f"{partial_query} {value}")
        
        return suggestions[:limit]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats() if self.cache else {}
    
    def get_analytics_stats(self) -> Dict[str, Any]:
        """Get analytics statistics."""
        return self.analytics.get_stats() if self.analytics else {}
    
    def clear_cache(self):
        """Clear search cache."""
        if self.cache:
            self.cache.clear()


# Utility functions for common search patterns
def create_issue_search(project: str = None, assignee: str = None, state: str = None) -> SearchQuery:
    """Create a basic issue search query."""
    query = SearchQuery()
    
    if project:
        query.add_condition("project", SearchOperator.EQUALS, project)
    if assignee:
        query.add_condition("assignee", SearchOperator.EQUALS, assignee)
    if state:
        query.add_condition("State", SearchOperator.EQUALS, state)
    
    return query


def create_date_range_search(field: str, days_back: int) -> SearchQuery:
    """Create a search query for issues within a date range."""
    query = SearchQuery()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    query.add_date_range(field, start_date, end_date)
    return query


def create_text_search(text: str, fields: List[str] = None) -> SearchQuery:
    """Create a text search query."""
    query = SearchQuery()
    
    if fields:
        # Search in specific fields
        for field in fields:
            query.add_condition(field, SearchOperator.CONTAINS, text)
    else:
        # General text search
        query.add_text_search(text)
    
    return query