"""
YouTrack Issues API client.
"""
from typing import Any, Dict, List, Optional
import json
import logging

from pydantic import BaseModel, Field

from youtrack_mcp.api.client import YouTrackClient, YouTrackAPIError

logger = logging.getLogger(__name__)


class Issue(BaseModel):
    """Model for a YouTrack issue."""
    
    id: str
    summary: Optional[str] = None
    description: Optional[str] = None
    created: Optional[int] = None
    updated: Optional[int] = None
    project: Dict[str, Any] = Field(default_factory=dict)
    reporter: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    custom_fields: List[Dict[str, Any]] = Field(default_factory=list)
    
    model_config = {
        "extra": "allow",  # Allow extra fields from the API
        "populate_by_name": True  # Allow population by field name (helps with aliases)
    }


class IssuesClient:
    """Client for interacting with YouTrack Issues API."""
    
    def __init__(self, client: YouTrackClient):
        """
        Initialize the Issues API client.
        
        Args:
            client: The YouTrack API client
        """
        self.client = client
    
    async def get_issue(self, *, issue_id: str) -> Issue:
        """
        Get an issue by ID.
        
        Args:
            issue_id: The issue ID or readable ID (e.g., PROJECT-123)
            
        Returns:
            The issue data with resolved field values
        """
        response = await self.client.get(f"issues/{issue_id}")
        
        # If the response doesn't have all needed fields, fetch more details
        if isinstance(response, dict) and response.get('$type') == 'Issue' and 'summary' not in response:
            # Get additional fields we need including detailed custom field values
            fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
            detailed_response = await self.client.get(f"issues/{issue_id}?fields={fields}")
            response = detailed_response
        
        # Enhance the response with resolved field values
        enhanced_response = await self._enhance_issue_with_field_values(response)
        
        return Issue.model_validate(enhanced_response)
    
    async def create_issue(self, 
                     project_id: str, 
                     summary: str, 
                     description: Optional[str] = None,
                     additional_fields: Optional[Dict[str, Any]] = None) -> Issue:
        """
        Create a new issue.
        
        Args:
            project_id: The ID of the project
            summary: The issue summary
            description: The issue description
            additional_fields: Additional fields to set on the issue
            
        Returns:
            The created issue data
        """
        # Make sure we have valid input data
        if not project_id:
            raise ValueError("Project ID is required")
        if not summary:
            raise ValueError("Summary is required")
            
        # Format request data according to YouTrack API requirements
        # Note: YouTrack API requires a specific format for some fields
        data = {
            "project": {
                "id": project_id
            },
            "summary": summary
        }
        
        if description:
            data["description"] = description
            
        if additional_fields:
            data.update(additional_fields)
        
        try:
            # For debugging
            logger.info(f"Creating issue with data: {json.dumps(data)}")
            
            # Use the async client's post method
            response = await self.client.post("issues", data=data)
            return Issue.model_validate(response)
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error creating issue: {str(e)}, Data: {data}")
            raise
    
    async def update_issue(self, 
                     issue_id: str, 
                     summary: Optional[str] = None,
                     description: Optional[str] = None,
                     additional_fields: Optional[Dict[str, Any]] = None) -> Issue:
        """
        Update an existing issue.
        
        Args:
            issue_id: The issue ID or readable ID
            summary: The new issue summary
            description: The new issue description
            additional_fields: Additional fields to update
            
        Returns:
            The updated issue data
        """
        data = {}
        
        if summary is not None:
            data["summary"] = summary
            
        if description is not None:
            data["description"] = description
            
        if additional_fields:
            data.update(additional_fields)
            
        if not data:
            # Nothing to update
            return await self.get_issue(issue_id=issue_id)
            
        response = await self.client.post(f"issues/{issue_id}", data=data)
        return Issue.model_validate(response)
    
    async def search_issues(self, *, query: str, limit: int = 10) -> List[Issue]:
        """
        Search for issues using YouTrack query language.
        
        Args:
            query: The search query
            limit: Maximum number of issues to return
            
        Returns:
            List of matching issues with resolved field values
        """
        # Request additional fields to ensure we get summary including detailed custom field values
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {"query": query, "$top": limit, "fields": fields}
        response = await self.client.get("issues", params=params)
        
        issues = []
        for item in response:
            try:
                # Enhance each issue with resolved field values
                enhanced_item = await self._enhance_issue_with_field_values(item)
                issues.append(Issue.model_validate(enhanced_item))
            except Exception as e:
                # Log the error but continue processing other issues
                import logging
                logging.getLogger(__name__).warning(f"Failed to validate issue: {str(e)}")
        
        return issues
    
    async def add_comment(self, *, issue_id: str, text: str) -> Dict[str, Any]:
        """
        Add a comment to an issue.
        
        Args:
            issue_id: The issue ID or readable ID
            text: The comment text
            
        Returns:
            The created comment data
        """
        data = {"text": text}
        return await self.client.post(f"issues/{issue_id}/comments", data=data)
    
    async def link_issues(self, *, source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
        """
        Link two issues together using YouTrack commands.
        
        This method uses the YouTrack commands API to create a link between issues.
        The command approach is preferred over direct link creation as it's more reliable.
        
        Args:
            source_issue_id: The ID of the issue that will have the link applied to it
            target_issue_id: The ID of the issue to link to
            link_type: The type of link (e.g., "relates to", "depends on", "blocks")
            
        Returns:
            Command execution result
        """
        # Prepare the command data
        command_data = {
            "query": f"{link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        logger.info(f"Linking issue {source_issue_id} to {target_issue_id} with link type '{link_type}'")
        logger.debug(f"Command data: {json.dumps(command_data)}")
        
        try:
            # Execute the command using the commands API
            result = await self.client.post("commands", data=command_data)
            logger.info(f"Successfully linked {source_issue_id} to {target_issue_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to link issues {source_issue_id} -> {target_issue_id}: {str(e)}")
            raise
    
    async def get_issue_links(self, *, issue_id: str) -> Dict[str, Any]:
        """
        Get all links for a specific issue.
        
        Args:
            issue_id: The issue ID or readable ID
            
        Returns:
            Dictionary containing issue link information
        """
        # Get links with comprehensive field information
        fields = "id,direction,linkType(id,name,directed),issues(id,idReadable,summary,project(id,name,shortName))"
        params = {"fields": fields}
        
        try:
            links = await self.client.get(f"issues/{issue_id}/links", params=params)
            logger.debug(f"Retrieved {len(links) if isinstance(links, list) else 0} links for issue {issue_id}")
            return links
        except Exception as e:
            logger.error(f"Failed to get links for issue {issue_id}: {str(e)}")
            raise
    
    async def get_available_link_types(self) -> Dict[str, Any]:
        """
        Get available issue link types from YouTrack.
        
        Returns:
            Dictionary containing available link types
        """
        try:
            # Get all issue link types with their names and directions
            fields = "id,name,directed,sourceToTarget,targetToSource,aggregation,readOnly"
            params = {"fields": fields}
            link_types = await self.client.get("issueLinkTypes", params=params)
            logger.debug(f"Retrieved {len(link_types) if isinstance(link_types, list) else 0} link types")
            return link_types
        except Exception as e:
            logger.error(f"Failed to get available link types: {str(e)}")
            raise
    
    async def update_issue_fields(self, *, issue_id: str, **fields) -> Dict[str, Any]:
        """
        Update issue fields using YouTrack commands.
        
        This method uses the YouTrack commands API to update issue fields like assignee,
        priority, state, etc. Different projects may have different field names.
        
        Args:
            issue_id: The issue ID or readable ID
            **fields: Field updates as keyword arguments (e.g., assignee="cventers", priority="Critical")
            
        Returns:
            Command execution result
        """
        # Build command query from field updates
        command_parts = []
        for field_name, field_value in fields.items():
            if field_name.lower() == 'assignee':
                if field_value and field_value.lower() not in ['unassigned', 'none', '']:
                    command_parts.append(f"for {field_value}")
                else:
                    command_parts.append("for Unassigned")
            elif field_name.lower() == 'priority':
                command_parts.append(f"Priority {field_value}")
            elif field_name.lower() == 'state':
                command_parts.append(f"State {field_value}")
            elif field_name.lower() == 'type':
                command_parts.append(f"Type {field_value}")
            else:
                # Generic field update format
                command_parts.append(f"{field_name} {field_value}")
        
        if not command_parts:
            raise ValueError("No valid field updates provided")
        
        # Join multiple commands with spaces
        query = " ".join(command_parts)
        
        command_data = {
            "query": query,
            "issues": [{"idReadable": issue_id}]
        }
        
        logger.info(f"Updating issue {issue_id} with command: {query}")
        logger.debug(f"Command data: {json.dumps(command_data)}")
        
        try:
            # Execute the command using the commands API
            result = await self.client.post("commands", data=command_data)
            logger.info(f"Successfully updated issue {issue_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update issue {issue_id}: {str(e)}")
            raise
    
    async def create_dependency(self, *, dependent_issue_id: str, dependency_issue_id: str) -> Dict[str, Any]:
        """
        Create a dependency relationship where one issue depends on another.
        
        This is a convenience method that uses the correct YouTrack syntax for dependencies.
        For YouTrack's "Depend" link type:
        - sourceToTarget: "is required for"
        - targetToSource: "depends on"
        
        Args:
            dependent_issue_id: The issue that depends on another (will have "depends on" applied to it)
            dependency_issue_id: The issue that is required (the dependency)
            
        Returns:
            Command execution result
        """
        return await self.link_issues(source_issue_id=dependent_issue_id, target_issue_id=dependency_issue_id, link_type="depends on")
    
    async def remove_link(self, *, source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
        """
        Remove a link between two issues using YouTrack commands.
        
        Args:
            source_issue_id: The ID of the issue that will have the link removed from it
            target_issue_id: The ID of the issue to unlink from
            link_type: The type of link to remove
            
        Returns:
            Command execution result
        """
        # Prepare the command data with remove prefix
        command_data = {
            "query": f"remove {link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        logger.info(f"Removing link from {source_issue_id} to {target_issue_id} with link type '{link_type}'")
        logger.debug(f"Command data: {json.dumps(command_data)}")
        
        try:
            # Execute the command using the commands API
            result = await self.client.post("commands", data=command_data)
            logger.info(f"Successfully removed link {source_issue_id} -> {target_issue_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to remove link {source_issue_id} -> {target_issue_id}: {str(e)}")
            raise
    
    async def _enhance_issue_with_field_values(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance issue data with resolved custom field values.
        
        Args:
            issue_data: Raw issue data from YouTrack API
            
        Returns:
            Enhanced issue data with resolved field values
        """
        if not isinstance(issue_data, dict):
            return issue_data
        
        # Make a copy to avoid modifying the original
        enhanced_issue = issue_data.copy()
        
        # Get project ID for field resolution context
        project_id = None
        if "project" in enhanced_issue and isinstance(enhanced_issue["project"], dict):
            project_id = enhanced_issue["project"].get("id")
        
        logger.debug(f"Enhancing issue {enhanced_issue.get('id', 'unknown')} with project ID {project_id}")
        
        # Process custom fields
        custom_fields = enhanced_issue.get("customFields", [])
        if isinstance(custom_fields, list):
            enhanced_fields = []
            for field in custom_fields:
                if isinstance(field, dict):
                    enhanced_field = field.copy()
                    
                    # Add debug info for field resolution
                    field_name = field.get("name", "unknown")
                    field_type = field.get("$type", "unknown")
                    logger.debug(f"Processing field {field_name} of type {field_type}")
                    
                    # Try to resolve the field value to human-readable text
                    resolved_value = await self.client.resolve_field_value(field, project_id)
                    if resolved_value:
                        enhanced_field["value_text"] = resolved_value
                        logger.debug(f"Resolved {field_name} to: {resolved_value}")
                    else:
                        logger.debug(f"Could not resolve field {field_name}")
                    
                    enhanced_fields.append(enhanced_field)
                else:
                    enhanced_fields.append(field)
            
            enhanced_issue["customFields"] = enhanced_fields
        
        return enhanced_issue 