#!/usr/bin/env python3
"""
YouTrack MCP Server - Consolidated Standard SDK Implementation
A Model Context Protocol server for JetBrains YouTrack using the standard MCP Python SDK.
Supports both stdio and HTTP transports with configurable binding.
"""
import argparse
import asyncio
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

# Standard MCP SDK imports
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# YouTrack API clients
from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.issues import IssuesClient
from youtrack_mcp.api.projects import ProjectsClient
from youtrack_mcp.api.users import UsersClient
from youtrack_mcp.api.search import SearchClient
from youtrack_mcp.config import Config, config
from youtrack_mcp.utils import convert_timestamp_to_iso8601, add_iso8601_timestamps

# Advanced search engine
from youtrack_mcp.search_advanced import (
    AdvancedSearchEngine, SearchQuery, SearchOperator, SortOrder, SearchScope,
    create_issue_search, create_date_range_search, create_text_search
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# App version
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Initialize the MCP server
mcp = FastMCP("YouTrack MCP")

# Global API clients - initialized after config load
youtrack_client: Optional[YouTrackClient] = None
issues_api: Optional[IssuesClient] = None
projects_api: Optional[ProjectsClient] = None
users_api: Optional[UsersClient] = None
search_api: Optional[SearchClient] = None
advanced_search: Optional[AdvancedSearchEngine] = None


def load_config():
    """Load configuration from environment variables."""
    logger.info("Loading configuration from environment variables")
    
    # Load from environment variables
    if os.getenv("YOUTRACK_URL"):
        config.YOUTRACK_URL = os.getenv("YOUTRACK_URL")
    
    if os.getenv("YOUTRACK_TOKEN_FILE"):
        token_file = os.getenv("YOUTRACK_TOKEN_FILE")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                config.YOUTRACK_API_TOKEN = f.read().strip()
            logger.info(f"Loaded API token from file: {token_file}")
    elif os.getenv("YOUTRACK_TOKEN"):
        config.YOUTRACK_API_TOKEN = os.getenv("YOUTRACK_TOKEN")
    
    config.YOUTRACK_CLOUD = os.getenv("YOUTRACK_CLOUD", "true").lower() == "true"
    config.VERIFY_SSL = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower() == "true"
    
    # Validate configuration
    config.validate()
    
    logger.info(f"Configured for YouTrack at: {config.YOUTRACK_URL}")
    logger.info(f"SSL verification: {'Enabled' if config.VERIFY_SSL else 'Disabled'}")


def initialize_clients():
    """Initialize API clients."""
    global youtrack_client, issues_api, projects_api, users_api, search_api, advanced_search
    
    youtrack_client = YouTrackClient()
    issues_api = IssuesClient(youtrack_client)
    projects_api = ProjectsClient(youtrack_client)
    users_api = UsersClient(youtrack_client)
    search_api = SearchClient(youtrack_client)
    advanced_search = AdvancedSearchEngine(youtrack_client, enable_cache=True, enable_analytics=True)
    
    logger.info("API clients and advanced search engine initialized")


# Issue Tools
@mcp.tool()
async def get_issue(issue_id: str) -> Dict[str, Any]:
    """
    Get information about a specific issue.
    
    Args:
        issue_id: The issue ID or readable ID (e.g., PROJECT-123)
        
    Returns:
        Issue information
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        raw_issue = await youtrack_client.get(f"issues/{issue_id}?fields={fields}")
        
        # Enhance with ISO8601 timestamps
        raw_issue = add_iso8601_timestamps(raw_issue)
        
        return raw_issue
        
    except Exception as e:
        logger.exception(f"Error getting issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def get_issue_raw(issue_id: str, fields: str = None) -> Dict[str, Any]:
    """
    Get raw issue data with custom field selection.
    
    Args:
        issue_id: The issue ID or readable ID (e.g., PROJECT-123)
        fields: Custom field selection string (optional)
        
    Returns:
        Raw issue data without processing
    """
    try:
        if not fields:
            # Default comprehensive fields
            fields = "id,idReadable,summary,description,created,updated,resolved,project(id,name,shortName),reporter(id,login,name,email),assignee(id,login,name,email),updater(id,login,name),customFields(id,name,value(id,name,$type,text,presentation)),attachments(id,name,size,url),comments(id,text,created,author(id,login,name)),links(id,direction,linkType(id,name),issues(id,idReadable,summary))"
        
        result = await youtrack_client.get(f"issues/{issue_id}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting raw issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def create_issue(project: str, summary: str, description: str = None) -> Dict[str, Any]:
    """
    Create a new issue in YouTrack.
    
    Args:
        project: Project key or ID
        summary: Issue summary/title
        description: Issue description (optional)
        
    Returns:
        Created issue information
    """
    try:
        issue_data = {
            "project": {"shortName": project},
            "summary": summary
        }
        
        if description:
            issue_data["description"] = description
        
        result = await youtrack_client.post("issues", data=issue_data)
        return result
        
    except Exception as e:
        logger.exception(f"Error creating issue in project {project}")
        return {"error": str(e)}


@mcp.tool()
async def search_issues(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for issues using YouTrack query language.
    
    Args:
        query: YouTrack search query
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of matching issues
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit
        }
        
        results = await youtrack_client.get("issues", params=params)
        
        # Enhance with ISO8601 timestamps
        results = add_iso8601_timestamps(results)
        
        return results if isinstance(results, list) else []
        
    except Exception as e:
        logger.exception(f"Error searching issues with query: {query}")
        return [{"error": str(e)}]


@mcp.tool()
async def advanced_search(query: str, sort_by: str = None, sort_order: str = "asc", 
                   limit: int = 50, skip: int = 0) -> Dict[str, Any]:
    """
    Advanced search for issues with sorting and pagination.
    
    Args:
        query: YouTrack search query
        sort_by: Field to sort by (e.g., 'created', 'updated', 'priority', 'summary')
        sort_order: Sort order ('asc' or 'desc', default: 'asc')
        limit: Maximum number of results (default: 50)
        skip: Number of results to skip for pagination (default: 0)
        
    Returns:
        Dictionary with results and metadata
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,resolved,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit,
            "$skip": skip
        }
        
        # Add sorting if specified
        if sort_by:
            if sort_order.lower() == "desc":
                params["$orderBy"] = f"{sort_by} desc"
            else:
                params["$orderBy"] = f"{sort_by} asc"
        
        results = await youtrack_client.get("issues", params=params)
        
        # Enhance with ISO8601 timestamps
        results = add_iso8601_timestamps(results)
        
        if not isinstance(results, list):
            results = []
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        logger.exception(f"Error in advanced search with query: {query}")
        return {"error": str(e), "results": []}


@mcp.tool()
async def filter_issues(project: str = None, assignee: str = None, reporter: str = None,
                 state: str = None, priority: str = None, created_after: str = None,
                 created_before: str = None, updated_after: str = None, 
                 updated_before: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Filter issues using structured parameters.
    
    Args:
        project: Project short name or ID
        assignee: Assignee login name ('Unassigned' for unassigned issues)
        reporter: Reporter login name
        state: Issue state (e.g., 'Open', 'Fixed', 'Verified')
        priority: Issue priority (e.g., 'Critical', 'High', 'Normal', 'Low')
        created_after: Created after date (YYYY-MM-DD or ISO format)
        created_before: Created before date (YYYY-MM-DD or ISO format)
        updated_after: Updated after date (YYYY-MM-DD or ISO format)
        updated_before: Updated before date (YYYY-MM-DD or ISO format)
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of filtered issues
    """
    try:
        # Build YouTrack query from filters
        query_parts = []
        
        if project:
            query_parts.append(f"project: {project}")
        if assignee:
            if assignee.lower() == "unassigned":
                query_parts.append("has: -Assignee")
            else:
                query_parts.append(f"Assignee: {assignee}")
        if reporter:
            query_parts.append(f"created by: {reporter}")
        if state:
            query_parts.append(f"State: {state}")
        if priority:
            query_parts.append(f"Priority: {priority}")
        
        # Date filters
        if created_after:
            query_parts.append(f"created: {created_after} .. *")
        if created_before:
            query_parts.append(f"created: * .. {created_before}")
        if updated_after:
            query_parts.append(f"updated: {updated_after} .. *")
        if updated_before:
            query_parts.append(f"updated: * .. {updated_before}")
        
        # Combine query parts
        if not query_parts:
            # No filters - return recent issues
            query = "created: -30d .. *"
        else:
            query = " ".join(query_parts)
        
        # Use advanced search for consistent results
        result = await advanced_search(query, sort_by="updated", sort_order="desc", limit=limit)
        return result.get("results", [])
        
    except Exception as e:
        logger.exception("Error in filter_issues")
        return [{"error": str(e)}]


@mcp.tool()
async def search_with_custom_fields(project: str = None, custom_field_filters: Dict[str, str] = None,
                             base_query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search issues with custom field filters.
    
    Args:
        project: Project short name or ID to search within
        custom_field_filters: Dictionary of custom field name -> value pairs
        base_query: Additional YouTrack query to combine with custom field filters
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of matching issues
    """
    try:
        query_parts = []
        
        # Add project filter
        if project:
            query_parts.append(f"project: {project}")
        
        # Add base query
        if base_query:
            query_parts.append(f"({base_query})")
        
        # Add custom field filters
        if custom_field_filters:
            for field_name, field_value in custom_field_filters.items():
                if field_value:
                    # Handle special values
                    if field_value.lower() in ["unset", "none", "empty"]:
                        query_parts.append(f"has: -{{{field_name}}}")
                    else:
                        query_parts.append(f"{{{field_name}}}: {field_value}")
        
        # Build final query
        if not query_parts:
            query = "*"  # Match all issues
        else:
            query = " ".join(query_parts)
        
        # Use advanced search
        result = await advanced_search(query, sort_by="updated", sort_order="desc", limit=limit)
        return result.get("results", [])
        
    except Exception as e:
        logger.exception("Error in search_with_custom_fields")
        return [{"error": str(e)}]


# Advanced Search Tools
@mcp.tool()
async def intelligent_search(
    query_text: str = None,
    project: str = None,
    assignee: str = None,
    state: str = None,
    priority: str = None,
    created_after: str = None,
    created_before: str = None,
    updated_after: str = None,
    updated_before: str = None,
    sort_by: str = "updated",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    include_resolved: bool = True,
    include_archived: bool = False
) -> Dict[str, Any]:
    """
    Intelligent search with advanced query building, caching, and analytics.
    
    Args:
        query_text: Free text search across summary and description
        project: Project name or short name
        assignee: Assignee login name ('unassigned' for unassigned issues)
        state: Issue state (e.g., 'Open', 'Fixed', 'Verified')
        priority: Issue priority (e.g., 'Critical', 'High', 'Normal', 'Low')
        created_after: Created after date (YYYY-MM-DD or relative like '-7d')
        created_before: Created before date (YYYY-MM-DD)
        updated_after: Updated after date (YYYY-MM-DD or relative like '-1w')
        updated_before: Updated before date (YYYY-MM-DD)
        sort_by: Field to sort by (created, updated, priority, summary)
        sort_order: Sort order ('asc' or 'desc')
        limit: Maximum number of results (1-1000)
        offset: Results offset for pagination
        include_resolved: Include resolved/closed issues
        include_archived: Include issues from archived projects
        
    Returns:
        Search results with metadata, suggestions, and analytics
    """
    try:
        # Create advanced search query
        search_query = advanced_search.create_query()
        
        # Add text search
        if query_text:
            search_query.add_text_search(query_text)
        
        # Add structured conditions
        if project:
            search_query.add_condition("project", SearchOperator.EQUALS, project)
        
        if assignee:
            if assignee.lower() == "unassigned":
                search_query.add_condition("assignee", SearchOperator.EQUALS, "Unassigned")
            else:
                search_query.add_condition("assignee", SearchOperator.EQUALS, assignee)
        
        if state:
            search_query.add_condition("State", SearchOperator.EQUALS, state)
        
        if priority:
            search_query.add_condition("Priority", SearchOperator.EQUALS, priority)
        
        # Handle date ranges with relative dates
        from datetime import datetime, timedelta
        
        def parse_relative_date(date_str: str) -> datetime:
            """Parse relative dates like '-7d', '-1w', '-1m'."""
            if date_str.startswith('-'):
                match = re.match(r'-(\d+)([dwmy])', date_str.lower())
                if match:
                    num, unit = int(match.group(1)), match.group(2)
                    if unit == 'd':
                        return datetime.now() - timedelta(days=num)
                    elif unit == 'w':
                        return datetime.now() - timedelta(weeks=num)
                    elif unit == 'm':
                        return datetime.now() - timedelta(days=num * 30)
                    elif unit == 'y':
                        return datetime.now() - timedelta(days=num * 365)
            
            # Try to parse as regular date
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None
        
        # Add date range conditions
        if created_after or created_before:
            from_date = parse_relative_date(created_after) if created_after else None
            to_date = parse_relative_date(created_before) if created_before else None
            if from_date or to_date:
                search_query.add_date_range("created", from_date, to_date)
        
        if updated_after or updated_before:
            from_date = parse_relative_date(updated_after) if updated_after else None
            to_date = parse_relative_date(updated_before) if updated_before else None
            if from_date or to_date:
                search_query.add_date_range("updated", from_date, to_date)
        
        # Configure query options
        search_query.include_resolved = include_resolved
        search_query.include_archived = include_archived
        search_query.set_pagination(limit, offset)
        search_query.set_sorting(sort_by, SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC)
        
        # Execute search
        result = await advanced_search.search(search_query)
        
        # Enhance with ISO8601 timestamps
        enhanced_issues = add_iso8601_timestamps(result.issues)
        
        return {
            "issues": enhanced_issues,
            "total_count": result.total_count,
            "execution_time_ms": int(result.execution_time * 1000),
            "query_used": result.query_used,
            "cache_hit": result.cache_hit,
            "suggested_queries": result.suggested_queries,
            "facets": result.facets,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(enhanced_issues) == limit
            }
        }
        
    except Exception as e:
        logger.exception("Error in intelligent_search")
        return {"error": str(e)}


@mcp.tool()
async def search_by_query_builder(conditions: List[Dict[str, Any]], 
                                 sort_field: str = "updated", 
                                 sort_order: str = "desc",
                                 limit: int = 50) -> Dict[str, Any]:
    """
    Advanced search using structured query conditions.
    
    Args:
        conditions: List of search conditions, each with:
                   - field: Field name (e.g., 'project', 'assignee', 'State')
                   - operator: Operator (':', '!:', '>', '<', 'in', 'not in', etc.)
                   - value: Value to search for
                   - negated: Whether to negate the condition (optional)
        sort_field: Field to sort results by
        sort_order: Sort order ('asc' or 'desc')
        limit: Maximum number of results
        
    Returns:
        Search results with metadata
    """
    try:
        # Create search query
        search_query = advanced_search.create_query()
        
        # Add conditions
        for condition in conditions:
            field = condition.get("field")
            operator_str = condition.get("operator", ":")
            value = condition.get("value")
            negated = condition.get("negated", False)
            
            if not field or value is None:
                continue
            
            # Map operator string to enum
            operator_map = {
                ":": SearchOperator.EQUALS,
                "!:": SearchOperator.NOT_EQUALS,
                "~": SearchOperator.CONTAINS,
                "!~": SearchOperator.NOT_CONTAINS,
                ">": SearchOperator.GREATER_THAN,
                "<": SearchOperator.LESS_THAN,
                ">=": SearchOperator.GREATER_EQUAL,
                "<=": SearchOperator.LESS_EQUAL,
                "in": SearchOperator.IN,
                "not in": SearchOperator.NOT_IN,
                "has": SearchOperator.HAS,
                "!has": SearchOperator.NOT_HAS
            }
            
            operator = operator_map.get(operator_str, SearchOperator.EQUALS)
            search_query.add_condition(field, operator, value, negated)
        
        # Set sorting and pagination
        search_query.set_sorting(sort_field, SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC)
        search_query.set_pagination(limit)
        
        # Execute search
        result = await advanced_search.search(search_query)
        
        # Enhance with ISO8601 timestamps
        enhanced_issues = add_iso8601_timestamps(result.issues)
        
        return {
            "issues": enhanced_issues,
            "total_count": result.total_count,
            "execution_time_ms": int(result.execution_time * 1000),
            "query_used": result.query_used,
            "cache_hit": result.cache_hit,
            "conditions_applied": len(conditions)
        }
        
    except Exception as e:
        logger.exception("Error in search_by_query_builder")
        return {"error": str(e)}


@mcp.tool()
async def search_suggestions(partial_query: str, limit: int = 5) -> List[str]:
    """
    Get search query suggestions based on partial input.
    
    Args:
        partial_query: Partial search query to get suggestions for
        limit: Maximum number of suggestions to return
        
    Returns:
        List of suggested query completions
    """
    try:
        suggestions = await advanced_search.get_search_suggestions(partial_query, limit)
        return suggestions
        
    except Exception as e:
        logger.exception("Error getting search suggestions")
        return [f"Error: {str(e)}"]


@mcp.tool()
async def search_analytics() -> Dict[str, Any]:
    """
    Get search analytics and performance statistics.
    
    Returns:
        Analytics data including popular queries, performance metrics, and cache statistics
    """
    try:
        analytics_stats = advanced_search.get_analytics_stats()
        cache_stats = advanced_search.get_cache_stats()
        
        return {
            "analytics": analytics_stats,
            "cache": cache_stats,
            "status": "enabled" if advanced_search.enable_analytics else "disabled"
        }
        
    except Exception as e:
        logger.exception("Error getting search analytics")
        return {"error": str(e)}


@mcp.tool()
async def clear_search_cache() -> Dict[str, Any]:
    """
    Clear the search cache to force fresh results.
    
    Returns:
        Status of cache clearing operation
    """
    try:
        if advanced_search.cache:
            advanced_search.clear_cache()
            return {"status": "success", "message": "Search cache cleared"}
        else:
            return {"status": "info", "message": "Search cache is not enabled"}
        
    except Exception as e:
        logger.exception("Error clearing search cache")
        return {"error": str(e)}


@mcp.tool()
async def add_comment(issue_id: str, text: str) -> Dict[str, Any]:
    """
    Add a comment to an issue.
    
    Args:
        issue_id: The issue ID or readable ID
        text: Comment text
        
    Returns:
        Comment creation result
    """
    try:
        comment_data = {"text": text}
        result = await youtrack_client.post(f"issues/{issue_id}/comments", data=comment_data)
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.exception(f"Error adding comment to issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def update_issue(issue_id: str, assignee: str = None, priority: str = None, 
                state: str = None, type: str = None) -> Dict[str, Any]:
    """
    Update issue fields using YouTrack commands.
    
    Args:
        issue_id: The issue ID or readable ID
        assignee: Username to assign to (optional)
        priority: Priority level (optional)
        state: Issue state (optional)
        type: Issue type (optional)
        
    Returns:
        Update result
    """
    try:
        command_parts = []
        
        if assignee:
            if assignee.lower() in ['unassigned', 'none', '']:
                command_parts.append("for Unassigned")
            else:
                command_parts.append(f"for {assignee}")
        
        if priority:
            command_parts.append(f"Priority {priority}")
        
        if state:
            command_parts.append(f"State {state}")
            
        if type:
            command_parts.append(f"Type {type}")
        
        if not command_parts:
            return {"error": "No valid field updates provided"}
        
        query = " ".join(command_parts)
        command_data = {
            "query": query,
            "issues": [{"idReadable": issue_id}]
        }
        
        result = await youtrack_client.post("commands", data=command_data)
        return {"status": "success", "message": f"Successfully updated issue {issue_id}", "result": result}
        
    except Exception as e:
        logger.exception(f"Error updating issue {issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def link_issues(source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
    """
    Link two issues together using a specified link type.
    
    Args:
        source_issue_id: The ID of the issue that will have the link applied to it
        target_issue_id: The ID of the issue to link to
        link_type: The type of link (default: "relates to")
        
    Returns:
        Link creation result
    """
    try:
        command_data = {
            "query": f"{link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        result = await youtrack_client.post("commands", data=command_data)
        return {
            "status": "success",
            "message": f"Successfully linked {source_issue_id} to {target_issue_id} with link type '{link_type}'",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error linking issues {source_issue_id} -> {target_issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def remove_link(source_issue_id: str, target_issue_id: str, link_type: str = "relates to") -> Dict[str, Any]:
    """
    Remove a link between two issues.
    
    Args:
        source_issue_id: The issue that will have the link removed from it
        target_issue_id: The issue to unlink from
        link_type: The type of link to remove (default: "relates to")
        
    Returns:
        Link removal result
    """
    try:
        command_data = {
            "query": f"remove {link_type} {target_issue_id}",
            "issues": [{"idReadable": source_issue_id}]
        }
        
        result = await youtrack_client.post("commands", data=command_data)
        return {
            "status": "success", 
            "message": f"Successfully removed {link_type} link from {source_issue_id} to {target_issue_id}",
            "result": result
        }
        
    except Exception as e:
        logger.exception(f"Error removing link {source_issue_id} -> {target_issue_id}")
        return {"error": str(e)}


@mcp.tool()
async def create_dependency(dependent_issue_id: str, dependency_issue_id: str) -> Dict[str, Any]:
    """
    Create a dependency relationship where one issue depends on another.
    
    Args:
        dependent_issue_id: The issue that depends on another
        dependency_issue_id: The issue that is required
        
    Returns:
        Dependency creation result
    """
    return await link_issues(dependent_issue_id, dependency_issue_id, "depends on")


@mcp.tool()
async def get_issue_links(issue_id: str) -> List[Dict[str, Any]]:
    """
    Get all links for a specific issue.
    
    Args:
        issue_id: The issue ID or readable ID
        
    Returns:
        List of issue links
    """
    try:
        fields = "id,direction,linkType(id,name,directed),issues(id,idReadable,summary,project(id,name,shortName))"
        params = {"fields": fields}
        
        links = await youtrack_client.get(f"issues/{issue_id}/links", params=params)
        return links if isinstance(links, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting links for issue {issue_id}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_available_link_types() -> List[Dict[str, Any]]:
    """
    Get available issue link types from YouTrack.
    
    Returns:
        List of available link types
    """
    try:
        fields = "id,name,directed,sourceToTarget,targetToSource,aggregation,readOnly"
        params = {"fields": fields}
        link_types = await youtrack_client.get("issueLinkTypes", params=params)
        return link_types if isinstance(link_types, list) else []
        
    except Exception as e:
        logger.exception("Error getting available link types")
        return [{"error": str(e)}]


# Project Tools
@mcp.tool()
async def create_project(short_name: str, name: str, description: str = None) -> Dict[str, Any]:
    """
    Create a new project in YouTrack.
    
    Args:
        short_name: Project short name/key (unique identifier)
        name: Project display name
        description: Project description (optional)
        
    Returns:
        Created project information
    """
    try:
        project_data = {
            "shortName": short_name,
            "name": name
        }
        
        if description:
            project_data["description"] = description
        
        result = await youtrack_client.post("admin/projects", data=project_data)
        return result
        
    except Exception as e:
        logger.exception(f"Error creating project {short_name}")
        return {"error": str(e)}


@mcp.tool()
async def update_project(project: str, name: str = None, description: str = None, 
                  archived: bool = None) -> Dict[str, Any]:
    """
    Update an existing project.
    
    Args:
        project: Project short name or ID
        name: New project name (optional)
        description: New project description (optional)
        archived: Archive/unarchive project (optional)
        
    Returns:
        Update result
    """
    try:
        update_data = {}
        
        if name:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if archived is not None:
            update_data["archived"] = archived
        
        if not update_data:
            return {"error": "No valid field updates provided"}
        
        result = await youtrack_client.post(f"admin/projects/{project}", data=update_data)
        return {"status": "success", "message": f"Successfully updated project {project}", "result": result}
        
    except Exception as e:
        logger.exception(f"Error updating project {project}")
        return {"error": str(e)}


@mcp.tool()
async def get_project_issues(project: str, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get all issues for a specific project.
    
    Args:
        project: Project short name or ID
        query: Additional YouTrack query filter (optional)
        limit: Maximum number of results (default: 50)
        
    Returns:
        List of project issues
    """
    try:
        # Build query with project filter
        project_query = f"project: {project}"
        if query:
            project_query = f"({project_query}) and ({query})"
        
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {
            "query": project_query,
            "fields": fields,
            "$top": limit
        }
        
        results = await youtrack_client.get("issues", params=params)
        
        # Enhance with ISO8601 timestamps
        results = add_iso8601_timestamps(results)
        
        return results if isinstance(results, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting issues for project {project}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_custom_fields(project: str = None) -> List[Dict[str, Any]]:
    """
    Get custom fields, optionally filtered by project.
    
    Args:
        project: Project short name or ID to filter by (optional)
        
    Returns:
        List of custom fields
    """
    try:
        if project:
            # Get project-specific custom fields
            fields = "id,name,fieldType,customField(id,name,fieldType)"
            params = {"fields": fields}
            result = await youtrack_client.get(f"admin/projects/{project}/customFields", params=params)
        else:
            # Get all custom fields
            fields = "id,name,fieldType,defaultValues(id,name)"
            params = {"fields": fields}
            result = await youtrack_client.get("admin/customFieldSettings/customFields", params=params)
        
        return result if isinstance(result, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting custom fields for project {project}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_project_by_name(name_or_key: str) -> Dict[str, Any]:
    """
    Find project by name or short name.
    
    Args:
        name_or_key: Project name or short name to search for
        
    Returns:
        Project information
    """
    try:
        # Search by short name first (exact match)
        try:
            result = await get_project(name_or_key)
            if "error" not in result:
                return result
        except:
            pass
        
        # Search by name in all projects
        projects = await get_projects(include_archived=True)
        for project in projects:
            if isinstance(project, dict):
                if (project.get("name", "").lower() == name_or_key.lower() or
                    project.get("shortName", "").lower() == name_or_key.lower()):
                    return project
        
        return {"error": f"Project not found: {name_or_key}"}
        
    except Exception as e:
        logger.exception(f"Error finding project by name {name_or_key}")
        return {"error": str(e)}


@mcp.tool()
async def get_projects(include_archived: bool = False) -> List[Dict[str, Any]]:
    """
    Get a list of all projects.
    
    Args:
        include_archived: Include archived projects (default: False)
        
    Returns:
        List of projects
    """
    try:
        fields = "id,name,shortName,description,archived"
        params = {"fields": fields}
        
        projects = await youtrack_client.get("admin/projects", params=params)
        
        if not include_archived and isinstance(projects, list):
            projects = [p for p in projects if not p.get("archived", False)]
        
        return projects if isinstance(projects, list) else []
        
    except Exception as e:
        logger.exception("Error getting projects")
        return [{"error": str(e)}]


@mcp.tool()
async def get_project(project: str) -> Dict[str, Any]:
    """
    Get information about a specific project.
    
    Args:
        project: Project short name or ID
        
    Returns:
        Project information
    """
    try:
        fields = "id,name,shortName,description,archived,leader(id,login,name)"
        result = await youtrack_client.get(f"admin/projects/{project}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting project {project}")
        return {"error": str(e)}


# User Tools
@mcp.tool()
async def get_user(user_id: str) -> Dict[str, Any]:
    """
    Get a user by their ID.
    
    Args:
        user_id: User ID
        
    Returns:
        User information
    """
    try:
        fields = "id,login,name,email,guest,online,banned,ringId"
        result = await youtrack_client.get(f"users/{user_id}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting user by ID {user_id}")
        return {"error": str(e)}


@mcp.tool()
async def get_user_groups(user_login: str) -> List[Dict[str, Any]]:
    """
    Get groups for a specific user.
    
    Args:
        user_login: User login name
        
    Returns:
        List of user groups
    """
    try:
        fields = "id,name,description"
        params = {"fields": fields}
        
        # Get user groups
        groups = await youtrack_client.get(f"users/{user_login}/groups", params=params)
        return groups if isinstance(groups, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting groups for user {user_login}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_current_user() -> Dict[str, Any]:
    """
    Get information about the currently authenticated user.
    
    Returns:
        Current user information
    """
    try:
        fields = "id,login,name,email,guest,online,banned"
        result = await youtrack_client.get(f"users/me?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception("Error getting current user")
        return {"error": str(e)}


@mcp.tool()
async def search_users(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for users using YouTrack query.
    
    Args:
        query: User search query
        limit: Maximum number of results (default: 10)
        
    Returns:
        List of matching users
    """
    try:
        fields = "id,login,name,email,guest,online,banned"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit
        }
        
        results = await youtrack_client.get("users", params=params)
        return results if isinstance(results, list) else []
        
    except Exception as e:
        logger.exception(f"Error searching users with query: {query}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_user_by_login(login: str) -> Dict[str, Any]:
    """
    Get a user by their login name.
    
    Args:
        login: User login name
        
    Returns:
        User information
    """
    try:
        fields = "id,login,name,email,guest,online,banned,ringId"
        result = await youtrack_client.get(f"users/{login}?fields={fields}")
        return result
        
    except Exception as e:
        logger.exception(f"Error getting user by login {login}")
        return {"error": str(e)}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YouTrack MCP Server (Consolidated)")
    
    # Transport options
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: 'stdio' for Claude integration (default), 'http' for API server"
    )
    
    # HTTP server options
    parser.add_argument(
        "--host",
        default=os.getenv("YOUTRACK_MCP_HOST", "127.0.0.2"),
        help="Host to bind HTTP server to (default: 127.0.0.2, env: YOUTRACK_MCP_HOST)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("YOUTRACK_MCP_PORT", "8000")),
        help="Port to bind HTTP server to (default: 8000, env: YOUTRACK_MCP_PORT)"
    )
    
    # YouTrack configuration
    parser.add_argument(
        "--youtrack-url",
        default=os.getenv("YOUTRACK_URL"),
        help="YouTrack instance URL (env: YOUTRACK_URL)"
    )
    parser.add_argument(
        "--youtrack-token",
        default=os.getenv("YOUTRACK_TOKEN"),
        help="YouTrack API token (env: YOUTRACK_TOKEN)"
    )
    parser.add_argument(
        "--youtrack-token-file",
        default=os.getenv("YOUTRACK_TOKEN_FILE"),
        help="Path to file containing YouTrack API token (env: YOUTRACK_TOKEN_FILE)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO, env: LOG_LEVEL)"
    )
    
    # SSL verification
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=None,
        help="Verify SSL certificates"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        dest="verify_ssl",
        help="Disable SSL certificate verification"
    )
    
    # Version
    parser.add_argument(
        "--version",
        action="store_true",
        help="Display version information and exit"
    )
    
    return parser.parse_args()


def apply_cli_config(args):
    """Apply CLI arguments to configuration."""
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Apply YouTrack configuration from CLI args
    if args.youtrack_url:
        config.YOUTRACK_URL = args.youtrack_url
    
    if args.youtrack_token:
        config.YOUTRACK_API_TOKEN = args.youtrack_token
    
    if args.youtrack_token_file and os.path.exists(args.youtrack_token_file):
        with open(args.youtrack_token_file, 'r') as f:
            config.YOUTRACK_API_TOKEN = f.read().strip()
        logger.info(f"Loaded API token from file: {args.youtrack_token_file}")
    
    if args.verify_ssl is not None:
        config.VERIFY_SSL = args.verify_ssl


def run_http_server(host: str, port: int):
    """Run HTTP server with JSON-RPC MCP endpoints for ChatGPT integration."""
    logger.info(f"Starting HTTP server on {host}:{port}")
    logger.info("HTTP mode - JSON-RPC MCP endpoints for ChatGPT integration")
    
    from fastapi import FastAPI, Request, HTTPException, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
    import uuid
    import asyncio
    import time
    from typing import Dict, AsyncIterator
    
    # Create FastAPI app
    app = FastAPI(
        title="YouTrack MCP Server",
        description="MCP Server for JetBrains YouTrack - HTTP/JSON-RPC for ChatGPT",
        version=APP_VERSION
    )
    
    # Add CORS for ChatGPT integration
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Optional Bearer token authentication
    security = HTTPBearer(auto_error=False)
    
    async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify bearer token if provided."""
        if credentials:
            # TODO: Add actual token validation here
            # For now, accept any bearer token
            logger.info(f"Authenticated request with token: {credentials.credentials[:10]}...")
        return credentials
    
    @app.get("/")
    async def root():
        """Root endpoint with server info."""
        return {
            "name": "YouTrack MCP Server",
            "version": APP_VERSION,
            "description": "HTTP/JSON-RPC MCP Server for ChatGPT integration",
            "endpoints": {
                "mcp": "/mcp - Main JSON-RPC endpoint (synchronous)",
                "sse": "/sse/{session_id} - Server-Sent Events connection",
                "sse_message": "/sse/{session_id}/message - Send messages to SSE session",
                "sse_list": "/sse - List active SSE connections", 
                "health": "/health - Health check",
                "tools": "/tools - List available tools"
            },
            "integration_notes": {
                "chatgpt": "Use /mcp endpoint for direct tool calls",
                "streaming": "Use /sse endpoints for real-time streaming responses",
                "authentication": "Optional Bearer token in Authorization header"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": APP_VERSION}
    
    @app.get("/tools")
    async def list_tools():
        """List available MCP tools."""
        # Get tools from MCP server
        tools_info = []
        for tool_name, tool_func in mcp.tools.items():
            # Get function signature and docstring
            import inspect
            sig = inspect.signature(tool_func.func)
            doc = tool_func.func.__doc__ or "No description available"
            
            tools_info.append({
                "name": tool_name,
                "description": doc.strip().split('\n')[0],  # First line of docstring
                "parameters": [
                    {
                        "name": param.name,
                        "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                        "required": param.default == inspect.Parameter.empty
                    }
                    for param in sig.parameters.values()
                ]
            })
        
        return {"tools": tools_info}
    
    @app.post("/mcp")
    async def handle_mcp_request(request: Request, auth: HTTPAuthorizationCredentials = Depends(verify_token)):
        """Handle JSON-RPC MCP requests from ChatGPT."""
        try:
            # Parse JSON-RPC request
            body = await request.json()
            
            # Validate JSON-RPC format
            if not isinstance(body, dict):
                raise HTTPException(status_code=400, detail="Request must be JSON object")
            
            jsonrpc = body.get("jsonrpc")
            if jsonrpc != "2.0":
                raise HTTPException(status_code=400, detail="Must use JSON-RPC 2.0")
            
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id", str(uuid.uuid4()))
            
            logger.info(f"MCP Request: {method} with params: {params}")
            
            # Handle different MCP methods
            if method == "tools/list":
                # Return list of available tools
                tools_list = []
                for tool_name, tool_func in mcp.tools.items():
                    import inspect
                    sig = inspect.signature(tool_func.func)
                    doc = tool_func.func.__doc__ or "No description available"
                    
                    # Build parameter schema
                    properties = {}
                    required = []
                    
                    for param_name, param in sig.parameters.items():
                        param_type = "string"  # Default type
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation == int:
                                param_type = "integer"
                            elif param.annotation == bool:
                                param_type = "boolean"
                            elif param.annotation == float:
                                param_type = "number"
                        
                        properties[param_name] = {"type": param_type}
                        if param.default == inspect.Parameter.empty:
                            required.append(param_name)
                    
                    tools_list.append({
                        "name": tool_name,
                        "description": doc.strip(),
                        "inputSchema": {
                            "type": "object",
                            "properties": properties,
                            "required": required
                        }
                    })
                
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                })
            
            elif method == "tools/call":
                # Call a specific tool
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    raise HTTPException(status_code=400, detail="Tool name required")
                
                if tool_name not in mcp.tools:
                    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
                
                # Call the tool function
                tool_func = mcp.tools[tool_name]
                try:
                    # Execute the tool
                    result = await tool_func.func(**arguments)
                    
                    # Format result for MCP
                    content = []
                    if isinstance(result, str):
                        content.append({"type": "text", "text": result})
                    elif isinstance(result, dict):
                        content.append({"type": "text", "text": json.dumps(result, indent=2)})
                    else:
                        content.append({"type": "text", "text": str(result)})
                    
                    return JSONResponse({
                        "jsonrpc": "2.0", 
                        "id": request_id,
                        "result": {"content": content}
                    })
                    
                except Exception as e:
                    logger.error(f"Tool execution error: {str(e)}")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }, status_code=500)
            
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Unknown method: {method}"
                    }
                }, status_code=404)
                
        except Exception as e:
            logger.error(f"MCP request processing error: {str(e)}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": "unknown",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                }
            }, status_code=400)
    
    # SSE connection management
    sse_connections: Dict[str, asyncio.Queue] = {}
    
    @app.get("/sse/{session_id}")
    async def sse_endpoint(session_id: str, request: Request):
        """Server-Sent Events endpoint for real-time streaming."""
        async def event_stream() -> AsyncIterator[str]:
            # Create connection queue
            sse_connections[session_id] = asyncio.Queue()
            
            try:
                # Send initial connection event
                yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
                
                while True:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break
                    
                    try:
                        # Wait for events with timeout
                        event = await asyncio.wait_for(
                            sse_connections[session_id].get(), 
                            timeout=30.0
                        )
                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': time.time()})}\n\n"
                    
            except Exception as e:
                logger.error(f"SSE connection error: {e}")
            finally:
                # Cleanup connection
                if session_id in sse_connections:
                    del sse_connections[session_id]
                logger.info(f"SSE connection closed: {session_id}")
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    @app.post("/sse/{session_id}/message")
    async def sse_message(session_id: str, request: Request, auth: HTTPAuthorizationCredentials = Depends(verify_token)):
        """Send message to SSE connection."""
        try:
            body = await request.json()
            
            if session_id not in sse_connections:
                raise HTTPException(status_code=404, detail="SSE session not found")
            
            # Validate JSON-RPC format
            jsonrpc = body.get("jsonrpc")
            if jsonrpc != "2.0":
                raise HTTPException(status_code=400, detail="Must use JSON-RPC 2.0")
            
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id", str(uuid.uuid4()))
            
            logger.info(f"SSE MCP Request: {method} for session {session_id}")
            
            # Handle the request similar to /mcp endpoint
            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name or tool_name not in mcp.tools:
                    await sse_connections[session_id].put({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": "Tool not found",
                            "data": f"Unknown tool: {tool_name}"
                        }
                    })
                    return {"status": "error", "message": "Tool not found"}
                
                # Execute tool asynchronously
                tool_func = mcp.tools[tool_name]
                try:
                    # Send progress update
                    await sse_connections[session_id].put({
                        "type": "progress",
                        "message": f"Executing {tool_name}...",
                        "request_id": request_id
                    })
                    
                    # Execute the tool
                    result = await tool_func.func(**arguments)
                    
                    # Format result for MCP
                    content = []
                    if isinstance(result, str):
                        content.append({"type": "text", "text": result})
                    elif isinstance(result, dict):
                        content.append({"type": "text", "text": json.dumps(result, indent=2)})
                    else:
                        content.append({"type": "text", "text": str(result)})
                    
                    # Send result via SSE
                    await sse_connections[session_id].put({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": content}
                    })
                    
                    return {"status": "success", "message": "Tool executed, result sent via SSE"}
                    
                except Exception as e:
                    logger.error(f"SSE Tool execution error: {str(e)}")
                    await sse_connections[session_id].put({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    })
                    return {"status": "error", "message": str(e)}
            
            else:
                await sse_connections[session_id].put({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Method not found",
                        "data": f"Unknown method: {method}"
                    }
                })
                return {"status": "error", "message": "Method not found"}
                
        except Exception as e:
            logger.error(f"SSE message processing error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/sse")
    async def list_sse_connections():
        """List active SSE connections."""
        return {
            "active_connections": list(sse_connections.keys()),
            "connection_count": len(sse_connections)
        }
    
    logger.info("HTTP server configured for ChatGPT integration with JSON-RPC MCP endpoints and SSE streaming")
    
    # Run server
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    args = parse_args()
    
    # Version check
    if args.version:
        print(f"YouTrack MCP Server (Consolidated) v{APP_VERSION}")
        sys.exit(0)
    
    # Apply CLI configuration
    apply_cli_config(args)
    
    # Load configuration
    load_config()
    
    # Initialize API clients
    initialize_clients()
    
    logger.info(f"Starting YouTrack MCP Server (Consolidated) v{APP_VERSION}")
    logger.info("Using standard MCP Python SDK with FastMCP")
    
    if args.transport == "http":
        logger.info(f"HTTP mode: {args.host}:{args.port}")
        # Run HTTP server
        run_http_server(args.host, args.port)
    else:
        logger.info("STDIO mode: for Claude/MCP integration")
        # Run stdio server
        mcp.run()


if __name__ == "__main__":
    main()