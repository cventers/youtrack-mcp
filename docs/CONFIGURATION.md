# YouTrack MCP Configuration Guide

This document describes all available configuration options for the YouTrack MCP server.

## Configuration File Locations

The server looks for configuration files in the following order:

1. `~/.youtrack-mcp.yaml` (recommended)
2. `./youtrack-mcp.yaml` (current working directory)
3. Environment variables (fallback)

## Configuration Format

Configuration can be provided via YAML file or environment variables. Environment variables override YAML settings.

### YAML Structure

```yaml
# YouTrack Configuration
youtrack_url: "https://your-instance.youtrack.cloud"
youtrack_api_token: "perm-XXXXXXXXXXXXXXXXXXXX"
youtrack_cloud: true
verify_ssl: true
max_retries: 3
retry_delay: 1.0

# MCP Server Configuration
mcp_server_name: "youtrack-mcp"
mcp_server_description: "YouTrack integration for Claude Code"
mcp_debug: false
mcp_transport: "stdio"

# OpenAI Configuration (for AI features)
openai_api_key: "your-openai-api-key"
openai_api_base: "https://api.openai.com/v1"
openai_model: "gpt-4"
openai_max_tokens: 1000
openai_temperature: 0.3
openai_timeout: 30
llm_enabled: true

# Alternative: Hugging Face Models
hf_model: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
hf_device: "cpu"
hf_max_tokens: 500
hf_temperature: 0.3
hf_torch_dtype: "auto"
hf_4bit: false
hf_8bit: false
hf_trust_remote_code: false
hf_enabled: false

# Cache Configuration
cache_enabled: true
cache_ttl: 300
cache_max_size: 100

# Logging Configuration
log_level: "INFO"
log_file: null

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
| `mcp_param_repair` | `MCP_PARAM_REPAIR` | `"false"` | Enable parameter repair |
| `mcp_transport` | `MCP_TRANSPORT` | `"stdio"` | Transport mode (stdio/http) |

### OpenAI Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `openai_api_key` | `OPENAI_API_KEY` | `""` | OpenAI API key |
| `openai_api_base` | `OPENAI_API_BASE` | `""` | OpenAI API base URL |
| `openai_model` | `OPENAI_MODEL` | `""` | OpenAI model name |
| `openai_max_tokens` | `OPENAI_MAX_TOKENS` | `"1000"` | Maximum tokens per request |
| `openai_temperature` | `OPENAI_TEMPERATURE` | `"0.3"` | Response temperature |
| `openai_timeout` | `OPENAI_TIMEOUT` | `"30"` | Request timeout (seconds) |
| `llm_enabled` | `LLM_ENABLED` | `"false"` | Enable LLM features |

### Hugging Face Configuration

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `hf_model` | `HF_MODEL` | `""` | Hugging Face model name |
| `hf_device` | `HF_DEVICE` | `"cpu"` | Device for model inference |
| `hf_max_tokens` | `HF_MAX_TOKENS` | `"500"` | Maximum tokens per request |
| `hf_temperature` | `HF_TEMPERATURE` | `"0.3"` | Response temperature |
| `hf_torch_dtype` | `HF_TORCH_DTYPE` | `"auto"` | PyTorch data type |
| `hf_4bit` | `HF_4BIT` | `"false"` | Enable 4-bit quantization |
| `hf_8bit` | `HF_8BIT` | `"false"` | Enable 8-bit quantization |
| `hf_trust_remote_code` | `HF_TRUST_REMOTE_CODE` | `"false"` | Trust remote code |
| `hf_enabled` | `HF_ENABLED` | `"false"` | Enable Hugging Face features |

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
| `log_file` | `LOG_FILE` | `null` | Log file path |

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

### OpenAI Setup
```yaml
openai_api_key: "sk-..."
openai_model: "gpt-4"
llm_enabled: true
```

### Groq Cloud (Recommended)
```yaml
openai_api_key: "gsk_..."
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
youtrack_api_token: "perm-Y3ZlbnRlcnM=.ODAtMzA=.rMtVyjC6FSRgSyWXYZoojZLbfXSEFK"
youtrack_cloud: true
verify_ssl: true
max_retries: 3
retry_delay: 1.0

mcp_server_name: "youtrack-mcp"
mcp_debug: false

openai_api_key: "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"
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