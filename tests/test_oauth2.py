"""
OAuth2/OIDC Authentication Tests for YouTrack MCP Server.

Tests the OAuth2 client credentials flow, JWT token validation,
and OIDC integration functionality.
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtrack_mcp.auth import (
    OAuth2Config, OAuth2Token, OAuth2Client, OAuth2Manager, JWTClaims,
    create_youtrack_oauth2_config, create_generic_oauth2_config
)
from youtrack_mcp.security import SecurityAuditLog


class TestOAuth2Config:
    """Test OAuth2 configuration validation and creation."""
    
    def test_basic_config(self):
        """Test basic OAuth2 configuration."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_endpoint="https://auth.example.com/token"
        )
        
        assert config.client_id == "test_client"
        assert config.client_secret == "test_secret"
        assert config.token_endpoint == "https://auth.example.com/token"
        assert config.grant_type == "client_credentials"
        assert config.scope == "openid profile"
    
    def test_full_oidc_config(self):
        """Test full OIDC configuration."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_endpoint="https://auth.example.com/token",
            authorization_endpoint="https://auth.example.com/auth",
            userinfo_endpoint="https://auth.example.com/userinfo",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            scope="openid profile read:issues write:issues"
        )
        
        assert config.authorization_endpoint == "https://auth.example.com/auth"
        assert config.userinfo_endpoint == "https://auth.example.com/userinfo"
        assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert config.issuer == "https://auth.example.com"
        assert config.scope == "openid profile read:issues write:issues"
    
    def test_invalid_url_validation(self):
        """Test URL validation."""
        with pytest.raises(ValueError, match="URLs must start with http"):
            OAuth2Config(
                client_id="test_client",
                client_secret="test_secret",
                token_endpoint="invalid-url"
            )
    
    def test_token_cache_settings(self):
        """Test token cache configuration."""
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_endpoint="https://auth.example.com/token",
            token_cache_ttl=600,
            refresh_threshold=120
        )
        
        assert config.token_cache_ttl == 600
        assert config.refresh_threshold == 120


class TestOAuth2Token:
    """Test OAuth2 token model and validation."""
    
    def test_basic_token(self):
        """Test basic token creation."""
        token = OAuth2Token(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600
        )
        
        assert token.access_token == "test_access_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.expires_at is not None
        assert not token.is_expired
    
    def test_token_expiry(self):
        """Test token expiry detection."""
        # Create expired token
        token = OAuth2Token(
            access_token="expired_token",
            expires_in=1
        )
        
        # Manually set expiry time to past
        token.expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        assert token.is_expired
        assert token.expires_soon(threshold_seconds=10)
    
    def test_token_without_expiry(self):
        """Test token without expiry information."""
        token = OAuth2Token(access_token="no_expiry_token")
        
        assert not token.is_expired
        assert not token.expires_soon()


class TestJWTClaims:
    """Test JWT claims model and validation."""
    
    def test_standard_claims(self):
        """Test standard JWT claims."""
        claims = JWTClaims(
            iss="https://auth.example.com",
            sub="user123",
            aud="client123",
            exp=int(time.time() + 3600),
            iat=int(time.time()),
            scope="openid profile"
        )
        
        assert claims.iss == "https://auth.example.com"
        assert claims.sub == "user123"
        assert claims.aud == "client123"
        assert not claims.is_expired
    
    def test_oidc_claims(self):
        """Test OIDC-specific claims."""
        claims = JWTClaims(
            sub="user123",
            name="John Doe",
            email="john@example.com",
            email_verified=True,
            preferred_username="john.doe"
        )
        
        assert claims.name == "John Doe"
        assert claims.email == "john@example.com"
        assert claims.email_verified is True
        assert claims.preferred_username == "john.doe"
    
    def test_expired_jwt(self):
        """Test expired JWT detection."""
        claims = JWTClaims(
            sub="user123",
            exp=int(time.time() - 3600)  # Expired 1 hour ago
        )
        
        assert claims.is_expired


class TestOAuth2Client:
    """Test OAuth2 client functionality."""
    
    @pytest.fixture
    def oauth2_config(self):
        """Create OAuth2 configuration for testing."""
        return OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_endpoint="https://auth.example.com/token",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com"
        )
    
    @pytest.fixture
    def audit_log(self):
        """Create audit log for testing."""
        return SecurityAuditLog()
    
    @pytest.mark.asyncio
    async def test_client_credentials_flow(self, oauth2_config, audit_log):
        """Test OAuth2 client credentials flow."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful token response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "openid profile"
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(oauth2_config, audit_log)
            
            # Test token acquisition
            token = await oauth2_client.get_access_token()
            
            assert token == "test_access_token"
            assert oauth2_client._token_cache.access_token == "test_access_token"
            assert oauth2_client._token_cache.expires_in == 3600
            
            await oauth2_client.close()
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, oauth2_config, audit_log):
        """Test automatic token refresh."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock token response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "refreshed_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(oauth2_config, audit_log)
            
            # First token acquisition
            token1 = await oauth2_client.get_access_token()
            
            # Force refresh
            token2 = await oauth2_client.get_access_token(force_refresh=True)
            
            assert token1 == "refreshed_token"
            assert token2 == "refreshed_token"
            
            # Verify post was called twice (initial + refresh)
            assert mock_client.return_value.post.call_count == 2
            
            await oauth2_client.close()
    
    @pytest.mark.asyncio
    async def test_jwt_validation_without_verification(self, oauth2_config, audit_log):
        """Test JWT validation without signature verification."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(oauth2_config, audit_log)
            
            # Create a test JWT (not signed)
            import base64
            header = {"alg": "none", "typ": "JWT"}
            payload = {
                "iss": "https://auth.example.com",
                "sub": "user123",
                "aud": "test_client",
                "exp": int(time.time() + 3600),
                "iat": int(time.time())
            }
            
            # Create JWT without signature
            header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
            payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
            jwt_token = f"{header_b64}.{payload_b64}."
            
            # Validate without signature verification
            claims = await oauth2_client.validate_jwt_token(jwt_token, verify_signature=False)
            
            assert claims.iss == "https://auth.example.com"
            assert claims.sub == "user123"
            assert claims.aud == "test_client"
            
            await oauth2_client.close()
    
    @pytest.mark.asyncio
    async def test_token_revocation(self, oauth2_config, audit_log):
        """Test OAuth2 token revocation."""
        config_with_revocation = OAuth2Config(
            **oauth2_config.model_dump(),
            revocation_endpoint="https://auth.example.com/revoke"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(config_with_revocation, audit_log)
            
            # Test token revocation
            await oauth2_client.revoke_token("test_token", "access_token")
            
            # Verify revocation endpoint was called
            mock_client.return_value.post.assert_called_once()
            call_args = mock_client.return_value.post.call_args
            assert "revoke" in call_args[0][0]
            
            await oauth2_client.close()
    
    @pytest.mark.asyncio
    async def test_userinfo_endpoint(self, oauth2_config, audit_log):
        """Test OIDC userinfo endpoint."""
        config_with_userinfo = OAuth2Config(
            **oauth2_config.model_dump(),
            userinfo_endpoint="https://auth.example.com/userinfo"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "sub": "user123",
                "name": "John Doe",
                "email": "john@example.com",
                "email_verified": True
            }
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(config_with_userinfo, audit_log)
            
            # Test userinfo retrieval
            userinfo = await oauth2_client.get_userinfo("test_access_token")
            
            assert userinfo["sub"] == "user123"
            assert userinfo["name"] == "John Doe"
            assert userinfo["email"] == "john@example.com"
            
            await oauth2_client.close()


class TestOAuth2Manager:
    """Test OAuth2 manager with multiple clients."""
    
    @pytest.fixture
    def audit_log(self):
        """Create audit log for testing."""
        return SecurityAuditLog()
    
    def test_add_and_get_client(self, audit_log):
        """Test adding and retrieving OAuth2 clients."""
        manager = OAuth2Manager(audit_log)
        
        config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            token_endpoint="https://auth.example.com/token"
        )
        
        # Add client
        client = manager.add_client("test", config)
        assert isinstance(client, OAuth2Client)
        
        # Get client
        retrieved_client = manager.get_client("test")
        assert retrieved_client is client
        
        # List clients
        client_names = manager.list_clients()
        assert "test" in client_names
    
    def test_nonexistent_client(self, audit_log):
        """Test retrieving nonexistent client."""
        manager = OAuth2Manager(audit_log)
        
        with pytest.raises(ValueError, match="OAuth2 client 'nonexistent' not found"):
            manager.get_client("nonexistent")
    
    @pytest.mark.asyncio
    async def test_close_all_clients(self, audit_log):
        """Test closing all OAuth2 clients."""
        manager = OAuth2Manager(audit_log)
        
        # Add multiple clients
        for i in range(3):
            config = OAuth2Config(
                client_id=f"client_{i}",
                client_secret=f"secret_{i}",
                token_endpoint=f"https://auth{i}.example.com/token"
            )
            manager.add_client(f"client_{i}", config)
        
        assert len(manager.list_clients()) == 3
        
        # Close all clients
        with patch.object(OAuth2Client, 'close', new_callable=AsyncMock) as mock_close:
            await manager.close_all()
            
            # Verify all clients were closed
            assert mock_close.call_count == 3
            assert len(manager.list_clients()) == 0


class TestUtilityFunctions:
    """Test OAuth2 utility functions."""
    
    def test_create_youtrack_oauth2_config(self):
        """Test YouTrack OAuth2 configuration creation."""
        config = create_youtrack_oauth2_config(
            base_url="https://workspace.youtrack.cloud",
            client_id="youtrack_client",
            client_secret="youtrack_secret",
            scope="openid profile youtrack:read youtrack:write"
        )
        
        assert config.client_id == "youtrack_client"
        assert config.client_secret == "youtrack_secret"
        assert config.scope == "openid profile youtrack:read youtrack:write"
        assert "workspace.youtrack.cloud" in config.token_endpoint
        assert "workspace.youtrack.cloud" in config.authorization_endpoint
        assert config.issuer == "https://workspace.youtrack.cloud"
    
    def test_create_generic_oauth2_config(self):
        """Test generic OAuth2 configuration creation."""
        config = create_generic_oauth2_config(
            token_endpoint="https://auth.provider.com/token",
            client_id="generic_client",
            client_secret="generic_secret",
            authorization_endpoint="https://auth.provider.com/auth",
            userinfo_endpoint="https://auth.provider.com/userinfo",
            jwks_uri="https://auth.provider.com/.well-known/jwks.json",
            issuer="https://auth.provider.com",
            scope="openid profile api:read"
        )
        
        assert config.token_endpoint == "https://auth.provider.com/token"
        assert config.authorization_endpoint == "https://auth.provider.com/auth"
        assert config.userinfo_endpoint == "https://auth.provider.com/userinfo"
        assert config.jwks_uri == "https://auth.provider.com/.well-known/jwks.json"
        assert config.issuer == "https://auth.provider.com"
        assert config.scope == "openid profile api:read"


class TestOAuth2Integration:
    """Test OAuth2 integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_oauth2_flow(self):
        """Test complete OAuth2 flow from configuration to API usage."""
        # Create configuration
        config = OAuth2Config(
            client_id="integration_client",
            client_secret="integration_secret",
            token_endpoint="https://auth.example.com/token",
            userinfo_endpoint="https://auth.example.com/userinfo",
            scope="openid profile api:read api:write"
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock token response
            token_response = MagicMock()
            token_response.json.return_value = {
                "access_token": "integration_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "openid profile api:read api:write"
            }
            token_response.raise_for_status.return_value = None
            
            # Mock userinfo response
            userinfo_response = MagicMock()
            userinfo_response.json.return_value = {
                "sub": "integration_user",
                "name": "Integration User",
                "email": "integration@example.com"
            }
            userinfo_response.raise_for_status.return_value = None
            
            mock_client.return_value.post = AsyncMock(return_value=token_response)
            mock_client.return_value.get = AsyncMock(return_value=userinfo_response)
            mock_client.return_value.aclose = AsyncMock()
            
            # Create OAuth2 client
            oauth2_client = OAuth2Client(config)
            
            # Get access token
            access_token = await oauth2_client.get_access_token()
            assert access_token == "integration_token"
            
            # Get user information
            userinfo = await oauth2_client.get_userinfo(access_token)
            assert userinfo["sub"] == "integration_user"
            assert userinfo["name"] == "Integration User"
            
            await oauth2_client.close()
    
    @pytest.mark.asyncio
    async def test_token_cache_and_refresh_lifecycle(self):
        """Test token caching and refresh lifecycle."""
        config = OAuth2Config(
            client_id="cache_client",
            client_secret="cache_secret",
            token_endpoint="https://auth.example.com/token",
            refresh_threshold=1  # 1 second refresh threshold
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            token_responses = [
                {
                    "access_token": "first_token",
                    "token_type": "Bearer",
                    "expires_in": 2  # Short expiry for testing
                },
                {
                    "access_token": "refreshed_token",
                    "token_type": "Bearer", 
                    "expires_in": 3600
                }
            ]
            
            mock_response = MagicMock()
            mock_response.json.side_effect = token_responses
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.aclose = AsyncMock()
            
            oauth2_client = OAuth2Client(config)
            
            # First token acquisition
            token1 = await oauth2_client.get_access_token()
            assert token1 == "first_token"
            
            # Wait for token to be near expiry
            await asyncio.sleep(1.5)
            
            # Second call should trigger refresh
            token2 = await oauth2_client.get_access_token()
            assert token2 == "refreshed_token"
            
            # Verify refresh was triggered
            assert mock_client.return_value.post.call_count == 2
            
            await oauth2_client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])