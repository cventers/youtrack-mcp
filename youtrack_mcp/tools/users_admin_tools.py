"""
Core Users Admin Tools for YouTrack MCP - Administrative Operations.

Implements admin-level user operations:
- users.create: Create new users (admin only)
- users.patch: Update user properties (admin only)
- users.deactivate: Deactivate/reactivate users (admin only)
"""

import json
import logging
from typing import Any, Dict, Optional

from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.api.users import UsersClient
from youtrack_mcp.mcp_wrappers import async_wrapper
from youtrack_mcp.utils import format_json_response

logger = logging.getLogger(__name__)


class UsersAdminTools:
    """Administrative user tools with permission gating."""

    def __init__(self):
        """Initialize admin user tools."""
        self.client = YouTrackClient()
        self.users_api = UsersClient(self.client)

    async def _check_admin_permissions(self) -> bool:
        """Check if user has admin permissions for user operations."""
        try:
            # Check if user can access admin user endpoints
            # This is a basic check - in production you'd want more sophisticated permission checking
            response = await self.client.get("admin/users", params={"$top": 1})
            return response is not None
        except Exception as e:
            logger.warning(f"Admin permission check failed: {e}")
            return False

    @async_wrapper
    async def create(self, login: str, name: str, email: Optional[str] = None) -> str:
        """
        Create a new user (admin only).

        FORMAT: users.create(login="jdoe", name="John Doe", email="john.doe@company.com")

        Args:
            login: User login name
            name: Full display name
            email: Optional email address

        Returns:
            JSON with created user data
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for user creation",
                    "login": login
                })

            # Create the user
            user_data = {
                "login": login,
                "name": name
            }
            if email:
                user_data["email"] = email

            result = await self.client.post("admin/users", json=user_data)

            return format_json_response({
                "success": True,
                "user": result,
                "login": login,
                "name": name,
                "email": email
            })

        except Exception as e:
            logger.exception(f"Error creating user {login}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "login": login
            })

    @async_wrapper
    async def patch(self, user_id: str, updates: Dict[str, Any]) -> str:
        """
        Update user properties (admin only).

        FORMAT: users.patch(user_id="user123", updates={"name": "New Name", "email": "new@email.com"})

        Args:
            user_id: User ID or login
            updates: Dictionary of properties to update

        Returns:
            JSON with updated user data
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for user updates",
                    "user_id": user_id
                })

            # Update the user
            result = await self.client.put(f"admin/users/{user_id}", json_data=updates)

            return format_json_response({
                "success": True,
                "user": result,
                "user_id": user_id,
                "updates": updates
            })

        except Exception as e:
            logger.exception(f"Error updating user {user_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": user_id
            })

    @async_wrapper
    async def deactivate(self, user_id: str, deactivate: bool = True) -> str:
        """
        Deactivate or reactivate a user (admin only).

        FORMAT: users.deactivate(user_id="user123", deactivate=True)

        Args:
            user_id: User ID or login
            deactivate: If True, deactivate; if False, reactivate

        Returns:
            JSON with deactivation status
        """
        try:
            # Check admin permissions
            if not await self._check_admin_permissions():
                return format_json_response({
                    "error": "Admin permissions required for user deactivation",
                    "user_id": user_id
                })

            # Deactivate/reactivate the user
            action = "deactivate" if deactivate else "reactivate"
            result = await self.client.post(f"admin/users/{user_id}/{action}")

            return format_json_response({
                "success": True,
                "user_id": user_id,
                "action": action,
                "deactivated": deactivate,
                "result": result
            })

        except Exception as e:
            logger.exception(f"Error deactivating user {user_id}")
            return format_json_response({
                "error": str(e),
                "error_type": type(e).__name__,
                "user_id": user_id
            })

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get admin user tool definitions."""
        return {
            "users.create": {
                "description": "Create new user (admin only)",
                "function": self.create
            },
            "users.patch": {
                "description": "Update user properties (admin only)",
                "function": self.patch
            },
            "users.deactivate": {
                "description": "Deactivate/reactivate user (admin only)",
                "function": self.deactivate
            }
        }


__all__ = ["UsersAdminTools"]