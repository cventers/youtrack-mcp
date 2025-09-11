"""
Router for backward compatibility with legacy custom fields tools.

Maps deprecated tools to new implementations with deprecation warnings.
"""

import logging
from typing import Dict, Any, Callable, Optional
import json

logger = logging.getLogger(__name__)

# Track which deprecation warnings have been logged (one-time per process)
DEPRECATED_TOOLS_LOGGED = set()

# Router mappings from legacy tools to new implementations
ROUTER_MAPPINGS = {
    "projects.custom_fields": {
        "target_tool": "projects.schema",
        "deprecation_message": "projects.custom_fields() is deprecated. Use projects.schema() for comprehensive field schemas",
        "parameter_mapping": lambda project_id: {"project_id": project_id},
        "response_mapping": lambda response: response  # Pass through as-is
    },
    "issues.custom_fields.update_custom_fields": {
        "target_tool": "issues.patch",
        "deprecation_message": "issues.custom_fields.update_custom_fields() is deprecated. Use issues.patch() with fields{} parameter",
        "parameter_mapping": lambda issue_id, custom_fields: {
            "issue_id": issue_id,
            "fields": custom_fields
        },
        "response_mapping": lambda response: response  # Pass through as-is
    }
}


def log_deprecation_once(tool_name: str, message: str):
    """Log deprecation warning once per process for each tool."""
    if tool_name not in DEPRECATED_TOOLS_LOGGED:
        logger.warning(f"DEPRECATED TOOL: {message}")
        DEPRECATED_TOOLS_LOGGED.add(tool_name)


def create_router_wrapper(legacy_tool_name: str, target_tool_func: Callable) -> Callable:
    """
    Create a wrapper function that routes legacy tool calls to new implementations.

    Args:
        legacy_tool_name: Name of the deprecated tool
        target_tool_func: The new tool function to route to

    Returns:
        Wrapped function that handles routing and deprecation warnings
    """
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
            # Fallback to original kwargs if mapping fails
            new_kwargs = kwargs

        # Call the target tool
        try:
            result = await target_tool_func(**new_kwargs)

            # Apply response mapping if needed
            result = mapping["response_mapping"](result)

            # Add deprecation notice to response
            if isinstance(result, str):
                try:
                    result_data = json.loads(result)
                    result_data["_deprecation"] = {
                        "tool": legacy_tool_name,
                        "message": mapping["deprecation_message"],
                        "use_instead": mapping["target_tool"]
                    }
                    result = json.dumps(result_data)
                except (json.JSONDecodeError, TypeError):
                    # If response isn't JSON, add deprecation as text
                    result += f"\n\nDEPRECATED: {mapping['deprecation_message']}"

            return result

        except Exception as e:
            logger.exception(f"Error routing {legacy_tool_name} to {mapping['target_tool']}: {e}")
            # Return error response with deprecation info
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

    # Preserve function metadata
    router_wrapper.__name__ = f"router_{legacy_tool_name.replace('.', '_')}"
    router_wrapper.__doc__ = f"Router for deprecated tool {legacy_tool_name}"

    return router_wrapper


def get_legacy_tool_names() -> list[str]:
    """Get list of legacy tool names that should be routed."""
    return list(ROUTER_MAPPINGS.keys())


def is_legacy_tool(tool_name: str) -> bool:
    """Check if a tool name is a legacy tool that should be routed."""
    return tool_name in ROUTER_MAPPINGS


def get_target_tool_name(legacy_tool_name: str) -> Optional[str]:
    """Get the target tool name for a legacy tool."""
    mapping = ROUTER_MAPPINGS.get(legacy_tool_name)
    return mapping["target_tool"] if mapping else None


__all__ = [
    "create_router_wrapper",
    "get_legacy_tool_names",
    "is_legacy_tool",
    "get_target_tool_name",
    "ROUTER_MAPPINGS"
]