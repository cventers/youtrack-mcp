from youtrack_mcp.tools.issues_tools import IssuesTools
from youtrack_mcp.tools.projects_tools import ProjectsTools
from youtrack_mcp.tools.users_tools import UsersTools
from youtrack_mcp.tools.search_tools import SearchTools
from youtrack_mcp.tools.resources_tools import ResourcesTools
from youtrack_mcp.tools.ai_tools import AITools
from typing import Dict, Any


class MCPServer:
    """YouTrack MCP Server - Minimal Core Tools."""

    def __init__(self):
        """Initialize the MCP server with core tools."""
        self.issues_tools = IssuesTools()
        self.projects_tools = ProjectsTools()
        self.users_tools = UsersTools()
        self.search_tools = SearchTools()
        self.resources_tools = ResourcesTools()
        self.ai_tools = AITools()

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
