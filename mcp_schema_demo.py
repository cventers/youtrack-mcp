#!/usr/bin/env python3
"""
Demo of what the model sees when connecting to YouTrack MCP server.
Shows the MCP handshake, capabilities, and tool schemas that models receive.
"""
import json
import asyncio
from typing import Dict, Any, List

def simulate_mcp_handshake():
    """Simulate the MCP handshake process."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {},
                "logging": {}
            },
            "clientInfo": {
                "name": "Claude Code",
                "version": "1.0.0"
            }
        }
    }

def simulate_mcp_handshake_response():
    """Simulate the MCP server's handshake response."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                },
                "prompts": {
                    "listChanged": False
                },
                "logging": {}
            },
            "serverInfo": {
                "name": "YouTrack MCP",
                "version": "1.0.0",
                "description": "A Model Context Protocol server for JetBrains YouTrack"
            }
        }
    }

def simulate_tools_list_request():
    """Simulate tools/list request."""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }

def simulate_tools_list_response():
    """Simulate the complete tools/list response showing all available YouTrack tools."""
    return {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {
                    "name": "get_issue",
                    "description": "Get detailed information about a specific YouTrack issue.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "issue_id": {
                                "type": "string",
                                "description": "Issue ID (e.g., 'PROJECT-123' or 'issue-id')"
                            }
                        },
                        "required": ["issue_id"]
                    }
                },
                {
                    "name": "create_issue", 
                    "description": "Create a new issue in YouTrack. Returns created issue information with intelligent attribute suggestions for missing fields to help improve issue completeness and tracking.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project": {
                                "type": "string", 
                                "description": "Project key or ID"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Issue summary/title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Issue description (optional)"
                            }
                        },
                        "required": ["project", "summary"]
                    }
                },
                {
                    "name": "update_issue",
                    "description": "Update an existing YouTrack issue with new field values.",
                    "inputSchema": {
                        "type": "object", 
                        "properties": {
                            "issue_id": {
                                "type": "string",
                                "description": "Issue ID to update"
                            },
                            "summary": {
                                "type": "string",
                                "description": "New issue summary (optional)"
                            },
                            "description": {
                                "type": "string", 
                                "description": "New issue description (optional)"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Issue priority (e.g., 'Critical', 'High', 'Normal', 'Low')"
                            },
                            "type": {
                                "type": "string",
                                "description": "Issue type (e.g., 'Bug', 'Feature', 'Task', 'Epic')"
                            },
                            "component": {
                                "type": "string",
                                "description": "Component or subsystem affected"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "User login or ID to assign the issue to"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Array of tags to categorize the issue"
                            }
                        },
                        "required": ["issue_id"]
                    }
                },
                {
                    "name": "search_issues",
                    "description": "Search for issues using YouTrack Query Language (YQL). Supports complex queries with filters, date ranges, custom fields, and logical operators.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "YouTrack search query using YQL syntax (e.g., 'project: MYPROJ state: Open priority: Critical', 'created: {Last week}', 'assignee: john.doe')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "advanced_search_issues",
                    "description": "Perform advanced issue searches with sophisticated filtering, sorting, and analytics. Supports natural language queries, date range searches, field-specific filters, and result analytics.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query - can be natural language, YQL syntax, or keyword-based"
                            },
                            "projects": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Limit search to specific projects"
                            },
                            "assignees": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "Filter by assignees"
                            },
                            "states": {
                                "type": "array",
                                "items": {"type": "string"}, 
                                "description": "Filter by issue states"
                            },
                            "priorities": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by priorities"
                            },
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "string", "description": "Start date (YYYY-MM-DD or relative like '1 week ago')"},
                                    "end": {"type": "string", "description": "End date (YYYY-MM-DD or relative like 'today')"},
                                    "field": {"type": "string", "description": "Date field to filter on", "default": "created"}
                                }
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "Field to sort by",
                                "default": "updated"
                            },
                            "sort_order": {
                                "type": "string", 
                                "enum": ["asc", "desc"],
                                "default": "desc"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 20
                            },
                            "include_analytics": {
                                "type": "boolean",
                                "description": "Include search result analytics",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "get_projects",
                    "description": "Get list of available YouTrack projects.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of projects to return",
                                "default": 50
                            }
                        }
                    }
                },
                {
                    "name": "create_project",
                    "description": "Create a new project in YouTrack.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Project name"
                            },
                            "short_name": {
                                "type": "string", 
                                "description": "Project key/short name (e.g., 'PROJ')"
                            },
                            "description": {
                                "type": "string",
                                "description": "Project description (optional)"
                            }
                        },
                        "required": ["name", "short_name"]
                    }
                },
                {
                    "name": "get_users",
                    "description": "Get list of YouTrack users.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of users to return",
                                "default": 50
                            }
                        }
                    }
                },
                {
                    "name": "search_users",
                    "description": "Search for YouTrack users by name or login.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (name or login)"
                            },
                            "limit": {
                                "type": "integer", 
                                "description": "Maximum number of results",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "link_issues",
                    "description": "Create a link relationship between two YouTrack issues.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "source_issue": {
                                "type": "string",
                                "description": "Source issue ID"
                            },
                            "target_issue": {
                                "type": "string",
                                "description": "Target issue ID"
                            },
                            "link_type": {
                                "type": "string",
                                "description": "Type of link (e.g., 'depends on', 'blocks', 'relates to', 'duplicates')"
                            }
                        },
                        "required": ["source_issue", "target_issue", "link_type"]
                    }
                },
                {
                    "name": "add_comment",
                    "description": "Add a comment to a YouTrack issue.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "issue_id": {
                                "type": "string",
                                "description": "Issue ID to comment on"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment text"
                            }
                        },
                        "required": ["issue_id", "comment"]
                    }
                }
            ]
        }
    }

def format_tool_for_display(tool: Dict[str, Any]) -> str:
    """Format a tool schema for readable display."""
    schema = tool["inputSchema"]
    props = schema.get("properties", {})
    required = schema.get("required", [])
    
    params = []
    for prop_name, prop_info in props.items():
        prop_type = prop_info.get("type", "unknown")
        prop_desc = prop_info.get("description", "")
        is_required = prop_name in required
        
        if prop_type == "array":
            items_type = prop_info.get("items", {}).get("type", "unknown")
            prop_type = f"array<{items_type}>"
        elif prop_type == "object":
            prop_type = "object"
        
        required_marker = " (required)" if is_required else " (optional)"
        params.append(f"    {prop_name}: {prop_type}{required_marker}")
        if prop_desc:
            params.append(f"      → {prop_desc}")
    
    return f"""
{tool['name']}
{'-' * len(tool['name'])}
Description: {tool['description']}

Parameters:
{chr(10).join(params) if params else '    (no parameters)'}
"""

def print_demo():
    """Print the complete MCP connection demo."""
    print("=" * 100)
    print("DEMO: What Models See When Connecting to YouTrack MCP Server")
    print("=" * 100)
    
    print("\n🤝 STEP 1: MCP Handshake")
    print("-" * 50)
    print("Model sends initialize request:")
    print(json.dumps(simulate_mcp_handshake(), indent=2))
    
    print("\nServer responds with capabilities:")
    print(json.dumps(simulate_mcp_handshake_response(), indent=2))
    
    print("\n🔧 STEP 2: Tool Discovery")
    print("-" * 50)
    print("Model requests available tools:")
    print(json.dumps(simulate_tools_list_request(), indent=2))
    
    print("\nServer responds with complete tool catalog:")
    response = simulate_tools_list_response()
    print(f"Found {len(response['result']['tools'])} available tools")
    
    print("\n📋 STEP 3: Available Tools (What the Model Learns)")
    print("-" * 50)
    
    tools = response['result']['tools']
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {format_tool_for_display(tool)}")
    
    print("\n🎯 STEP 4: Key Capabilities the Model Discovers")
    print("-" * 50)
    
    print("""
✅ ISSUE MANAGEMENT:
   • create_issue - With intelligent attribute suggestions
   • update_issue - Comprehensive field updates  
   • get_issue - Detailed issue information
   • link_issues - Create relationships between issues
   • add_comment - Add comments and updates

🔍 SEARCH & DISCOVERY:
   • search_issues - YQL-powered search
   • advanced_search_issues - Natural language + analytics
   • get_projects - Project discovery
   • get_users/search_users - User management

🤖 INTELLIGENT FEATURES:
   • Attribute suggestions with contextual analysis
   • Ready-to-use follow-up MCP calls
   • Educational prompts and reasoning
   • Configurable suggestion system
""")
    
    print("\n📝 STEP 5: Example Tool Usage the Model Learns")
    print("-" * 50)
    
    print("""
Basic Issue Creation:
  create_issue(project="WEBAPP", summary="Login button broken", description="...")

Advanced Search:
  advanced_search_issues(
    query="critical bugs assigned to me", 
    date_range={"start": "1 week ago", "field": "created"},
    include_analytics=true
  )

Issue Updates:
  update_issue(issue_id="WEBAPP-123", priority="Critical", type="Bug")

Complex Queries:
  search_issues(query="project: WEBAPP state: Open priority: {Critical High}")
""")
    
    print("\n🎭 STEP 6: What Makes This MCP Special")
    print("-" * 50)
    
    print("""
🧠 INTELLIGENT SUGGESTIONS:
   • create_issue returns not just the created issue, but also:
     - Contextual attribute suggestions based on content analysis
     - Ready-to-execute MCP calls for improvements
     - Educational reasoning for better learning

🔗 AGENTIC WORKFLOWS:
   • Models can chain tool calls based on suggestions
   • Implements the Suggest → Execute → Amend pattern
   • Provides exact MCP calls with real issue IDs

📊 ADVANCED SEARCH:
   • Natural language query processing
   • Result analytics and insights
   • Flexible filtering and sorting
   • Date range handling with relative dates

⚙️ CONFIGURATION DRIVEN:
   • YAML-based suggestion configuration
   • Project-specific overrides
   • Environment variable controls
   • Multiple response formats
""")
    
    print("\n" + "=" * 100)
    print("RESULT: Models can effectively create, manage, and enhance YouTrack issues")
    print("with intelligent guidance and contextual suggestions!")
    print("=" * 100)

if __name__ == "__main__":
    print_demo()