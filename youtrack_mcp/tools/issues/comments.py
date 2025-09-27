"""
YouTrack Issue Comments Module.

This module provides functionality for retrieving and managing comments on YouTrack issues:
- Get comments for specific issues
- Get comments across projects
- Support for pagination with cursor-based navigation
- Proper field selection and error handling

These functions enable tracking of issue activity and team collaboration through comments.
"""

import json
from youtrack_mcp.logging import get_logger
from typing import Any, Dict, Optional, List


logger = get_logger(__name__)


class CommentOperations:
    """Operations for managing issue comments."""

    def __init__(self, issues_api) -> None:
        """Initialize with API client."""
        self.issues_api = issues_api
        self.client = issues_api.client  # Direct access for complex queries

    @sync_wrapper  
    def get_task_comments(self, task_id: str, cursor: Optional[str] = None, limit: int = 50) -> dict:
        """
        Get comments for a specific task/issue.
        
        FORMAT: get_task_comments(task_id="DEMO-123")
        
        Args:
            task_id: The issue identifier
            cursor: Pagination cursor
            limit: Max number of comments to return (default 50)
            
        Returns:
            JSON string with task comments
        """
        return self.get_comments(task_id=task_id, cursor=cursor, limit=limit)

    def get_project_comments(self, project_id: str, cursor: Optional[str] = None, limit: int = 50) -> dict:
        """
        Get recent comments across a project.
        
        FORMAT: get_project_comments(project_id="DEMO")
        
        Args:
            project_id: The project identifier
            cursor: Pagination cursor  
            limit: Max number of comments to return (default 50)
            
        Returns:
            JSON string with project comments
        """
        return self.get_comments(project_id=project_id, cursor=cursor, limit=limit)

    def get_comment(self, issue_id: str, comment_id: str) -> dict:
        """
        Get a specific comment by ID.
        
        FORMAT: get_comment(issue_id="DEMO-123", comment_id="comment-id")
        
        Note: YouTrack API requires the issue ID to access comments.
        
        Args:
            issue_id: The issue identifier
            comment_id: The comment identifier
            
        Returns:
            JSON string with comment details
        """
        try:
            fields = "id,text,created,author(id,login,name),updated,updater(id,login,name)"
            url = f"issues/{issue_id}/comments/{comment_id}"
            comment = self.client.get(url, params={"fields": fields})
            
            return {
                "issue_id": issue_id,
                "comment": comment
            }
        except Exception as e:
            logger.exception(f"Error retrieving comment {comment_id}: {e}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "note": "YouTrack requires issue ID to access comments"
            }

    def update_comment(self, issue_id: str, comment_id: str, text: str) -> dict:
        """
        Update an existing comment.
        
        FORMAT: update_comment(issue_id="DEMO-123", comment_id="comment-id", text="Updated text")
        
        Note: This is a placeholder - YouTrack API has limitations on comment updates.
        
        Args:
            issue_id: The issue identifier
            comment_id: The comment identifier
            text: New comment text
            
        Returns:
            JSON string with update status
        """
        return {
            "error": "Comment update not fully implemented",
            "note": "YouTrack API has limitations on updating comments. Most use cases require deleting and recreating the comment.",
            "issue_id": issue_id,
            "comment_id": comment_id
        }

    def delete_comment(self, issue_id: str, comment_id: str) -> dict:
        """
        Delete a comment.
        
        FORMAT: delete_comment(issue_id="DEMO-123", comment_id="comment-id")
        
        Note: This is a placeholder - YouTrack API requires specific permissions.
        
        Args:
            issue_id: The issue identifier
            comment_id: The comment identifier
            
        Returns:
            JSON string with deletion status
        """
        return {
            "error": "Comment deletion not fully implemented",
            "note": "YouTrack API requires specific permissions to delete comments. Only comment authors or users with appropriate permissions can delete comments.",
            "issue_id": issue_id,
            "comment_id": comment_id
        }