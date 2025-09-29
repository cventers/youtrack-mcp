"""Integration test for autosearch functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import os

from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.tools.ai_tools import AITools
from youtrack_mcp.api.search import SearchClient


class TestAutosearchIntegration:
    """Test autosearch integration with the AI tools."""

    @pytest.mark.asyncio
    async def test_autosearch_without_ai_tools(self):
        """Test autosearch falls back gracefully without AI tools."""
        # Create SearchTools without AI tools
        mock_search_api = AsyncMock(spec=SearchClient)
        mock_search_api.search_issues.return_value = []
        
        search_tools = SearchTools(search_api=mock_search_api, ai_tools=None)
        
        # Attempt autosearch without AI
        result = await search_tools.autosearch("find bugs")
        
        # Should return an error or fallback
        assert "error" in result or result.get("degraded", False)
        
    @pytest.mark.asyncio
    async def test_autosearch_with_mocked_ai(self):
        """Test autosearch with mocked AI translation."""
        # Mock the search API
        mock_search_api = AsyncMock(spec=SearchClient)
        mock_search_api.search_issues.return_value = [
            {"id": "TEST-1", "summary": "Test issue"}
        ]
        
        # Mock the AI tools
        mock_ai_tools = AsyncMock(spec=AITools)
        mock_ai_tools.translate_to_yql.return_value = {
            "yql_query": "type: Bug",
            "confidence": 0.95,
            "reasoning": "Translated 'find bugs' to YQL",
            "detected_entities": {"types": ["Bug"]},
            "suggestions": [],
            "ai_provider": "llm"
        }
        
        # Create SearchTools with mocked dependencies
        search_tools = SearchTools(search_api=mock_search_api, ai_tools=mock_ai_tools)
        
        # Execute autosearch
        result = await search_tools.autosearch("find bugs")
        
        # Assertions
        assert result["yql"] == "type: Bug"
        assert result["confidence"] == 0.95
        assert not result.get("degraded", False)
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "TEST-1"
        
        # Verify AI was called
        mock_ai_tools.translate_to_yql.assert_called_once_with("find bugs", None)

    @pytest.mark.asyncio
    async def test_autosearch_low_confidence_degraded(self):
        """Test that low confidence translations are marked as degraded."""
        # Mock the search API
        mock_search_api = AsyncMock(spec=SearchClient)
        
        # Mock the AI tools with low confidence response
        mock_ai_tools = AsyncMock(spec=AITools)
        mock_ai_tools.translate_to_yql.return_value = {
            "yql_query": "maybe: something",
            "confidence": 0.5,  # Low confidence
            "reasoning": "Uncertain translation",
            "detected_entities": {},
            "suggestions": ["Try being more specific"],
            "ai_provider": "llm"
        }
        
        # Create SearchTools
        search_tools = SearchTools(search_api=mock_search_api, ai_tools=mock_ai_tools)
        
        # Execute autosearch
        result = await search_tools.autosearch("vague query")
        
        # Assertions
        assert result["yql"] == "maybe: something"
        assert result["confidence"] == 0.5
        assert result["degraded"] == True  # Should be degraded due to low confidence
        assert len(result["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_autosearch_query_execution_error(self):
        """Test handling of query execution errors."""
        # Mock the search API to raise an error
        mock_search_api = AsyncMock(spec=SearchClient)
        mock_search_api.search_issues.side_effect = ValueError("Invalid query syntax")
        
        # Mock the AI tools
        mock_ai_tools = AsyncMock(spec=AITools)
        mock_ai_tools.translate_to_yql.return_value = {
            "yql_query": "invalid: syntax here",
            "confidence": 0.9,
            "reasoning": "Translation attempt",
            "detected_entities": {},
            "suggestions": [],
            "ai_provider": "llm"
        }
        
        # Create SearchTools
        search_tools = SearchTools(search_api=mock_search_api, ai_tools=mock_ai_tools)
        
        # Execute autosearch
        result = await search_tools.autosearch("test query")
        
        # Assertions
        assert result["yql"] == "invalid: syntax here"
        assert result["degraded"] == True
        assert "error" in result
        
    @pytest.mark.asyncio
    async def test_autosearch_fallback_on_exception(self):
        """Test fallback to text search on complete failure."""
        # Mock the search API
        mock_search_api = AsyncMock(spec=SearchClient)
        mock_search_api.search_issues.return_value = [
            {"id": "TEST-2", "summary": "Contains search text"}
        ]
        
        # Mock AI tools to raise an exception
        mock_ai_tools = AsyncMock(spec=AITools)
        mock_ai_tools.translate_to_yql.side_effect = RuntimeError("AI service unavailable")
        
        # Create SearchTools
        search_tools = SearchTools(search_api=mock_search_api, ai_tools=mock_ai_tools)
        
        # Execute autosearch
        result = await search_tools.autosearch("search text")
        
        # Assertions - should fallback to text search
        assert "text:" in result["yql"]
        assert "search text" in result["yql"]
        assert result["confidence"] == 0.0
        assert result["degraded"] == True
        assert "Fallback" in result.get("notes", "")