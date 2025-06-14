# Security Features

This document describes the security features implemented in the YouTrack MCP server.

## Token Security

### Secure Token Storage

The YouTrack MCP server supports multiple secure methods for storing and retrieving API tokens:

#### 1. Keyring Storage (Recommended)
```bash
# Install keyring support
pip install keyring

# Store token securely in system keyring
python -c "
from youtrack_mcp.security import credential_manager
credential_manager.store_token('your-username', 'your-api-token')
"

# Configure environment to use keyring
export YOUTRACK_KEYRING_USERNAME=your-username
```

#### 2. Secure Token Files
```bash
# Create token file with secure permissions
echo "your-api-token" > ~/.youtrack/token
chmod 600 ~/.youtrack/token

# Configure environment
export YOUTRACK_TOKEN_FILE=~/.youtrack/token
```

#### 3. Environment Variables (Less Secure)
```bash
export YOUTRACK_API_TOKEN=your-api-token
```

### Token Validation

All API tokens are automatically validated for format and structure:

- **Permanent Tokens**: Format `perm:username.workspace.hash`
- **Legacy Tokens**: Format `perm-base64.encoded.parts`
- **Workspace Detection**: Automatic extraction from token format
- **Format Validation**: Ensures tokens match YouTrack patterns

### Security Audit Logging

All token-related operations are logged for security auditing:

```bash
# Enable security audit logging
export YOUTRACK_SECURITY_AUDIT_LOG=/var/log/youtrack-mcp-security.log
```

Audit events include:
- Token validation attempts
- Authentication failures
- Client initialization
- Token access patterns

### Token Masking

Sensitive information is automatically masked in logs and error messages:

```
# Instead of: Token: perm:user.workspace.abcd1234efgh5678
# Shows: Token: ***5678
```

## Configuration Security

### Secure Configuration Loading

The configuration system loads credentials in order of security preference:

1. **Keyring** (most secure)
2. **Secure token files** (with permission checks)
3. **Environment variables** (least secure)

### SSL/TLS Verification

```bash
# Enable SSL verification (default)
export YOUTRACK_VERIFY_SSL=true

# Disable SSL verification (not recommended for production)
export YOUTRACK_VERIFY_SSL=false
```

## API Client Security

### Secure Error Handling

- Automatic masking of tokens in error messages
- Safe error message formatting
- Authentication failure audit logging

### Connection Security

- HTTP connection pooling with security considerations
- Proper SSL context management
- Retry logic with exponential backoff

## Best Practices

### Development Environment
```bash
# Use keyring for secure token storage
pip install keyring
python -c "from youtrack_mcp.security import credential_manager; credential_manager.store_token('dev', 'your-token')"
export YOUTRACK_KEYRING_USERNAME=dev
```

### Production Environment
```bash
# Use secure token file with restrictive permissions
install -m 600 /dev/null /etc/youtrack-mcp/token
echo "your-production-token" > /etc/youtrack-mcp/token
export YOUTRACK_TOKEN_FILE=/etc/youtrack-mcp/token

# Enable audit logging
export YOUTRACK_SECURITY_AUDIT_LOG=/var/log/youtrack-mcp-security.log

# Ensure SSL verification
export YOUTRACK_VERIFY_SSL=true
```

### Container Environments
```bash
# Use secrets management
docker run -e YOUTRACK_API_TOKEN_FILE=/run/secrets/youtrack-token \
           -v youtrack-token:/run/secrets/youtrack-token:ro \
           youtrack-mcp

# Or use environment with proper secret handling
docker run --env-file youtrack.env youtrack-mcp
```

## Security Validation

### Token Format Validation

```python
from youtrack_mcp.security import token_validator

# Validate token format
result = token_validator.validate_token_format("perm:user.workspace.hash")
print(f"Valid: {result['valid']}")
print(f"Type: {result['token_type']}")
print(f"Workspace: {result.get('workspace')}")
```

### Security Audit

```python
from youtrack_mcp.security import audit_log

# Manual audit logging
audit_log.log_token_access(
    event="manual_validation",
    token_hash="abcd1234",
    source="manual",
    success=True
)
```

## Security Monitoring

### Audit Log Format

Each security event is logged in JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "event": "token_validation",
  "token_hash": "abcd1234",
  "source": "keyring",
  "success": true,
  "pid": 12345
}
```

### Log Analysis

```bash
# Monitor authentication failures
jq 'select(.event == "authentication_failure")' /var/log/youtrack-mcp-security.log

# Track token access patterns
jq 'select(.event == "token_validation") | .source' /var/log/youtrack-mcp-security.log | sort | uniq -c
```

## Troubleshooting

### Common Security Issues

#### Token Not Found
```
Error: YouTrack API token is required. Provide it using:
1. YOUTRACK_API_TOKEN environment variable
2. YOUTRACK_TOKEN_FILE pointing to a token file
3. Secure keyring storage (if available)
4. Configuration parameter
```

**Solution**: Configure token using one of the supported methods.

#### Invalid Token Format
```
Error: Invalid YouTrack API token format (token: ***5678): Token does not match known YouTrack token formats
```

**Solution**: Verify your token is a valid YouTrack permanent token.

#### Permission Denied on Token File
```
Error: Permission denied reading token file: /path/to/token
```

**Solution**: Check file permissions and ownership:
```bash
chmod 600 /path/to/token
chown $(whoami) /path/to/token
```

#### Keyring Not Available
```
Warning: keyring not available - secure credential storage disabled
```

**Solution**: Install keyring support:
```bash
pip install keyring
```

## Security Updates

### Dependencies

Keep security-related dependencies updated:

```bash
pip install --upgrade keyring httpx pydantic
```

### Configuration Review

Regularly review your security configuration:

- Rotate API tokens periodically
- Monitor audit logs for suspicious activity
- Update to latest versions
- Review file permissions

### Incident Response

If you suspect token compromise:

1. **Immediately rotate the API token** in YouTrack
2. **Update the token** in your secure storage
3. **Review audit logs** for unauthorized access
4. **Check YouTrack logs** for suspicious activity
5. **Restart services** to ensure new token is used