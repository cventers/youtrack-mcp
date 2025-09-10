"""
Configuration for YouTrack MCP server.
"""

import os
import ssl
from typing import Optional, Dict, Any

# Optional import for dotenv
try:
    from dotenv import load_dotenv

    # Load environment variables from .env file if it exists
    load_dotenv()
except ImportError:
    # dotenv is not required
    pass


class Config:
    """Configuration settings for YouTrack MCP server."""

    # Configuration file
    CONFIG_FILE: str = os.getenv("YOUTRACK_CONFIG_FILE", "")

    # YouTrack API configuration
    YOUTRACK_URL: str = os.getenv("YOUTRACK_URL", "")
    YOUTRACK_API_TOKEN: str = os.getenv("YOUTRACK_API_TOKEN", "")
    YOUTRACK_TOKEN_FILE: str = os.getenv("YOUTRACK_TOKEN_FILE", "")
    VERIFY_SSL: bool = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    # Cloud instance configuration
    YOUTRACK_CLOUD: bool = os.getenv("YOUTRACK_CLOUD", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # API client configuration
    MAX_RETRIES: int = int(os.getenv("YOUTRACK_MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("YOUTRACK_RETRY_DELAY", "1.0"))

    # Token security configuration
    TOKEN_TTL_SECONDS: int = int(os.getenv("YOUTRACK_TOKEN_TTL_SECONDS", "3600"))  # 1 hour default
    ENABLE_TOKEN_REFRESH: bool = os.getenv("YOUTRACK_ENABLE_TOKEN_REFRESH", "true").lower() in (
        "true", "1", "yes"
    )

    # MCP Server configuration
    MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "youtrack-mcp")
    MCP_SERVER_DESCRIPTION: str = os.getenv(
        "MCP_SERVER_DESCRIPTION", "YouTrack MCP Server"
    )
    MCP_DEBUG: bool = os.getenv("MCP_DEBUG", "false").lower() in (
        "true", "1", "yes",
    )
    MCP_PARAM_REPAIR: bool = os.getenv("MCP_PARAM_REPAIR", "false").lower() in (
        "true", "1", "yes",
    )
    MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")
    MCP_TIMEOUT: int = int(os.getenv("MCP_TIMEOUT", "15000"))  # Default 15 seconds
    YOUTRACK_CAPS: str = os.getenv("YOUTRACK_CAPS", "")

    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Hugging Face Configuration
    HF_MODEL: str = os.getenv("HF_MODEL", "")
    HF_DEVICE: str = os.getenv("HF_DEVICE", "cpu")
    HF_MAX_TOKENS: int = int(os.getenv("HF_MAX_TOKENS", "500"))
    HF_TEMPERATURE: float = float(os.getenv("HF_TEMPERATURE", "0.3"))
    HF_TORCH_DTYPE: str = os.getenv("HF_TORCH_DTYPE", "auto")
    HF_4BIT: bool = os.getenv("HF_4BIT", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    HF_8BIT: bool = os.getenv("HF_8BIT", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    HF_TRUST_REMOTE_CODE: bool = os.getenv("HF_TRUST_REMOTE_CODE", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    HF_ENABLED: bool = os.getenv("HF_ENABLED", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Cache Configuration
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "100"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

    # Connection Configuration
    CONNECTION_POOL_SIZE: int = int(os.getenv("CONNECTION_POOL_SIZE", "10"))
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "30"))
    READ_TIMEOUT: int = int(os.getenv("READ_TIMEOUT", "60"))

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

    # User Preferences
    DATE_FORMAT: str = os.getenv("DATE_FORMAT", "%Y-%m-%d")
    DATETIME_FORMAT: str = os.getenv("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Chicago")
    MAX_DESCRIPTION_LENGTH: int = int(os.getenv("MAX_DESCRIPTION_LENGTH", "500"))
    TRUNCATE_LONG_TEXT: bool = os.getenv("TRUNCATE_LONG_TEXT", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    SHOW_ISSUE_URL: bool = os.getenv("SHOW_ISSUE_URL", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    DEFAULT_QUERY_CONTEXT: str = os.getenv("DEFAULT_QUERY_CONTEXT", "me")
    DEFAULT_STATE_FILTER: str = os.getenv("DEFAULT_STATE_FILTER", "Open")

    # Feature Flags
    NATURAL_LANGUAGE_SEARCH: bool = os.getenv("NATURAL_LANGUAGE_SEARCH", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    SMART_SUGGESTIONS: bool = os.getenv("SMART_SUGGESTIONS", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    ACTIVITY_ANALYSIS: bool = os.getenv("ACTIVITY_ANALYSIS", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    AUTO_FIELD_DETECTION: bool = os.getenv("AUTO_FIELD_DETECTION", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    BATCH_OPERATIONS: bool = os.getenv("BATCH_OPERATIONS", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    ASYNC_PROCESSING: bool = os.getenv("ASYNC_PROCESSING", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    CACHING_LAYER: bool = os.getenv("CACHING_LAYER", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from a dictionary.

        Args:
            config_dict: Dictionary with configuration values
        """
        # Set configuration values from the dictionary
        for key, value in config_dict.items():
            if hasattr(cls, key):
                setattr(cls, key, value)

    @classmethod
    def get_api_token(cls) -> str:
        """
        Get the API token from environment variable or token file with lazy loading.

        Returns:
            str: The API token

        Raises:
            ValueError: If no token is found
        """
        # First try environment variable (lazy loaded)
        token = os.getenv("YOUTRACK_API_TOKEN", "")
        if token:
            return token

        # Then try token file (lazy loaded)
        token_file = os.getenv("YOUTRACK_TOKEN_FILE", "")
        if token_file:
            try:
                with open(token_file, "r") as f:
                    token = f.read().strip()
                    if token:
                        return token
            except (FileNotFoundError, IOError) as e:
                raise ValueError(
                    f"Could not read token file {token_file}: {e}"
                )

        raise ValueError(
            "YouTrack API token is required. Provide it using YOUTRACK_API_TOKEN environment variable, "
            "YOUTRACK_TOKEN_FILE environment variable, or in configuration."
        )

    @classmethod
    def validate(cls) -> None:
        """
        Validate the configuration settings.

        Raises:
            ValueError: If required settings are missing or invalid
        """
        # API token is always required (from env var or file)
        try:
            cls.get_api_token()
        except ValueError as e:
            raise e

        # URL is only required for self-hosted instances (Cloud instances can use API token only)
        if not cls.YOUTRACK_CLOUD and not cls.YOUTRACK_URL:
            raise ValueError(
                "YouTrack URL is required for self-hosted instances. Provide it using YOUTRACK_URL environment variable or set YOUTRACK_CLOUD=true for cloud instances."
            )

        # If URL is provided, ensure it doesn't end with a trailing slash
        if cls.YOUTRACK_URL:
            cls.YOUTRACK_URL = cls.YOUTRACK_URL.rstrip("/")

    @classmethod
    def get_ssl_context(cls) -> Optional[ssl.SSLContext]:
        """
        Get SSL context for HTTPS requests.

        Returns:
            SSLContext with proper configuration or None for default behavior
        """
        if not cls.VERIFY_SSL:
            # Create a context that doesn't verify certificates
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        return None

    @classmethod
    def is_cloud_instance(cls) -> bool:
        """
        Check if the configured YouTrack instance is a cloud instance.

        Returns:
            True if the instance is a cloud instance, False otherwise
        """
        return cls.YOUTRACK_CLOUD or not cls.YOUTRACK_URL

    @classmethod
    def get_base_url(cls) -> str:
        """
        Get the base URL for the YouTrack instance API.

        For self-hosted instances, this is the configured URL.
        For cloud instances, this is the workspace-specific youtrack.cloud API URL,
        which is extracted from the API token or used directly if provided.

        Returns:
            Base URL for the YouTrack API
        """
        # If URL is explicitly provided, use it regardless of cloud setting
        if cls.YOUTRACK_URL:
            # Remove trailing slash to prevent double slashes
            clean_url = cls.YOUTRACK_URL.rstrip('/')
            return f"{clean_url}/api"

        # For cloud instances without explicit URL, try to extract from token
        if cls.is_cloud_instance():
            # Handle both token formats: perm: and perm-
            if "." in cls.YOUTRACK_API_TOKEN and (
                cls.YOUTRACK_API_TOKEN.startswith("perm:")
                or cls.YOUTRACK_API_TOKEN.startswith("perm-")
            ):
                token_parts = cls.YOUTRACK_API_TOKEN.split(".")

                # Extract workspace from specific token formats
                if len(token_parts) > 1:
                    # For format: perm:username.workspace.12345...
                    if cls.YOUTRACK_API_TOKEN.startswith("perm:"):
                        workspace = token_parts[1]
                        return f"https://{workspace}.youtrack.cloud/api"

                    # For format: perm-base64.base64.hash
                    elif cls.YOUTRACK_API_TOKEN.startswith("perm-"):
                        # If we have a fixed workspace name from environment, use it
                        if os.getenv("YOUTRACK_WORKSPACE"):
                            workspace = os.getenv("YOUTRACK_WORKSPACE")
                            return f"https://{workspace}.youtrack.cloud/api"

                        if os.getenv("YOUTRACK_URL"):
                            return f"{os.getenv('YOUTRACK_URL')}/api"

            # Fallback error with better guidance
            raise ValueError(
                "Could not determine YouTrack Cloud URL. Please either:\n"
                "1. Set YOUTRACK_URL to your YouTrack Cloud URL (e.g., https://yourworkspace.youtrack.cloud)\n"
                "2. Set YOUTRACK_WORKSPACE to your workspace name\n"
                "3. Use a token in the format perm:username.workspace.12345..."
            )

        # Should never reach here as is_cloud_instance() returns True if URL is missing
        raise ValueError(
            "YouTrack URL is required. Please set YOUTRACK_URL environment variable."
        )


# Create a global config instance
config = Config()
