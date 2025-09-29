"""
Unit tests for OAuth2/OIDC authentication.
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from youtrack_mcp.auth import (
    OAuth2Config, OAuth2Token, OAuth2Client, OAuth2Manager
)
from youtrack_mcp.security import SecurityAuditLog


class TestOAuth2Config:
    """Test OAuth2 configuration."""
    
    def test_config_validation(self):
        """Test OAuth2 config validation."""
        config = OAuth2Config(
            token_endpoint="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        assert config.token_endpoint == "https://auth.example.com/token"
        assert config.client_id == "test-client"
        assert config.client_secret == "test-secret"
        assert config.grant_type == "client_credentials"
        assert config.scope == "openid profile"
    
    def test_config_with_oidc_endpoints(self):
        """Test config with OIDC endpoints."""
        config = OAuth2Config(
            token_endpoint="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret",
            jwks_uri="https://auth.example.com/.well-known/jwks.json",
            issuer="https://auth.example.com",
            userinfo_endpoint="https://auth.example.com/userinfo"
        )
        
        assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
        assert config.issuer == "https://auth.example.com"
        assert config.userinfo_endpoint == "https://auth.example.com/userinfo"


class TestOAuth2Token:
    """Test OAuth2 token handling."""
    
    def test_token_creation(self):
        """Test OAuth2Token creation and properties."""
        token = OAuth2Token(
            access_token="test-access-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test-refresh-token",
            scope="openid profile"
        )
        
        assert token.access_token == "test-access-token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "test-refresh-token"
        assert token.scope == "openid profile"
    
    def test_token_expiry(self):
        """Test token expiry calculation."""
        # Token that expires in 1 hour
        token = OAuth2Token(
            access_token="test-token",
            token_type="Bearer", 
            expires_in=3600
        )
        
        # Should not be expired immediately
        assert not token.is_expired()
        
        # Should need refresh within threshold (default 300s)
        assert not token.needs_refresh(threshold=3700)
        assert token.needs_refresh(threshold=300)
    
    def test_token_from_response(self):
        """Test creating token from OAuth2 response."""
        response = {
            "access_token": "response-token",
            "token_type": "Bearer",
            "expires_in": 7200,
            "refresh_token": "response-refresh",
            "scope": "custom scope"
        }
        
        token = OAuth2Token(**response)
        assert token.access_token == "response-token"
        assert token.expires_in == 7200


class TestOAuth2Client:
    """Test OAuth2 client functionality."""
    
    @pytest.fixture
    def oauth_config(self):
        """Create test OAuth2 config."""
        return OAuth2Config(
            token_endpoint="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret"
        )
    
    @pytest.fixture
    def oauth_client(self, oauth_config):
        """Create OAuth2 client with mocked dependencies."""
        audit_log = MagicMock(spec=SecurityAuditLog)
        return OAuth2Client(oauth_config, audit_log)
    
    @pytest.mark.asyncio
    async def test_acquire_token_success(self, oauth_client):
        """Test successful token acquisition."""
        mock_response = {
            "access_token": "new-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_async_client = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value = mock_async_client
            
            mock_post_response = AsyncMock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = mock_response
            mock_async_client.post.return_value = mock_post_response
            
            token = await oauth_client.acquire_token()
            
            assert token.access_token == "new-token"
            assert token.token_type == "Bearer"
            assert token.expires_in == 3600
            
            # Verify audit log was called
            oauth_client.audit_log.log_authentication_success.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_acquire_token_failure(self, oauth_client):
        """Test token acquisition failure."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_async_client = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value = mock_async_client
            
            mock_post_response = AsyncMock()
            mock_post_response.status_code = 401
            mock_post_response.text = "Invalid credentials"
            mock_post_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_async_client.post.return_value = mock_post_response
            
            with pytest.raises(Exception) as exc_info:
                await oauth_client.acquire_token()
            
            assert "401" in str(exc_info.value)
            oauth_client.audit_log.log_authentication_failure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, oauth_client):
        """Test successful token refresh."""
        old_token = OAuth2Token(
            access_token="old-token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh-token"
        )
        
        mock_response = {
            "access_token": "refreshed-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new-refresh-token"
        }
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_async_client = AsyncMock()
            mock_httpx.return_value.__aenter__.return_value = mock_async_client
            
            mock_post_response = AsyncMock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = mock_response
            mock_async_client.post.return_value = mock_post_response
            
            new_token = await oauth_client.refresh_token(old_token)
            
            assert new_token.access_token == "refreshed-token"
            assert new_token.refresh_token == "new-refresh-token"
            
            oauth_client.audit_log.log_token_refresh.assert_called_once()
    
    def test_get_cached_token(self, oauth_client):
        """Test getting cached token."""
        # No cached token initially
        assert oauth_client.get_cached_token() is None
        
        # Cache a token
        token = OAuth2Token(
            access_token="cached-token",
            token_type="Bearer",
            expires_in=3600
        )
        oauth_client._cached_token = token
        
        # Should return cached token if not expired
        assert oauth_client.get_cached_token() == token
        
        # Should return None if expired
        expired_token = OAuth2Token(
            access_token="expired-token",
            token_type="Bearer",
            expires_in=-100  # Already expired
        )
        oauth_client._cached_token = expired_token
        assert oauth_client.get_cached_token() is None




class TestOAuth2Manager:
    """Test OAuth2Manager for managing multiple clients."""
    
    @pytest.fixture
    def oauth_manager(self):
        """Create OAuth2Manager."""
        audit_log = MagicMock(spec=SecurityAuditLog)
        return OAuth2Manager(audit_log)
    
    def test_register_client(self, oauth_manager):
        """Test registering OAuth2 clients."""
        config1 = OAuth2Config(
            token_endpoint="https://auth1.example.com/token",
            client_id="client1",
            client_secret="secret1"
        )
        
        config2 = OAuth2Config(
            token_endpoint="https://auth2.example.com/token",
            client_id="client2",
            client_secret="secret2"
        )
        
        oauth_manager.register_client("service1", config1)
        oauth_manager.register_client("service2", config2)
        
        assert "service1" in oauth_manager._clients
        assert "service2" in oauth_manager._clients
    
    @pytest.mark.asyncio
    async def test_get_token_for_service(self, oauth_manager):
        """Test getting token for a specific service."""
        config = OAuth2Config(
            token_endpoint="https://auth.example.com/token",
            client_id="test-client",
            client_secret="test-secret"
        )
        
        oauth_manager.register_client("test-service", config)
        
        # Mock the client's acquire_token method
        mock_token = OAuth2Token(
            access_token="service-token",
            token_type="Bearer",
            expires_in=3600
        )
        
        with patch.object(oauth_manager._clients["test-service"], 'acquire_token') as mock_acquire:
            mock_acquire.return_value = mock_token
            
            token = await oauth_manager.get_token("test-service")
            
            assert token.access_token == "service-token"
            mock_acquire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_token_unknown_service(self, oauth_manager):
        """Test getting token for unknown service."""
        with pytest.raises(ValueError) as exc_info:
            await oauth_manager.get_token("unknown-service")
        
        assert "No client registered" in str(exc_info.value)


class TestSecurityIntegration:
    """Test security audit log integration."""
    
    def test_security_audit_log_oauth_events(self):
        """Test that OAuth2 events are properly logged."""
        audit_log = SecurityAuditLog()
        
        # Test authentication success
        audit_log.log_authentication_success("test-client", "Bearer")
        
        # Test authentication failure  
        audit_log.log_authentication_failure("test-client", "Invalid credentials")
        
        # Test token refresh
        audit_log.log_token_refresh("test-client", 1234567890)
        
        # Test token validation failure
        audit_log.log_token_validation_failure(
            "Invalid signature",
            {"iss": "https://auth.example.com", "aud": "test"}
        )
        
        # No assertions needed - just ensure methods don't raise exceptions