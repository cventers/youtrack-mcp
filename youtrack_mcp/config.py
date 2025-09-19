"""
Simplified configuration for YouTrack MCP v3 with LiteLLM/Instructor.

This module provides streamlined configuration with provider-agnostic LLM support.
"""

import os
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


class LLMConfig(BaseSettings):
    """Simplified LLM configuration with litellm/instructor support."""

    model_config = ConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )

    # Provider configuration
    provider: str = Field("openai", description="LLM provider (openai, anthropic, gemini, etc.)")
    model: str = Field("gpt-4o-mini", description="Model name without provider prefix")

    # API configuration
    api_key: Optional[SecretStr] = Field(None, description="API key for provider")
    api_base: Optional[str] = Field(None, description="Custom API endpoint")

    # Instructor retry configuration
    max_retries: int = Field(3, description="Max validation retries")
    retry_on_validation_error: bool = Field(True, description="Retry on validation errors")
    timeout: float = Field(60.0, description="Request timeout in seconds")
    temperature: float = Field(0.3, description="Temperature for responses (0.0-2.0)")

    # LiteLLM conversation logging
    log_conversations: bool = Field(False, description="Enable conversation logging")
    log_level: str = Field("INFO", description="Logging level for LLM conversations")
    log_format: str = Field("json", description="Format for conversation logs (json/text)")
    redact_api_keys: bool = Field(True, description="Redact API keys from logs")

    # Template configuration
    template_dir: Optional[Path] = Field(None, description="Template directory (defaults to ai/templates)")

    # Feature flags
    enabled: bool = Field(True, description="Enable LLM features")

    @field_validator('api_key', mode='before')
    def handle_openai_env(cls, v, info):
        """Handle OPENAI_API_KEY env var for backward compatibility."""
        if not v and info.data.get('provider') == 'openai':
            # Check for OPENAI_API_KEY env var
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                return SecretStr(openai_key)
        return v if isinstance(v, SecretStr) else SecretStr(str(v) if v else "")

    @field_validator('enabled', mode='after')
    def auto_enable(cls, v, info):
        """Auto-enable if API key is present."""
        if v is not None:
            return v
        # Auto-enable if we have an API key
        return bool(info.data.get('api_key'))

    @property
    def full_model_name(self) -> str:
        """Get full model name with provider prefix for litellm."""
        if "/" in self.model:
            # Already has provider prefix
            return self.model
        # Add provider prefix
        return f"{self.provider}/{self.model}"


class CacheConfig(BaseSettings):
    """Caching configuration."""

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


class Settings(BaseSettings):
    """Main configuration settings for YouTrack MCP server v3."""

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
    llm: LLMConfig = Field(default_factory=LLMConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)

    def load_from_yaml(self, yaml_file: str) -> None:
        """Load configuration from a YAML file.

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
                if 'llm' in yaml_config:
                    self.llm = LLMConfig(**yaml_config['llm'])
                if 'cache' in yaml_config:
                    self.cache = CacheConfig(**yaml_config['cache'])
                if 'logging' in yaml_config:
                    self.logging = LoggingConfig(**yaml_config['logging'])
                if 'display' in yaml_config:
                    self.display = DisplayConfig(**yaml_config['display'])
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML file {yaml_file}: {e}")

    def get_api_token(self) -> str:
        """Get the API token from configuration.

        Returns:
            str: The API token

        Raises:
            ValueError: If no token is found
        """
        token_value = self.youtrack.api_token.get_secret_value() if self.youtrack.api_token else ""

        if token_value:
            return token_value

        # Try token file if no direct token
        if self.youtrack.token_file and self.youtrack.token_file.exists():
            return self.youtrack.token_file.read_text().strip()

        raise ValueError("No API token found. Set YOUTRACK_API_TOKEN or use --token-file")