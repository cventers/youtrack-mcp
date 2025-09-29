"""
Tests for AIService.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from youtrack_mcp.ai.service import AIService
from youtrack_mcp.ai.llm_client import LLMClient
from youtrack_mcp.ai.models import YQLTranslationResponse


class TestAIService:
    """Test AIService functionality."""

    def test_init_without_client(self):
        """Test initialization with minimal setup."""
        mock_llm_client = Mock(spec=LLMClient)
        service = AIService(llm_client=mock_llm_client)
        assert service.llm_client == mock_llm_client

    def test_init_with_client(self):
        """Test initialization with LLM client."""
        mock_client = Mock(spec=LLMClient)
        service = AIService(llm_client=mock_client)
        assert service.llm_client == mock_client

    def test_load_error_patterns(self):
        """Test loading error patterns."""
        mock_llm_client = Mock(spec=LLMClient)
        mock_error_handler = Mock()
        mock_error_handler.patterns = [
            {
                'id': 'test',
                'match': 'exact|test error',
                'scope': 'test',
                'classification': {
                    'category': 'test_error',
                    'severity': 'low'
                },
                'explanation': 'Test error',
                'remediation_steps': ['Fix test']
            }
        ]

        service = AIService(llm_client=mock_llm_client, error_handler=mock_error_handler)
        patterns = service.error_handler.patterns
        assert len(patterns) == 1
        assert patterns[0]['id'] == 'test'

    @pytest.mark.asyncio
    async def test_translate_nl_to_yql_without_client(self):
        """Test NL to YQL with fallback."""
        mock_llm_client = Mock(spec=LLMClient)
        # Make generate_structured raise an exception to trigger fallback
        mock_llm_client.generate_structured = AsyncMock(side_effect=Exception("LLM error"))

        service = AIService(llm_client=mock_llm_client)

        result = await service.translate_nl_to_yql("find my bugs")

        # Should return a fallback response
        assert isinstance(result, dict)
        assert "query" in result

    @pytest.mark.asyncio
    async def test_translate_nl_to_yql_with_client(self):
        """Test NL to YQL with OpenAI client."""
        mock_llm_client = Mock(spec=LLMClient)
        mock_response = YQLTranslationResponse(
            query="assignee: me state: Open",
            explanation="Finding issues assigned to you that are open",
            confidence=0.9
        )
        mock_llm_client.generate_structured = AsyncMock(return_value=mock_response)

        service = AIService(llm_client=mock_llm_client)

        result = await service.translate_nl_to_yql("find my open issues")

        assert result["query"] == "assignee: me state: Open"
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_enhance_error_message_rule_based(self):
        """Test error enhancement with rule-based fallback."""
        mock_llm_client = Mock(spec=LLMClient)
        mock_error_handler = Mock()

        # Mock error handler to return an enhancement
        mock_error_handler.enhance_error = Mock(return_value={
            "error": "404 Not Found",
            "category": "not_found",
            "explanation": "The requested issue was not found",
            "user_action": "Check the issue ID",
            "learn_from_this": "Issue IDs are case-sensitive"
        })

        service = AIService(llm_client=mock_llm_client, error_handler=mock_error_handler)

        result = await service.enhance_error_message("404 Not Found", {"issue_id": "DEMO-999"})

        assert result["error"] == "404 Not Found"
        assert result["category"] == "not_found"
        assert "Check the issue ID" in result["user_action"]