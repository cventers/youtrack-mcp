"""
OAuth2/OIDC Authentication System for YouTrack MCP Server.

Provides OAuth2 client credentials flow and OIDC integration with JWT token validation,
token refresh, and secure credential management.
"""
import asyncio
import base64
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlencode

import httpx
import jwt
from pydantic import BaseModel, Field, field_validator

from youtrack_mcp.api.client import YouTrackModel
from youtrack_mcp.security import SecurityAuditLog

logger = logging.getLogger(__name__)


class OAuth2Config(YouTrackModel):
    """OAuth2/OIDC configuration."""
    
    # OAuth2 endpoints
    authorization_endpoint: Optional[str] = Field(None, description="OAuth2 authorization endpoint URL")
    token_endpoint: str = Field(..., description="OAuth2 token endpoint URL")
    revocation_endpoint: Optional[str] = Field(None, description="OAuth2 token revocation endpoint URL")
    introspection_endpoint: Optional[str] = Field(None, description="OAuth2 token introspection endpoint URL")
    
    # OIDC endpoints
    userinfo_endpoint: Optional[str] = Field(None, description="OIDC userinfo endpoint URL")
    jwks_uri: Optional[str] = Field(None, description="OIDC JWKS endpoint URL")
    issuer: Optional[str] = Field(None, description="OIDC issuer URL")
    
    # Client configuration
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    scope: str = Field("openid profile", description="OAuth2 scopes")
    
    # Flow configuration
    grant_type: str = Field("client_credentials", description="OAuth2 grant type")
    token_endpoint_auth_method: str = Field("client_secret_basic", description="Token endpoint authentication method")
    
    # Token configuration
    token_cache_ttl: int = Field(300, ge=60, le=3600, description="Token cache TTL in seconds")
    refresh_threshold: int = Field(60, ge=30, le=300, description="Refresh token before expiry (seconds)")
    
    @field_validator('token_endpoint', 'authorization_endpoint', 'userinfo_endpoint', 'jwks_uri')
    @classmethod
    def validate_urls(cls, v):
        """Validate that URLs are properly formatted."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("URLs must start with http:// or https://")
        return v


class OAuth2Token(YouTrackModel):
    """OAuth2 access token with metadata."""
    
    access_token: str = Field(..., description="OAuth2 access token")
    token_type: str = Field("Bearer", description="Token type")
    expires_in: Optional[int] = Field(None, description="Token expiry in seconds")
    refresh_token: Optional[str] = Field(None, description="OAuth2 refresh token")
    scope: Optional[str] = Field(None, description="Granted scopes")
    
    # Metadata
    issued_at: datetime = Field(default_factory=datetime.utcnow, description="Token issue time")
    expires_at: Optional[datetime] = Field(None, description="Token expiry time")
    
    def model_post_init(self, __context):
        """Calculate expiry time after initialization."""
        if self.expires_in and not self.expires_at:
            self.expires_at = self.issued_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    @property
    def expires_soon(self, threshold_seconds: int = 60) -> bool:
        """Check if token expires soon."""
        if not self.expires_at:
            return False
        return datetime.utcnow() + timedelta(seconds=threshold_seconds) >= self.expires_at


class JWTClaims(YouTrackModel):
    """JWT token claims."""
    
    # Standard claims
    iss: Optional[str] = Field(None, description="Issuer")
    sub: Optional[str] = Field(None, description="Subject")
    aud: Optional[Union[str, List[str]]] = Field(None, description="Audience")
    exp: Optional[int] = Field(None, description="Expiration time")
    iat: Optional[int] = Field(None, description="Issued at")
    nbf: Optional[int] = Field(None, description="Not before")
    jti: Optional[str] = Field(None, description="JWT ID")
    
    # OIDC claims
    name: Optional[str] = Field(None, description="Full name")
    given_name: Optional[str] = Field(None, description="Given name")
    family_name: Optional[str] = Field(None, description="Family name")
    email: Optional[str] = Field(None, description="Email address")
    email_verified: Optional[bool] = Field(None, description="Email verified")
    preferred_username: Optional[str] = Field(None, description="Preferred username")
    
    # Custom claims
    scope: Optional[str] = Field(None, description="OAuth2 scopes")
    client_id: Optional[str] = Field(None, description="OAuth2 client ID")
    
    @property
    def is_expired(self) -> bool:
        """Check if JWT is expired."""
        if not self.exp:
            return False
        return time.time() >= self.exp


class OAuth2Client:
    """OAuth2/OIDC client with token management."""
    
    def __init__(self, config: OAuth2Config, audit_log: Optional[SecurityAuditLog] = None):
        self.config = config
        self.audit_log = audit_log or SecurityAuditLog()
        self._client = httpx.AsyncClient(timeout=30.0)
        self._token_cache: Optional[OAuth2Token] = None
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            Valid access token
        """
        # Check if we need to refresh the token
        if (force_refresh or 
            not self._token_cache or 
            self._token_cache.is_expired or 
            self._token_cache.expires_soon(self.config.refresh_threshold)):
            
            await self._refresh_token()
        
        if not self._token_cache:
            raise ValueError("Failed to obtain access token")
        
        return self._token_cache.access_token
    
    async def _refresh_token(self):
        """Refresh the OAuth2 access token."""
        try:
            if self.config.grant_type == "client_credentials":
                token = await self._client_credentials_flow()
            else:
                raise ValueError(f"Unsupported grant type: {self.config.grant_type}")
            
            self._token_cache = token
            
            # Log successful token refresh
            await self.audit_log.log_event(
                "oauth2_token_refresh",
                {"grant_type": self.config.grant_type, "expires_in": token.expires_in},
                "INFO"
            )
            
            logger.info(f"OAuth2 token refreshed successfully, expires in {token.expires_in} seconds")
            
        except Exception as e:
            # Log token refresh failure
            await self.audit_log.log_event(
                "oauth2_token_refresh_failed",
                {"error": str(e), "grant_type": self.config.grant_type},
                "ERROR"
            )
            logger.error(f"OAuth2 token refresh failed: {e}")
            raise
    
    async def _client_credentials_flow(self) -> OAuth2Token:
        """Execute OAuth2 client credentials flow."""
        # Prepare request data
        data = {
            "grant_type": "client_credentials",
            "scope": self.config.scope
        }
        
        # Prepare authentication
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        if self.config.token_endpoint_auth_method == "client_secret_basic":
            # HTTP Basic authentication
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        elif self.config.token_endpoint_auth_method == "client_secret_post":
            # Include credentials in POST body
            data["client_id"] = self.config.client_id
            data["client_secret"] = self.config.client_secret
        else:
            raise ValueError(f"Unsupported authentication method: {self.config.token_endpoint_auth_method}")
        
        # Make token request
        response = await self._client.post(
            self.config.token_endpoint,
            data=data,
            headers=headers
        )
        response.raise_for_status()
        
        token_data = response.json()
        return OAuth2Token(**token_data)
    
    async def validate_jwt_token(self, token: str, verify_signature: bool = True) -> JWTClaims:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token to validate
            verify_signature: Whether to verify the JWT signature
            
        Returns:
            Decoded JWT claims
        """
        try:
            if verify_signature and self.config.jwks_uri:
                # Get JWKS for signature verification
                jwks = await self._get_jwks()
                
                # Decode and verify the token
                decoded = jwt.decode(
                    token,
                    jwks,
                    algorithms=["RS256", "HS256"],
                    audience=self.config.client_id,
                    issuer=self.config.issuer,
                    options={"verify_signature": True}
                )
            else:
                # Decode without verification (for testing/development)
                decoded = jwt.decode(token, options={"verify_signature": False})
            
            claims = JWTClaims(**decoded)
            
            # Log successful JWT validation
            await self.audit_log.log_event(
                "jwt_validation_success",
                {"subject": claims.sub, "client_id": claims.client_id},
                "INFO"
            )
            
            return claims
            
        except jwt.ExpiredSignatureError:
            await self.audit_log.log_event(
                "jwt_validation_failed",
                {"error": "Token expired", "token_prefix": token[:10]},
                "WARNING"
            )
            raise ValueError("JWT token has expired")
        
        except jwt.InvalidTokenError as e:
            await self.audit_log.log_event(
                "jwt_validation_failed",
                {"error": str(e), "token_prefix": token[:10]},
                "ERROR"
            )
            raise ValueError(f"Invalid JWT token: {e}")
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS (JSON Web Key Set) for JWT signature verification."""
        # Check cache
        if (self._jwks_cache and self._jwks_cache_time and 
            datetime.utcnow() - self._jwks_cache_time < timedelta(hours=1)):
            return self._jwks_cache
        
        # Fetch JWKS
        response = await self._client.get(self.config.jwks_uri)
        response.raise_for_status()
        
        jwks = response.json()
        self._jwks_cache = jwks
        self._jwks_cache_time = datetime.utcnow()
        
        return jwks
    
    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from OIDC userinfo endpoint.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User information
        """
        if not self.config.userinfo_endpoint:
            raise ValueError("Userinfo endpoint not configured")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self._client.get(self.config.userinfo_endpoint, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    async def revoke_token(self, token: str, token_type_hint: str = "access_token"):
        """
        Revoke an OAuth2 token.
        
        Args:
            token: Token to revoke
            token_type_hint: Type of token (access_token or refresh_token)
        """
        if not self.config.revocation_endpoint:
            logger.warning("Token revocation endpoint not configured")
            return
        
        data = {
            "token": token,
            "token_type_hint": token_type_hint,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            response = await self._client.post(
                self.config.revocation_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            
            await self.audit_log.log_event(
                "oauth2_token_revoked",
                {"token_type_hint": token_type_hint},
                "INFO"
            )
            
        except Exception as e:
            await self.audit_log.log_event(
                "oauth2_token_revocation_failed",
                {"error": str(e), "token_type_hint": token_type_hint},
                "WARNING"
            )
            logger.warning(f"Failed to revoke token: {e}")
    
    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect an OAuth2 token to get its metadata.
        
        Args:
            token: Token to introspect
            
        Returns:
            Token introspection result
        """
        if not self.config.introspection_endpoint:
            raise ValueError("Token introspection endpoint not configured")
        
        data = {
            "token": token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        response = await self._client.post(
            self.config.introspection_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        return response.json()


class OAuth2Manager:
    """High-level OAuth2/OIDC management with multiple client support."""
    
    def __init__(self, audit_log: Optional[SecurityAuditLog] = None):
        self.audit_log = audit_log or SecurityAuditLog()
        self._clients: Dict[str, OAuth2Client] = {}
    
    def add_client(self, name: str, config: OAuth2Config) -> OAuth2Client:
        """
        Add an OAuth2 client configuration.
        
        Args:
            name: Client configuration name
            config: OAuth2 configuration
            
        Returns:
            OAuth2 client instance
        """
        client = OAuth2Client(config, self.audit_log)
        self._clients[name] = client
        return client
    
    def get_client(self, name: str) -> OAuth2Client:
        """
        Get an OAuth2 client by name.
        
        Args:
            name: Client configuration name
            
        Returns:
            OAuth2 client instance
        """
        if name not in self._clients:
            raise ValueError(f"OAuth2 client '{name}' not found")
        return self._clients[name]
    
    def list_clients(self) -> List[str]:
        """List all configured OAuth2 client names."""
        return list(self._clients.keys())
    
    async def close_all(self):
        """Close all OAuth2 clients."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()


# Utility functions for common OAuth2/OIDC configurations

def create_youtrack_oauth2_config(
    base_url: str,
    client_id: str,
    client_secret: str,
    scope: str = "openid profile youtrack:read youtrack:write"
) -> OAuth2Config:
    """
    Create OAuth2 configuration for YouTrack Hub.
    
    Args:
        base_url: YouTrack Hub base URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        scope: OAuth2 scopes
        
    Returns:
        OAuth2 configuration
    """
    return OAuth2Config(
        authorization_endpoint=urljoin(base_url, "/api/rest/oauth2/auth"),
        token_endpoint=urljoin(base_url, "/api/rest/oauth2/token"),
        revocation_endpoint=urljoin(base_url, "/api/rest/oauth2/revoke"),
        userinfo_endpoint=urljoin(base_url, "/api/rest/users/me"),
        jwks_uri=urljoin(base_url, "/api/rest/oauth2/jwks"),
        issuer=base_url,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        grant_type="client_credentials"
    )


def create_generic_oauth2_config(
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    authorization_endpoint: Optional[str] = None,
    userinfo_endpoint: Optional[str] = None,
    jwks_uri: Optional[str] = None,
    issuer: Optional[str] = None,
    scope: str = "openid profile"
) -> OAuth2Config:
    """
    Create a generic OAuth2/OIDC configuration.
    
    Args:
        token_endpoint: OAuth2 token endpoint URL
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        authorization_endpoint: OAuth2 authorization endpoint URL
        userinfo_endpoint: OIDC userinfo endpoint URL
        jwks_uri: OIDC JWKS endpoint URL
        issuer: OIDC issuer URL
        scope: OAuth2 scopes
        
    Returns:
        OAuth2 configuration
    """
    return OAuth2Config(
        token_endpoint=token_endpoint,
        authorization_endpoint=authorization_endpoint,
        userinfo_endpoint=userinfo_endpoint,
        jwks_uri=jwks_uri,
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        scope=scope,
        grant_type="client_credentials"
    )