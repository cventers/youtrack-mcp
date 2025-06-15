"""
Configuration for YouTrack MCP server.
"""
import os
import ssl
import logging
from typing import Optional, Dict, Any

# Optional import for dotenv
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
except ImportError:
    # dotenv is not required
    pass

# Import security utilities (with fallback if not available)
try:
    from .security import (
        token_validator, 
        credential_manager, 
        audit_log,
        TokenFileManager
    )
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

# Import OAuth2/OIDC utilities (with fallback if not available)
try:
    from .auth import (
        OAuth2Config,
        OAuth2Manager,
        create_youtrack_oauth2_config,
        create_generic_oauth2_config
    )
    OAUTH2_AVAILABLE = True
except ImportError:
    OAUTH2_AVAILABLE = False

logger = logging.getLogger(__name__)


class Config:
    """Configuration settings for YouTrack MCP server."""
    
    # YouTrack API configuration
    YOUTRACK_URL: str = os.getenv("YOUTRACK_URL", "")
    YOUTRACK_API_TOKEN: str = os.getenv("YOUTRACK_API_TOKEN", "")
    YOUTRACK_TOKEN_FILE: str = os.getenv("YOUTRACK_TOKEN_FILE", "")
    VERIFY_SSL: bool = os.getenv("YOUTRACK_VERIFY_SSL", "true").lower() in ("true", "1", "yes")
    
    # Cloud instance configuration
    YOUTRACK_CLOUD: bool = os.getenv("YOUTRACK_CLOUD", "false").lower() in ("true", "1", "yes")
    
    # API client configuration
    MAX_RETRIES: int = int(os.getenv("YOUTRACK_MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("YOUTRACK_RETRY_DELAY", "1.0"))
    
    # MCP Server configuration
    MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "youtrack-mcp")
    MCP_SERVER_DESCRIPTION: str = os.getenv("MCP_SERVER_DESCRIPTION", "YouTrack MCP Server")
    MCP_DEBUG: bool = os.getenv("MCP_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # OAuth2/OIDC configuration
    OAUTH2_ENABLED: bool = os.getenv("OAUTH2_ENABLED", "false").lower() in ("true", "1", "yes")
    OAUTH2_CLIENT_ID: str = os.getenv("OAUTH2_CLIENT_ID", "")
    OAUTH2_CLIENT_SECRET: str = os.getenv("OAUTH2_CLIENT_SECRET", "")
    OAUTH2_TOKEN_ENDPOINT: str = os.getenv("OAUTH2_TOKEN_ENDPOINT", "")
    OAUTH2_AUTHORIZATION_ENDPOINT: str = os.getenv("OAUTH2_AUTHORIZATION_ENDPOINT", "")
    OAUTH2_USERINFO_ENDPOINT: str = os.getenv("OAUTH2_USERINFO_ENDPOINT", "")
    OAUTH2_JWKS_URI: str = os.getenv("OAUTH2_JWKS_URI", "")
    OAUTH2_ISSUER: str = os.getenv("OAUTH2_ISSUER", "")
    OAUTH2_SCOPE: str = os.getenv("OAUTH2_SCOPE", "openid profile")
    OAUTH2_GRANT_TYPE: str = os.getenv("OAUTH2_GRANT_TYPE", "client_credentials")
    
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
    def validate(cls) -> None:
        """
        Validate the configuration settings with enhanced security.
        
        Raises:
            ValueError: If required settings are missing or invalid
        """
        token_source = "unknown"
        
        # Try multiple sources for the API token in order of preference
        if not cls.YOUTRACK_API_TOKEN:
            # 1. Try keyring first (most secure)
            if SECURITY_AVAILABLE:
                keyring_username = os.getenv("YOUTRACK_KEYRING_USERNAME", "default")
                keyring_token = credential_manager.retrieve_token(keyring_username)
                if keyring_token:
                    cls.YOUTRACK_API_TOKEN = keyring_token
                    token_source = "keyring"
                    logger.info("Token loaded from secure keyring")
            
            # 2. Try token file
            if not cls.YOUTRACK_API_TOKEN and cls.YOUTRACK_TOKEN_FILE:
                if SECURITY_AVAILABLE:
                    # Use secure file reader
                    file_token = TokenFileManager.read_token_file(cls.YOUTRACK_TOKEN_FILE)
                    if file_token:
                        cls.YOUTRACK_API_TOKEN = file_token
                        token_source = "secure_file"
                else:
                    # Fallback to basic file reading
                    try:
                        with open(cls.YOUTRACK_TOKEN_FILE, 'r') as f:
                            cls.YOUTRACK_API_TOKEN = f.read().strip()
                        token_source = "file"
                        logger.warning(f"Token loaded from file without security validation: {cls.YOUTRACK_TOKEN_FILE}")
                    except Exception as e:
                        raise ValueError(f"Failed to read YouTrack API token from file {cls.YOUTRACK_TOKEN_FILE}: {e}")
            
            # 3. Environment variable (already loaded)
            if cls.YOUTRACK_API_TOKEN and token_source == "unknown":
                token_source = "env_var"
        
        # API token is always required
        if not cls.YOUTRACK_API_TOKEN:
            error_msg = (
                "YouTrack API token is required. Provide it using:\n"
                "1. YOUTRACK_API_TOKEN environment variable\n"
                "2. YOUTRACK_TOKEN_FILE pointing to a token file\n"
                "3. Secure keyring storage (if available)\n"
                "4. Configuration parameter"
            )
            if SECURITY_AVAILABLE:
                error_msg += f"\n\nFor secure storage, use: credential_manager.store_token('username', 'your_token')"
            raise ValueError(error_msg)
        
        # Validate token format and log security audit
        if SECURITY_AVAILABLE:
            validation_result = token_validator.validate_token_format(cls.YOUTRACK_API_TOKEN)
            token_hash = token_validator.get_token_hash(cls.YOUTRACK_API_TOKEN)
            
            # Log token access for security audit
            audit_log.log_token_access(
                event="token_validation",
                token_hash=token_hash,
                source=token_source,
                success=validation_result["valid"]
            )
            
            if not validation_result["valid"]:
                masked_token = token_validator.mask_token(cls.YOUTRACK_API_TOKEN)
                raise ValueError(f"Invalid YouTrack API token format (token: {masked_token}): {validation_result['error']}")
            
            logger.info(f"Token validation successful - type: {validation_result['token_type']}, source: {token_source}")
            
            # Extract workspace info if available
            if validation_result.get("workspace"):
                logger.info(f"Detected workspace: {validation_result['workspace']}")
        
        # URL validation for self-hosted instances
        if not cls.YOUTRACK_CLOUD and not cls.YOUTRACK_URL:
            raise ValueError("YouTrack URL is required for self-hosted instances. Provide it using YOUTRACK_URL environment variable or set YOUTRACK_CLOUD=true for cloud instances.")
        
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
            return f"{cls.YOUTRACK_URL}/api"
            
        # For cloud instances without explicit URL, try to extract from token
        if cls.is_cloud_instance():
            # Handle both token formats: perm: and perm-
            if "." in cls.YOUTRACK_API_TOKEN and (cls.YOUTRACK_API_TOKEN.startswith("perm:") or cls.YOUTRACK_API_TOKEN.startswith("perm-")):
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
        raise ValueError("YouTrack URL is required. Please set YOUTRACK_URL environment variable.")
    
    @classmethod
    def get_oauth2_config(cls) -> Optional['OAuth2Config']:
        """
        Get OAuth2/OIDC configuration if enabled and available.
        
        Returns:
            OAuth2Config instance or None if not enabled/available
        """
        if not cls.OAUTH2_ENABLED or not OAUTH2_AVAILABLE:
            return None
        
        if not cls.OAUTH2_CLIENT_ID or not cls.OAUTH2_CLIENT_SECRET or not cls.OAUTH2_TOKEN_ENDPOINT:
            logger.warning("OAuth2 is enabled but required configuration is missing")
            return None
        
        return OAuth2Config(
            client_id=cls.OAUTH2_CLIENT_ID,
            client_secret=cls.OAUTH2_CLIENT_SECRET,
            token_endpoint=cls.OAUTH2_TOKEN_ENDPOINT,
            authorization_endpoint=cls.OAUTH2_AUTHORIZATION_ENDPOINT or None,
            userinfo_endpoint=cls.OAUTH2_USERINFO_ENDPOINT or None,
            jwks_uri=cls.OAUTH2_JWKS_URI or None,
            issuer=cls.OAUTH2_ISSUER or None,
            scope=cls.OAUTH2_SCOPE,
            grant_type=cls.OAUTH2_GRANT_TYPE
        )
    
    @classmethod
    def create_youtrack_oauth2_config(cls, workspace: str) -> Optional['OAuth2Config']:
        """
        Create OAuth2 configuration for YouTrack Cloud/Hub.
        
        Args:
            workspace: YouTrack workspace name
            
        Returns:
            OAuth2Config for YouTrack or None if not available
        """
        if not OAUTH2_AVAILABLE or not cls.OAUTH2_CLIENT_ID or not cls.OAUTH2_CLIENT_SECRET:
            return None
        
        base_url = f"https://{workspace}.youtrack.cloud" if workspace else cls.get_base_url().rstrip("/api")
        
        return create_youtrack_oauth2_config(
            base_url=base_url,
            client_id=cls.OAUTH2_CLIENT_ID,
            client_secret=cls.OAUTH2_CLIENT_SECRET,
            scope=cls.OAUTH2_SCOPE
        )


# Create a global config instance
config = Config() 