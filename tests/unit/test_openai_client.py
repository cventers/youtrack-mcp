"""
Tests for OpenAIClient.
"""

import pytest
from unittest.mock import Mock, patch
from youtrack_mcp.ai.openai_client import OpenAIClient


class TestOpenAIClient:
    """Test OpenAIClient functionality."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = OpenAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "gpt-4o-mini"
        assert client.temperature == 0.7

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key required"):
                OpenAIClient()

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'env-key',
            'OPENAI_BASE_URL': 'https://custom.api.com',
            'OPENAI_MODEL': 'gpt-4',
            'OPENAI_TEMPERATURE': '0.5',
            'OPENAI_TIMEOUT': '60'
        }):
            client = OpenAIClient()
            assert client.api_key == 'env-key'
            assert client.base_url == 'https://custom.api.com'
            assert client.model == 'gpt-4'
            assert client.temperature == 0.5
            assert client.timeout == 60

    @patch('youtrack_mcp.ai.openai_client.OpenAI')
    def test_complete_success(self, mock_openai_class):
        """Test successful completion."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.complete("Test prompt")

        assert result["content"] == "Test response"
        assert result["usage"]["total_tokens"] == 15
        assert result["confidence"] == 0.8

        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["messages"][0]["content"] == "Test prompt"
        assert call_args[1]["temperature"] == 0.7

    @patch('youtrack_mcp.ai.openai_client.OpenAI')
    def test_complete_with_system_prompt(self, mock_openai_class):
        """Test completion with system prompt."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 3
        mock_response.usage.total_tokens = 8
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.complete("User prompt", system="System prompt")

        messages = mock_client.chat.completions.create.call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User prompt"

    @patch('youtrack_mcp.ai.openai_client.OpenAI')
    def test_complete_with_custom_params(self, mock_openai_class):
        """Test completion with custom parameters."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 3
        mock_response.usage.total_tokens = 8
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.complete(
            "Prompt",
            max_tokens=100,
            temperature=0.9
        )

        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["max_tokens"] == 100
        assert call_args["temperature"] == 0.9

    @patch('youtrack_mcp.ai.openai_client.OpenAI')
    def test_complete_api_error(self, mock_openai_class):
        """Test API error handling."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(RuntimeError, match="OpenAI API call failed"):
            client.complete("Test prompt")

    @patch('youtrack_mcp.ai.openai_client.OpenAI')
    def test_complete_empty_response(self, mock_openai_class):
        """Test handling of empty response."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = []
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAIClient(api_key="test-key")
        result = client.complete("Test prompt")

        assert result["content"] == ""