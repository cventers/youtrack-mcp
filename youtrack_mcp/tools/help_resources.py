"""
Help Resources for YouTrack MCP Tools.

Provides detailed documentation and examples for all tools.
This system supports the help:// URI scheme for accessing tool documentation.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class HelpResources:
    """Help resource system for YouTrack MCP tools."""

    def __init__(self):
        """Initialize help resources."""
        self.resources = self._build_help_resources()

    def get_resource(self, uri: str) -> Optional[str]:
        """Get help resource by URI."""
        try:
            if not uri.startswith("help://"):
                return None

            # Remove help:// prefix
            resource_path = uri[7:]  # Remove "help://"

            # Navigate to the resource
            parts = resource_path.split("/")
            current = self.resources

            for part in parts:
                if part in current:
                    current = current[part]
                else:
                    return None

            # Return the resource content
            if isinstance(current, dict):
                return json.dumps(current, indent=2)
            elif isinstance(current, str):
                return current
            else:
                return str(current)

        except Exception as e:
            logger.exception(f"Error getting help resource: {uri}")
            return None

    def _build_help_resources(self) -> Dict[str, Any]:
        """Build the help resources structure."""
        return {
            "issues": {
                "get": {
                    "title": "Get Issue Details",
                    "description": "Retrieve detailed information about a specific issue with optional expansions",
                    "syntax": "issues.get(issue_id='PROJECT-123', include=['customFields', 'comments'])",
                    "parameters": {
                        "issue_id": {
                            "type": "string",
                            "description": "Issue ID or readable ID (e.g., 'PROJECT-123')",
                            "required": True
                        },
                        "include": {
                            "type": "list",
                            "description": "List of expansions to include",
                            "options": ["customFields", "comments", "attachments", "links"],
                            "required": False
                        }
                    },
                    "examples": [
                        "issues.get('DEMO-123')",
                        "issues.get('PROJECT-456', include=['customFields', 'comments'])",
                        "issues.get('BUG-789', include=['attachments'])"
                    ],
                    "notes": [
                        "Use human-readable IDs (PROJECT-123) instead of internal IDs",
                        "Expansions provide additional data but may impact performance",
                        "Custom fields are project-specific"
                    ]
                },
                "create": {
                    "title": "Create New Issue",
                    "description": "Create a new issue in a YouTrack project",
                    "syntax": "issues.create(project='DEMO', summary='Bug title', description='Details...')",
                    "parameters": {
                        "project": {
                            "type": "string",
                            "description": "Project ID or short name",
                            "required": True
                        },
                        "summary": {
                            "type": "string",
                            "description": "Issue title/summary",
                            "required": True
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed issue description",
                            "required": False
                        }
                    },
                    "examples": [
                        "issues.create('DEMO', 'Login button not working')",
                        "issues.create('PROJECT', 'Feature request', 'Please add dark mode support')"
                    ],
                    "notes": [
                        "Project must exist and be accessible",
                        "Summary is required, description is optional",
                        "Returns the created issue data"
                    ]
                },
                "patch": {
                    "title": "Update Issue",
                    "description": "Update issue properties using simple fields or typed operations",
                    "syntax": "issues.patch(issue_id='PROJECT-123', fields={'summary': 'New title'})",
                    "parameters": {
                        "issue_id": {
                            "type": "string",
                            "description": "Issue ID or readable ID",
                            "required": True
                        },
                        "fields": {
                            "type": "dict",
                            "description": "Simple field updates (summary, description)",
                            "required": False
                        },
                        "ops": {
                            "type": "list",
                            "description": "Typed operations for complex updates",
                            "required": False
                        }
                    },
                    "examples": [
                        "issues.patch('DEMO-123', fields={'summary': 'Updated title'})",
                        "issues.patch('PROJECT-456', fields={'description': 'More details'})",
                        "issues.patch('BUG-789', ops=[{'op': 'set', 'field': 'state', 'value': 'Fixed'}])"
                    ],
                    "notes": [
                        "Either 'fields' or 'ops' parameter must be provided",
                        "Typed operations support complex field updates",
                        "Returns updated issue data"
                    ]
                }
            },
            "projects": {
                "list": {
                    "title": "List Projects",
                    "description": "Get list of accessible projects",
                    "syntax": "projects.list(include_archived=False)",
                    "parameters": {
                        "include_archived": {
                            "type": "boolean",
                            "description": "Whether to include archived projects",
                            "default": False,
                            "required": False
                        }
                    },
                    "examples": [
                        "projects.list()",
                        "projects.list(include_archived=True)"
                    ],
                    "notes": [
                        "Returns only projects the user can access",
                        "Archived projects are excluded by default"
                    ]
                },
                "get": {
                    "title": "Get Project Details",
                    "description": "Get detailed project information with expansions",
                    "syntax": "projects.get(project_id='DEMO', include=['customFields', 'issues'])",
                    "parameters": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or short name",
                            "required": True
                        },
                        "include": {
                            "type": "list",
                            "description": "List of expansions to include",
                            "options": ["customFields", "issues"],
                            "required": False
                        }
                    },
                    "examples": [
                        "projects.get('DEMO')",
                        "projects.get('PROJECT', include=['customFields'])"
                    ],
                    "notes": [
                        "Use project short name (key) not display name",
                        "Expansions provide additional data"
                    ]
                },
                "patch": {
                    "title": "Update Project",
                    "description": "Update project properties using typed operations",
                    "syntax": "projects.patch(project_id='DEMO', ops=[{'op': 'set', 'field': 'name', 'value': 'New Name'}])",
                    "parameters": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or short name",
                            "required": True
                        },
                        "ops": {
                            "type": "list",
                            "description": "List of typed operations",
                            "required": True
                        }
                    },
                    "examples": [
                        "projects.patch('DEMO', ops=[{'op': 'set', 'field': 'name', 'value': 'Demo Project'}])",
                        "projects.patch('PROJECT', ops=[{'op': 'set', 'field': 'description', 'value': 'Updated description'}])"
                    ],
                    "notes": [
                        "Operations list is required",
                        "Supports set, add, remove operations",
                        "Returns updated project data"
                    ]
                },
                "create": {
                    "title": "Create Project",
                    "description": "Create a new YouTrack project",
                    "syntax": "projects.create(name='Demo Project', short_name='DEMO', lead_id='admin')",
                    "parameters": {
                        "name": {
                            "type": "string",
                            "description": "Project display name",
                            "required": True
                        },
                        "short_name": {
                            "type": "string",
                            "description": "Project short name/key",
                            "required": True
                        },
                        "lead_id": {
                            "type": "string",
                            "description": "Project leader user ID",
                            "required": True
                        }
                    },
                    "examples": [
                        "projects.create('Demo Project', 'DEMO', 'admin')",
                        "projects.create('My Project', 'MYPROJ', 'user123')"
                    ],
                    "notes": [
                        "Short name must be unique",
                        "Lead user must exist",
                        "Returns created project data"
                    ]
                }
            },
            "search": {
                "query": {
                    "title": "Execute YQL Query",
                    "description": "Execute explicit YouTrack Query Language queries",
                    "syntax": "search.query(query='project: DEMO #Unresolved', limit=10, sort_by='created', sort_order='desc')",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "YouTrack Query Language string",
                            "required": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                            "required": False
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Field to sort by",
                            "required": False
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Sort order ('asc' or 'desc')",
                            "required": False
                        }
                    },
                    "examples": [
                        "search.query('project: DEMO')",
                        "search.query('assignee: me #Unresolved', limit=5)",
                        "search.query('created: -7d .. *', sort_by='created', sort_order='desc')"
                    ],
                    "notes": [
                        "Uses YouTrack Query Language (YQL) syntax",
                        "Supports all YQL operators and functions",
                        "Results are sorted by relevance by default"
                    ]
                },
                "autosearch": {
                    "title": "Natural Language Search",
                    "description": "Translate natural language to YQL and execute search",
                    "syntax": "search.autosearch(natural_language_query='bugs assigned to me this week')",
                    "parameters": {
                        "natural_language_query": {
                            "type": "string",
                            "description": "Natural language search description",
                            "required": True
                        },
                        "project_context": {
                            "type": "string",
                            "description": "Optional project context for better translation",
                            "required": False
                        }
                    },
                    "examples": [
                        "search.autosearch('bugs assigned to me')",
                        "search.autosearch('high priority issues this week', 'DEMO')",
                        "search.autosearch('unresolved tasks')"
                    ],
                    "notes": [
                        "Uses AI to translate natural language to YQL",
                        "Returns confidence score and translation details",
                        "Falls back to text search if translation fails"
                    ]
                }
            },
            "users": {
                "search": {
                    "title": "Search Users",
                    "description": "Find users by name or login",
                    "syntax": "users.search(query='admin', limit=10)",
                    "parameters": {
                        "query": {
                            "type": "string",
                            "description": "Search term for user name or login",
                            "required": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                            "required": False
                        }
                    },
                    "examples": [
                        "users.search('admin')",
                        "users.search('john', limit=5)",
                        "users.search('developer')"
                    ],
                    "notes": [
                        "Searches both user names and login names",
                        "Returns user details including ID and login",
                        "Case-insensitive search"
                    ]
                }
            },
            "ai": {
                "plan": {
                    "title": "Plan Intent Analysis",
                    "description": "Analyze user intent and create execution plan",
                    "syntax": "ai.plan(intent='Create a bug report for login issues', context={'project': 'DEMO'})",
                    "parameters": {
                        "intent": {
                            "type": "string",
                            "description": "Natural language description of desired action",
                            "required": True
                        },
                        "context": {
                            "type": "dict",
                            "description": "Optional context dictionary",
                            "required": False
                        }
                    },
                    "examples": [
                        "ai.plan('Create a bug report')",
                        "ai.plan('Find unresolved issues', {'project': 'DEMO'})",
                        "ai.plan('Update issue status to fixed')"
                    ],
                    "notes": [
                        "Analyzes intent to suggest appropriate tools",
                        "Always requires confirmation before execution",
                        "Provides execution plan with explanations"
                    ]
                }
            },
            "resources": {
                "read": {
                    "title": "Read Resources",
                    "description": "Read YouTrack resources using URI format",
                    "syntax": "resources.read(uri='youtrack://issues/DEMO-123')",
                    "parameters": {
                        "uri": {
                            "type": "string",
                            "description": "YouTrack URI in youtrack:// format",
                            "required": True
                        }
                    },
                    "examples": [
                        "resources.read('youtrack://issues/DEMO-123')",
                        "resources.read('youtrack://projects/DEMO')",
                        "resources.read('youtrack://users/admin')",
                        "resources.read('youtrack://projects')"
                    ],
                    "notes": [
                        "Supports issues, projects, and users",
                        "URI format: youtrack://resource_type/resource_id",
                        "List resources by omitting ID: youtrack://issues"
                    ]
                }
            },
            "yql": {
                "guide": {
                    "title": "YouTrack Query Language Guide",
                    "description": "Complete guide to YouTrack Query Language (YQL)",
                    "syntax": "Field operators: field: value, field: value1 .. value2",
                    "operators": {
                        "basic": ["field: value", "field: value1 .. value2", "field: *"],
                        "logical": ["and", "or", "not"],
                        "comparison": ["=", "!=", ">", "<", ">=", "<="],
                        "text": ["text: search_term", "~field: pattern"]
                    },
                    "examples": [
                        "project: DEMO",
                        "assignee: me",
                        "state: Open",
                        "priority: Critical",
                        "created: 2025-01-01 .. *",
                        "text: login issue",
                        "project: DEMO and state: Open"
                    ],
                    "fields": [
                        "project", "assignee", "reporter", "state", "priority",
                        "type", "created", "updated", "resolved", "due",
                        "text", "comment", "attachment"
                    ],
                    "notes": [
                        "Field names are case-sensitive",
                        "Use curly braces for custom fields: {Custom Field}: value",
                        "Date formats: YYYY-MM-DD, relative dates: -7d, {Today}",
                        "Wildcards: * for any value, ? for single character"
                    ]
                }
            }
        }


# Global help resources instance
help_resources = HelpResources()


def get_help_resource(uri: str) -> Optional[str]:
    """Get help resource by URI."""
    return help_resources.get_resource(uri)