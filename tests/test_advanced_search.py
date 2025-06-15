"""
Advanced Search Tests for YouTrack MCP Server.

Tests the advanced search engine functionality including query building,
caching, analytics, and performance optimization.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtrack_mcp.search_advanced import (
    AdvancedSearchEngine, SearchQuery, SearchCondition, SearchOperator, 
    SortOrder, SearchScope, SearchResult, SearchCache, SearchAnalytics,
    create_issue_search, create_date_range_search, create_text_search
)
from youtrack_mcp.api.client import YouTrackClient


class TestSearchCondition:
    """Test search condition building and query string generation."""
    
    def test_basic_condition(self):
        """Test basic search condition."""
        condition = SearchCondition("project", SearchOperator.EQUALS, "TEST")
        assert condition.to_query_string() == 'project : "TEST"'
    
    def test_numeric_condition(self):
        """Test numeric search condition."""
        condition = SearchCondition("created", SearchOperator.GREATER_THAN, 1640995200000)
        assert condition.to_query_string() == "created > 1640995200000"
    
    def test_negated_condition(self):
        """Test negated search condition."""
        condition = SearchCondition("state", SearchOperator.EQUALS, "Closed", negated=True)
        assert condition.to_query_string() == 'state !: "Closed"'
    
    def test_in_condition(self):
        """Test IN operator with multiple values."""
        condition = SearchCondition("priority", SearchOperator.IN, ["High", "Critical"])
        assert condition.to_query_string() == 'priority in ("High", "Critical")'
    
    def test_special_values(self):
        """Test special values like 'me', 'Unassigned'."""
        condition = SearchCondition("assignee", SearchOperator.EQUALS, "Unassigned")
        assert condition.to_query_string() == "assignee : Unassigned"


class TestSearchQuery:
    """Test advanced search query building and validation."""
    
    def test_empty_query(self):
        """Test empty search query."""
        query = SearchQuery()
        assert query.to_youtrack_query() == "*"
    
    def test_basic_query_building(self):
        """Test basic query building."""
        query = SearchQuery()
        query.add_condition("project", SearchOperator.EQUALS, "TEST")
        query.add_condition("assignee", SearchOperator.EQUALS, "user1")
        
        query_str = query.to_youtrack_query()
        assert 'project : "TEST"' in query_str
        assert 'assignee : "user1"' in query_str
        assert " and " in query_str
    
    def test_text_search(self):
        """Test free text search."""
        query = SearchQuery()
        query.add_text_search("bug fix")
        
        query_str = query.to_youtrack_query()
        assert 'summary: "bug fix"' in query_str
        assert 'description: "bug fix"' in query_str
    
    def test_date_range(self):
        """Test date range filtering."""
        query = SearchQuery()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        query.add_date_range("created", start_date, end_date)
        
        query_str = query.to_youtrack_query()
        assert "created: 2024-01-01 .. 2024-01-31" in query_str
    
    def test_project_scope(self):
        """Test project scope filtering."""
        query = SearchQuery()
        query.project_scope = SearchScope.SPECIFIC_PROJECTS
        query.specific_projects = ["PROJ1", "PROJ2"]
        
        query_str = query.to_youtrack_query()
        assert 'project: ("PROJ1", "PROJ2")' in query_str
    
    def test_archived_filter(self):
        """Test archived project filtering."""
        query = SearchQuery()
        query.include_archived = False
        
        query_str = query.to_youtrack_query()
        assert "project.archived: false" in query_str
    
    def test_resolved_filter(self):
        """Test resolved issues filtering."""
        query = SearchQuery()
        query.include_resolved = False
        
        query_str = query.to_youtrack_query()
        assert "resolved: Unresolved" in query_str
    
    def test_validation_error(self):
        """Test validation for specific projects scope."""
        with pytest.raises(ValueError, match="specific_projects must be provided"):
            SearchQuery(
                project_scope=SearchScope.SPECIFIC_PROJECTS,
                specific_projects=[]
            )
    
    def test_method_chaining(self):
        """Test method chaining for query building."""
        query = (SearchQuery()
                .add_condition("project", SearchOperator.EQUALS, "TEST")
                .add_text_search("bug")
                .set_pagination(50, 10)
                .set_sorting("created", SortOrder.DESC))
        
        assert len(query.conditions) == 1
        assert query.text_search == "bug"
        assert query.limit == 50
        assert query.offset == 10
        assert query.sort_field == "created"
        assert query.sort_order == SortOrder.DESC


class TestSearchCache:
    """Test search result caching functionality."""
    
    @pytest.fixture
    def cache(self):
        """Create a search cache for testing."""
        return SearchCache(max_entries=10, ttl_seconds=1)
    
    def test_cache_put_get(self, cache):
        """Test basic cache put and get operations."""
        result = SearchResult(issues=[], total_count=0, execution_time=0.1, query_used="test")
        
        cache.put("test_key", result)
        retrieved = cache.get("test_key")
        
        assert retrieved is not None
        assert retrieved.cache_hit is True
        assert retrieved.query_used == "test"
    
    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_expiry(self, cache):
        """Test cache entry expiry."""
        result = SearchResult(issues=[], total_count=0, execution_time=0.1, query_used="test")
        
        cache.put("test_key", result)
        
        # Wait for expiry
        time.sleep(1.1)
        
        retrieved = cache.get("test_key")
        assert retrieved is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = SearchCache(max_entries=2, ttl_seconds=60)
        
        # Fill cache
        for i in range(3):
            result = SearchResult(issues=[], total_count=0, execution_time=0.1, query_used=f"test{i}")
            cache.put(f"key{i}", result)
        
        # First entry should be evicted
        assert cache.get("key0") is None
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
    
    def test_cache_stats(self, cache):
        """Test cache statistics."""
        stats = cache.get_stats()
        
        assert "entries" in stats
        assert "max_entries" in stats
        assert "ttl_seconds" in stats
        assert stats["max_entries"] == 10
        assert stats["ttl_seconds"] == 1


class TestSearchAnalytics:
    """Test search analytics functionality."""
    
    @pytest.fixture
    def analytics(self):
        """Create search analytics for testing."""
        return SearchAnalytics()
    
    def test_record_search(self, analytics):
        """Test recording search analytics."""
        analytics.record_search(
            query="project: TEST",
            execution_time=0.15,
            result_count=5,
            fields_used=["project", "assignee"]
        )
        
        stats = analytics.get_stats()
        assert stats["total_searches"] == 1
        assert stats["average_execution_time"] == 0.15
        assert stats["popular_fields"]["project"] == 1
        assert stats["popular_fields"]["assignee"] == 1
    
    def test_record_search_error(self, analytics):
        """Test recording search errors."""
        analytics.record_search(
            query="invalid query",
            execution_time=0.05,
            result_count=0,
            fields_used=[],
            error="Invalid syntax"
        )
        
        stats = analytics.get_stats()
        assert stats["error_counts"]["Invalid syntax"] == 1
    
    def test_query_normalization(self, analytics):
        """Test query normalization for counting."""
        analytics.record_search("project: TEST-123", 0.1, 1, ["project"])
        analytics.record_search("project: TEST-456", 0.1, 1, ["project"])
        
        stats = analytics.get_stats()
        # Both queries should be normalized to the same pattern
        assert stats["total_searches"] == 2
        assert stats["unique_query_patterns"] == 1
    
    def test_popular_queries(self, analytics):
        """Test popular queries tracking."""
        for i in range(5):
            analytics.record_search("project: test", 0.1, 1, ["project"])
        
        for i in range(3):
            analytics.record_search("assignee: user", 0.1, 1, ["assignee"])
        
        stats = analytics.get_stats()
        popular = stats["popular_queries"]
        
        # Should be sorted by frequency
        query_counts = list(popular.values())
        assert query_counts[0] >= query_counts[1] if len(query_counts) > 1 else True


class TestAdvancedSearchEngine:
    """Test the advanced search engine integration."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock YouTrack client."""
        client = AsyncMock(spec=YouTrackClient)
        client.get.return_value = [
            {
                "id": "TEST-1",
                "summary": "Test Issue 1",
                "project": {"shortName": "TEST"},
                "created": 1640995200000
            },
            {
                "id": "TEST-2", 
                "summary": "Test Issue 2",
                "project": {"shortName": "TEST"},
                "created": 1640995300000
            }
        ]
        return client
    
    @pytest.fixture
    def search_engine(self, mock_client):
        """Create an advanced search engine for testing."""
        return AdvancedSearchEngine(mock_client, enable_cache=True, enable_analytics=True)
    
    @pytest.mark.asyncio
    async def test_string_query_search(self, search_engine):
        """Test search with string query."""
        result = await search_engine.search("project: TEST")
        
        assert isinstance(result, SearchResult)
        assert len(result.issues) == 2
        assert result.total_count == 2
        assert result.execution_time > 0
        assert result.query_used != ""
    
    @pytest.mark.asyncio
    async def test_search_query_object(self, search_engine):
        """Test search with SearchQuery object."""
        query = SearchQuery()
        query.add_condition("project", SearchOperator.EQUALS, "TEST")
        query.set_pagination(10)
        
        result = await search_engine.search(query)
        
        assert isinstance(result, SearchResult)
        assert len(result.issues) == 2
        assert result.total_count == 2
    
    @pytest.mark.asyncio
    async def test_search_caching(self, search_engine):
        """Test search result caching."""
        query = "project: TEST"
        
        # First search
        result1 = await search_engine.search(query)
        assert result1.cache_hit is False
        
        # Second search should hit cache
        result2 = await search_engine.search(query)
        assert result2.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_search_analytics_recording(self, search_engine):
        """Test analytics recording during search."""
        await search_engine.search("project: TEST")
        
        stats = search_engine.get_analytics_stats()
        assert stats["total_searches"] == 1
        assert stats["average_execution_time"] > 0
    
    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_engine):
        """Test search suggestions."""
        suggestions = await search_engine.get_search_suggestions("proj")
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should suggest "project:"
        assert any("project:" in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_engine):
        """Test search error handling."""
        # Mock client to raise an exception
        search_engine.client.get.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await search_engine.search("project: TEST")
        
        # Check that error was recorded in analytics
        stats = search_engine.get_analytics_stats()
        assert stats["error_counts"]["API Error"] == 1
    
    def test_cache_stats(self, search_engine):
        """Test cache statistics retrieval."""
        stats = search_engine.get_cache_stats()
        
        assert "entries" in stats
        assert "max_entries" in stats
        assert "ttl_seconds" in stats
    
    def test_analytics_stats(self, search_engine):
        """Test analytics statistics retrieval."""
        stats = search_engine.get_analytics_stats()
        
        assert "total_searches" in stats
        assert "unique_query_patterns" in stats
        assert "average_execution_time" in stats
        assert "popular_queries" in stats
        assert "popular_fields" in stats
        assert "uptime_seconds" in stats
    
    def test_clear_cache(self, search_engine):
        """Test cache clearing."""
        # Add something to cache
        search_engine.cache.put("test", SearchResult([], 0, 0.1, "test"))
        assert search_engine.cache.get("test") is not None
        
        # Clear cache
        search_engine.clear_cache()
        assert search_engine.cache.get("test") is None


class TestUtilityFunctions:
    """Test utility functions for common search patterns."""
    
    def test_create_issue_search(self):
        """Test issue search utility function."""
        query = create_issue_search(project="TEST", assignee="user1", state="Open")
        
        assert len(query.conditions) == 3
        assert any(c.field == "project" and c.value == "TEST" for c in query.conditions)
        assert any(c.field == "assignee" and c.value == "user1" for c in query.conditions)
        assert any(c.field == "State" and c.value == "Open" for c in query.conditions)
    
    def test_create_date_range_search(self):
        """Test date range search utility function."""
        query = create_date_range_search("created", 7)
        
        assert query.date_range_field == "created"
        assert query.date_from is not None
        assert query.date_to is not None
        assert query.date_to > query.date_from
    
    def test_create_text_search(self):
        """Test text search utility function."""
        query = create_text_search("bug fix")
        
        assert query.text_search == "bug fix"
    
    def test_create_text_search_with_fields(self):
        """Test text search with specific fields."""
        query = create_text_search("error", fields=["summary", "description"])
        
        assert len(query.conditions) == 2
        assert any(c.field == "summary" and c.value == "error" for c in query.conditions)
        assert any(c.field == "description" and c.value == "error" for c in query.conditions)


class TestSearchPerformance:
    """Test search performance and optimization."""
    
    @pytest.mark.asyncio
    async def test_cache_performance(self):
        """Test that caching improves performance."""
        mock_client = AsyncMock(spec=YouTrackClient)
        
        # Simulate slow API response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return [{"id": "TEST-1", "summary": "Test"}]
        
        mock_client.get = slow_response
        
        search_engine = AdvancedSearchEngine(mock_client, enable_cache=True)
        
        # First search (slow)
        start_time = time.time()
        await search_engine.search("project: TEST")
        first_duration = time.time() - start_time
        
        # Second search (should be much faster due to cache)
        start_time = time.time()
        result = await search_engine.search("project: TEST")
        second_duration = time.time() - start_time
        
        assert result.cache_hit is True
        assert second_duration < first_duration / 2  # Should be much faster
    
    @pytest.mark.asyncio
    async def test_field_parameter_optimization(self):
        """Test field parameter optimization."""
        mock_client = AsyncMock(spec=YouTrackClient)
        mock_client.get.return_value = []
        
        search_engine = AdvancedSearchEngine(mock_client)
        
        query = SearchQuery()
        query.include_fields = ["summary", "description"]
        query.exclude_fields = ["customFields"]
        
        await search_engine.search(query)
        
        # Check that the API was called with optimized fields
        call_args = mock_client.get.call_args
        assert "fields" in call_args[1]["params"]
        fields_param = call_args[1]["params"]["fields"]
        assert "summary" in fields_param
        assert "description" in fields_param
        assert "customFields" not in fields_param


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])