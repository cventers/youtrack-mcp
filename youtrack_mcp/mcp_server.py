from youtrack_mcp.tools.core_issues import CoreIssuesTools
from youtrack_mcp.tools.core_projects import CoreProjectsTools
from youtrack_mcp.tools.core_users import CoreUsersTools
from youtrack_mcp.tools.core_search import CoreSearchTools
from youtrack_mcp.tools.core_resources import CoreResourcesTools
from youtrack_mcp.tools.core_ai import CoreAITools
from typing import Dict, Any


class MCPServer:
    """YouTrack MCP Server - Minimal Core Tools."""

    def __init__(self):
        """Initialize the MCP server with core tools."""
        self.issues_tools = CoreIssuesTools()
        self.projects_tools = CoreProjectsTools()
        self.users_tools = CoreUsersTools()
        self.search_tools = CoreSearchTools()
        self.resources_tools = CoreResourcesTools()
        self.ai_tools = CoreAITools()

    def get_all_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all core tool definitions."""

        all_tools = {}

        # Add core issues tools
        issues_tool_definitions = self.issues_tools.get_tool_definitions()
        for tool_name, tool_config in issues_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                    "parameter_descriptions": tool_config.get("parameter_descriptions", {}),
                }

        # Add core projects tools
        projects_tool_definitions = self.projects_tools.get_tool_definitions()
        for tool_name, tool_config in projects_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                }

        # Add core users tools
        users_tool_definitions = self.users_tools.get_tool_definitions()
        for tool_name, tool_config in users_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                }

        # Add core search tools
        search_tool_definitions = self.search_tools.get_tool_definitions()
        for tool_name, tool_config in search_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                }

        # Add core resources tools
        resources_tool_definitions = self.resources_tools.get_tool_definitions()
        for tool_name, tool_config in resources_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                }

        # Add core AI tools
        ai_tool_definitions = self.ai_tools.get_tool_definitions()
        for tool_name, tool_config in ai_tool_definitions.items():
            function = tool_config.get("function")
            if function:
                all_tools[tool_name] = {
                    "description": tool_config["description"],
                    "function": function,
                }

        return all_tools
