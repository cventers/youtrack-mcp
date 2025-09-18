# YouTrack MCP Configuration Guide

This document describes all available configuration options for the YouTrack MCP server.

## Configuration File Locations

The server looks for configuration files in the following order:

1. `~/.youtrack-mcp.yaml` (recommended)
2. `./youtrack-mcp.yaml` (current working directory)
3. Environment variables (fallback)

## Configuration Format

Configuration can be provided via YAML file or environment variables. Environment variables override YAML settings.

### Configuration Format

Configuration can be provided via YAML file or environment variables. Environment variables override YAML settings.

### YAML Structure

```yaml
# YouTrack Configuration
youtrack:
  url: "https://your-instance.youtrack.cloud"
  api_token: "perm-XXXXXXXXXXXXXXXXXXXX"
  cloud: true
  verify_ssl: true
  max_retries: 3
  retry_delay: 1.0

# MCP Server Configuration
mcp:
  server_name: "youtrack-mcp"
  server_description: "YouTrack MCP Server"
  debug: false
  transport: "stdio"
  timeout: 15000

# AI Configuration
ai:
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-your-openai-key"
    model: "gpt-4o-mini"
    max_tokens: 1000
    temperature: 0.7
    timeout: 30
    enabled: true



# Cache Configuration
cache:
  enabled: true
  ttl: 300
  max_size: 100

# Logging Configuration
logging:
  level: "INFO"
  file: null
  console_disable: false

# Connection Configuration
connection:
  pool_size: 10
  timeout: 30
  read_timeout: 60

# Rate Limiting
rate_limit:
  enabled: true
  requests: 100
  period: 60

# User Preferences
preferences:
  date_format: "%Y-%m-%d"
  datetime_format: "%Y-%m-%d %H:%M:%S"
  timezone: "America/Chicago"
  max_description_length: 500
  truncate_long_text: true
  show_issue_url: false
  default_query_context: "me"
  default_state_filter: "Open"

# Feature Flags
features:
  natural_language_search: false
  smart_suggestions: false
  activity_analysis: false
  auto_field_detection: false
  batch_operations: false
  async_processing: false
  caching_layer: false
```

# Tool-specific Settings
tools:
  search:
    default_limit: 50
    max_limit: 500
    default_sort: "updated desc"

  issue:
    default_fields: ["summary", "description", "state", "priority", "assignee", "created", "updated"]
    include_comments: false
    include_attachments: false
    include_links: false

  project:
    include_custom_fields: true
    include_issue_types: true
    include_workflows: false

# User Preferences
preferences:
  date_format: "%Y-%m-%d"
  datetime_format: "%Y-%m-%d %H:%M:%S"
  timezone: "America/Chicago"
  max_description_length: 500
  truncate_long_text: true
  show_issue_url: false
  default_query_context: "me"
  default_state_filter: "Open"

# Advanced Settings
advanced:
  connection_pool_size: 10
  connection_timeout: 30
  read_timeout: 60
  rate_limit_enabled: true
  rate_limit_requests: 100
  rate_limit_period: 60
  retry_on_status: [429, 500, 502, 503, 504]
  retry_backoff_factor: 2
  custom_headers: {}
  user_agent: "youtrack-mcp/1.0"

# Feature Flags
features:
  natural_language_search: true
  smart_suggestions: true
  activity_analysis: true
  auto_field_detection: true
  batch_operations: true
  async_processing: true
  caching_layer: true
```

## Configuration Sections

### YouTrack Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `youtrack_url` | `YOUTRACK_URL` | `""` | YouTrack instance URL |
| `youtrack_api_token` | `YOUTRACK_API_TOKEN` | `""` | API token for authentication |
| `youtrack_token_file` | `YOUTRACK_TOKEN_FILE` | `""` | Path to token file |
| `youtrack_cloud` | `YOUTRACK_CLOUD` | `"false"` | Whether using YouTrack Cloud |
| `verify_ssl` | `YOUTRACK_VERIFY_SSL` | `"true"` | Verify SSL certificates |
| `max_retries` | `YOUTRACK_MAX_RETRIES` | `"3"` | Maximum API retry attempts |
| `retry_delay` | `YOUTRACK_RETRY_DELAY` | `"1.0"` | Delay between retries (seconds) |

### MCP Server Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `mcp_server_name` | `MCP_SERVER_NAME` | `"youtrack-mcp"` | Server name |
| `mcp_server_description` | `MCP_SERVER_DESCRIPTION` | `"YouTrack MCP Server"` | Server description |
| `mcp_debug` | `MCP_DEBUG` | `"false"` | Enable debug logging |
| `mcp_transport` | `MCP_TRANSPORT` | `"stdio"` | Transport mode (stdio/http) |

### AI Configuration

Error enhancement is always rule-based. NL to YQL translation (ai.plan, search autosearch) requires OpenAI configuration.

### OpenAI Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `openai_api_key` | `OPENAI_API_KEY` | `""` | OpenAI API key |
| `openai_base_url` | `OPENAI_BASE_URL` | `""` | OpenAI API base URL |
| `openai_model` | `OPENAI_MODEL` | `"gpt-4o-mini"` | OpenAI model name |
| `openai_max_tokens` | `OPENAI_MAX_TOKENS` | `"1000"` | Maximum tokens per request |
| `openai_temperature` | `OPENAI_TEMPERATURE` | `"0.7"` | Response temperature |
| `openai_timeout` | `OPENAI_TIMEOUT` | `"30"` | Request timeout (seconds) |
| `llm_enabled` | `LLM_ENABLED` | `"false"` | Enable LLM features |

### Cache Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `cache_enabled` | `CACHE_ENABLED` | `"true"` | Enable caching |
| `cache_ttl` | `CACHE_TTL` | `"300"` | Cache TTL in seconds |
| `cache_max_size` | `CACHE_MAX_SIZE` | `"100"` | Maximum cache size |

### Logging Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `log_level` | `LOG_LEVEL` | `"INFO"` | Logging level |
| `log_file` | `LOG_FILE` | `null` | Log file path (enables console + file logging) |
| `log_console_disable` | `LOG_CONSOLE_DISABLE` | `"false"` | Disable console logging (only log to file if specified) |

**YAML Configuration Example:**
```yaml
logging:
  level: DEBUG
  file: /var/log/youtrack-mcp.log
  console_disable: true
```

### Connection Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `connection_pool_size` | `CONNECTION_POOL_SIZE` | `"10"` | Connection pool size |
| `connection_timeout` | `CONNECTION_TIMEOUT` | `"30"` | Connection timeout |
| `read_timeout` | `READ_TIMEOUT` | `"60"` | Read timeout |

### Rate Limiting

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `rate_limit_enabled` | `RATE_LIMIT_ENABLED` | `"true"` | Enable rate limiting |
| `rate_limit_requests` | `RATE_LIMIT_REQUESTS` | `"100"` | Requests per period |
| `rate_limit_period` | `RATE_LIMIT_PERIOD` | `"60"` | Rate limit period (seconds) |

### User Preferences

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `date_format` | `DATE_FORMAT` | `"%Y-%m-%d"` | Date format |
| `datetime_format` | `DATETIME_FORMAT` | `"%Y-%m-%d %H:%M:%S"` | DateTime format |
| `timezone` | `TIMEZONE` | `"America/Chicago"` | Timezone |
| `max_description_length` | `MAX_DESCRIPTION_LENGTH` | `"500"` | Max description length |
| `truncate_long_text` | `TRUNCATE_LONG_TEXT` | `"true"` | Truncate long text |
| `show_issue_url` | `SHOW_ISSUE_URL` | `"false"` | Show issue URLs |
| `default_query_context` | `DEFAULT_QUERY_CONTEXT` | `"me"` | Default query context |
| `default_state_filter` | `DEFAULT_STATE_FILTER` | `"Open"` | Default state filter |

### Feature Flags

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `natural_language_search` | `NATURAL_LANGUAGE_SEARCH` | `"false"` | Enable natural language search |
| `smart_suggestions` | `SMART_SUGGESTIONS` | `"false"` | Enable smart suggestions |
| `activity_analysis` | `ACTIVITY_ANALYSIS` | `"false"` | Enable activity analysis |
| `auto_field_detection` | `AUTO_FIELD_DETECTION` | `"false"` | Enable auto field detection |
| `batch_operations` | `BATCH_OPERATIONS` | `"false"` | Enable batch operations |
| `async_processing` | `ASYNC_PROCESSING` | `"false"` | Enable async processing |
| `caching_layer` | `CACHING_LAYER` | `"false"` | Enable caching layer |

## Environment Variable Overrides

All YAML settings can be overridden using environment variables with the `YOUTRACK_MCP_` prefix:

```bash
export YOUTRACK_MCP_YOUTRACK_URL="https://your-instance.youtrack.cloud"
export YOUTRACK_MCP_YOUTRACK_API_TOKEN="your-token"
export YOUTRACK_MCP_LOG_LEVEL="DEBUG"
```

Or use direct environment variables (these take precedence over YOUTRACK_MCP_ prefixed ones):

```bash
export YOUTRACK_URL="https://your-instance.youtrack.cloud"
export YOUTRACK_API_TOKEN="your-token"
export LOG_LEVEL="DEBUG"
```

## Authentication

### YouTrack Cloud
For YouTrack Cloud instances, you typically only need the API token:

```yaml
youtrack_api_token: "perm-XXXXXXXXXXXXXXXXXXXX"
youtrack_cloud: true
```

### Self-Hosted YouTrack
For self-hosted instances, provide the full URL:

```yaml
youtrack_url: "https://your-youtrack-instance.com"
youtrack_api_token: "perm-XXXXXXXXXXXXXXXXXXXX"
youtrack_cloud: false
```

### Token File
Alternatively, store the token in a file:

```yaml
youtrack_token_file: "/path/to/token/file"
```

## AI Integration

### AI Configuration
- **Error Enhancement**: Always rule-based (no configuration required)
- **NL to YQL Translation**: Requires OpenAI configuration for ai.plan and search autosearch

```yaml
# YAML format
ai:
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-..."
    model: "gpt-4o-mini"
    temperature: 0.7
    enabled: true
```

```bash
# Environment variables
export YOUTRACK_MCP_OPENAI_API_KEY="sk-..."
export YOUTRACK_MCP_OPENAI_BASE_URL="https://api.openai.com/v1"
export YOUTRACK_MCP_OPENAI_MODEL="gpt-4o-mini"
export YOUTRACK_MCP_OPENAI_TEMPERATURE="0.7"
export YOUTRACK_MCP_LLM_ENABLED="true"
```

### OpenAI Setup
```yaml
ai:
  llm:
    api_key: "sk-..."
    model: "gpt-4"
    enabled: true
```

```bash
export YOUTRACK_MCP_OPENAI_API_KEY="sk-..."
export YOUTRACK_MCP_OPENAI_MODEL="gpt-4"
export YOUTRACK_MCP_LLM_ENABLED="true"
```

### Groq Cloud (Recommended)
```yaml
openai_api_key: "your-groq-api-key-here"
openai_api_base: "https://api.groq.com/openai/v1"
openai_model: "openai/gpt-oss-120b"
llm_enabled: true
```

### Hugging Face (Local)
```yaml
hf_model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
hf_device: "cpu"
hf_enabled: true
```

## Examples

### Minimal Configuration
```yaml
youtrack_api_token: "perm-XXXXXXXXXXXXXXXXXXXX"
youtrack_cloud: true
```

### Full Configuration
```yaml
youtrack_url: "https://exceleron.myjetbrains.com"
youtrack_api_token: ""your-youtrack-api-token""
youtrack_cloud: true
verify_ssl: true
max_retries: 3
retry_delay: 1.0

mcp_server_name: "youtrack-mcp"
mcp_debug: false

openai_api_key: "your-openai-api-key-here"
openai_api_base: "https://api.groq.com/openai/v1"
openai_model: "openai/gpt-oss-120b"
llm_enabled: true

cache_enabled: true
log_level: "INFO"

features:
  natural_language_search: true
  smart_suggestions: true
```

## Validation

The server validates configuration on startup and will exit with an error if required settings are missing or invalid.