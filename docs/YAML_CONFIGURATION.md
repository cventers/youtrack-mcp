# YAML Configuration Guide

## Overview

The YouTrack MCP server supports comprehensive YAML configuration, allowing you to define all settings in a structured format instead of using environment variables. YAML configuration is recommended for complex deployments and provides better organization and readability.

## Configuration Priority

Settings are loaded in the following priority order (highest to lowest):
1. **Environment Variables** (highest priority)
2. **YAML Configuration File**
3. **Default Values** (lowest priority)

This allows you to define base settings in YAML and override specific values with environment variables for different deployment environments.

## Configuration File Location

The server automatically searches for configuration files in this order:
1. `./config.yaml` (current directory)
2. `../config.yaml` (parent directory)
3. `{project_root}/config.yaml`

You can also specify a custom path:
```bash
python main.py --config /path/to/custom-config.yaml
```

## Complete Configuration Schema

### Basic YouTrack Settings

```yaml
# YouTrack connection settings
youtrack:
  # Self-hosted YouTrack instance
  url: "https://youtrack.yourcompany.com"
  
  # For YouTrack Cloud instances
  # url: "https://yourworkspace.youtrack.cloud"
  # cloud: true
  
  # API authentication
  api_token: "perm:your_api_token"
  # token_file: "/secure/path/to/token"
  
  # SSL/TLS settings
  verify_ssl: true
```

### API Client Configuration

```yaml
# API client behavior
api:
  max_retries: 3        # Number of retry attempts
  retry_delay: 1.0      # Initial delay between retries (seconds)
```

### MCP Server Settings

```yaml
# MCP protocol settings
mcp:
  server_name: "youtrack-mcp"
  server_description: "YouTrack MCP Server with AI"
  debug: false          # Enable debug logging
```

### AI/LLM Configuration

```yaml
# AI and LLM settings
ai:
  enabled: true         # Enable AI features
  max_memory_mb: 2048   # Maximum memory for AI models
  
  # OpenAI-compatible API provider (highest priority)
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-your-openai-key"
    model: "gpt-3.5-turbo"
    max_tokens: 1000
    temperature: 0.3
    timeout: 30
    enabled: true
  
  # Hugging Face Transformers (local CPU inference)
  huggingface:
    model: "Qwen/Qwen1.5-0.5B-Chat"
    device: "cpu"
    max_tokens: 1000
    temperature: 0.3
    torch_dtype: "auto"
    quantization_4bit: false
    quantization_8bit: false
    trust_remote_code: false
    enabled: false
  
  # Local model support (future feature)
  local:
    model_path: "/path/to/local/model"
    enabled: false
```

### OAuth2/OIDC Configuration

```yaml
# OAuth2 authentication (optional)
oauth2:
  enabled: false
  client_id: "your_oauth2_client_id"
  client_secret: "your_oauth2_client_secret"
  token_endpoint: "https://youtrack.yourcompany.com/hub/api/rest/oauth2/token"
  authorization_endpoint: "https://youtrack.yourcompany.com/hub/api/rest/oauth2/auth"
  userinfo_endpoint: "https://youtrack.yourcompany.com/hub/api/rest/users/me"
  jwks_uri: "https://youtrack.yourcompany.com/hub/api/rest/oauth2/jwks"
  issuer: "https://youtrack.yourcompany.com/hub"
  scope: "openid profile"
  grant_type: "client_credentials"
```

### Feature Settings

```yaml
# Response formatting and features
quirks:
  no_epoch: true        # Convert epoch timestamps to ISO8601

# Ticket suggestions
suggestions:
  enabled: true
```

## Configuration Examples

### 1. OpenAI with Local Fallback

```yaml
youtrack:
  url: "https://yourworkspace.youtrack.cloud"
  api_token: "perm:your_token"

ai:
  enabled: true
  
  # Primary: OpenAI API
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-your-openai-key"
    model: "gpt-3.5-turbo"
    enabled: true
  
  # Fallback: Local CPU model
  huggingface:
    model: "Qwen/Qwen1.5-0.5B-Chat"
    device: "cpu"
    enabled: true
```

### 2. Privacy-First Local Only

```yaml
youtrack:
  url: "https://youtrack.yourcompany.com"
  token_file: "/secure/youtrack-token"
  verify_ssl: true

ai:
  enabled: true
  max_memory_mb: 4096
  
  # No external APIs
  llm:
    enabled: false
  
  # Local CPU inference only
  huggingface:
    model: "Qwen/Qwen1.5-0.5B-Chat"
    device: "cpu"
    quantization_4bit: true
    enabled: true
```

### 3. Anthropic Claude

```yaml
youtrack:
  url: "https://yourworkspace.youtrack.cloud"
  api_token: "perm:your_token"

ai:
  enabled: true
  
  llm:
    api_url: "https://api.anthropic.com/v1"
    api_key: "sk-ant-your-anthropic-key"
    model: "claude-3-haiku-20240307"
    max_tokens: 1500
    temperature: 0.2
    enabled: true
```

### 4. Local Ollama Server

```yaml
youtrack:
  url: "https://youtrack.yourcompany.com"
  api_token: "perm:your_token"

ai:
  enabled: true
  
  llm:
    api_url: "http://localhost:11434/v1"
    api_key: "ollama"
    model: "llama2"
    timeout: 60
    enabled: true
```

### 5. High-Performance Local Setup

```yaml
youtrack:
  url: "https://youtrack.yourcompany.com"
  api_token: "perm:your_token"

ai:
  enabled: true
  max_memory_mb: 6144
  
  huggingface:
    model: "Qwen/Qwen1.5-1.8B-Chat"
    device: "cpu"
    torch_dtype: "auto"
    quantization_4bit: true
    max_tokens: 1500
    temperature: 0.1
    enabled: true

api:
  max_retries: 5
  retry_delay: 0.5
```

### 6. Development/Testing Setup

```yaml
youtrack:
  url: "https://dev-youtrack.yourcompany.com"
  api_token: "perm:dev_token"
  verify_ssl: false    # For self-signed certificates

mcp:
  debug: true          # Enable debug logging

ai:
  enabled: true
  
  # Fast model for development
  huggingface:
    model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    device: "cpu"
    enabled: true

suggestions:
  enabled: false       # Disable for testing
```

### 7. Enterprise Production Setup

```yaml
youtrack:
  url: "https://youtrack.enterprise.com"
  token_file: "/etc/youtrack-mcp/token"
  verify_ssl: true

api:
  max_retries: 5
  retry_delay: 2.0

mcp:
  server_name: "youtrack-mcp-prod"
  server_description: "Production YouTrack MCP Server"
  debug: false

ai:
  enabled: true
  max_memory_mb: 8192
  
  # Production-grade external API
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-prod-key"
    model: "gpt-4"
    max_tokens: 2000
    temperature: 0.2
    timeout: 45
    enabled: true
  
  # High-quality local fallback
  huggingface:
    model: "Qwen/Qwen1.5-1.8B-Chat"
    device: "cpu"
    quantization_4bit: true
    enabled: true

oauth2:
  enabled: true
  client_id: "prod_client_id"
  client_secret: "prod_client_secret"
  token_endpoint: "https://auth.enterprise.com/oauth2/token"
  scope: "youtrack:read youtrack:write"

quirks:
  no_epoch: true

suggestions:
  enabled: true
```

## Environment Variable Overrides

You can override any YAML setting with environment variables using the standard naming convention:

### YouTrack Settings
```bash
export YOUTRACK_URL="https://override.youtrack.com"
export YOUTRACK_API_TOKEN="override_token"
export YOUTRACK_VERIFY_SSL="false"
```

### AI/LLM Settings
```bash
export YOUTRACK_AI_ENABLED="true"
export YOUTRACK_LLM_API_URL="https://api.openai.com/v1"
export YOUTRACK_LLM_API_KEY="sk-override-key"
export YOUTRACK_HF_MODEL="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
export YOUTRACK_HF_ENABLED="true"
```

### MCP Settings
```bash
export MCP_DEBUG="true"
export MCP_SERVER_NAME="youtrack-mcp-dev"
```

## Validation and Testing

### Configuration Validation

The server validates configuration on startup:

```bash
python main.py
# Output:
# INFO - Configuration loaded from: /path/to/config.yaml
# INFO - Configured for YouTrack at: https://youtrack.company.com
# INFO - AI features: enabled (max memory: 2048MB)
# INFO - LLM client initialized with 2 provider(s)
#   1. openai_compatible: gpt-3.5-turbo
#   2. rule_based: default
```

### Test Configuration

Use the test scripts to verify your configuration:

```bash
# Test basic connectivity
python -c "
from youtrack_mcp.config import config
config.validate()
print('Configuration valid!')
"

# Test AI integration
python test_llm_integration.py

# Test full system
python test_ai_integration.py
```

## Configuration Management

### Version Control

**Include in version control:**
```yaml
# config.example.yaml - Template with dummy values
youtrack:
  url: "https://your-youtrack-instance.com"
  api_token: "YOUR_TOKEN_HERE"
  
ai:
  llm:
    api_key: "YOUR_API_KEY_HERE"
```

**Exclude from version control:**
```gitignore
# .gitignore
config.yaml
config.*.yaml
*.local.yaml
```

### Multiple Environments

Use environment-specific configuration files:

```bash
# Development
cp config.example.yaml config.dev.yaml
# Edit config.dev.yaml

# Production
cp config.example.yaml config.prod.yaml
# Edit config.prod.yaml

# Use specific config
python main.py --config config.dev.yaml
```

### Configuration Templates

Create templates for common scenarios:

```bash
# Quick start templates
config.openai.yaml      # OpenAI API setup
config.local.yaml       # Local CPU-only setup
config.hybrid.yaml      # API + local fallback
config.enterprise.yaml  # Production enterprise setup
```

## Security Considerations

### Sensitive Data

**Never commit sensitive data to version control:**
- API tokens
- OAuth2 client secrets
- Private URLs or endpoints

**Use secure storage:**
```yaml
youtrack:
  token_file: "/secure/path/to/token"  # File-based token
  
ai:
  llm:
    api_key: "${OPENAI_API_KEY}"      # Environment variable
```

### File Permissions

Set appropriate permissions on configuration files:
```bash
chmod 600 config.yaml           # Owner read/write only
chmod 640 config.example.yaml   # Owner read/write, group read
```

### Configuration Validation

The system validates sensitive configuration:
- API token format validation
- URL format checking
- Required field validation
- Security audit logging

## Troubleshooting

### Common Issues

#### **"Configuration file not found"**
```bash
# Specify explicit path
python main.py --config ./config.yaml

# Check search paths
python -c "
from youtrack_mcp.config import config
config.load_yaml_config()
"
```

#### **"Invalid YAML syntax"**
```bash
# Validate YAML syntax
python -c "
import yaml
with open('config.yaml') as f:
    yaml.safe_load(f)
print('YAML syntax is valid')
"
```

#### **"Configuration validation failed"**
```bash
# Check required fields
python -c "
from youtrack_mcp.config import config
try:
    config.validate()
    print('Configuration is valid')
except ValueError as e:
    print(f'Configuration error: {e}')
"
```

### Debug Configuration Loading

Enable debug mode to see configuration loading details:

```yaml
mcp:
  debug: true
```

Or use environment variable:
```bash
export MCP_DEBUG=true
python main.py
```

This will show:
- Configuration file search paths
- Loaded configuration values
- Environment variable overrides
- Validation results

## Migration from Environment Variables

To migrate from environment variables to YAML:

1. **Create base configuration:**
   ```bash
   cp config.example.yaml config.yaml
   ```

2. **Extract current environment variables:**
   ```bash
   env | grep YOUTRACK_ > current-env.txt
   ```

3. **Convert to YAML format:**
   ```bash
   # Example conversion:
   # YOUTRACK_URL=https://example.com -> youtrack.url: "https://example.com"
   # YOUTRACK_LLM_API_KEY=sk-key -> ai.llm.api_key: "sk-key"
   ```

4. **Test configuration:**
   ```bash
   python test_llm_integration.py
   ```

5. **Remove environment variables:**
   ```bash
   unset YOUTRACK_URL YOUTRACK_API_TOKEN YOUTRACK_LLM_API_KEY
   # etc.
   ```

The YAML configuration system provides a more maintainable and organized approach to configuring the YouTrack MCP server, especially for complex deployments with multiple AI providers and enterprise settings.