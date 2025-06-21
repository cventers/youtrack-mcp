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
from datetime import datetime, timedelta
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
from youtrack_mcp.utils import convert_timestamp_to_iso8601, add_iso8601_timestamps, generate_ticket_suggestions, normalize_issue_ids, validate_issue_id
from youtrack_mcp.ai_processor import initialize_ai_processor, get_ai_processor
from youtrack_mcp.llm_client import create_llm_client_from_config

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
ai_processor = None


def load_config():
    """Load configuration from environment variables."""
    logger.info("Loading configuration from environment variables")
    
    # Load from environment variables
    if os.getenv("YOUTRACK_URL"):
        Config.YOUTRACK_URL = os.getenv("YOUTRACK_URL")
    
    if os.getenv("YOUTRACK_TOKEN_FILE"):
        token_file = os.getenv("YOUTRACK_TOKEN_FILE")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                Config.YOUTRACK_API_TOKEN = f.read().strip()
            logger.info(f"Loaded API token from file: {token_file}")
    elif os.getenv("YOUTRACK_TOKEN"):
        Config.YOUTRACK_API_TOKEN = os.getenv("YOUTRACK_TOKEN")
    
    Config.YOUTRACK_CLOUD = os.getenv("YOUTRACK_CLOUD", "true").lower() == "true"
    Config.VERIFY_SSL = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower() == "true"
    
    # Validate configuration
    Config.validate()
    
    logger.info(f"Configured for YouTrack at: {Config.YOUTRACK_URL}")
    logger.info(f"SSL verification: {'Enabled' if Config.VERIFY_SSL else 'Disabled'}")


def initialize_clients():
    """Initialize API clients, LLM client, and AI processor."""
    global youtrack_client, issues_api, projects_api, users_api, search_api, advanced_search, ai_processor
    
    youtrack_client = YouTrackClient()
    issues_api = IssuesClient(youtrack_client)
    projects_api = ProjectsClient(youtrack_client)
    users_api = UsersClient(youtrack_client)
    search_api = SearchClient(youtrack_client)
    advanced_search = AdvancedSearchEngine(youtrack_client, enable_cache=True, enable_analytics=True)
    
    # Initialize LLM client from environment configuration
    llm_client = create_llm_client_from_config()
    
    # Initialize AI processor with LLM client  
    enable_ai = Config.AI_ENABLED
    max_memory = Config.AI_MAX_MEMORY_MB
    ai_processor = initialize_ai_processor(enable_ai=enable_ai, max_memory_mb=max_memory, llm_client=llm_client)
    
    logger.info("API clients, advanced search engine, LLM client, and AI processor initialized")
    logger.info(f"AI features: {'enabled' if enable_ai else 'disabled'} (max memory: {max_memory}MB)")
    
    # Log LLM configuration status
    if llm_client:
        provider_count = len([c for c in llm_client.configs if c.enabled])
        logger.info(f"LLM client initialized with {provider_count} provider(s)")
        for i, config in enumerate(llm_client.configs):
            if config.enabled:
                model_info = config.model_name or "default"
                logger.info(f"  {i+1}. {config.provider.value}: {model_info}")
    else:
        logger.info("LLM client not configured - using rule-based AI only")


def filter_tools_by_config():
    """Filter and remove disabled tools from the MCP server based on configuration."""
    enabled_tools = set(Config.get_enabled_tools())
    disabled_tools = Config.get_disabled_tools()
    
    # Get all currently registered tools
    all_registered_tools = list(mcp._tool_manager._tools.keys())
    
    # Remove disabled tools
    for tool_name in all_registered_tools:
        if tool_name not in enabled_tools:
            if tool_name in mcp._tool_manager._tools:
                del mcp._tool_manager._tools[tool_name]
                logger.info(f"Disabled tool: {tool_name}")
    
    # Log configuration summary
    tool_summary = Config.get_tool_config_summary()
    logger.info(f"Tool filtering applied: {tool_summary['enabled_count']} enabled, {tool_summary['disabled_count']} disabled")
    
    if disabled_tools:
        logger.info(f"Disabled tools: {', '.join(disabled_tools)}")
    
    # Log enabled categories
    enabled_categories = [cat for cat, enabled in Config.TOOLS_ENABLED.items() if enabled]
    logger.info(f"Enabled categories: {', '.join(enabled_categories)}")


# Issue Tools
@mcp.tool()
async def get_issue(issue_id: str) -> Dict[str, Any]:
    """
    Get information about a specific issue.
    
    Args:
        issue_id: The issue ID or readable ID (e.g., PROJECT-123)
        
    Returns:
        Issue information with 'id' field containing the human-readable ID (e.g., PAY-557).
        Internal database IDs are in '_internal_id' field and should NOT be used for references.
        Always use the 'id' field value when referencing issues in other operations.
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),assignee(id,login,name),customFields(id,name,value(id,name,$type))"
        raw_issue = await youtrack_client.get(f"issues/{issue_id}?fields={fields}")
        
        # Enhance with ISO8601 timestamps and normalize IDs
        raw_issue = add_iso8601_timestamps(raw_issue)
        raw_issue = normalize_issue_ids(raw_issue)
        
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
        Raw issue data with normalized IDs. The 'id' field contains human-readable ID (e.g., PAY-557).
        Internal database IDs are in '_internal_id' field and should NOT be used for references.
    """
    try:
        if not fields:
            # Default comprehensive fields
            fields = "id,idReadable,summary,description,created,updated,resolved,project(id,name,shortName),reporter(id,login,name,email),assignee(id,login,name,email),updater(id,login,name),customFields(id,name,value(id,name,$type,text,presentation)),attachments(id,name,size,url),comments(id,text,created,author(id,login,name)),links(id,direction,linkType(id,name),issues(id,idReadable,summary))"
        
        result = await youtrack_client.get(f"issues/{issue_id}?fields={fields}")
        # Normalize IDs to prefer human-readable format
        result = normalize_issue_ids(result)
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
        Created issue information with attribute suggestions for missing fields
    """
    try:
        issue_data = {
            "project": {"shortName": project},
            "summary": summary
        }
        
        if description:
            issue_data["description"] = description
        
        # Create the issue
        result = await youtrack_client.post("issues", data=issue_data)
        
        # Generate suggestions for missing attributes
        issue_id = result.get('idReadable', result.get('id'))
        suggestions = generate_ticket_suggestions(issue_data, project, issue_id)
        
        # Enhance the response with suggestions
        if suggestions.get('suggestions_available', False):
            result['attribute_suggestions'] = suggestions
            
            # Add a helpful note for the model
            result['mcp_guidance'] = {
                'message': 'The issue was created successfully. Consider the suggested improvements below.',
                'next_steps': 'You can use the suggested MCP calls to enhance this issue with missing attributes.',
                'last_created_issue': issue_id
            }
        
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
        List of matching issues with normalized IDs. Each issue's 'id' field contains 
        human-readable ID (e.g., PAY-557). Internal database IDs are in '_internal_id' field 
        and should NOT be used for references. Always use the 'id' field when referencing issues.
    """
    try:
        fields = "id,idReadable,summary,description,created,updated,project(id,name,shortName),reporter(id,login,name),customFields(id,name,value(id,name,$type))"
        params = {
            "query": query,
            "fields": fields,
            "$top": limit
        }
        
        results = await youtrack_client.get("issues", params=params)
        
        # Enhance with ISO8601 timestamps and normalize IDs
        results = add_iso8601_timestamps(results)
        results = normalize_issue_ids(results)
        
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
        Dictionary with results and metadata. Each issue's 'id' field contains 
        human-readable ID (e.g., PAY-557). Internal database IDs are in '_internal_id' field 
        and should NOT be used for references. Always use the 'id' field when referencing issues.
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
        
        # Enhance with ISO8601 timestamps and normalize IDs
        results = add_iso8601_timestamps(results)
        results = normalize_issue_ids(results)
        
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
async def get_comments(project_id: str = None, task_id: str = None, cursor: str = None, limit: int = 50) -> Dict[str, Any]:
    """
    Get comments for a task or project.
    
    Args:
        project_id: Project ID to get comments for
        task_id: Task ID to get comments for
        cursor: Pagination cursor
        limit: Max number of comments to return (default 50)
        
    Returns:
        List of comments
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
                
            result = await youtrack_client.get(f"issues/{task_id}/comments", params=params)
            return result if isinstance(result, list) else []
            
        elif project_id:
            # Get comments for a project (all issues in the project)
            # Note: YouTrack doesn't have a direct "project comments" endpoint,
            # so we'll get recent issues with comments from the project
            fields = "id,idReadable,summary,comments(id,text,created,author(id,login,name))"
            params = {
                "query": f"project: {project_id} has: comments",
                "fields": fields,
                "$top": limit or 50
            }
            
            issues = await youtrack_client.get("issues", params=params)
            
            # Extract comments from all issues
            all_comments = []
            for issue in (issues if isinstance(issues, list) else []):
                issue_comments = issue.get("comments", [])
                for comment in issue_comments:
                    comment["issue_id"] = issue.get("idReadable", issue.get("id"))
                    comment["issue_summary"] = issue.get("summary", "")
                    all_comments.append(comment)
            
            # Sort by created date (most recent first)
            all_comments.sort(key=lambda x: x.get("created", 0), reverse=True)
            
            return all_comments
            
        else:
            return {"error": "Either project_id or task_id must be provided"}
            
    except Exception as e:
        logger.exception("Error getting comments")
        return {"error": str(e)}


@mcp.tool()
async def get_task_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    Get comments from a task in YouTrack.
    
    Args:
        task_id: Task/issue ID
        
    Returns:
        List of comments for the task
    """
    try:
        fields = "id,text,created,author(id,login,name),updated,updater(id,login,name)"
        params = {"fields": fields}
        
        result = await youtrack_client.get(f"issues/{task_id}/comments", params=params)
        return result if isinstance(result, list) else []
        
    except Exception as e:
        logger.exception(f"Error getting comments for task {task_id}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_project_comments(project_id: str) -> List[Dict[str, Any]]:
    """
    Get comments from a project in YouTrack.
    
    Args:
        project_id: Project ID
        
    Returns:
        List of comments from all issues in the project
    """
    try:
        # Get recent issues with comments from the project
        fields = "id,idReadable,summary,comments(id,text,created,author(id,login,name))"
        params = {
            "query": f"project: {project_id} has: comments",
            "fields": fields,
            "$top": 100  # Get up to 100 issues with comments
        }
        
        issues = await youtrack_client.get("issues", params=params)
        
        # Extract comments from all issues
        all_comments = []
        for issue in (issues if isinstance(issues, list) else []):
            issue_comments = issue.get("comments", [])
            for comment in issue_comments:
                comment["issue_id"] = issue.get("idReadable", issue.get("id"))
                comment["issue_summary"] = issue.get("summary", "")
                all_comments.append(comment)
        
        # Sort by created date (most recent first)
        all_comments.sort(key=lambda x: x.get("created", 0), reverse=True)
        
        return all_comments
        
    except Exception as e:
        logger.exception(f"Error getting comments for project {project_id}")
        return [{"error": str(e)}]


@mcp.tool()
async def get_comment(comment_id: str) -> Dict[str, Any]:
    """
    Get a comment from a task or project in YouTrack.
    
    Args:
        comment_id: Comment ID
        
    Returns:
        Comment information
    """
    try:
        # YouTrack doesn't have a direct comment endpoint by ID, so we need to work around this
        # This would require knowing which issue the comment belongs to
        return {"error": "Direct comment retrieval by ID is not supported. Use get_task_comments instead."}
        
    except Exception as e:
        logger.exception(f"Error getting comment {comment_id}")
        return {"error": str(e)}


@mcp.tool()
async def update_comment(comment_id: str, content: str) -> Dict[str, Any]:
    """
    Update a comment in YouTrack.
    
    Args:
        comment_id: The ID of the comment to update
        content: The new content for the comment
        
    Returns:
        Update result
    """
    try:
        # YouTrack API for updating comments requires the issue ID and comment ID
        # Since we only have comment ID, this is a limitation
        return {"error": "Comment updates require both issue ID and comment ID. Use issue-specific comment endpoints."}
        
    except Exception as e:
        logger.exception(f"Error updating comment {comment_id}")
        return {"error": str(e)}


@mcp.tool()
async def delete_comment(comment_id: str) -> Dict[str, Any]:
    """
    Delete a comment from a task in YouTrack.
    
    Args:
        comment_id: Comment ID
        
    Returns:
        Deletion result
    """
    try:
        # YouTrack API for deleting comments requires the issue ID and comment ID
        # Since we only have comment ID, this is a limitation
        return {"error": "Comment deletion requires both issue ID and comment ID. Use issue-specific comment endpoints."}
        
    except Exception as e:
        logger.exception(f"Error deleting comment {comment_id}")
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


@mcp.tool()
async def validate_issue_id_format(issue_id: str) -> Dict[str, Any]:
    """
    Validate and classify an issue ID format to help ensure correct usage.
    
    Args:
        issue_id: Issue ID to validate (e.g., PAY-557, PROJECT-123, or 82-12318)
        
    Returns:
        Validation results with recommendations for proper ID usage.
        Encourages use of human-readable IDs (PROJECT-123) over internal IDs (82-12318).
    """
    try:
        validation_result = validate_issue_id(issue_id)
        
        # Add additional context for the AI
        if validation_result['type'] == 'human_readable':
            validation_result['ai_guidance'] = f"✅ Excellent! '{issue_id}' is a human-readable ID. Always prefer this format when referencing issues."
        elif validation_result['type'] == 'internal':
            validation_result['ai_guidance'] = f"⚠️  '{issue_id}' appears to be an internal database ID. These work but human-readable IDs (like PROJECT-123) are preferred for clarity."
            validation_result['alternative_suggestion'] = "Try to find the corresponding human-readable ID (e.g., PAY-557) for this issue using get_issue() and use that in future references."
        else:
            validation_result['ai_guidance'] = f"'{issue_id}' has an unrecognized format. Verify this is a valid YouTrack issue identifier."
        
        return validation_result
        
    except Exception as e:
        logger.exception(f"Error validating issue ID {issue_id}")
        return {
            'valid': False,
            'type': 'error',
            'message': f'Error validating issue ID: {str(e)}',
            'recommendation': 'Ensure the issue ID is a valid string'
        }


@mcp.tool()
async def smart_search_issues(natural_query: str, project_context: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    Search for issues using natural language with AI-powered query translation.
    
    Args:
        natural_query: Natural language query (e.g., "Show me critical bugs from last week")
        project_context: Optional project context for more accurate translation
        limit: Maximum number of results (default: 10)
        
    Returns:
        Search results with translation details and issue list. Issues use human-readable IDs.
    """
    try:
        ai = get_ai_processor()
        
        # Get project schemas for better translation
        project_schemas = None
        if project_context:
            try:
                projects = await youtrack_client.get("projects")
                project_schemas = [p for p in projects if p.get('shortName') == project_context or p.get('name') == project_context]
            except Exception:
                logger.warning(f"Could not fetch project schema for {project_context}")
        
        # Translate natural language to YQL
        translation = await ai.translate_natural_query(
            natural_query=natural_query,
            context_hints={'project': project_context} if project_context else None,
            project_schemas=project_schemas
        )
        
        # Execute the translated query
        if translation.confidence > 0.3:  # Only execute if we have reasonable confidence
            try:
                results = await search_issues(translation.yql_query, limit)
                
                return {
                    'translation': {
                        'natural_query': translation.original_input,
                        'yql_query': translation.yql_query,
                        'confidence': translation.confidence,
                        'reasoning': translation.reasoning,
                        'detected_entities': translation.detected_entities
                    },
                    'results': results,
                    'suggestions': translation.suggestions,
                    'ai_enhanced': True
                }
            except Exception as search_error:
                # If search fails, enhance the error with AI
                enhanced_error = await ai.enhance_error_message(
                    error=search_error,
                    context={
                        'operation': 'smart_search',
                        'natural_query': natural_query,
                        'translated_query': translation.yql_query,
                        'project': project_context
                    }
                )
                
                return {
                    'translation': {
                        'natural_query': translation.original_input,
                        'yql_query': translation.yql_query,
                        'confidence': translation.confidence,
                        'reasoning': translation.reasoning
                    },
                    'error': 'Search execution failed',
                    'ai_enhanced_error': {
                        'explanation': enhanced_error.enhanced_explanation,
                        'fix_suggestion': enhanced_error.fix_suggestion,
                        'example_correction': enhanced_error.example_correction,
                        'learning_tip': enhanced_error.learning_tip
                    },
                    'ai_enhanced': True
                }
        else:
            return {
                'translation': {
                    'natural_query': translation.original_input,
                    'yql_query': translation.yql_query,
                    'confidence': translation.confidence,
                    'reasoning': translation.reasoning
                },
                'warning': 'Low confidence translation - please refine your query',
                'suggestions': translation.suggestions,
                'ai_enhanced': True
            }
        
    except Exception as e:
        logger.exception(f"Error in smart search: {e}")
        return {
            'error': f"Smart search failed: {str(e)}",
            'fallback_suggestion': f"Try using regular search_issues() with YouTrack query language",
            'natural_query': natural_query,
            'ai_enhanced': False
        }


@mcp.tool()
async def analyze_user_activity_patterns(user_login: str, days_back: int = 30, analysis_types: List[str] = None) -> Dict[str, Any]:
    """
    Analyze user activity patterns with AI-powered insights.
    
    Args:
        user_login: User login name to analyze
        days_back: Number of days to look back (default: 30)
        analysis_types: Types of analysis ['productivity_trends', 'collaboration_patterns', 'focus_areas']
        
    Returns:
        AI-powered activity analysis with insights and recommendations.
    """
    try:
        ai = get_ai_processor()
        
        if analysis_types is None:
            analysis_types = ['productivity_trends', 'collaboration_patterns', 'focus_areas']
        
        # Get user activity data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Search for user activity
        query = f"updated: {start_date.strftime('%Y-%m-%d')} .. {end_date.strftime('%Y-%m-%d')} assignee: {user_login}"
        
        try:
            activity_issues = await search_issues(query, limit=500)
            
            # Convert to activity records for AI analysis
            activity_data = []
            for issue in activity_issues:
                activity_data.append({
                    'date': issue.get('updated_iso8601', issue.get('updated', '')),
                    'project': issue.get('project', {}).get('shortName', 'Unknown'),
                    'assignee': user_login,
                    'type': 'issue_update',
                    'issue_id': issue.get('id'),
                    'summary': issue.get('summary', '')
                })
            
            # Run AI analysis
            patterns = await ai.analyze_activity_patterns(activity_data, analysis_types)
            
            return {
                'user': user_login,
                'analysis_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'total_activities': len(activity_data),
                'ai_insights': {
                    'patterns': patterns.patterns,
                    'insights': patterns.insights,
                    'recommendations': patterns.recommendations,
                    'productivity_score': patterns.productivity_score,
                    'trends': patterns.trends
                },
                'analysis_types': analysis_types,
                'ai_enhanced': True
            }
            
        except Exception as search_error:
            logger.error(f"Error fetching activity data: {search_error}")
            return {
                'error': f"Could not fetch activity data: {str(search_error)}",
                'user': user_login,
                'ai_enhanced': False
            }
        
    except Exception as e:
        logger.exception(f"Error in activity pattern analysis: {e}")
        return {
            'error': f"Pattern analysis failed: {str(e)}",
            'user': user_login,
            'ai_enhanced': False
        }


@mcp.tool()
async def get_tool_configuration() -> Dict[str, Any]:
    """
    Get the current tool configuration showing enabled/disabled tools and categories.
    
    Returns:
        Current tool configuration with categories, individual overrides, and summaries
    """
    try:
        return Config.get_tool_config_summary()
    except Exception as e:
        logger.exception("Error getting tool configuration")
        return {"error": str(e)}


@mcp.tool()
async def set_tool_enabled(tool_name: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable a specific tool dynamically.
    
    Args:
        tool_name: Name of the tool to enable/disable
        enabled: True to enable, False to disable
        
    Returns:
        Result of the configuration change
    """
    try:
        # Check if tool exists in any category
        tool_categories = Config.get_tool_categories()
        tool_exists = any(tool_name in tools for tools in tool_categories.values())
        
        if not tool_exists:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": [tool for tools in tool_categories.values() for tool in tools]
            }
        
        # Set tool configuration
        Config.set_tool_enabled(tool_name, enabled)
        
        # Apply filtering to MCP server
        filter_tools_by_config()
        
        return {
            "status": "success",
            "message": f"Tool '{tool_name}' {'enabled' if enabled else 'disabled'}",
            "tool_name": tool_name,
            "enabled": enabled,
            "current_config": Config.get_tool_config_summary()
        }
        
    except Exception as e:
        logger.exception(f"Error setting tool enabled: {tool_name}")
        return {"error": str(e)}


@mcp.tool()
async def set_category_enabled(category: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable an entire tool category dynamically.
    
    Args:
        category: Name of the category to enable/disable 
        enabled: True to enable, False to disable
        
    Returns:
        Result of the configuration change
    """
    try:
        # Check if category exists
        if category not in Config.TOOLS_ENABLED:
            return {
                "error": f"Unknown category: {category}",
                "available_categories": list(Config.TOOLS_ENABLED.keys())
            }
        
        # Set category configuration
        Config.set_category_enabled(category, enabled)
        
        # Apply filtering to MCP server
        filter_tools_by_config()
        
        tool_categories = Config.get_tool_categories()
        affected_tools = tool_categories.get(category, [])
        
        return {
            "status": "success",
            "message": f"Category '{category}' {'enabled' if enabled else 'disabled'}",
            "category": category,
            "enabled": enabled,
            "affected_tools": affected_tools,
            "current_config": Config.get_tool_config_summary()
        }
        
    except Exception as e:
        logger.exception(f"Error setting category enabled: {category}")
        return {"error": str(e)}


@mcp.tool()
async def list_tool_categories() -> Dict[str, Any]:
    """
    List all available tool categories and their tools.
    
    Returns:
        Dictionary mapping categories to their tools with current enabled status
    """
    try:
        tool_categories = Config.get_tool_categories()
        enabled_tools = set(Config.get_enabled_tools())
        
        result = {}
        for category, tools in tool_categories.items():
            result[category] = {
                "enabled": Config.TOOLS_ENABLED.get(category, True),
                "tools": tools,
                "enabled_tools": [tool for tool in tools if tool in enabled_tools],
                "disabled_tools": [tool for tool in tools if tool not in enabled_tools]
            }
        
        return {
            "categories": result,
            "summary": Config.get_tool_config_summary()
        }
        
    except Exception as e:
        logger.exception("Error listing tool categories")
        return {"error": str(e)}


@mcp.tool()
async def enhance_error_context(error_message: str, operation_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Enhance error messages with AI-powered context and suggestions.
    
    Args:
        error_message: The error message to enhance
        operation_context: Context about the failed operation
        
    Returns:
        Enhanced error explanation with fix suggestions and learning tips.
    """
    try:
        ai = get_ai_processor()
        
        if operation_context is None:
            operation_context = {}
        
        # Create a mock exception for the AI processor
        class ContextError(Exception):
            def __init__(self, message):
                self.message = message
                super().__init__(message)
            
            def __str__(self):
                return self.message
        
        mock_error = ContextError(error_message)
        
        # Get AI enhancement
        enhancement = await ai.enhance_error_message(
            error=mock_error,
            context=operation_context
        )
        
        return {
            'original_error': error_message,
            'enhanced_explanation': enhancement.enhanced_explanation,
            'fix_suggestion': enhancement.fix_suggestion,
            'example_correction': enhancement.example_correction,
            'learning_tip': enhancement.learning_tip,
            'confidence': enhancement.confidence,
            'ai_enhanced': True
        }
        
    except Exception as e:
        logger.exception(f"Error in error enhancement: {e}")
        return {
            'original_error': error_message,
            'enhancement_error': f"Could not enhance error: {str(e)}",
            'ai_enhanced': False
        }


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
        Config.YOUTRACK_URL = args.youtrack_url
    
    if args.youtrack_token:
        Config.YOUTRACK_API_TOKEN = args.youtrack_token
    
    if args.youtrack_token_file and os.path.exists(args.youtrack_token_file):
        with open(args.youtrack_token_file, 'r') as f:
            Config.YOUTRACK_API_TOKEN = f.read().strip()
        logger.info(f"Loaded API token from file: {args.youtrack_token_file}")
    
    if args.verify_ssl is not None:
        Config.VERIFY_SSL = args.verify_ssl


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
        # Use FastMCP's built-in list_tools method
        try:
            tools_response = await mcp.list_tools()
            # Extract tools from the MCP response format
            tools_info = []
            # Handle both list and object responses
            tools_list = tools_response.tools if hasattr(tools_response, 'tools') else tools_response
            for tool in tools_list:
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description or "No description available",
                    "input_schema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else (tool.inputSchema or {})
                })
            return {"tools": tools_info}
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            # Fallback: return basic tool names
            return {"tools": [
                {"name": "get_issue", "description": "Get YouTrack issue by ID"},
                {"name": "search_issues", "description": "Search YouTrack issues"},
                {"name": "create_issue", "description": "Create new YouTrack issue"},
                {"name": "update_issue", "description": "Update YouTrack issue"},
                {"name": "get_projects", "description": "Get YouTrack projects"},
                {"name": "get_users", "description": "Get YouTrack users"}
            ]}
    
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
                # Return list of available tools using FastMCP's list_tools method
                try:
                    tools_response = await mcp.list_tools()
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": tools_response
                    }
                except Exception as e:
                    logger.error(f"Error listing tools: {e}")
                    return {
                        "jsonrpc": "2.0", 
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error listing tools",
                            "data": str(e)
                        }
                    }
            
            elif method == "tools/call":
                # Call a specific tool
                try:
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if not tool_name:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": "Invalid params: missing tool name"
                            }
                        }
                    
                    result = await mcp.call_tool(tool_name, arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                except Exception as e:
                    logger.error(f"Error calling tool {tool_name}: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution error: {str(e)}"
                        }
                    }
            
            elif method == "initialize":
                # MCP initialization
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "YouTrack MCP",
                            "version": APP_VERSION
                        }
                    }
                }
            
            # Legacy tools handling (keeping for compatibility)
            elif False:  # Disabled old code block
                tools_list = []
                for tool_name, tool_func in {}.items():
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
                
                if tool_name not in mcp._tool_manager._tools:
                    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
                
                # Call the tool function
                tool_func = mcp._tool_manager._tools[tool_name]
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
                
                if not tool_name or tool_name not in mcp._tool_manager._tools:
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
                tool_func = mcp._tool_manager._tools[tool_name]
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
    
    # Filter tools based on configuration
    filter_tools_by_config()
    
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