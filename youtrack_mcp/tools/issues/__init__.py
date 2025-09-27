"""
YouTrack Issue Tools Package.

This package contains modular issue management tools broken down by functionality:
- basic_operations: Core CRUD operations
- custom_fields: Custom field management  
- dedicated_updates: Specialized update functions
- linking: Issue relationships
- diagnostics: Workflow analysis & help
- attachments: File & raw data operations
- comments: Comment retrieval and management
"""

from youtrack_mcp.logging import get_logger
from typing import Any, Dict, List, Optional

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.api.projects import ProjectsClient

# Import all modular components
from .dedicated_updates import DedicatedUpdates
from .diagnostics import Diagnostics
from .custom_fields import CustomFields
from .basic_operations import BasicOperations
from .linking import Linking
from .attachments import Attachments
from .utilities import Utilities
from .comments import CommentOperations

logger = get_logger(__name__)


class IssueTools:
    """
    Unified interface for YouTrack issue management tools.
    
    This class delegates to the appropriate modular components while maintaining
    backward compatibility with the original monolithic interface.
    """

    def __init__(self) -> None:
        """Initialize with API clients and create module instances."""
        # Initialize API clients like other tool classes
        self.client = YouTrackClient()
        self.issues_api = IssuesClient(self.client)
        self.projects_api = ProjectsClient(self.client)
        
        # Initialize all modular components
        self.custom_fields = CustomFields(self.issues_api, self.projects_api)
        self.dedicated_updates = DedicatedUpdates(self.issues_api, self.projects_api, self.custom_fields)
        self.diagnostics = Diagnostics(self.issues_api, self.projects_api)
        self.basic_operations = BasicOperations(self.issues_api, self.projects_api)
        self.linking = Linking(self.issues_api, self.projects_api)
        self.attachments = Attachments(self.issues_api, self.projects_api)
        self.utilities = Utilities(self.issues_api, self.projects_api)
        self.comments = CommentOperations(self.issues_api, self.projects_api)
        
        logger.info("IssueTools initialized with modular components")

    # === Dedicated Update Functions ===
    
    def update_issue_state(self, issue_id: str, state: str) -> dict:
        """Update issue state with enhanced error handling."""
        return self.dedicated_updates.update_issue_state(issue_id, state)
    
    def update_issue_priority(self, issue_id: str, priority: str) -> dict:
        """Update issue priority."""
        return self.dedicated_updates.update_issue_priority(issue_id, priority)
    
    def update_issue_assignee(self, issue_id: str, assignee: str) -> dict:
        """Update issue assignee."""
        return self.dedicated_updates.update_issue_assignee(issue_id, assignee)
    
    def update_issue_type(self, issue_id: str, issue_type: str) -> dict:
        """Update issue type."""
        return self.dedicated_updates.update_issue_type(issue_id, issue_type)
    
    def update_issue_estimation(self, issue_id: str, estimation: str) -> dict:
        """Update issue estimation."""
        return self.dedicated_updates.update_issue_estimation(issue_id, estimation)

    # === Diagnostic Functions ===
    
    def diagnose_workflow_restrictions(self, issue_id: str) -> dict:
        """Analyze workflow restrictions for an issue."""
        return self.diagnostics.diagnose_workflow_restrictions(issue_id)
    
    def get_help(self, topic: str = "all") -> dict:
        """Get interactive help for YouTrack operations."""
        return self.diagnostics.get_help(topic)

    # === Custom Field Functions ===
    
    def update_custom_fields(self, issue_id: str, custom_fields: Dict[str, Any], validate: bool = True) -> dict:
        """Update multiple custom fields on an issue."""
        return self.custom_fields.update_custom_fields(issue_id, custom_fields, validate)
    
    def batch_update_custom_fields(
        self,
        updates: Optional[List[Dict[str, Any]]] = None,
        issues: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Batch update custom fields across multiple issues with flexible formats."""
        return self.custom_fields.batch_update_custom_fields(
            updates=updates,
            issues=issues,
            custom_fields=custom_fields
        )
    
    def get_custom_fields(self, issue_id: str) -> dict:
        """Get all custom fields for an issue."""
        return self.custom_fields.get_custom_fields(issue_id)
    
    def validate_custom_field(self, project_id: str, field_name: str, field_value: Any) -> dict:
        """Validate a custom field value for a project."""
        return self.custom_fields.validate_custom_field(project_id, field_name, field_value)
    
    def get_available_custom_field_values(self, project_id: str, field_name: str) -> dict:
        """Get available values for a custom field."""
        return self.custom_fields.get_available_custom_field_values(project_id, field_name)

    # === Basic Operations ===
    
    def get_issue(self, issue_id: str) -> dict:
        """Get detailed issue information."""
        return self.basic_operations.get_issue(issue_id)
    
    def search_issues(self, query: str, limit: int = 10) -> dict:
        """Search for issues using YouTrack query syntax."""
        return self.basic_operations.search_issues(query, limit)
    
    def create_issue(self, project: str, summary: str, description: Optional[str] = None) -> dict:
        """Create a new issue in the specified project."""
        return self.basic_operations.create_issue(project, summary, description)
    
    def update_issue(self, issue_id: str, summary: Optional[str] = None, description: Optional[str] = None, additional_fields: Optional[Dict[str, Any]] = None) -> dict:
        """Update basic issue fields."""
        return self.basic_operations.update_issue(issue_id, summary, description, additional_fields)
    
    def add_comment(self, issue_id: str, text: str) -> dict:
        """Add a comment to an issue."""
        return self.basic_operations.add_comment(issue_id, text)

    # === Linking Functions ===
    
    def link_issues(self, source_issue_id: str, target_issue_id: str, link_type: str) -> dict:
        """Create a link between two issues."""
        return self.linking.link_issues(source_issue_id, target_issue_id, link_type)
    
    def get_issue_links(self, issue_id: str) -> dict:
        """Get all links for an issue."""
        return self.linking.get_issue_links(issue_id)
    
    def get_available_link_types(self) -> dict:
        """Get available link types."""
        return self.linking.get_available_link_types()
    
    def add_dependency(self, dependent_issue_id: str, dependency_issue_id: str) -> dict:
        """Add a dependency relationship."""
        return self.linking.add_dependency(dependent_issue_id, dependency_issue_id)
    
    def remove_dependency(self, dependent_issue_id: str, dependency_issue_id: str) -> dict:
        """Remove a dependency relationship."""
        return self.linking.remove_dependency(dependent_issue_id, dependency_issue_id)
    
    def add_relates_link(self, source_issue_id: str, target_issue_id: str) -> dict:
        """Add a 'relates to' link."""
        return self.linking.add_relates_link(source_issue_id, target_issue_id)
    
    def add_duplicate_link(self, duplicate_issue_id: str, original_issue_id: str) -> dict:
        """Add a duplicate link."""
        return self.linking.add_duplicate_link(duplicate_issue_id, original_issue_id)

    # === Attachment Functions ===
    
    def get_issue_raw(self, issue_id: str) -> dict:
        """Get raw issue data with all fields."""
        return self.attachments.get_issue_raw(issue_id)
    
    def get_attachment_content(self, issue_id: str, attachment_id: str) -> dict:
        """Get attachment content as base64."""
        return self.attachments.get_attachment_content(issue_id, attachment_id)

    # === Comment Functions ===
    
    def get_comments(self, project_id: Optional[str] = None, task_id: Optional[str] = None, 
                    cursor: Optional[str] = None, limit: int = 50) -> dict:
        """Get comments for a task or project."""
        return self.comments.get_comments(project_id, task_id, cursor, limit)
    
    def get_task_comments(self, task_id: str, cursor: Optional[str] = None, limit: int = 50) -> dict:
        """Get comments for a specific task/issue."""
        return self.comments.get_task_comments(task_id, cursor, limit)
    
    def get_project_comments(self, project_id: str, cursor: Optional[str] = None, limit: int = 50) -> dict:
        """Get recent comments across a project."""
        return self.comments.get_project_comments(project_id, cursor, limit)
    
    def get_comment(self, issue_id: str, comment_id: str) -> dict:
        """Get a specific comment by ID."""
        return self.comments.get_comment(issue_id, comment_id)
    
    def update_comment(self, issue_id: str, comment_id: str, text: str) -> dict:
        """Update an existing comment (placeholder)."""
        return self.comments.update_comment(issue_id, comment_id, text)
    
    def delete_comment(self, issue_id: str, comment_id: str) -> dict:
        """Delete a comment (placeholder)."""
        return self.comments.delete_comment(issue_id, comment_id)

    # === Utility Functions ===
    
    def close(self) -> None:
        """Close API clients and clean up resources."""
        return self.utilities.close()
    
    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get consolidated tool definitions from all modules."""
        return self.utilities.get_tool_definitions()


__all__ = [
    "IssueTools",
    "DedicatedUpdates", 
    "Diagnostics",
    "CustomFields",
    "BasicOperations",
    "Linking",
    "Attachments",
    "Utilities",
    "CommentOperations",
]