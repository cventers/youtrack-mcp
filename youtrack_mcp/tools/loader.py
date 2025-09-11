"""
Tool loader module for YouTrack MCP.
Loads all tools from the youtrack_mcp.tools package.
"""

import importlib
import inspect
import logging
from typing import Dict, Callable, Any
from collections import defaultdict

from youtrack_mcp.mcp_wrappers import create_bound_tool

# Set up logger
logger = logging.getLogger(__name__)

# Router mappings for backward compatibility
ROUTER_MAPPINGS = {
    "projects.custom_fields": {
        "target_tool": "projects.schema",
        "deprecation_message": "projects.custom_fields() is deprecated. Use projects.schema() for comprehensive field schemas",
        "parameter_mapping": lambda project_id: {"project_id": project_id},
        "response_mapping": lambda response: response
    },
    "issues.custom_fields.update_custom_fields": {
        "target_tool": "issues.patch",
        "deprecation_message": "issues.custom_fields.update_custom_fields() is deprecated. Use issues.patch() with fields{} parameter",
        "parameter_mapping": lambda issue_id, custom_fields: {
            "issue_id": issue_id,
            "fields": custom_fields
        },
        "response_mapping": lambda response: response
    }
}

# Track which deprecation warnings have been logged (one-time per process)
DEPRECATED_TOOLS_LOGGED = set()

def log_deprecation_once(tool_name: str, message: str):
    """Log deprecation warning once per process for each tool."""
    if tool_name not in DEPRECATED_TOOLS_LOGGED:
        logger.warning(f"DEPRECATED TOOL: {message}")
        DEPRECATED_TOOLS_LOGGED.add(tool_name)

def create_router_wrapper(legacy_tool_name: str, target_tool_func: Callable) -> Callable:
    """Create a wrapper function that routes legacy tool calls to new implementations."""
    mapping = ROUTER_MAPPINGS.get(legacy_tool_name)
    if not mapping:
        raise ValueError(f"No router mapping found for legacy tool: {legacy_tool_name}")

    async def router_wrapper(*args, **kwargs):
        # Log deprecation warning (once per process)
        log_deprecation_once(legacy_tool_name, mapping["deprecation_message"])

        # Map parameters from legacy format to new format
        try:
            new_kwargs = mapping["parameter_mapping"](*args, **kwargs)
        except Exception as e:
            logger.error(f"Parameter mapping failed for {legacy_tool_name}: {e}")
            new_kwargs = kwargs

        # Call the target tool
        try:
            result = await target_tool_func(**new_kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error routing {legacy_tool_name} to {mapping['target_tool']}: {e}")
            import json
            error_response = {
                "error": str(e),
                "error_type": type(e).__name__,
                "_deprecation": {
                    "tool": legacy_tool_name,
                    "message": mapping["deprecation_message"],
                    "use_instead": mapping["target_tool"]
                }
            }
            return json.dumps(error_response)

    router_wrapper.__name__ = f"router_{legacy_tool_name.replace('.', '_')}"
    router_wrapper.__doc__ = f"Router for deprecated tool {legacy_tool_name}"
    return router_wrapper

# Define priority classes for resolving duplicates
TOOL_PRIORITY = {
    "IssueTools": {
        "create_issue": 100,  # Give highest priority to IssueTools.create_issue
    },
    "ProjectTools": {
        "get_custom_fields": 100,  # Highest priority for this tool in ProjectTools
    },
    "SearchTools": {
        "get_custom_fields": 50,  # Lower priority in SearchTools
        "search_with_custom_fields": 100,  # High priority for search_with_custom_fields in SearchTools
    },
    "ResourcesTools": {
        "get_issue": 200,  # Higher priority for resource-based tools
        "get_project": 200,
        "get_project_issues": 200,
        "get_user": 200,
        "get_all_issues": 200,
        "get_all_projects": 200,
        "get_all_users": 200,
        "get_issue_comments": 200,
        "search_issues": 200,
    },
}


def load_all_tools() -> Dict[str, Callable]:
    """
    Load all tools from the youtrack_mcp.tools package.

    This function loads the 12 core tools for the minimal tool surface refactor.
    The core tools provide a lossless but much more efficient interface.

    Available core tools:
    - issues.get, issues.create, issues.patch (from CoreIssuesTools)
    - projects.list, projects.get, projects.patch, projects.create (from CoreProjectsTools)
    - users.search (from CoreUsersTools)
    - search.query, search.autosearch (from CoreSearchTools)
    - ai.plan (from CoreAITools)
    - resources.read (from CoreResourcesTools)

    Returns:
        Dict[str, Callable]: Dictionary mapping tool names to their functions
    """
    tools = {}

    # Import core tool modules for minimal surface
    from youtrack_mcp.tools.core_issues import CoreIssuesTools
    from youtrack_mcp.tools.core_projects import CoreProjectsTools
    from youtrack_mcp.tools.core_users import CoreUsersTools
    from youtrack_mcp.tools.core_search import CoreSearchTools
    from youtrack_mcp.tools.core_resources import CoreResourcesTools
    from youtrack_mcp.tools.core_ai import CoreAITools
    # DateTimeTools is not a class, it's a module with functions
    # We'll handle datetime tools separately if needed

    # Initialize core tool classes
    tool_classes = [
        CoreIssuesTools(),
        CoreProjectsTools(),
        CoreUsersTools(),
        CoreSearchTools(),
        CoreResourcesTools(),
        CoreAITools(),
    ]

    # Load tools from core classes - simplified for minimal surface
    for tool_class in tool_classes:
        class_name = tool_class.__class__.__name__
        
        # Drop "Core" prefix from class names for cleaner naming
        display_name = class_name.replace("Core", "").replace("Tools", "Tools")
        if display_name.endswith("ToolsTools"):
            display_name = display_name[:-5]  # Remove duplicate "Tools"

        # Get tool definitions from core classes
        if hasattr(tool_class, "get_tool_definitions"):
            tool_definitions = tool_class.get_tool_definitions()

            for tool_name, definition in tool_definitions.items():
                # Get the actual function from the definition
                if "function" in definition:
                    # Use the function directly from the definition
                    bound_tool = definition["function"]
                else:
                    # Fallback to old behavior (shouldn't happen with proper definitions)
                    # Replace dots with underscores for method lookup
                    method_name = tool_name.replace(".", "_")
                    bound_tool = create_bound_tool(tool_class, method_name)

                # Register with full name (e.g., "issues.get")
                tools[tool_name] = bound_tool
                logger.debug(f"Registered tool '{tool_name}' from {display_name}")

    # Add legacy tools with router wrappers for backward compatibility
    for legacy_tool_name, mapping in ROUTER_MAPPINGS.items():
        target_tool_name = mapping["target_tool"]
        if target_tool_name in tools:
            target_tool_func = tools[target_tool_name]
            router_wrapper = create_router_wrapper(legacy_tool_name, target_tool_func)
            tools[legacy_tool_name] = router_wrapper
            logger.debug(f"Added router wrapper for legacy tool '{legacy_tool_name}' -> '{target_tool_name}'")

    # Log total number of tools loaded (including legacy routers)
    logger.info(f"Loader registered {len(tools)} tools (minimal surface + legacy routers)")

    return tools


def _get_tools_from_class(tool_class: Any) -> Dict[str, Callable]:
    """
    Get all tools from a tool class.

    This function extracts all public methods from a tool class,
    excluding special methods (starting with '__'), internal methods,
    and Mock-specific methods when testing.

    Args:
        tool_class: Tool class instance

    Returns:
        Dictionary mapping method names to callables
    """
    result = {}

    # Mock-specific methods to exclude (for testing)
    mock_methods = {
        "assert_any_call",
        "assert_called",
        "assert_called_once",
        "assert_called_once_with",
        "assert_called_with",
        "assert_has_calls",
        "assert_not_called",
        "attach_mock",
        "configure_mock",
        "mock_add_spec",
        "reset_mock",
        "return_value",
        "side_effect",
        "call_args",
        "call_args_list",
        "call_count",
        "called",
        "method_calls",
    }

    # Get all class methods
    for name in dir(tool_class):
        # Skip special and internal methods
        if name.startswith("__") or name in ["close", "get_tool_definitions"]:
            continue

        # Skip Mock-specific methods when testing
        if name in mock_methods:
            continue

        # Get the attribute
        attr = getattr(tool_class, name)

        # Only include if it's a callable
        if callable(attr):
            result[name] = attr

    return result
