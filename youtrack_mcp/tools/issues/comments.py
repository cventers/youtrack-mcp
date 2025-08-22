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
import logging
from typing import Any, Dict, Optional, List

from youtrack_mcp.mcp_wrappers import sync_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class CommentOperations:
    """Operations for managing issue comments."""

    def __init__(self, issues_api, projects_api):
        """Initialize with API clients."""
        self.issues_api = issues_api
        self.projects_api = projects_api
        self.client = issues_api.client  # Direct access for complex queries

    @sync_wrapper
    def get_comments(self, project_id: Optional[str] = None, task_id: Optional[str] = None, 
                    cursor: Optional[str] = None, limit: int = 50) -> str:
        """
        Get comments for a task or project.
        
        FORMAT: get_comments(task_id="DEMO-123") or get_comments(project_id="DEMO")
        
        Args:
            project_id: Project ID to get comments for
            task_id: Task ID to get comments for  
            cursor: Pagination cursor
            limit: Max number of comments to return (default 50)
            
        Returns:
            JSON string with list of comments
        """
        try:
            if task_id:
                # Get comments for a specific task/issue
                fields = "id,text,created,author(id,login,name),updated,updater(id,login,name)"
                params = {"fields": fields}
                
                if cursor:
                    params["cursor"] = cursor
                if limit:
                    params["$top"] = limit
                    
                url = f"issues/{task_id}/comments"
                response = self.client.get(url, params=params)
                
                # Format the response
                comments = response.get("comments", []) if isinstance(response, dict) else response
                
                return format_json_response({
                    "task_id": task_id,
                    "comments": comments,
                    "count": len(comments),
                    "cursor": response.get("cursor") if isinstance(response, dict) else None
                })
                
            elif project_id:
                # Get recent comments across a project
                # YouTrack doesn't directly support project-wide comment queries,
                # so we need to search for issues in the project and get their comments
                issue_query = f"project: {{{project_id}}}"
                fields = "id,idReadable,comments(id,text,created,author(id,login,name))"
                params = {
                    "query": issue_query,
                    "fields": fields,
                    "$top": limit
                }
                
                if cursor:
                    params["cursor"] = cursor
                    
                issues = self.client.get("issues", params=params)
                
                # Collect all comments from the issues
                all_comments = []
                for issue in issues.get("issues", []) if isinstance(issues, dict) else issues:
                    issue_comments = issue.get("comments", [])
                    for comment in issue_comments:
                        comment["issue_id"] = issue.get("idReadable", issue.get("id"))
                        all_comments.append(comment)
                
                # Sort by creation date (most recent first)
                all_comments.sort(key=lambda c: c.get("created", 0), reverse=True)
                
                # Apply limit
                all_comments = all_comments[:limit]
                
                return format_json_response({
                    "project_id": project_id,
                    "comments": all_comments,
                    "count": len(all_comments),
                    "cursor": issues.get("cursor") if isinstance(issues, dict) else None
                })
            else:
                raise ValueError("Either project_id or task_id must be provided")
                
        except Exception as e:
            logger.exception(f"Error retrieving comments: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__
            })

    @sync_wrapper  
    def get_task_comments(self, task_id: str, cursor: Optional[str] = None, limit: int = 50) -> str:
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

    @sync_wrapper
    def get_project_comments(self, project_id: str, cursor: Optional[str] = None, limit: int = 50) -> str:
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

    @sync_wrapper
    def get_comment(self, issue_id: str, comment_id: str) -> str:
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
            
            return format_json_response({
                "issue_id": issue_id,
                "comment": comment
            })
        except Exception as e:
            logger.exception(f"Error retrieving comment {comment_id}: {e}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "note": "YouTrack requires issue ID to access comments"
            })

    @sync_wrapper
    def update_comment(self, issue_id: str, comment_id: str, text: str) -> str:
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
        return format_json_response({
            "error": "Comment update not fully implemented",
            "note": "YouTrack API has limitations on updating comments. Most use cases require deleting and recreating the comment.",
            "issue_id": issue_id,
            "comment_id": comment_id
        })

    @sync_wrapper
    def delete_comment(self, issue_id: str, comment_id: str) -> str:
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
        return format_json_response({
            "error": "Comment deletion not fully implemented",
            "note": "YouTrack API requires specific permissions to delete comments. Only comment authors or users with appropriate permissions can delete comments.",
            "issue_id": issue_id,
            "comment_id": comment_id
        })