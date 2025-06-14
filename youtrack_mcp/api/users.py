"""
YouTrack Users API client.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Self

from youtrack_mcp.api.client import YouTrackClient, YouTrackModel


class User(YouTrackModel):
    """Model for a YouTrack user with enhanced validation."""
    
    # Core user fields
    login: Optional[str] = Field(None, description="User login name")
    name: Optional[str] = Field(None, description="User display name")
    email: Optional[str] = Field(None, description="User email address")
    jabber: Optional[str] = Field(None, description="Jabber/XMPP address")
    
    # User status and metadata
    ring_id: Optional[str] = Field(None, alias="ringId", description="Ring ID for authentication")
    guest: Optional[bool] = Field(None, description="Whether user is a guest")
    online: Optional[bool] = Field(None, description="Whether user is currently online")
    banned: Optional[bool] = Field(None, description="Whether user is banned")
    
    # Additional fields
    avatar_url: Optional[str] = Field(None, alias="avatarUrl", description="User avatar URL")
    tags: List[str] = Field(default_factory=list, description="User tags")
    groups: List[Dict[str, Any]] = Field(default_factory=list, description="User groups")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is not None:
            # Basic email validation (Pydantic's EmailStr is stricter than needed for YouTrack)
            if '@' not in v or '.' not in v.split('@')[-1]:
                raise ValueError("Invalid email format")
            return v.lower().strip()
        return v
    
    @field_validator('login', 'name')
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean text fields."""
        if v is not None:
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v
    
    def is_active(self) -> bool:
        """Check if user is active (not banned and not a guest)."""
        return not (self.banned or self.guest)
    
    def get_display_name(self) -> str:
        """Get the best display name for the user."""
        return self.name or self.login or self.id


class UsersClient:
    """Client for interacting with YouTrack Users API."""
    
    def __init__(self, client: YouTrackClient):
        """
        Initialize the Users API client.
        
        Args:
            client: The YouTrack API client
        """
        self.client = client
    
    async def get_current_user(self) -> User:
        """
        Get the current authenticated user.
        
        Returns:
            The user data
        """
        fields = "id,login,name,email,jabber,ringId,guest,online,banned"
        response = await self.client.get(f"users/me?fields={fields}")
        return User.model_validate(response)
    
    async def get_user(self, user_id: str) -> User:
        """
        Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user data
        """
        fields = "id,login,name,email,jabber,ringId,guest,online,banned"
        response = await self.client.get(f"users/{user_id}?fields={fields}")
        return User.model_validate(response)
    
    async def search_users(self, query: str, limit: int = 10) -> List[User]:
        """
        Search for users.
        
        Args:
            query: The search query (name, login, or email)
            limit: Maximum number of users to return
            
        Returns:
            List of matching users
        """
        # Request additional fields to ensure we get complete user data
        fields = "id,login,name,email,jabber,ringId,guest,online,banned"
        params = {"query": query, "$top": limit, "fields": fields}
        response = await self.client.get("users", params=params)
        
        users = []
        for item in response:
            try:
                users.append(User.model_validate(item))
            except Exception as e:
                # Log the error but continue processing other users
                import logging
                logging.getLogger(__name__).warning(f"Failed to validate user: {str(e)}")
        
        return users
    
    async def get_user_by_login(self, login: str) -> Optional[User]:
        """
        Get a user by login name.
        
        Args:
            login: The user login name
            
        Returns:
            The user data or None if not found
        """
        # Search for the exact login
        users = await self.search_users(f"login: {login}", limit=1)
        return users[0] if users else None
    
    async def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get groups for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of group data
        """
        response = await self.client.get(f"users/{user_id}/groups")
        return response
    
    async def check_user_permissions(self, user_id: str, permission: str) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: The user ID
            permission: The permission to check
            
        Returns:
            True if the user has the permission, False otherwise
        """
        try:
            # YouTrack doesn't have a direct API for checking permissions,
            # but we can check user's groups and infer permissions
            groups = await self.get_user_groups(user_id)
            
            # Different permissions might require different group checks
            # This is a simplified example
            for group in groups:
                if permission.lower() in (group.get('name', '').lower() or ''):
                    return True
            
            return False
        except Exception:
            # If we can't determine, assume no permission
            return False 