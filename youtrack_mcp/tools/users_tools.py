"""
Core Users Tools for YouTrack MCP - Minimal Implementation.

Implements the 1 core user tool:
- users.search: User resolution
"""

from youtrack_mcp.logging import get_logger
from typing import Any, Dict, Optional

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.users import UsersClient

logger = get_logger(__name__)


class UsersTools:
    """Minimal users tools with clean interfaces."""

    def __init__(self):
        """Initialize core users tools."""
        self.client = YouTrackClient()
        self.users_api = UsersClient(self.client)

    async def search(self, query: str, limit: int = 10) -> dict:
        """
        Resolve users by name/login.

        FORMAT: users.search(query="admin", limit=5)

        Args:
            query: Search term for user name or login
            limit: Maximum number of results to return

        Returns:
            JSON with list of matching users
        """
        try:
            users = await self.users_api.search_users(query, limit)

            # Convert to dicts for JSON response
            result = []
            for user in users:
                if hasattr(user, "model_dump"):
                    result.append(user.model_dump())
                else:
                    result.append(user)

            return {
                "users": result,
                "count": len(result),
                "query": query,
                "limit": limit
            }

        except Exception as e:
            logger.exception(f"Error searching users with query: {query}")
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "query": query
            }

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get core users tool definitions."""
        return {
            "users.search": {
                "description": "Search for users by name",
                "function": self.search
            }
        }


__all__ = ["UsersTools"]