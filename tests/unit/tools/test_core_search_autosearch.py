"""
Golden tests for core search autosearch confidence rails.

Tests the natural language to YQL translation with confidence scoring.
"""

import pytest
from unittest.mock import Mock, patch
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.utils import format_json_response


class TestCoreSearchAutosearch:
    """Test cases for autosearch functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = SearchTools()
        self.tools.client = Mock()

    def test_autosearch_high_confidence(self):
        """Test autosearch with high confidence translation."""
        # Mock the translation and search
        mock_results = [
            {"id": "DEMO-123", "summary": "Login bug", "assignee": {"name": "John"}},
            {"id": "DEMO-456", "summary": "Password reset issue", "assignee": {"name": "John"}}
        ]

        with patch.object(self.tools, '_translate_natural_language') as mock_translate, \
             patch.object(self.tools, '_execute_search') as mock_execute:

            mock_translate.return_value = {
                "yql": "assignee: me #Unresolved",
                "confidence": 0.95,
                "explanation": "High confidence translation for 'my unresolved issues'"
            }
            mock_execute.return_value = mock_results

            result = self.tools.autosearch("my unresolved issues")

            # Verify translation was called
            mock_translate.assert_called_once_with("my unresolved issues", None)

            # Verify search was executed
            mock_execute.assert_called_once_with("assignee: me #Unresolved", 10)

            # Verify response format
            expected = format_json_response({
                "query": "my unresolved issues",
                "yql_translation": "assignee: me #Unresolved",
                "confidence": 0.95,
                "explanation": "High confidence translation for 'my unresolved issues'",
                "results": mock_results,
                "result_count": 2
            })
            assert result == expected

    def test_autosearch_medium_confidence(self):
        """Test autosearch with medium confidence."""
        mock_results = [
            {"id": "DEMO-123", "summary": "Database connection issue"}
        ]

        with patch.object(self.tools, '_translate_natural_language') as mock_translate, \
             patch.object(self.tools, '_execute_search') as mock_execute:

            mock_translate.return_value = {
                "yql": "text: database connection",
                "confidence": 0.75,
                "explanation": "Medium confidence - using text search for 'database problems'"
            }
            mock_execute.return_value = mock_results

            result = self.tools.autosearch("database problems")

            expected = format_json_response({
                "query": "database problems",
                "yql_translation": "text: database connection",
                "confidence": 0.75,
                "explanation": "Medium confidence - using text search for 'database problems'",
                "results": mock_results,
                "result_count": 1
            })
            assert result == expected

    def test_autosearch_low_confidence_fallback(self):
        """Test autosearch with low confidence falling back to text search."""
        mock_results = [
            {"id": "DEMO-123", "summary": "Some issue with xyz"}
        ]

        with patch.object(self.tools, '_translate_natural_language') as mock_translate, \
             patch.object(self.tools, '_execute_search') as mock_execute:

            mock_translate.return_value = {
                "yql": "text: xyz problems",
                "confidence": 0.45,
                "explanation": "Low confidence - falling back to text search"
            }
            mock_execute.return_value = mock_results

            result = self.tools.autosearch("xyz problems")

            expected = format_json_response({
                "query": "xyz problems",
                "yql_translation": "text: xyz problems",
                "confidence": 0.45,
                "explanation": "Low confidence - falling back to text search",
                "results": mock_results,
                "result_count": 1
            })
            assert result == expected

    def test_autosearch_with_project_context(self):
        """Test autosearch with project context for better translation."""
        mock_results = [
            {"id": "DEMO-123", "summary": "UI bug in login"}
        ]

        with patch.object(self.tools, '_translate_natural_language') as mock_translate, \
             patch.object(self.tools, '_execute_search') as mock_execute:

            mock_translate.return_value = {
                "yql": "project: DEMO text: login ui",
                "confidence": 0.88,
                "explanation": "Used project context to improve translation"
            }
            mock_execute.return_value = mock_results

            result = self.tools.autosearch("login ui issues", "DEMO")

            mock_translate.assert_called_once_with("login ui issues", "DEMO")

            expected = format_json_response({
                "query": "login ui issues",
                "project_context": "DEMO",
                "yql_translation": "project: DEMO text: login ui",
                "confidence": 0.88,
                "explanation": "Used project context to improve translation",
                "results": mock_results,
                "result_count": 1
            })
            assert result == expected

    def test_autosearch_no_results(self):
        """Test autosearch when no results are found."""
        with patch.object(self.tools, '_translate_natural_language') as mock_translate, \
             patch.object(self.tools, '_execute_search') as mock_execute:

            mock_translate.return_value = {
                "yql": "assignee: nonexistent",
                "confidence": 0.9,
                "explanation": "High confidence for user lookup"
            }
            mock_execute.return_value = []

            result = self.tools.autosearch("issues assigned to nonexistent user")

            expected = format_json_response({
                "query": "issues assigned to nonexistent user",
                "yql_translation": "assignee: nonexistent",
                "confidence": 0.9,
                "explanation": "High confidence for user lookup",
                "results": [],
                "result_count": 0,
                "suggestions": [
                    "Check if the user exists in the system",
                    "Try searching by user name instead of login",
                    "Use partial name matching"
                ]
            })
            assert result == expected

    def test_autosearch_translation_error(self):
        """Test autosearch when translation fails."""
        with patch.object(self.tools, '_translate_natural_language') as mock_translate:

            mock_translate.side_effect = Exception("Translation service unavailable")

            result = self.tools.autosearch("some query")

            assert "error" in result
            assert "Translation service unavailable" in result["error"]
            assert result["query"] == "some query"


class TestAutosearchConfidenceRails:
    """Test confidence scoring rails and thresholds."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = SearchTools()

    def test_high_confidence_threshold(self):
        """Test that high confidence (>= 0.8) uses direct YQL."""
        confidence = self.tools._calculate_confidence("assignee: me #Unresolved", "my unresolved issues")
        assert confidence >= 0.8

    def test_medium_confidence_threshold(self):
        """Test medium confidence (0.6-0.8) uses refined search."""
        confidence = self.tools._calculate_confidence("text: login issue", "login problems")
        assert 0.6 <= confidence < 0.8

    def test_low_confidence_threshold(self):
        """Test low confidence (< 0.6) falls back to text search."""
        confidence = self.tools._calculate_confidence("text: xyz", "some random query xyz")
        assert confidence < 0.6

    def test_exact_field_match_high_confidence(self):
        """Test exact field matches get high confidence."""
        confidence = self.tools._calculate_confidence("state: Open", "open issues")
        assert confidence >= 0.9

    def test_user_mention_high_confidence(self):
        """Test user mentions get high confidence."""
        confidence = self.tools._calculate_confidence("assignee: me", "my issues")
        assert confidence >= 0.85

    def test_date_range_medium_confidence(self):
        """Test date ranges get medium confidence."""
        confidence = self.tools._calculate_confidence("created: -7d .. *", "issues from last week")
        assert 0.7 <= confidence < 0.9

    def test_complex_query_variable_confidence(self):
        """Test complex queries get variable confidence based on complexity."""
        # Simple query
        simple = self.tools._calculate_confidence("project: DEMO", "demo project issues")
        assert simple >= 0.8

        # Complex query
        complex_query = self.tools._calculate_confidence(
            "project: DEMO assignee: me state: Open created: -30d .. *",
            "my open issues in demo from last month"
        )
        assert 0.6 <= complex_query < 0.9

    def test_confidence_rails_boundaries(self):
        """Test confidence rails stay within 0.0-1.0 bounds."""
        # Test various inputs
        test_queries = [
            "very specific technical term that should not match well",
            "assignee: me state: Open priority: Critical",
            "bugs",
            "issues created today",
            "project: DEMO unresolved tasks"
        ]

        for query in test_queries:
            confidence = self.tools._calculate_confidence(f"text: {query}", query)
            assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} out of bounds for query: {query}"