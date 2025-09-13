# OAuth2/OIDC Authentication Setup

The YouTrack MCP server supports OAuth2 and OpenID Connect (OIDC) authentication for enhanced security and enterprise integration. This guide covers setup, configuration, and usage.

## Overview

OAuth2/OIDC authentication provides:

- **Secure Token Management**: Automatic token refresh and secure storage
- **Enterprise Integration**: Support for existing OAuth2/OIDC providers
- **JWT Token Validation**: Full OIDC compliance with JWT signature verification
- **Multiple Grant Types**: Client credentials flow with support for other flows
- **Audit Logging**: Comprehensive security event logging

## Features

### Supported OAuth2 Flows

1. **Client Credentials Flow** - Server-to-server authentication
2. **Authorization Code Flow** - Interactive user authentication (future)
3. **JWT Bearer Token** - Direct JWT token usage

### OIDC Features

- JWT token validation with signature verification
- JWKS (JSON Web Key Set) support
- Userinfo endpoint integration
- Standard claims support (iss, aud, exp, etc.)

## Configuration

### Environment Variables

Configure OAuth2/OIDC using environment variables:

```bash
# Enable OAuth2/OIDC
export OAUTH2_ENABLED=true

# OAuth2 Client Configuration
export OAUTH2_CLIENT_ID=your_client_id
export OAUTH2_CLIENT_SECRET=your_client_secret
export OAUTH2_SCOPE="openid profile youtrack:read youtrack:write"
export OAUTH2_GRANT_TYPE=client_credentials

# OAuth2 Endpoints
export OAUTH2_TOKEN_ENDPOINT=https://auth.yourdomain.com/oauth2/token
export OAUTH2_AUTHORIZATION_ENDPOINT=https://auth.yourdomain.com/oauth2/auth
export OAUTH2_USERINFO_ENDPOINT=https://auth.yourdomain.com/userinfo

# OIDC Configuration
export OAUTH2_JWKS_URI=https://auth.yourdomain.com/.well-known/jwks.json
export OAUTH2_ISSUER=https://auth.yourdomain.com
```

### YouTrack Hub Configuration

For YouTrack Hub (Cloud) integration:

```bash
# Enable OAuth2 for YouTrack Hub
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=your_hub_client_id
export OAUTH2_CLIENT_SECRET=your_hub_client_secret
export OAUTH2_SCOPE="openid profile youtrack:read youtrack:write"

# YouTrack Hub endpoints (auto-configured)
export YOUTRACK_WORKSPACE=your_workspace_name
```

### Generic OAuth2 Provider

For other OAuth2/OIDC providers (Azure AD, Keycloak, etc.):

```bash
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=your_client_id
export OAUTH2_CLIENT_SECRET=your_client_secret
export OAUTH2_TOKEN_ENDPOINT=https://provider.com/oauth2/token
export OAUTH2_JWKS_URI=https://provider.com/.well-known/jwks.json
export OAUTH2_ISSUER=https://provider.com
export OAUTH2_SCOPE="openid profile api:read api:write"
```

## Usage Examples

### Basic OAuth2 Setup

```python
from youtrack_mcp.auth import OAuth2Client, OAuth2Config
from youtrack_mcp.config import config

# Get OAuth2 configuration
oauth2_config = config.get_oauth2_config()

if oauth2_config:
    # Create OAuth2 client
    oauth2_client = OAuth2Client(oauth2_config)
    
    # Get access token
    access_token = await oauth2_client.get_access_token()
    
    # Use token with YouTrack API
    headers = {"Authorization": f"Bearer {access_token}"}
```

### JWT Token Validation

```python
from youtrack_mcp.auth import OAuth2Client, JWTClaims

# Validate a JWT token
try:
    claims = await oauth2_client.validate_jwt_token(jwt_token)
    print(f"Token valid for user: {claims.sub}")
    print(f"Scopes: {claims.scope}")
except ValueError as e:
    print(f"Token validation failed: {e}")
```

### Multiple OAuth2 Clients

```python
from youtrack_mcp.auth import OAuth2Manager, create_youtrack_oauth2_config

# Create OAuth2 manager
oauth2_manager = OAuth2Manager()

# Add YouTrack Hub client
youtrack_config = create_youtrack_oauth2_config(
    base_url="https://workspace.youtrack.cloud",
    client_id="youtrack_client_id",
    client_secret="youtrack_client_secret"
)
oauth2_manager.add_client("youtrack", youtrack_config)

# Add generic OIDC client
from youtrack_mcp.auth import create_generic_oauth2_config

generic_config = create_generic_oauth2_config(
    token_endpoint="https://auth.company.com/oauth2/token",
    client_id="company_client_id",
    client_secret="company_client_secret",
    jwks_uri="https://auth.company.com/.well-known/jwks.json"
)
oauth2_manager.add_client("company", generic_config)

# Use specific client
youtrack_client = oauth2_manager.get_client("youtrack")
token = await youtrack_client.get_access_token()
```

## Provider-Specific Setup

### Azure AD (Microsoft Entra ID)

```bash
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=your_azure_app_id
export OAUTH2_CLIENT_SECRET=your_azure_client_secret
export OAUTH2_TOKEN_ENDPOINT=https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
export OAUTH2_AUTHORIZATION_ENDPOINT=https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
export OAUTH2_JWKS_URI=https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
export OAUTH2_ISSUER=https://login.microsoftonline.com/{tenant}/v2.0
export OAUTH2_SCOPE="openid profile https://yourdomain.youtrack.cloud/.default"
```

### Keycloak

```bash
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=youtrack-mcp
export OAUTH2_CLIENT_SECRET=your_keycloak_secret
export OAUTH2_TOKEN_ENDPOINT=https://keycloak.company.com/auth/realms/master/protocol/openid-connect/token
export OAUTH2_AUTHORIZATION_ENDPOINT=https://keycloak.company.com/auth/realms/master/protocol/openid-connect/auth
export OAUTH2_USERINFO_ENDPOINT=https://keycloak.company.com/auth/realms/master/protocol/openid-connect/userinfo
export OAUTH2_JWKS_URI=https://keycloak.company.com/auth/realms/master/protocol/openid-connect/certs
export OAUTH2_ISSUER=https://keycloak.company.com/auth/realms/master
```

### Auth0

```bash
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=your_auth0_client_id
export OAUTH2_CLIENT_SECRET=your_auth0_client_secret
export OAUTH2_TOKEN_ENDPOINT=https://your-domain.auth0.com/oauth/token
export OAUTH2_AUTHORIZATION_ENDPOINT=https://your-domain.auth0.com/authorize
export OAUTH2_USERINFO_ENDPOINT=https://your-domain.auth0.com/userinfo
export OAUTH2_JWKS_URI=https://your-domain.auth0.com/.well-known/jwks.json
export OAUTH2_ISSUER=https://your-domain.auth0.com/
export OAUTH2_SCOPE="openid profile read:youtrack write:youtrack"
```

## Security Best Practices

### Token Storage

OAuth2 tokens are automatically cached in memory with configurable TTL:

```bash
# Configure token caching (optional)
export OAUTH2_TOKEN_CACHE_TTL=300  # 5 minutes
export OAUTH2_REFRESH_THRESHOLD=60  # Refresh 60 seconds before expiry
```

### JWT Signature Verification

Always enable JWT signature verification in production:

```python
# Validate JWT with signature verification
claims = await oauth2_client.validate_jwt_token(
    jwt_token, 
    verify_signature=True  # Always True in production
)
```

### Audit Logging

OAuth2 events are automatically logged for security auditing:

```python
from youtrack_mcp.auth import OAuth2Client
from youtrack_mcp.security import SecurityAuditLog

# Custom audit log
audit_log = SecurityAuditLog()
oauth2_client = OAuth2Client(config, audit_log)

# All OAuth2 events are automatically logged:
# - oauth2_token_refresh
# - oauth2_token_refresh_failed
# - jwt_validation_success
# - jwt_validation_failed
# - oauth2_token_revoked
```

## Troubleshooting

### Common Issues

#### 1. Token Validation Failed

```
Error: JWT token has expired
```

**Solution**: Check token expiry and refresh configuration:
- Verify `OAUTH2_REFRESH_THRESHOLD` is set appropriately
- Check provider token lifetime settings
- Ensure clock synchronization between server and provider

#### 2. Invalid Client Credentials

```
Error: OAuth2 token refresh failed: 401 Unauthorized
```

**Solution**: Verify OAuth2 client configuration:
- Check `OAUTH2_CLIENT_ID` and `OAUTH2_CLIENT_SECRET`
- Verify client is enabled in OAuth2 provider
- Confirm correct token endpoint URL

#### 3. JWKS Verification Failed

```
Error: Invalid JWT token: Unable to find a signing key
```

**Solution**: Check JWKS configuration:
- Verify `OAUTH2_JWKS_URI` is accessible
- Check issuer configuration (`OAUTH2_ISSUER`)
- Ensure JWT algorithm matches JWKS keys

#### 4. Scope Insufficient

```
Error: Access denied: insufficient scope
```

**Solution**: Update OAuth2 scopes:
- Add required scopes to `OAUTH2_SCOPE`
- Verify client has permission to requested scopes
- Check YouTrack permission mapping

### Debug Mode

Enable debug logging for OAuth2 troubleshooting:

```bash
export LOG_LEVEL=DEBUG
export MCP_DEBUG=true
```

Debug logs include:
- OAuth2 token requests and responses
- JWT validation details
- JWKS retrieval and caching
- Token refresh attempts

### Health Checks

Test OAuth2 configuration:

```python
from youtrack_mcp.auth import OAuth2Client
from youtrack_mcp.config import config

async def test_oauth2():
    oauth2_config = config.get_oauth2_config()
    if not oauth2_config:
        print("OAuth2 not configured")
        return
    
    oauth2_client = OAuth2Client(oauth2_config)
    
    try:
        # Test token acquisition
        token = await oauth2_client.get_access_token()
        print("✓ OAuth2 token acquired successfully")
        
        # Test JWT validation if available
        if oauth2_config.jwks_uri:
            claims = await oauth2_client.validate_jwt_token(token)
            print(f"✓ JWT validation successful for {claims.sub}")
        
    except Exception as e:
        print(f"✗ OAuth2 test failed: {e}")
    finally:
        await oauth2_client.close()

# Run test
import asyncio
asyncio.run(test_oauth2())
```

## Integration Examples

### Use with MCP Server

The OAuth2 authentication is automatically integrated with the MCP server when enabled:

```bash
# Start MCP server with OAuth2
export OAUTH2_ENABLED=true
export OAUTH2_CLIENT_ID=your_client_id
export OAUTH2_CLIENT_SECRET=your_client_secret
export OAUTH2_TOKEN_ENDPOINT=https://auth.yourdomain.com/oauth2/token

python main.py --transport http --host 0.0.0.0 --port 8000
```

### API Client Integration

```python
from youtrack_mcp.api.client import YouTrackClient
from youtrack_mcp.auth import OAuth2Client
from youtrack_mcp.config import config

# Create OAuth2-enabled YouTrack client
oauth2_config = config.get_oauth2_config()
oauth2_client = OAuth2Client(oauth2_config)

# Get access token and create API client
access_token = await oauth2_client.get_access_token()
youtrack_client = YouTrackClient()

# Override authentication header
youtrack_client.default_headers["Authorization"] = f"Bearer {access_token}"

# Use API client normally
issues = await youtrack_client.get("issues", params={"query": "project: TEST"})
```

## Reference

### OAuth2Config Model

```python
class OAuth2Config(YouTrackModel):
    # OAuth2 endpoints
    authorization_endpoint: Optional[str]
    token_endpoint: str
    revocation_endpoint: Optional[str]
    introspection_endpoint: Optional[str]
    
    # OIDC endpoints
    userinfo_endpoint: Optional[str]
    jwks_uri: Optional[str]
    issuer: Optional[str]
    
    # Client configuration
    client_id: str
    client_secret: str
    scope: str = "openid profile"
    
    # Flow configuration
    grant_type: str = "client_credentials"
    token_endpoint_auth_method: str = "client_secret_basic"
    
    # Token configuration
    token_cache_ttl: int = 300  # 5 minutes
    refresh_threshold: int = 60  # 1 minute
```

### JWT Claims Model

```python
class JWTClaims(YouTrackModel):
    # Standard claims
    iss: Optional[str]  # Issuer
    sub: Optional[str]  # Subject
    aud: Optional[Union[str, List[str]]]  # Audience
    exp: Optional[int]  # Expiration time
    iat: Optional[int]  # Issued at
    nbf: Optional[int]  # Not before
    jti: Optional[str]  # JWT ID
    
    # OIDC claims
    name: Optional[str]
    email: Optional[str]
    preferred_username: Optional[str]
    
    # Custom claims
    scope: Optional[str]
    client_id: Optional[str]
```

For complete API reference, see the source code in `youtrack_mcp/auth.py`.