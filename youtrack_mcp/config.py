"""
Configuration management using pydantic-settings.

This module provides type-safe, validated configuration for the YouTrack MCP server
using pydantic-settings, supporting environment variables, YAML files, and .env files.
"""

import os
import ssl
from typing import Optional, Literal, Dict
from pathlib import Path
from pydantic import Field, SecretStr, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)


class YouTrackConfig(BaseSettings):
    """YouTrack connection configuration."""
    
    model_config = ConfigDict(
        env_prefix="YOUTRACK_",
        case_sensitive=False,
    )
    
    url: str = Field("", description="YouTrack instance URL")
    api_token: SecretStr = Field(SecretStr(""), description="API authentication token")
    token_file: Optional[Path] = Field(None, description="Path to token file")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    cloud: bool = Field(False, description="Is this a cloud instance")
    workspace: Optional[str] = Field(None, description="Cloud workspace name")
    
    # Retry configuration
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, ge=0, description="Retry delay in seconds")
    
    # Token management
    token_ttl_seconds: int = Field(3600, ge=60, description="Token cache TTL")
    enable_token_refresh: bool = Field(True, description="Enable auto token refresh")
    
    @field_validator('api_token', mode='before')
    def load_token_from_file(cls, v, info):
        """Load token from file if token_file is specified."""
        if not v and info.data.get('token_file'):
            token_path = Path(info.data['token_file'])
            if token_path.exists():
                token = token_path.read_text().strip()
                return SecretStr(token)
        return v if isinstance(v, SecretStr) else SecretStr(str(v) if v else "")
    
    @field_validator('url', mode='after')
    def clean_url(cls, v):
        """Remove trailing slashes from URL."""
        if v:
            return v.rstrip('/')
        return v


class MCPConfig(BaseSettings):
    """MCP server configuration."""
    
    model_config = ConfigDict(
        env_prefix="MCP_",
        case_sensitive=False,
    )
    
    server_name: str = Field("youtrack-mcp", description="Server name")
    server_description: str = Field("YouTrack MCP Server", description="Server description")
    debug: bool = Field(False, description="Enable debug mode")


class OpenAIConfig(BaseSettings):
    """OpenAI/LLM configuration."""
    
    model_config = ConfigDict(
        env_prefix="OPENAI_",
        case_sensitive=False,
        extra='ignore',
    )
    
    api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    base_url: Optional[str] = Field(None, description="OpenAI base URL")
    model: str = Field("gpt-4o-mini", description="Model name")
    max_tokens: int = Field(1000, ge=1, description="Maximum tokens for completion")
    temperature: float = Field(0.3, ge=0, le=2, description="Temperature")
    timeout: int = Field(30, ge=1, description="Request timeout")
    llm_enabled: Optional[bool] = Field(None, description="Enable LLM features (auto-enabled if API key present)")
    
    @field_validator('llm_enabled', mode='after')
    def set_llm_enabled_default(cls, v, info):
        """Default llm_enabled to True if api_key is present, False otherwise."""
        if v is not None:
            return v
        # Check for LLM_ENABLED env var (without OPENAI_ prefix for backward compat)
        env_val = os.getenv("LLM_ENABLED")
        if env_val is not None:
            return env_val.lower() in ("true", "1", "yes")
        # Default to True if api_key is present
        return bool(info.data.get('api_key'))


class CacheConfig(BaseSettings):
    """Caching configuration (future feature)."""
    
    model_config = ConfigDict(
        env_prefix="CACHE_",
        case_sensitive=False,
    )
    
    enabled: bool = Field(True, description="Enable caching")
    ttl: int = Field(300, ge=0, description="Cache TTL in seconds")
    max_size: int = Field(100, ge=1, description="Maximum cache size")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    model_config = ConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
    )
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Log level"
    )
    file: Optional[Path] = Field(None, description="Log file path")
    console_disable: bool = Field(False, description="Disable console logging")


class DisplayConfig(BaseSettings):
    """Display configuration."""
    
    model_config = ConfigDict(
        env_prefix="DISPLAY_",
        case_sensitive=False,
    )
    
    timezone: Optional[str] = Field("America/Chicago", description="Timezone for date/time operations")


class LLMConfig(BaseSettings):
    """LLM-specific configuration for enhanced prompting."""

    model_config = ConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )

    # Output mode configuration (tristate)
    output_mode: Literal["json_schema", "json_object", "inline"] = Field(
        "json_schema",
        description="Output mode: json_schema (strict), json_object (validated), inline (flexible)"
    )

    # Retry configuration
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts for LLM calls")
    initial_backoff: float = Field(1.0, ge=0.1, le=10.0, description="Initial backoff delay in seconds")
    backoff_multiplier: float = Field(2.0, ge=1.0, le=5.0, description="Backoff multiplier for exponential backoff")
    min_confidence: float = Field(0.6, ge=0.0, le=1.0, description="Minimum confidence threshold")

    # Token limits nested by operation type (for response/completion only, not input)
    max_tokens: Dict[str, int] = Field(
        default={
            "yql": 500,      # Response tokens for YQL translation
            "error": 800,    # Response tokens for error enhancement
            "intent": 1500   # Response tokens for intent analysis
        },
        description="Max tokens for LLM response per operation type (does not include input tokens)"
    )

    # Cache settings
    cache_ttl: int = Field(3600, ge=60, description="Cache TTL in seconds (default 1 hour)")

    # Validation settings (only apply to inline mode)
    extract_json_from_markdown: bool = Field(True, description="Try to extract JSON from markdown blocks")


class Settings(BaseSettings):
    """Main configuration settings for YouTrack MCP server."""
    
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Nested configurations
    youtrack: YouTrackConfig = Field(default_factory=YouTrackConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    def load_from_yaml(self, yaml_file: str) -> None:
        """
        Load configuration from a YAML file.
        
        Args:
            yaml_file: Path to the YAML configuration file
        """
        import yaml
        
        if not os.path.exists(yaml_file):
            raise FileNotFoundError(f"YAML configuration file not found: {yaml_file}")
        
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
            
            if yaml_config:
                # Update nested configs
                if 'youtrack' in yaml_config:
                    self.youtrack = YouTrackConfig(**yaml_config['youtrack'])
                if 'mcp' in yaml_config:
                    self.mcp = MCPConfig(**yaml_config['mcp'])
                if 'openai' in yaml_config:
                    self.openai = OpenAIConfig(**yaml_config['openai'])
                if 'cache' in yaml_config:
                    self.cache = CacheConfig(**yaml_config['cache'])
                if 'logging' in yaml_config:
                    self.logging = LoggingConfig(**yaml_config['logging'])
                if 'display' in yaml_config:
                    self.display = DisplayConfig(**yaml_config['display'])
                if 'llm' in yaml_config:
                    self.llm = LLMConfig(**yaml_config['llm'])
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML file {yaml_file}: {e}")
    
    def get_api_token(self) -> str:
        """
        Get the API token from configuration.
        
        Returns:
            str: The API token
            
        Raises:
            ValueError: If no token is found
        """
        token_value = self.youtrack.api_token.get_secret_value() if self.youtrack.api_token else ""
        
        if token_value:
            return token_value
        
        # Try token file if no direct token
        if self.youtrack.token_file and Path(self.youtrack.token_file).exists():
            try:
                token_value = Path(self.youtrack.token_file).read_text().strip()
                if token_value:
                    return token_value
            except (FileNotFoundError, IOError) as e:
                logger.error(f"Could not read token file: {e}")
        
        raise ValueError(
            "YouTrack API token is required. Provide it using YOUTRACK_API_TOKEN environment variable, "
            "YOUTRACK_TOKEN_FILE environment variable, or in configuration."
        )
    
    def validate(self) -> None:
        """
        Validate the configuration settings.
        
        Raises:
            ValueError: If required settings are missing or invalid
        """
        # API token is always required
        self.get_api_token()
        
        # URL is only required for self-hosted instances
        if not self.youtrack.cloud and not self.youtrack.url:
            raise ValueError(
                "YouTrack URL is required for self-hosted instances. "
                "Provide it using YOUTRACK_URL environment variable or set YOUTRACK_CLOUD=true for cloud instances."
            )
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        Get SSL context for HTTPS requests.
        
        Returns:
            SSLContext with proper configuration or None for default behavior
        """
        if not self.youtrack.verify_ssl:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        return None
    
    def is_cloud_instance(self) -> bool:
        """
        Check if the configured YouTrack instance is a cloud instance.
        
        Returns:
            True if the instance is a cloud instance, False otherwise
        """
        return self.youtrack.cloud or not self.youtrack.url
    
    def get_base_url(self) -> str:
        """
        Get the base URL for the YouTrack instance API.
        
        Returns:
            Base URL for the YouTrack API
        """
        if self.youtrack.url:
            return f"{self.youtrack.url}/api"
        
        if self.is_cloud_instance():
            token_value = self.youtrack.api_token.get_secret_value() if self.youtrack.api_token else ""
            
            # Handle both token formats
            if "." in token_value and (
                token_value.startswith("perm:") or token_value.startswith("perm-")
            ):
                token_parts = token_value.split(".")
                
                if len(token_parts) > 1 and token_value.startswith("perm:"):
                    workspace = token_parts[1]
                    return f"https://{workspace}.youtrack.cloud/api"
                elif self.youtrack.workspace:
                    return f"https://{self.youtrack.workspace}.youtrack.cloud/api"
            
            if self.youtrack.workspace:
                return f"https://{self.youtrack.workspace}.youtrack.cloud/api"
            
            raise ValueError(
                "Could not determine YouTrack Cloud URL. Please either:\n"
                "1. Set YOUTRACK_URL to your YouTrack Cloud URL\n"
                "2. Set YOUTRACK_WORKSPACE to your workspace name\n"
                "3. Use a token in the format perm:username.workspace.12345..."
            )
        
        raise ValueError("YouTrack URL is required. Please set YOUTRACK_URL environment variable.")


# Backward compatibility layer for old Config class
class Config:
    """
    Backward compatibility wrapper for the old Config class.
    This allows existing code to work without modification.
    """
    
    def __init__(self):
        self._settings = Settings()
    
    def __getattr__(self, name):
        """Map old attribute names to new structure."""
        # Direct mappings
        if name == "YOUTRACK_URL":
            return self._settings.youtrack.url
        elif name == "YOUTRACK_API_TOKEN":
            token = self._settings.youtrack.api_token
            return token.get_secret_value() if token else ""
        elif name == "YOUTRACK_TOKEN_FILE":
            return str(self._settings.youtrack.token_file) if self._settings.youtrack.token_file else ""
        elif name == "VERIFY_SSL":
            return self._settings.youtrack.verify_ssl
        elif name == "YOUTRACK_CLOUD":
            return self._settings.youtrack.cloud
        elif name == "MAX_RETRIES":
            return self._settings.youtrack.max_retries
        elif name == "RETRY_DELAY":
            return self._settings.youtrack.retry_delay
        elif name == "TOKEN_TTL_SECONDS":
            return self._settings.youtrack.token_ttl_seconds
        elif name == "ENABLE_TOKEN_REFRESH":
            return self._settings.youtrack.enable_token_refresh
        
        # MCP settings
        elif name == "MCP_SERVER_NAME":
            return self._settings.mcp.server_name
        elif name == "MCP_SERVER_DESCRIPTION":
            return self._settings.mcp.server_description
        elif name == "MCP_DEBUG":
            return self._settings.mcp.debug
        
        # OpenAI settings
        elif name == "OPENAI_API_KEY":
            key = self._settings.openai.api_key
            return key.get_secret_value() if key else ""
        elif name == "OPENAI_BASE_URL":
            return self._settings.openai.base_url or ""
        elif name == "OPENAI_MODEL":
            return self._settings.openai.model
        elif name == "OPENAI_MAX_TOKENS":
            return self._settings.openai.max_tokens
        elif name == "OPENAI_TEMPERATURE":
            return self._settings.openai.temperature
        elif name == "OPENAI_TIMEOUT":
            return self._settings.openai.timeout
        elif name == "LLM_ENABLED":
            return self._settings.openai.llm_enabled
        
        # Cache settings
        elif name == "CACHE_ENABLED":
            return self._settings.cache.enabled
        elif name == "CACHE_TTL":
            return self._settings.cache.ttl
        elif name == "CACHE_MAX_SIZE":
            return self._settings.cache.max_size
        
        # Logging settings
        elif name == "LOG_LEVEL":
            return self._settings.logging.level
        elif name == "LOG_FILE":
            return str(self._settings.logging.file) if self._settings.logging.file else None
        elif name == "LOG_CONSOLE_DISABLE":
            return self._settings.logging.console_disable
        
        # Display settings
        elif name == "TIMEZONE":
            return self._settings.display.timezone
        
        # Default for unknown attributes
        else:
            # Return empty string for removed feature flags to avoid errors
            removed_flags = [
                "NATURAL_LANGUAGE_SEARCH", "SMART_SUGGESTIONS", "ACTIVITY_ANALYSIS",
                "AUTO_FIELD_DETECTION", "BATCH_OPERATIONS", "ASYNC_PROCESSING",
                "CACHING_LAYER", "DEFAULT_QUERY_CONTEXT", "DEFAULT_STATE_FILTER",
                "SHOW_ISSUE_URL", "MAX_DESCRIPTION_LENGTH", "TRUNCATE_LONG_TEXT",
                "DATE_FORMAT", "DATETIME_FORMAT", "RATE_LIMIT_ENABLED",
                "RATE_LIMIT_REQUESTS", "RATE_LIMIT_PERIOD", "CONNECTION_POOL_SIZE",
                "CONNECTION_TIMEOUT", "READ_TIMEOUT", "MCP_TRANSPORT", "MCP_TIMEOUT",
                "YOUTRACK_CAPS", "CONFIG_FILE"
            ]
            if name in removed_flags:
                return "" if name.endswith("_FORMAT") or name.endswith("_FILTER") or name.endswith("_CONTEXT") else False
            raise AttributeError(f"Config has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """Allow setting attributes for backward compatibility."""
        if name == "_settings":
            super().__setattr__(name, value)
        elif name == "YOUTRACK_URL":
            self._settings.youtrack.url = value
        elif name == "YOUTRACK_API_TOKEN":
            self._settings.youtrack.api_token = SecretStr(value)
        elif name == "YOUTRACK_CLOUD":
            self._settings.youtrack.cloud = value
        elif name == "VERIFY_SSL":
            self._settings.youtrack.verify_ssl = value
        elif name == "OPENAI_TEMPERATURE":
            self._settings.openai.temperature = value
        elif name == "OPENAI_TIMEOUT":
            self._settings.openai.timeout = value
        elif name == "LLM_ENABLED":
            self._settings.openai.llm_enabled = value
        elif name == "LOG_LEVEL":
            self._settings.logging.level = value
        elif name == "LOG_FILE":
            self._settings.logging.file = Path(value) if value else None
        elif name == "LOG_CONSOLE_DISABLE":
            self._settings.logging.console_disable = value
        else:
            # Ignore setting of removed attributes
            pass
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> None:
        """Update configuration from a dictionary (backward compat)."""
        global config
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    def load_from_yaml(self, yaml_file: str) -> None:
        """Load configuration from YAML file (backward compat)."""
        self._settings.load_from_yaml(yaml_file)
    
    def get_api_token(self) -> str:
        """Get the API token (backward compat)."""
        return self._settings.get_api_token()
    
    def validate(self) -> None:
        """Validate configuration (backward compat)."""
        return self._settings.validate()
    
    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context (backward compat)."""
        return self._settings.get_ssl_context()
    
    def is_cloud_instance(self) -> bool:
        """Check if cloud instance (backward compat)."""
        return self._settings.is_cloud_instance()
    
    def get_base_url(self) -> str:
        """Get base URL (backward compat)."""
        return self._settings.get_base_url()


# Global instances for backward compatibility
config = Config()
settings = config._settings  # Direct access to new settings if needed