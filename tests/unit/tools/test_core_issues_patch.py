"""
Golden tests for core issues PATCH operations and subpaths.

Tests the typed operations and field updates for issue patching.
"""

import pytest
from unittest.mock import Mock, patch
from youtrack_mcp.tools.core_issues import CoreIssuesTools
from youtrack_mcp.utils import format_json_response


class TestCoreIssuesPatch:
    """Test cases for issue PATCH operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreIssuesTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()

    def test_patch_simple_fields(self):
        """Test patching simple fields like summary and description."""
        # Mock the API response
        mock_issue = {
            "id": "DEMO-123",
            "summary": "Updated title",
            "description": "Updated description"
        }
        self.tools.issues_api.patch_issue.return_value = mock_issue

        # Call the patch method
        result = self.tools.patch(
            issue_id="DEMO-123",
            fields={"summary": "Updated title", "description": "Updated description"}
        )

        # Verify the API was called correctly
        self.tools.issues_api.patch_issue.assert_called_once_with(
            issue_id="DEMO-123",
            fields={"summary": "Updated title", "description": "Updated description"},
            ops=None
        )

        # Verify the response format
        expected = format_json_response({
            "issue": mock_issue,
            "updated_fields": ["summary", "description"]
        })
        assert result == expected

    def test_patch_typed_operations(self):
        """Test patching with typed operations."""
        mock_issue = {
            "id": "DEMO-123",
            "state": "Fixed"
        }
        self.tools.issues_api.patch_issue.return_value = mock_issue

        ops = [{"op": "set", "field": "state", "value": "Fixed"}]

        result = self.tools.patch(issue_id="DEMO-123", ops=ops)

        self.tools.issues_api.patch_issue.assert_called_once_with(
            issue_id="DEMO-123",
            fields=None,
            ops=ops
        )

        expected = format_json_response({
            "issue": mock_issue,
            "operations_applied": ops
        })
        assert result == expected

    def test_patch_assignee_operation(self):
        """Test patching assignee with user reference."""
        mock_issue = {
            "id": "DEMO-123",
            "assignee": {"id": "user123", "name": "John Doe"}
        }
        self.tools.issues_api.patch_issue.return_value = mock_issue

        ops = [{"op": "set", "field": "assignee", "value": "user123"}]

        result = self.tools.patch(issue_id="DEMO-123", ops=ops)

        expected = format_json_response({
            "issue": mock_issue,
            "operations_applied": ops
        })
        assert result == expected

    def test_patch_custom_field_operation(self):
        """Test patching custom fields with proper value formatting."""
        mock_issue = {
            "id": "DEMO-123",
            "customFields": [{"name": "Priority", "value": "High"}]
        }
        self.tools.issues_api.patch_issue.return_value = mock_issue

        ops = [{"op": "set", "field": "Priority", "value": "High"}]

        result = self.tools.patch(issue_id="DEMO-123", ops=ops)

        expected = format_json_response({
            "issue": mock_issue,
            "operations_applied": ops
        })
        assert result == expected

    def test_patch_error_handling(self):
        """Test error handling in patch operations."""
        self.tools.issues_api.patch_issue.side_effect = Exception("API Error")

        result = self.tools.patch(
            issue_id="DEMO-123",
            fields={"summary": "Test"}
        )

        response = result
        assert "error" in response
        assert "API Error" in response["error"]
        assert response["issue_id"] == "DEMO-123"

    def test_patch_validation_error(self):
        """Test validation errors in patch operations."""
        # Test missing both fields and ops
        result = self.tools.patch(issue_id="DEMO-123")

        assert "error" in result
        assert "Either 'fields' or 'ops' parameter must be provided" in result["error"]


class TestCoreIssuesPatchSubpaths:
    """Test cases for PATCH subpath operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = CoreIssuesTools()
        self.tools.client = Mock()
        self.tools.issues_api = Mock()

    def test_patch_comments_subpath(self):
        """Test patching comments subpath."""
        mock_comment = {
            "id": "comment123",
            "text": "Updated comment",
            "author": {"id": "user123", "name": "John Doe"}
        }
        self.tools.issues_api.patch_issue_comment.return_value = mock_comment

        result = self.tools.patch(
            issue_id="DEMO-123",
            subpath="comments/comment123",
            fields={"text": "Updated comment"}
        )

        self.tools.issues_api.patch_issue_comment.assert_called_once_with(
            issue_id="DEMO-123",
            comment_id="comment123",
            fields={"text": "Updated comment"}
        )

        expected = format_json_response({
            "comment": mock_comment,
            "updated_fields": ["text"]
        })
        assert result == expected

    def test_patch_attachments_subpath(self):
        """Test patching attachments subpath."""
        mock_attachment = {
            "id": "attach123",
            "name": "updated_file.txt",
            "size": 1024
        }
        self.tools.issues_api.patch_issue_attachment.return_value = mock_attachment

        result = self.tools.patch(
            issue_id="DEMO-123",
            subpath="attachments/attach123",
            fields={"name": "updated_file.txt"}
        )

        expected = format_json_response({
            "attachment": mock_attachment,
            "updated_fields": ["name"]
        })
        assert result == expected

    def test_patch_links_subpath(self):
        """Test patching issue links subpath."""
        mock_link = {
            "id": "link123",
            "direction": "OUTWARD",
            "linkType": {"name": "relates to"},
            "issues": [{"id": "DEMO-456"}]
        }
        self.tools.issues_api.patch_issue_link.return_value = mock_link

        result = self.tools.patch(
            issue_id="DEMO-123",
            subpath="links/link123",
            fields={"direction": "INWARD"}
        )

        expected = format_json_response({
            "link": mock_link,
            "updated_fields": ["direction"]
        })
        assert result == expected