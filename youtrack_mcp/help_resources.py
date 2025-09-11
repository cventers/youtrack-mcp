"""
Help resources for YouTrack MCP tools.

This module provides detailed examples and documentation for tools
that would be too verbose for the main tool descriptions.
"""

from typing import Dict, Any


# Tool examples and detailed documentation
TOOL_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "issues.get": {
        "description": "Get issue with optional expansions",
        "examples": [
            {
                "description": "Get basic issue information",
                "call": {
                    "tool_name": "issues.get",
                    "arguments": {
                        "issue_id": "DEMO-123"
                    }
                },
                "response": "Returns basic issue fields: id, summary, description, status, assignee, etc."
            },
            {
                "description": "Get issue with custom fields",
                "call": {
                    "tool_name": "issues.get",
                    "arguments": {
                        "issue_id": "DEMO-123",
                        "include": ["customFields"]
                    }
                },
                "response": "Returns issue with all custom field values included"
            },
            {
                "description": "Get issue with full expansions",
                "call": {
                    "tool_name": "issues.get",
                    "arguments": {
                        "issue_id": "DEMO-123",
                        "include": ["customFields", "comments", "attachments", "links", "work_items"]
                    }
                },
                "response": "Returns issue with all available expansions"
            }
        ],
        "notes": [
            "Use include array to specify which expansions you need",
            "Available expansions: customFields, comments, attachments, links, work_items, history, activities, time_tracking",
            "Expansions are optional and can be combined as needed"
        ]
    },

    "issues.create": {
        "description": "Create new issue in project",
        "examples": [
            {
                "description": "Create basic issue",
                "call": {
                    "tool_name": "issues.create",
                    "arguments": {
                        "project": "DEMO",
                        "summary": "Bug report: Login button not working"
                    }
                },
                "response": "Creates issue with minimal required fields"
            },
            {
                "description": "Create issue with description and custom fields",
                "call": {
                    "tool_name": "issues.create",
                    "arguments": {
                        "project": "DEMO",
                        "summary": "Feature request: Dark mode support",
                        "description": "Users have requested dark mode theme support for better accessibility",
                        "custom_fields": {
                            "Type": "Feature",
                            "Priority": "Medium",
                            "Component": "UI"
                        }
                    }
                },
                "response": "Creates issue with description and custom field values"
            }
        ],
        "notes": [
            "Use projects.custom_fields() first to see required custom fields for the project",
            "Custom field names must match exactly (case-sensitive)",
            "Description is optional but recommended for clarity"
        ]
    },

    "issues.patch": {
        "description": "Update issue fields with schema-aware coercion",
        "examples": [
            {
                "description": "Update using friendly fields format",
                "call": {
                    "tool_name": "issues.patch",
                    "arguments": {
                        "issue_id": "DEMO-123",
                        "fields": {
                            "summary": "Updated issue title",
                            "description": "Updated description"
                        }
                    }
                },
                "response": "Updates summary and description fields"
            },
            {
                "description": "Update using patch operations",
                "call": {
                    "tool_name": "issues.patch",
                    "arguments": {
                        "issue_id": "DEMO-123",
                        "ops": [
                            {"op": "replace", "path": "/fields/summary", "value": "New title"},
                            {"op": "replace", "path": "/fields/Priority", "value": "High"}
                        ]
                    }
                },
                "response": "Applies patch operations to update fields"
            },
            {
                "description": "Update custom fields",
                "call": {
                    "tool_name": "issues.patch",
                    "arguments": {
                        "issue_id": "DEMO-123",
                        "fields": {
                            "Type": "Bug",
                            "Priority": "Critical",
                            "Assignee": "john.doe"
                        }
                    }
                },
                "response": "Updates custom fields with schema-aware validation"
            }
        ],
        "notes": [
            "Use either 'fields' (friendly format) OR 'ops' (patch format), not both",
            "Custom field names must match project schema exactly",
            "System fields (summary, description) use simple names",
            "Custom fields use their display names (e.g., 'Priority', 'Type')"
        ]
    },

    "projects.list": {
        "description": "List all available projects",
        "examples": [
            {
                "description": "List all projects",
                "call": {
                    "tool_name": "projects.list",
                    "arguments": {}
                },
                "response": "Returns all projects with basic metadata"
            },
            {
                "description": "List projects with pagination",
                "call": {
                    "tool_name": "projects.list",
                    "arguments": {
                        "limit": 10,
                        "offset": 20
                    }
                },
                "response": "Returns 10 projects starting from the 21st project"
            }
        ],
        "notes": [
            "Use limit and offset for pagination",
            "Default limit is 50 projects",
            "Projects are returned in alphabetical order"
        ]
    },

    "projects.get": {
        "description": "Get project details with optional expansions",
        "examples": [
            {
                "description": "Get basic project info",
                "call": {
                    "tool_name": "projects.get",
                    "arguments": {
                        "project_id": "DEMO"
                    }
                },
                "response": "Returns project metadata: name, description, lead, etc."
            },
            {
                "description": "Get project with schema",
                "call": {
                    "tool_name": "projects.get",
                    "arguments": {
                        "project_id": "DEMO",
                        "include": ["schema"]
                    }
                },
                "response": "Returns project with custom field schema information"
            }
        ],
        "notes": [
            "Use include array for expansions: schema, versions, builds, subsystems, assignees, fields",
            "Schema expansion shows all custom fields available in the project",
            "Fields expansion shows field configurations and validation rules"
        ]
    },

    "search.query": {
        "description": "Execute YouTrack Query Language",
        "examples": [
            {
                "description": "Search for unresolved issues",
                "call": {
                    "tool_name": "search.query",
                    "arguments": {
                        "query": "project: DEMO #Unresolved"
                    }
                },
                "response": "Returns all unresolved issues in DEMO project"
            },
            {
                "description": "Search with sorting and limit",
                "call": {
                    "tool_name": "search.query",
                    "arguments": {
                        "query": "assignee: me",
                        "limit": 5,
                        "sort_by": "updated",
                        "sort_order": "desc"
                    }
                },
                "response": "Returns 5 most recently updated issues assigned to current user"
            }
        ],
        "notes": [
            "Use YouTrack Query Language (YQL) syntax",
            "Common queries: 'project: NAME', '#State', 'assignee: user'",
            "Sort options: created, updated, priority, summary",
            "Default limit is 10, maximum is 100"
        ]
    },

    "search.autosearch": {
        "description": "Translate natural language to YQL",
        "examples": [
            {
                "description": "Natural language search",
                "call": {
                    "tool_name": "search.autosearch",
                    "arguments": {
                        "natural_language_query": "bugs assigned to me this week"
                    }
                },
                "response": "Translates to YQL and executes search"
            },
            {
                "description": "Context-aware search",
                "call": {
                    "tool_name": "search.autosearch",
                    "arguments": {
                        "natural_language_query": "high priority features",
                        "project_context": "DEMO"
                    }
                },
                "response": "Uses project context for more accurate translation"
            }
        ],
        "notes": [
            "Supports natural language like 'bugs this week', 'my tasks', 'high priority'",
            "Returns both the generated YQL query and search results",
            "Includes confidence score and reasoning for the translation",
            "Use project_context for better accuracy in specific projects"
        ]
    }
}


def get_tool_help(tool_name: str) -> Dict[str, Any]:
    """
    Get detailed help information for a tool.

    Args:
        tool_name: The name of the tool (e.g., "issues.get")

    Returns:
        Dictionary with examples and documentation
    """
    return TOOL_EXAMPLES.get(tool_name, {
        "description": f"Tool {tool_name}",
        "examples": [],
        "notes": ["No detailed help available for this tool"]
    })


def get_all_tool_help() -> Dict[str, Dict[str, Any]]:
    """
    Get help information for all tools.

    Returns:
        Dictionary mapping tool names to their help information
    """
    return TOOL_EXAMPLES


# Migration guide for old vs new calling patterns
MIGRATION_GUIDE = """
# Tool Calls Migration Guide

## Old Pattern (Deprecated)
```python
# Flexible args/kwargs with repair
result = issues.get("DEMO-123", include=["customFields"])
result = issues.create(project="DEMO", summary="Bug", custom_fields={"Type": "Bug"})
```

## New Pattern (Recommended)
```python
# Strict JSON schema
result = call_tool({
    "tool_name": "issues.get",
    "arguments": {
        "issue_id": "DEMO-123",
        "include": ["customFields"]
    }
})

result = call_tool({
    "tool_name": "issues.create",
    "arguments": {
        "project": "DEMO",
        "summary": "Bug",
        "custom_fields": {"Type": "Bug"}
    }
})
```

## Key Changes
1. **Single argument object**: All parameters go in `arguments` object
2. **No positional args**: Everything is named parameters
3. **Strict validation**: No automatic repair or type coercion
4. **Clear schemas**: Each tool has a defined JSON schema
5. **No parameter name mapping**: Use exact field names from schema

## Benefits
- **Predictable**: Same input format always produces same behavior
- **Debuggable**: Clear validation errors instead of silent repairs
- **Portable**: Works with any MCP client without custom wrappers
- **Maintainable**: No complex repair logic to maintain
"""


__all__ = [
    "TOOL_EXAMPLES",
    "get_tool_help",
    "get_all_tool_help",
    "MIGRATION_GUIDE"
]