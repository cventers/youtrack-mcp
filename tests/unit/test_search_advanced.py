"""
Unit tests for advanced search tools.
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from youtrack_mcp.tools.search_advanced import (
    AdvancedSearchTools, SearchCondition, SearchOperator, SearchStats
)


class TestSearchCondition:
    """Test SearchCondition query building."""
    
    def test_simple_equals_condition(self):
        """Test simple equals condition."""
        condition = SearchCondition(
            field="state",
            operator=SearchOperator.EQUALS,
            value="Open"
        )
        assert condition.to_query_string() == 'state : "Open"'
    
    def test_not_equals_condition(self):
        """Test not equals condition."""
        condition = SearchCondition(
            field="type",
            operator=SearchOperator.NOT_EQUALS,
            value="Bug"
        )
        assert condition.to_query_string() == 'type !: "Bug"'
    
    def test_negated_condition(self):
        """Test negated condition."""
        condition = SearchCondition(
            field="priority",
            operator=SearchOperator.EQUALS,
            value="High",
            negated=True
        )
        assert condition.to_query_string() == 'priority !: "High"'
    
    def test_special_values(self):
        """Test special string values."""
        # Special values should not be quoted
        condition1 = SearchCondition(
            field="assignee",
            operator=SearchOperator.EQUALS,
            value="me"
        )
        assert condition1.to_query_string() == "assignee : me"
        
        condition2 = SearchCondition(
            field="assignee",
            operator=SearchOperator.EQUALS,
            value="Unassigned"
        )
        assert condition2.to_query_string() == "assignee : Unassigned"
    
    def test_in_operator_with_list(self):
        """Test IN operator with list values."""
        condition = SearchCondition(
            field="project",
            operator=SearchOperator.IN,
            value=["DEMO", "WEB", "API"]
        )
        assert condition.to_query_string() == 'project in ("DEMO", "WEB", "API")'
    
    def test_multiple_values_with_other_operators(self):
        """Test multiple values with non-IN operators."""
        condition = SearchCondition(
            field="tag",
            operator=SearchOperator.EQUALS,
            value=["urgent", "critical", "bug"]
        )
        result = condition.to_query_string()
        assert result == '(tag : "urgent" or tag : "critical" or tag : "bug")'
    
    def test_numeric_values(self):
        """Test numeric values."""
        condition = SearchCondition(
            field="votes",
            operator=SearchOperator.GREATER_THAN,
            value=10
        )
        assert condition.to_query_string() == "votes > 10"


class TestAdvancedSearchTools:
    """Test suite for advanced search tools."""
    
    @pytest.fixture
    def search_tools(self):
        """Create AdvancedSearchTools instance with mocked APIs."""
        with patch('youtrack_mcp.tools.search_advanced.YouTrackClient'):
            tools = AdvancedSearchTools()
            # Mock the APIs
            tools.issues_api = MagicMock()
            tools.projects_api = MagicMock()
            return tools
    
    def test_initialization(self, search_tools):
        """Test search tools initialization."""
        assert search_tools.query_cache is not None
        assert search_tools.suggestion_cache is not None
        assert isinstance(search_tools.stats, SearchStats)
        assert search_tools.stats.total_searches == 0
    
    def test_intelligent_search_basic(self, search_tools):
        """Test basic intelligent search."""
        # Mock search results
        mock_results = {
            "issues": [
                {"id": "1", "summary": "Bug 1"},
                {"id": "2", "summary": "Bug 2"}
            ]
        }
        search_tools.issues_api.search_issues.return_value = mock_results
        
        result = search_tools.intelligent_search(
            "bugs assigned to me last week",
            project="DEMO",
            limit=10
        )
        result_dict = json.loads(result)
        
        # Verify YQL conversion happened
        assert "query" in result_dict
        assert result_dict["query"]["natural"] == "bugs assigned to me last week"
        assert "assignee: me" in result_dict["query"]["yql"]
        assert "type: Bug" in result_dict["query"]["yql"]
        
        # Verify results
        assert len(result_dict["results"]["issues"]) == 2
        assert result_dict["metadata"]["result_count"] == 2
        assert result_dict["metadata"]["from_cache"] is False
        
        # Verify stats updated
        assert search_tools.stats.total_searches == 1
        assert search_tools.stats.total_results == 2
    
    def test_intelligent_search_caching(self, search_tools):
        """Test search result caching."""
        mock_results = {"issues": [{"id": "1"}]}
        search_tools.issues_api.search_issues.return_value = mock_results
        
        # First search - should hit API
        result1 = search_tools.intelligent_search("open bugs", limit=5)
        result1_dict = json.loads(result1)
        assert result1_dict["metadata"]["from_cache"] is False
        assert search_tools.stats.cache_misses == 1
        
        # Second identical search - should hit cache
        result2 = search_tools.intelligent_search("open bugs", limit=5)
        result2_dict = json.loads(result2)
        assert result2_dict["from_cache"] is True
        assert search_tools.stats.cache_hits == 1
        
        # API should only be called once
        search_tools.issues_api.search_issues.assert_called_once()
    
    def test_intelligent_search_error_handling(self, search_tools):
        """Test error handling in intelligent search."""
        search_tools.issues_api.search_issues.side_effect = Exception("API Error")
        
        result = search_tools.intelligent_search("test query")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert result_dict["error"] == "API Error"
        assert result_dict["query"] == "test query"
        assert search_tools.stats.error_count == 1
    
    def test_search_by_query_builder(self, search_tools):
        """Test structured query builder search."""
        mock_results = {"issues": [{"id": "1"}]}
        search_tools.issues_api.search_issues.return_value = mock_results
        
        conditions = [
            {"field": "state", "operator": ":", "value": "Open"},
            {"field": "priority", "operator": ":", "value": "High"},
            {"field": "type", "operator": "!:", "value": "Task", "negated": True}
        ]
        
        result = search_tools.search_by_query_builder(
            conditions=conditions,
            text_search="login",
            projects=["DEMO", "WEB"],
            limit=20,
            sort_by="created",
            sort_order="desc"
        )
        result_dict = json.loads(result)
        
        # Verify query construction
        expected_parts = [
            "project: (DEMO, WEB)",
            'state: "Open"',
            'priority: "High"',
            'type !!: "Task"',  # Double negation
            'text: "login"'
        ]
        
        query = result_dict["query"]
        for part in expected_parts:
            assert part in query or part.replace("!!", "!") in query
        
        # Verify metadata
        assert result_dict["metadata"]["total_conditions"] == 3
        assert result_dict["metadata"]["projects"] == ["DEMO", "WEB"]
        assert result_dict["metadata"]["sort"]["field"] == "created"
        assert result_dict["metadata"]["sort"]["order"] == "desc"
    
    def test_search_suggestions_field_values(self, search_tools):
        """Test search suggestions for field values."""
        result = search_tools.search_suggestions("state: ", context="project: DEMO")
        result_dict = json.loads(result)
        
        assert len(result_dict["suggestions"]) > 0
        assert any(s["value"] == "Open" for s in result_dict["suggestions"])
        assert any(s["value"] == "Resolved" for s in result_dict["suggestions"])
    
    def test_search_suggestions_fields(self, search_tools):
        """Test search suggestions for fields."""
        result = search_tools.search_suggestions("proj", context=None)
        result_dict = json.loads(result)
        
        assert len(result_dict["suggestions"]) > 0
        assert any(s["value"] == "project" for s in result_dict["suggestions"])
    
    def test_search_suggestions_operators(self, search_tools):
        """Test search suggestions for operators."""
        result = search_tools.search_suggestions("state ", context=None)
        result_dict = json.loads(result)
        
        suggestions = result_dict["suggestions"]
        assert any(s["value"] == ":" for s in suggestions)
        assert any(s["value"] == "!:" for s in suggestions)
    
    def test_search_analytics(self, search_tools):
        """Test search analytics generation."""
        # Populate some stats
        search_tools.stats.total_searches = 10
        search_tools.stats.total_results = 150
        search_tools.stats.total_execution_time = 5.5
        search_tools.stats.cache_hits = 3
        search_tools.stats.cache_misses = 7
        search_tools.stats.popular_queries = {
            "bugs": 5,
            "features": 3,
            "assigned to me": 2
        }
        search_tools.stats.field_usage = {
            "state": 8,
            "project": 10,
            "assignee": 6
        }
        
        result = search_tools.analytics()
        result_dict = json.loads(result)
        
        # Verify performance metrics
        assert result_dict["performance"]["total_searches"] == 10
        assert result_dict["performance"]["average_execution_time"] == 0.55
        
        # Verify cache metrics
        assert result_dict["cache"]["hit_rate"] == 0.3
        assert result_dict["cache"]["hits"] == 3
        
        # Verify usage metrics
        assert len(result_dict["usage"]["top_queries"]) <= 10
        assert result_dict["usage"]["top_queries"][0]["query"] == "bugs"
        assert result_dict["usage"]["top_fields"][0]["field"] == "project"
    
    def test_clear_search_cache(self, search_tools):
        """Test clearing search caches."""
        # Add some items to caches
        search_tools.query_cache["test1"] = {"data": "test1"}
        search_tools.query_cache["test2"] = {"data": "test2"}
        search_tools.suggestion_cache["sug1"] = ["suggestion1"]
        
        result = search_tools.clear_search_cache()
        result_dict = json.loads(result)
        
        assert result_dict["cleared"]["query_cache"] == 2
        assert result_dict["cleared"]["suggestion_cache"] == 1
        assert len(search_tools.query_cache) == 0
        assert len(search_tools.suggestion_cache) == 0
    
    def test_natural_to_yql_conversion(self, search_tools):
        """Test natural language to YQL conversion."""
        # Test various natural language patterns
        test_cases = [
            ("bugs assigned to me", ["assignee: me", "type: Bug"]),
            ("open features last week", ["state: Open", "type: Feature", "Last week"]),
            ("critical issues today", ["priority: Critical", "Today"]),
            ("my tasks in progress", ["assignee: me", "type: Task", "In Progress"]),
            ("closed yesterday", ["state: Closed", "Yesterday"]),
            ("high priority bugs", ["priority: High", "type: Bug"])
        ]
        
        for natural, expected_parts in test_cases:
            yql = search_tools._natural_to_yql(natural)
            for part in expected_parts:
                assert part in yql, f"Expected '{part}' in YQL for '{natural}', got: {yql}"
    
    def test_natural_to_yql_with_project(self, search_tools):
        """Test natural language conversion with project context."""
        yql = search_tools._natural_to_yql("my bugs", project="DEMO")
        assert "project: DEMO" in yql
        assert "assignee: me" in yql
        assert "type: Bug" in yql
    
    def test_field_extraction(self, search_tools):
        """Test field extraction from YQL query."""
        query = "project: DEMO state: Open assignee: me type: Bug"
        fields = search_tools._extract_fields_from_query(query)
        
        assert "project" in fields
        assert "state" in fields
        assert "assignee" in fields
        assert "type" in fields
        assert len(fields) == 4
    
    def test_generate_suggestions(self, search_tools):
        """Test query refinement suggestions."""
        mock_results = {
            "issues": [
                {"project": {"shortName": "DEMO"}},
                {"project": {"shortName": "WEB"}},
                {"project": {"shortName": "API"}}
            ]
        }
        
        suggestions = search_tools._generate_suggestions("bugs", mock_results)
        
        # Should suggest project filters
        assert any("project: DEMO" in s["suggestion"] for s in suggestions)
        
        # Should suggest state filter
        assert any("#Unresolved" in s["suggestion"] for s in suggestions)
    
    def test_get_tool_definitions(self, search_tools):
        """Test tool definitions."""
        definitions = search_tools.get_tool_definitions()
        
        expected_tools = [
            "intelligent_search",
            "search_by_query_builder", 
            "search_suggestions",
            "search_analytics",
            "clear_search_cache"
        ]
        
        for tool in expected_tools:
            assert tool in definitions
            assert definitions[tool]["category"] == "search"
            assert "description" in definitions[tool]