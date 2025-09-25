"""Test autosearch people resolution functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from youtrack_mcp.ai.service import AIService
from youtrack_mcp.ai.llm_client import LLMClient
from youtrack_mcp.ai.models import YQLTranslationResponse
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.tools.users_tools import UsersTools


class TestAutosearchPeopleResolution:
    """Test cases for people resolution in autosearch."""

    @pytest.mark.asyncio
    async def test_autosearch_resolves_display_name(self):
        """Test that display names are resolved via users.search tool call."""
        # Setup mocks
        mock_llm_client = Mock(spec=LLMClient)
        mock_mcp_instance = Mock()
        mock_users_tools = AsyncMock(spec=UsersTools)
        
        # Mock the users.search response
        mock_users_tools.search.return_value = {
            "users": [
                {
                    "login": "cventers",
                    "fullName": "Chase Venters",
                    "email": "chase.venters@company.com"
                }
            ],
            "count": 1
        }
        
        # Attach users tools to mcp instance
        mock_mcp_instance.tools = {"users": mock_users_tools}
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=mock_mcp_instance
        )
        
        # Mock the LLM response with tool call
        async def mock_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
            # Simulate tool call for "Chase Venters"
            tool_result = await tool_handler("users_search", {"query": "Chase Venters", "limit": 5})
            
            # Return final YQL response
            return YQLTranslationResponse(
                yql_query="project: OPS, PAY, SP created by: cventers",
                confidence=0.95,
                reasoning="Resolved 'Chase Venters' to login 'cventers' via users.search",
                detected_entities={
                    "projects": ["OPS", "PAY", "SP"],
                    "users": ["cventers"]
                }
            )
        
        mock_llm_client.complete_with_tools = mock_complete_with_tools
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "tickets created by Chase Venters in projects OPS, PAY, SP"
        )
        
        # Assertions
        assert "created by: cventers" in result.yql_query
        assert "project: OPS, PAY, SP" in result.yql_query
        assert result.confidence > 0.9
        assert "cventers" in result.detected_entities.get("users", [])
        
        # Verify users.search was called
        mock_users_tools.search.assert_called_once_with(
            query="Chase Venters",
            limit=5
        )

    @pytest.mark.asyncio
    async def test_autosearch_direct_login_no_tool_call(self):
        """Test that direct logins don't trigger users.search."""
        # Setup mocks
        mock_llm_client = Mock(spec=LLMClient)
        mock_mcp_instance = Mock()
        mock_users_tools = AsyncMock(spec=UsersTools)
        
        # Attach users tools to mcp instance
        mock_mcp_instance.tools = {"users": mock_users_tools}
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=mock_mcp_instance
        )
        
        # Mock the LLM response WITHOUT tool call (direct login)
        async def mock_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
            # No tool call needed for direct login
            return YQLTranslationResponse(
                yql_query="created by: cventers",
                confidence=0.98,
                reasoning="Direct login 'cventers' used without resolution",
                detected_entities={
                    "users": ["cventers"]
                }
            )
        
        mock_llm_client.complete_with_tools = mock_complete_with_tools
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "created by cventers"
        )
        
        # Assertions
        assert result.yql_query == "created by: cventers"
        assert result.confidence > 0.95
        
        # Verify users.search was NOT called
        mock_users_tools.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_autosearch_email_resolution(self):
        """Test that email addresses are resolved via users.search."""
        # Setup mocks
        mock_llm_client = Mock(spec=LLMClient)
        mock_mcp_instance = Mock()
        mock_users_tools = AsyncMock(spec=UsersTools)
        
        # Mock the users.search response for email
        mock_users_tools.search.return_value = {
            "users": [
                {
                    "login": "jdoe",
                    "fullName": "John Doe",
                    "email": "john.doe@company.com"
                }
            ],
            "count": 1
        }
        
        # Attach users tools to mcp instance
        mock_mcp_instance.tools = {"users": mock_users_tools}
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=mock_mcp_instance
        )
        
        # Mock the LLM response with tool call for email
        async def mock_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
            # Simulate tool call for email
            tool_result = await tool_handler("users_search", {"query": "john.doe@company.com", "limit": 5})
            
            # Return final YQL response
            return YQLTranslationResponse(
                yql_query="for: jdoe",
                confidence=0.96,
                reasoning="Resolved email 'john.doe@company.com' to login 'jdoe' via users.search",
                detected_entities={
                    "users": ["jdoe"]
                }
            )
        
        mock_llm_client.complete_with_tools = mock_complete_with_tools
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "assigned to john.doe@company.com"
        )
        
        # Assertions
        assert result.yql_query == "for: jdoe"
        assert result.confidence > 0.9
        assert "jdoe" in result.detected_entities.get("users", [])
        
        # Verify users.search was called with the email
        mock_users_tools.search.assert_called_once_with(
            query="john.doe@company.com",
            limit=5
        )

    @pytest.mark.asyncio
    async def test_autosearch_multiple_people_resolution(self):
        """Test that multiple people in one query are resolved."""
        # Setup mocks
        mock_llm_client = Mock(spec=LLMClient)
        mock_mcp_instance = Mock()
        mock_users_tools = AsyncMock(spec=UsersTools)
        
        # Mock the users.search responses
        call_count = 0
        async def mock_search(query, limit=10):
            nonlocal call_count
            call_count += 1
            
            if "Chase Venters" in query:
                return {
                    "users": [{
                        "login": "cventers",
                        "fullName": "Chase Venters",
                        "email": "chase@company.com"
                    }],
                    "count": 1
                }
            elif "John Doe" in query:
                return {
                    "users": [{
                        "login": "jdoe",
                        "fullName": "John Doe",
                        "email": "john@company.com"
                    }],
                    "count": 1
                }
            return {"users": [], "count": 0}
        
        mock_users_tools.search = mock_search
        
        # Attach users tools to mcp instance
        mock_mcp_instance.tools = {"users": mock_users_tools}
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=mock_mcp_instance
        )
        
        # Mock the LLM response with multiple tool calls
        async def mock_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
            # Simulate tool calls for both names
            result1 = await tool_handler("users_search", {"query": "Chase Venters", "limit": 5})
            result2 = await tool_handler("users_search", {"query": "John Doe", "limit": 5})
            
            # Return final YQL response with both resolved logins
            return YQLTranslationResponse(
                yql_query="created by: cventers for: jdoe",
                confidence=0.94,
                reasoning="Resolved multiple display names to logins",
                detected_entities={
                    "users": ["cventers", "jdoe"]
                }
            )
        
        mock_llm_client.complete_with_tools = mock_complete_with_tools
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "created by Chase Venters and assigned to John Doe"
        )
        
        # Assertions
        assert "created by: cventers" in result.yql_query
        assert "for: jdoe" in result.yql_query
        assert result.confidence > 0.9
        assert "cventers" in result.detected_entities.get("users", [])
        assert "jdoe" in result.detected_entities.get("users", [])
        
        # Verify users.search was called twice
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_autosearch_fallback_without_tool_support(self):
        """Test that autosearch still works without tool calling support."""
        # Setup mocks with no complete_with_tools method
        mock_llm_client = Mock(spec=LLMClient)
        mock_llm_client.complete_with_tools = None  # No tool support
        
        # Mock regular complete_structured
        async def mock_complete_structured(response_model, messages, **kwargs):
            return YQLTranslationResponse(
                yql_query='created by: {Chase Venters}',  # Falls back to using display name with braces
                confidence=0.7,
                reasoning="No tool support, using display name directly",
                warnings=["Could not resolve display names without tool support"],
                detected_entities={}
            )
        
        mock_llm_client.complete_structured = mock_complete_structured
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=None  # No MCP instance
        )
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "created by Chase Venters"
        )
        
        # Assertions - should still work but with lower confidence
        assert "Chase Venters" in result.yql_query
        assert result.confidence < 0.8
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_autosearch_handles_tool_error(self):
        """Test that autosearch handles errors in users.search gracefully."""
        # Setup mocks
        mock_llm_client = Mock(spec=LLMClient)
        mock_mcp_instance = Mock()
        mock_users_tools = AsyncMock(spec=UsersTools)
        
        # Mock the users.search to raise an error
        mock_users_tools.search.side_effect = Exception("API error")
        
        # Attach users tools to mcp instance
        mock_mcp_instance.tools = {"users": mock_users_tools}
        
        # Create AI service
        ai_service = AIService(
            llm_client=mock_llm_client,
            mcp_instance=mock_mcp_instance
        )
        
        # Mock the LLM response handling tool error
        async def mock_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
            # Try to call tool, get error
            tool_result = await tool_handler("users_search", {"query": "Chase Venters", "limit": 5})
            
            # Fallback to using display name
            return YQLTranslationResponse(
                yql_query='created by: {Chase Venters}',
                confidence=0.6,
                reasoning="Tool call failed, using display name as fallback",
                warnings=["Could not resolve user: API error"],
                detected_entities={}
            )
        
        mock_llm_client.complete_with_tools = mock_complete_with_tools
        
        # Execute the translation
        result = await ai_service.translate_nl_to_yql(
            "created by Chase Venters"
        )
        
        # Assertions
        assert "Chase Venters" in result.yql_query
        assert result.confidence < 0.7
        assert len(result.warnings) > 0