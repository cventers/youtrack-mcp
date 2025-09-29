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
        # Make complete_structured raise an exception to trigger fallback
        mock_llm_client.complete_structured = AsyncMock(side_effect=Exception("LLM error"))
        mock_llm_client.complete_with_tools = None  # No tools support

        service = AIService(llm_client=mock_llm_client)

        result = await service.translate_nl_to_yql("find my bugs")

        # Should return a fallback YQLTranslationResponse
        assert isinstance(result, YQLTranslationResponse)
        assert result.yql_query == 'text: "find my bugs"'
        assert result.confidence == 0.1
        assert "Translation failed" in result.reasoning

    @pytest.mark.asyncio
    async def test_translate_nl_to_yql_with_client(self):
        """Test NL to YQL with OpenAI client."""
        mock_llm_client = Mock(spec=LLMClient)
        mock_response = YQLTranslationResponse(
            yql_query="assignee: me state: Open",
            reasoning="Finding issues assigned to you that are open",
            confidence=0.9
        )
        mock_llm_client.complete_structured = AsyncMock(return_value=mock_response)
        mock_llm_client.complete_with_tools = None  # No tools support

        service = AIService(llm_client=mock_llm_client)

        result = await service.translate_nl_to_yql("find my open issues")

        assert isinstance(result, YQLTranslationResponse)
        assert result.yql_query == "assignee: me state: Open"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_enhance_error_message_rule_based(self):
        """Test error enhancement with rule-based fallback."""
        from youtrack_mcp.ai.models import ErrorEnhancementResponse

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

        # Mock LLM response
        mock_response = ErrorEnhancementResponse(
            error_category="not_found",
            enhanced_explanation="The requested issue was not found",
            root_cause="404 error when accessing issue DEMO-999",
            immediate_fix="Check the issue ID and verify it exists",
            confidence=0.9,
            estimated_fix_time="immediate",
            example_correction={"wrong": "DEMO-999", "correct": "DEMO-123"},
            prevention_tips=["Always verify issue IDs before using them"]
        )
        mock_llm_client.complete_structured = AsyncMock(return_value=mock_response)

        service = AIService(llm_client=mock_llm_client, error_handler=mock_error_handler)

        # Create an exception to pass
        error = Exception("404 Not Found")
        result = await service.enhance_error_with_llm(error, {"issue_id": "DEMO-999"})

        assert isinstance(result, ErrorEnhancementResponse)
        assert result.error_category == "not_found"
        assert "Check the issue ID" in result.immediate_fix