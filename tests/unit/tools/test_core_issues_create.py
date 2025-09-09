"""
Golden tests for core issues CREATE operations.

Tests the schema-aware issue creation functionality.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from youtrack_mcp.tools.core_issues import CoreIssuesTools
from youtrack_mcp.utils import format_json_response


class TestCoreIssuesCreate:
    """Test cases for issue CREATE operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreIssuesTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()

    @pytest.mark.asyncio
    async def test_create_basic_issue(self):
        """Test creating a basic issue with minimal fields."""
        mock_issue = {
            "id": "DEMO-123",
            "idReadable": "DEMO-123",
            "summary": "Test Issue",
            "description": "Test description",
            "project": {"id": "0-0", "shortName": "DEMO"}
        }

        # Mock the async create_issue method
        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary="Test Issue",
            description="Test description"
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="DEMO",
            summary="Test Issue",
            description="Test description"
        )

        # Parse the JSON result
        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_without_description(self):
        """Test creating an issue without description."""
        mock_issue = {
            "id": "DEMO-124",
            "idReadable": "DEMO-124",
            "summary": "Test Issue No Description",
            "project": {"id": "0-0", "shortName": "DEMO"}
        }

        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary="Test Issue No Description"
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="DEMO",
            summary="Test Issue No Description",
            description=None
        )

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_with_project_id(self):
        """Test creating an issue using project ID instead of short name."""
        mock_issue = {
            "id": "PROJ-125",
            "idReadable": "PROJ-125",
            "summary": "Test Issue with ID",
            "project": {"id": "1-0", "shortName": "PROJ"}
        }

        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="1-0",
            summary="Test Issue with ID",
            description="Using project ID"
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="1-0",
            summary="Test Issue with ID",
            description="Using project ID"
        )

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_empty_summary(self):
        """Test creating an issue with empty summary."""
        mock_issue = {
            "id": "DEMO-126",
            "idReadable": "DEMO-126",
            "summary": "",
            "project": {"id": "0-0", "shortName": "DEMO"}
        }

        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary=""
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="DEMO",
            summary="",
            description=None
        )

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_long_description(self):
        """Test creating an issue with a long description."""
        long_description = "This is a very long description that contains multiple sentences and provides detailed information about the issue that needs to be created. It should test how the system handles longer text content."

        mock_issue = {
            "id": "DEMO-127",
            "idReadable": "DEMO-127",
            "summary": "Long Description Issue",
            "description": long_description,
            "project": {"id": "0-0", "shortName": "DEMO"}
        }

        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary="Long Description Issue",
            description=long_description
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="DEMO",
            summary="Long Description Issue",
            description=long_description
        )

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_special_characters(self):
        """Test creating an issue with special characters in summary and description."""
        special_summary = "Issue with special chars: @#$%^&*()_+{}|:<>?[]\\;',./"
        special_description = "Description with special chars: ñáéíóú 中文 🚀 émojis"

        mock_issue = {
            "id": "DEMO-128",
            "idReadable": "DEMO-128",
            "summary": special_summary,
            "description": special_description,
            "project": {"id": "0-0", "shortName": "DEMO"}
        }

        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary=special_summary,
            description=special_description
        )

        self.tools.issues_api.create_issue.assert_called_once_with(
            project_id="DEMO",
            summary=special_summary,
            description=special_description
        )

        result_data = json.loads(result)
        expected = {
            "issue": mock_issue,
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_api_error(self):
        """Test error handling when API call fails."""
        self.tools.issues_api.create_issue = AsyncMock(side_effect=Exception("API Error"))

        result = await self.tools.create(
            project="DEMO",
            summary="Test Issue",
            description="Test description"
        )

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["project"] == "DEMO"
        assert result_data["summary"] == "Test Issue"

    @pytest.mark.asyncio
    async def test_create_issue_with_pydantic_model(self):
        """Test creating an issue that returns a Pydantic model."""
        class MockIssue:
            def __init__(self):
                self.id = "DEMO-129"
                self.summary = "Pydantic Issue"
                self.description = "From Pydantic model"

            def model_dump(self):
                return {
                    "id": self.id,
                    "summary": self.summary,
                    "description": self.description
                }

        mock_issue = MockIssue()
        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary="Pydantic Issue",
            description="From Pydantic model"
        )

        result_data = json.loads(result)
        expected = {
            "issue": {"id": "DEMO-129", "summary": "Pydantic Issue", "description": "From Pydantic model"},
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_with_dict_response(self):
        """Test creating an issue that returns a plain dict."""
        class MockIssue:
            def __init__(self):
                self.__dict__ = {
                    "id": "DEMO-130",
                    "summary": "Dict Issue"
                }

        mock_issue = MockIssue()
        self.tools.issues_api.create_issue = AsyncMock(return_value=mock_issue)

        result = await self.tools.create(
            project="DEMO",
            summary="Dict Issue"
        )

        result_data = json.loads(result)
        expected = {
            "issue": {"id": "DEMO-130", "summary": "Dict Issue"},
            "created": True
        }
        assert result_data == expected

    @pytest.mark.asyncio
    async def test_create_issue_with_string_response(self):
        """Test creating an issue that returns a string."""
        self.tools.issues_api.create_issue = AsyncMock(return_value="DEMO-131")

        result = await self.tools.create(
            project="DEMO",
            summary="String Issue"
        )

        result_data = json.loads(result)
        expected = {
            "issue": "DEMO-131",
            "created": True
        }
        assert result_data == expected