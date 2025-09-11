"""
JSON Schema definitions for YouTrack MCP tools.

This module defines strict JSON schemas for all MCP tools following the
canonical invocation pattern: {"tool_name": "name", "arguments": {...}}
"""

from typing import Dict, Any


# Base schema components
BASE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string"},
        "arguments": {"type": "object"}
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Issues tool schemas
ISSUES_GET_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["issues.get"]},
        "arguments": {
            "type": "object",
            "properties": {
                "issue_id": {"type": "string", "description": "Issue ID or readable ID (e.g., PROJECT-123)"},
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["customFields", "comments", "attachments", "links", "work_items", "history", "activities", "time_tracking"]},
                    "description": "List of expansions to include"
                }
            },
            "required": ["issue_id"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

ISSUES_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["issues.create"]},
        "arguments": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project ID or short name"},
                "summary": {"type": "string", "description": "Issue summary/title"},
                "description": {"type": "string", "description": "Optional issue description"},
                "custom_fields": {
                    "type": "object",
                    "description": "Optional dictionary of custom field names and values",
                    "additionalProperties": True
                }
            },
            "required": ["project", "summary"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

ISSUES_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["issues.patch"]},
        "arguments": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string", "description": "Issue ID to update"},
                        "fields": {
                            "type": "object",
                            "description": "Friendly field mapping",
                            "additionalProperties": True
                        }
                    },
                    "required": ["issue_id", "fields"],
                    "additionalProperties": False
                },
                {
                    "type": "object",
                    "properties": {
                        "issue_id": {"type": "string", "description": "Issue ID to update"},
                        "ops": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "op": {"type": "string", "enum": ["add", "remove", "replace"]},
                                    "path": {"type": "string", "pattern": "^/fields/"},
                                    "value": {}  # Any type for value
                                },
                                "required": ["op", "path"],
                                "additionalProperties": False
                            },
                            "description": "Typed patch operations"
                        }
                    },
                    "required": ["issue_id", "ops"],
                    "additionalProperties": False
                }
            ]
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Projects tool schemas
PROJECTS_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["projects.list"]},
        "arguments": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                "offset": {"type": "integer", "minimum": 0, "default": 0}
            },
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

PROJECTS_GET_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["projects.get"]},
        "arguments": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID or short name"},
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["schema", "versions", "builds", "subsystems", "assignees", "fields"]},
                    "description": "List of expansions to include"
                }
            },
            "required": ["project_id"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

PROJECTS_SCHEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["projects.schema"]},
        "arguments": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID or short name"},
                "field_name": {"type": "string", "description": "Optional specific field name to get schema for"}
            },
            "required": ["project_id"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

PROJECTS_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["projects.patch"]},
        "arguments": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Project ID to update"},
                "fields": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "leader": {"type": "string"}
                    },
                    "additionalProperties": False
                }
            },
            "required": ["project_id", "fields"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

PROJECTS_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["projects.create"]},
        "arguments": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "short_name": {"type": "string", "description": "Project short name/ID"},
                "description": {"type": "string", "description": "Optional project description"},
                "leader_id": {"type": "string", "description": "User ID of project leader"}
            },
            "required": ["name", "short_name", "leader_id"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Users tool schemas
USERS_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["users.search"]},
        "arguments": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (name, login, email)"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Search tool schemas
SEARCH_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["search.query"]},
        "arguments": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "YouTrack Query Language string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "sort_by": {"type": "string", "enum": ["created", "updated", "priority", "summary"]},
                "sort_order": {"type": "string", "enum": ["asc", "desc"]}
            },
            "required": ["query"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

SEARCH_AUTOSEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["search.autosearch"]},
        "arguments": {
            "type": "object",
            "properties": {
                "natural_language_query": {"type": "string", "description": "Natural language description of the search"},
                "project_context": {"type": "string", "description": "Optional project ID for context-aware translation"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                "confidence_floor": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.6},
                "strict_mode": {"type": "boolean", "default": True}
            },
            "required": ["natural_language_query"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# AI tool schemas
AI_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["ai.plan"]},
        "arguments": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "description": "Natural language description of the intended operation"}
            },
            "required": ["intent"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Resources tool schemas
RESOURCES_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string", "enum": ["resources.read"]},
        "arguments": {
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "MCP resource URI to read"}
            },
            "required": ["uri"],
            "additionalProperties": False
        }
    },
    "required": ["tool_name", "arguments"],
    "additionalProperties": False
}

# Master schema registry
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "issues.get": ISSUES_GET_SCHEMA,
    "issues.create": ISSUES_CREATE_SCHEMA,
    "issues.patch": ISSUES_PATCH_SCHEMA,
    "projects.list": PROJECTS_LIST_SCHEMA,
    "projects.get": PROJECTS_GET_SCHEMA,
    "projects.schema": PROJECTS_SCHEMA_SCHEMA,
    "projects.patch": PROJECTS_PATCH_SCHEMA,
    "projects.create": PROJECTS_CREATE_SCHEMA,
    "users.search": USERS_SEARCH_SCHEMA,
    "search.query": SEARCH_QUERY_SCHEMA,
    "search.autosearch": SEARCH_AUTOSEARCH_SCHEMA,
    "ai.plan": AI_PLAN_SCHEMA,
    "resources.read": RESOURCES_READ_SCHEMA,
}


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """
    Get the JSON schema for a specific tool.

    Args:
        tool_name: The name of the tool (e.g., "issues.get")

    Returns:
        JSON schema dictionary for the tool

    Raises:
        ValueError: If the tool schema is not found
    """
    if tool_name not in TOOL_SCHEMAS:
        available_tools = list(TOOL_SCHEMAS.keys())
        raise ValueError(f"Unknown tool '{tool_name}'. Available tools: {available_tools}")

    return TOOL_SCHEMAS[tool_name]


def validate_tool_call(tool_name: str, arguments: Dict[str, Any]) -> None:
    """
    Validate a tool call against its schema.

    Args:
        tool_name: The name of the tool
        arguments: The arguments dictionary

    Raises:
        ValueError: If validation fails
    """
    import jsonschema

    schema = get_tool_schema(tool_name)

    # Create the full call object for validation
    call_object = {
        "tool_name": tool_name,
        "arguments": arguments
    }

    try:
        jsonschema.validate(call_object, schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Tool call validation failed: {e.message}") from e
    except jsonschema.SchemaError as e:
        raise ValueError(f"Schema validation error: {e.message}") from e


__all__ = [
    "TOOL_SCHEMAS",
    "get_tool_schema",
    "validate_tool_call",
    "ISSUES_GET_SCHEMA",
    "ISSUES_CREATE_SCHEMA",
    "ISSUES_PATCH_SCHEMA",
    "PROJECTS_LIST_SCHEMA",
    "PROJECTS_GET_SCHEMA",
    "PROJECTS_SCHEMA_SCHEMA",
    "PROJECTS_PATCH_SCHEMA",
    "PROJECTS_CREATE_SCHEMA",
    "USERS_SEARCH_SCHEMA",
    "SEARCH_QUERY_SCHEMA",
    "SEARCH_AUTOSEARCH_SCHEMA",
    "AI_PLAN_SCHEMA",
    "RESOURCES_READ_SCHEMA",
]