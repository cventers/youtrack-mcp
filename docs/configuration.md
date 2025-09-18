# Configuration Guide

The YouTrack MCP server uses a modern configuration system built on `pydantic-settings` that provides type safety, validation, and support for multiple configuration sources.

## Configuration Sources

Configuration is loaded from the following sources in order of precedence (highest to lowest):

1. **Environment Variables** - Override all other settings
2. **YAML Configuration File** - Structured configuration
3. **`.env` File** - Local development settings
4. **Default Values** - Built-in defaults

## Environment Variables

All configuration can be set via environment variables using the following prefixes:

### YouTrack Settings
```bash
YOUTRACK_URL=https://example.youtrack.cloud
YOUTRACK_API_TOKEN=perm:xxx.xxx.xxx
YOUTRACK_CLOUD=true
YOUTRACK_VERIFY_SSL=true
YOUTRACK_MAX_RETRIES=3
YOUTRACK_RETRY_DELAY=1.0
YOUTRACK_TOKEN_TTL_SECONDS=3600
YOUTRACK_ENABLE_TOKEN_REFRESH=true
```

### MCP Settings
```bash
MCP_SERVER_NAME=youtrack-mcp
MCP_SERVER_DESCRIPTION="YouTrack MCP Server"
MCP_DEBUG=false
```

### OpenAI/LLM Settings
```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.3
OPENAI_TIMEOUT=30
OPENAI_LLM_ENABLED=true  # Optional - auto-enables if API key is present
# For backward compatibility, LLM_ENABLED (without prefix) also works
```

**Smart Defaults**: `llm_enabled` automatically defaults to `true` when an API key is configured, `false` otherwise. You can explicitly override this behavior by setting `OPENAI_LLM_ENABLED` or `LLM_ENABLED`.

### Cache Settings
```bash
CACHE_ENABLED=true
CACHE_TTL=300
CACHE_MAX_SIZE=100
```

### Logging Settings
```bash
LOG_LEVEL=INFO
LOG_FILE=/var/log/youtrack-mcp.log
LOG_CONSOLE_DISABLE=false
```

### Display Settings
```bash
DISPLAY_TIMEZONE=America/Chicago
```

## YAML Configuration

Create a `youtrack-mcp-config.yaml` file with the following structure:

```yaml
youtrack:
  url: https://example.youtrack.cloud
  api_token: ${YOUTRACK_API_TOKEN}  # Can reference env vars
  cloud: true
  verify_ssl: true
  max_retries: 3
  retry_delay: 1.0
  token_ttl_seconds: 3600
  enable_token_refresh: true

mcp:
  server_name: youtrack-mcp
  server_description: YouTrack MCP Server
  debug: false

openai:
  api_key: ${OPENAI_API_KEY}
  base_url: https://api.openai.com
  model: gpt-4o-mini
  max_tokens: 1000
  temperature: 0.3
  timeout: 30
  llm_enabled: true  # Auto-enabled if api_key present, can be explicitly set

cache:
  enabled: true
  ttl: 300
  max_size: 100

logging:
  level: INFO
  file: /var/log/youtrack-mcp.log
  console_disable: false

display:
  timezone: America/Chicago
```

To use a YAML configuration file:
1. Set the `YOUTRACK_CONFIG_FILE` environment variable to the file path
2. Or pass `--config /path/to/config.yaml` when running the server

## Required Settings

The following settings are required for the server to function:

- **YOUTRACK_API_TOKEN** - Your YouTrack API token (required)
- **YOUTRACK_URL** - YouTrack instance URL (required for self-hosted, optional for cloud)

## Token Configuration

### Cloud Instances

For YouTrack Cloud instances, the server can automatically detect the workspace from the token format:
- Format: `perm:username.workspace.xxxxx`

Alternatively, set:
- `YOUTRACK_WORKSPACE` - Your workspace name
- `YOUTRACK_URL` - Full URL like `https://workspace.youtrack.cloud`

### Self-Hosted Instances

For self-hosted YouTrack:
- Set `YOUTRACK_URL` to your instance URL
- Set `YOUTRACK_CLOUD=false`

### Token File

Instead of setting the token directly, you can store it in a file:
```bash
YOUTRACK_TOKEN_FILE=/path/to/token/file
```

## Development Setup

For local development, create a `.env` file in the project root:

```env
# YouTrack Configuration
YOUTRACK_URL=https://your-instance.youtrack.cloud
YOUTRACK_API_TOKEN=your-token-here
YOUTRACK_CLOUD=true

# Optional: Enable LLM features
LLM_ENABLED=true
OPENAI_API_KEY=your-openai-key

# Optional: Debug logging
LOG_LEVEL=DEBUG
MCP_DEBUG=true
```

## Docker Configuration

When running in Docker, pass environment variables:

```bash
docker run -e YOUTRACK_URL=https://example.youtrack.cloud \
           -e YOUTRACK_API_TOKEN=your-token \
           -e LLM_ENABLED=true \
           -e OPENAI_API_KEY=your-key \
           youtrack-mcp
```

Or use a env file:
```bash
docker run --env-file .env youtrack-mcp
```

## Configuration Validation

The server validates configuration on startup and will fail with clear error messages if required settings are missing or invalid.

## Removed Configuration Variables

The following configuration variables have been removed in the simplified configuration:

- All feature flags (NATURAL_LANGUAGE_SEARCH, SMART_SUGGESTIONS, etc.)
- Unused display options (DATE_FORMAT, MAX_DESCRIPTION_LENGTH, etc.)
- Unused rate limiting settings
- Unused connection pool settings
- MCP_TRANSPORT and MCP_TIMEOUT (handled by FastMCP)

These features were never implemented and removing them reduces complexity by 55%.