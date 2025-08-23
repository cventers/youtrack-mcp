"""
Unit tests for issue comment operations.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from youtrack_mcp.tools.issues.comments import CommentOperations


class TestCommentOperations:
    """Test suite for comment operations."""
    
    @pytest.fixture
    def comment_ops(self):
        """Create CommentOperations instance with mocked APIs."""
        mock_issues_api = MagicMock()
        mock_projects_api = MagicMock()
        
        # Create mock client
        mock_client = MagicMock()
        mock_issues_api.client = mock_client
        
        return CommentOperations(mock_issues_api, mock_projects_api)
    
    def test_get_comments_for_task(self, comment_ops):
        """Test getting comments for a specific task."""
        # Mock response
        mock_response = {
            "comments": [
                {
                    "id": "comment-1",
                    "text": "First comment",
                    "created": 1234567890,
                    "author": {"id": "user1", "login": "john", "name": "John Doe"}
                },
                {
                    "id": "comment-2", 
                    "text": "Second comment",
                    "created": 1234567900,
                    "author": {"id": "user2", "login": "jane", "name": "Jane Doe"}
                }
            ],
            "cursor": "next-page-cursor"
        }
        comment_ops.client.get.return_value = mock_response
        
        result = comment_ops.get_comments(task_id="DEMO-123", limit=50)
        result_dict = json.loads(result)
        
        # Verify API call
        comment_ops.client.get.assert_called_once_with(
            "issues/DEMO-123/comments",
            params={
                "fields": "id,text,created,author(id,login,name),updated,updater(id,login,name)",
                "$top": 50
            }
        )
        
        # Verify response
        assert result_dict["task_id"] == "DEMO-123"
        assert result_dict["count"] == 2
        assert len(result_dict["comments"]) == 2
        assert result_dict["comments"][0]["text"] == "First comment"
        assert result_dict["cursor"] == "next-page-cursor"
    
    def test_get_comments_for_task_with_cursor(self, comment_ops):
        """Test getting comments with pagination cursor."""
        mock_response = {"comments": [], "cursor": None}
        comment_ops.client.get.return_value = mock_response
        
        result = comment_ops.get_comments(task_id="DEMO-123", cursor="page2", limit=25)
        
        # Verify cursor was passed
        comment_ops.client.get.assert_called_once_with(
            "issues/DEMO-123/comments",
            params={
                "fields": "id,text,created,author(id,login,name),updated,updater(id,login,name)",
                "cursor": "page2",
                "$top": 25
            }
        )
    
    def test_get_comments_for_project(self, comment_ops):
        """Test getting comments across a project."""
        # Mock issues with comments
        mock_issues = {
            "issues": [
                {
                    "id": "issue-1",
                    "idReadable": "DEMO-1",
                    "comments": [
                        {
                            "id": "comment-1",
                            "text": "Comment on issue 1",
                            "created": 1234567890,
                            "author": {"id": "user1", "login": "john"}
                        }
                    ]
                },
                {
                    "id": "issue-2",
                    "idReadable": "DEMO-2",
                    "comments": [
                        {
                            "id": "comment-2",
                            "text": "Comment on issue 2",
                            "created": 1234567900,
                            "author": {"id": "user2", "login": "jane"}
                        }
                    ]
                }
            ],
            "cursor": "issues-cursor"
        }
        comment_ops.client.get.return_value = mock_issues
        
        result = comment_ops.get_comments(project_id="DEMO", limit=10)
        result_dict = json.loads(result)
        
        # Verify API call
        comment_ops.client.get.assert_called_once_with(
            "issues",
            params={
                "query": "project: {DEMO}",
                "fields": "id,idReadable,comments(id,text,created,author(id,login,name))",
                "$top": 10
            }
        )
        
        # Verify response
        assert result_dict["project_id"] == "DEMO"
        assert result_dict["count"] == 2
        assert len(result_dict["comments"]) == 2
        
        # Check that issue_id was added to comments
        assert result_dict["comments"][0]["issue_id"] == "DEMO-2"  # Newer comment first
        assert result_dict["comments"][1]["issue_id"] == "DEMO-1"
        
        # Verify comments are sorted by creation date (descending)
        assert result_dict["comments"][0]["created"] >= result_dict["comments"][1]["created"]
    
    def test_get_comments_no_params_error(self, comment_ops):
        """Test error when neither project_id nor task_id provided."""
        result = comment_ops.get_comments()
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert "project_id or task_id must be provided" in result_dict["error"]
    
    def test_get_comments_api_error(self, comment_ops):
        """Test error handling for API exceptions."""
        comment_ops.client.get.side_effect = Exception("API Error")
        
        result = comment_ops.get_comments(task_id="DEMO-123")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert result_dict["error"] == "API Error"
        assert result_dict["error_type"] == "Exception"
    
    def test_get_task_comments(self, comment_ops):
        """Test get_task_comments wrapper method."""
        # Mock the underlying get_comments method
        with patch.object(comment_ops, 'get_comments') as mock_get_comments:
            mock_get_comments.return_value = '{"comments": []}'
            
            result = comment_ops.get_task_comments("DEMO-123", cursor="c1", limit=100)
            
            # Verify it calls get_comments with correct params
            mock_get_comments.assert_called_once_with(
                task_id="DEMO-123",
                cursor="c1",
                limit=100
            )
    
    def test_get_project_comments(self, comment_ops):
        """Test get_project_comments wrapper method."""
        with patch.object(comment_ops, 'get_comments') as mock_get_comments:
            mock_get_comments.return_value = '{"comments": []}'
            
            result = comment_ops.get_project_comments("PROJ", cursor="c2", limit=50)
            
            mock_get_comments.assert_called_once_with(
                project_id="PROJ",
                cursor="c2", 
                limit=50
            )
    
    def test_get_comment(self, comment_ops):
        """Test getting a specific comment."""
        mock_comment = {
            "id": "comment-123",
            "text": "Specific comment",
            "created": 1234567890,
            "author": {"id": "user1", "login": "john", "name": "John Doe"}
        }
        comment_ops.client.get.return_value = mock_comment
        
        result = comment_ops.get_comment("DEMO-123", "comment-123")
        result_dict = json.loads(result)
        
        # Verify API call
        comment_ops.client.get.assert_called_once_with(
            "issues/DEMO-123/comments/comment-123",
            params={"fields": "id,text,created,author(id,login,name),updated,updater(id,login,name)"}
        )
        
        # Verify response
        assert result_dict["issue_id"] == "DEMO-123"
        assert result_dict["comment"]["id"] == "comment-123"
        assert result_dict["comment"]["text"] == "Specific comment"
    
    def test_get_comment_error(self, comment_ops):
        """Test error handling when getting a specific comment."""
        comment_ops.client.get.side_effect = Exception("Comment not found")
        
        result = comment_ops.get_comment("DEMO-123", "invalid-id")
        result_dict = json.loads(result)
        
        assert "error" in result_dict
        assert result_dict["error"] == "Comment not found"
        assert "YouTrack requires issue ID" in result_dict["note"]
    
    def test_update_comment_placeholder(self, comment_ops):
        """Test update_comment placeholder returns expected message."""
        result = comment_ops.update_comment("DEMO-123", "comment-123", "Updated text")
        result_dict = json.loads(result)
        
        assert result_dict["error"] == "Comment update not fully implemented"
        assert "limitations" in result_dict["note"]
        assert result_dict["issue_id"] == "DEMO-123"
        assert result_dict["comment_id"] == "comment-123"
    
    def test_delete_comment_placeholder(self, comment_ops):
        """Test delete_comment placeholder returns expected message."""
        result = comment_ops.delete_comment("DEMO-123", "comment-123")
        result_dict = json.loads(result)
        
        assert result_dict["error"] == "Comment deletion not fully implemented"
        assert "permissions" in result_dict["note"]
        assert result_dict["issue_id"] == "DEMO-123"
        assert result_dict["comment_id"] == "comment-123"
    
    def test_empty_comments_response(self, comment_ops):
        """Test handling of empty comments response."""
        # Test with list response (no wrapper)
        comment_ops.client.get.return_value = []
        
        result = comment_ops.get_comments(task_id="DEMO-123")
        result_dict = json.loads(result)
        
        assert result_dict["task_id"] == "DEMO-123"
        assert result_dict["count"] == 0
        assert result_dict["comments"] == []
        assert result_dict["cursor"] is None
    
    def test_project_comments_sorting(self, comment_ops):
        """Test that project comments are properly sorted by date."""
        mock_issues = {
            "issues": [
                {
                    "idReadable": "DEMO-1",
                    "comments": [
                        {"id": "c1", "text": "Old", "created": 1000},
                        {"id": "c3", "text": "Newest", "created": 3000}
                    ]
                },
                {
                    "idReadable": "DEMO-2",
                    "comments": [
                        {"id": "c2", "text": "Middle", "created": 2000}
                    ]
                }
            ]
        }
        comment_ops.client.get.return_value = mock_issues
        
        result = comment_ops.get_comments(project_id="DEMO", limit=10)
        result_dict = json.loads(result)
        
        # Should be sorted newest first
        assert result_dict["comments"][0]["id"] == "c3"
        assert result_dict["comments"][1]["id"] == "c2"
        assert result_dict["comments"][2]["id"] == "c1"