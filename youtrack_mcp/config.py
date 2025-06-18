"""
Configuration for YouTrack MCP server.
"""
import os
import ssl
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# Optional import for dotenv
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    load_dotenv()
except ImportError:
    # dotenv is not required
    pass

# Import YAML (required dependency)
import yaml

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
    
    # Response formatting quirks
    NO_EPOCH: bool = os.getenv("YOUTRACK_NO_EPOCH", "true").lower() in ("true", "1", "yes")
    
    # Ticket attribute suggestions
    SUGGESTIONS_ENABLED: bool = os.getenv("YOUTRACK_SUGGESTIONS_ENABLED", "true").lower() in ("true", "1", "yes")
    SUGGESTIONS_CONFIG: Dict[str, Any] = {}
    
    # AI/LLM configuration
    AI_ENABLED: bool = os.getenv("YOUTRACK_AI_ENABLED", "true").lower() in ("true", "1", "yes")
    AI_MAX_MEMORY_MB: int = int(os.getenv("YOUTRACK_AI_MAX_MEMORY_MB", "2048"))
    
    # OpenAI-compatible LLM provider
    LLM_API_URL: str = os.getenv("YOUTRACK_LLM_API_URL", "")
    LLM_API_KEY: str = os.getenv("YOUTRACK_LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("YOUTRACK_LLM_MODEL", "gpt-3.5-turbo")
    LLM_MAX_TOKENS: int = int(os.getenv("YOUTRACK_LLM_MAX_TOKENS", "1000"))
    LLM_TEMPERATURE: float = float(os.getenv("YOUTRACK_LLM_TEMPERATURE", "0.3"))
    LLM_TIMEOUT: int = int(os.getenv("YOUTRACK_LLM_TIMEOUT", "30"))
    LLM_ENABLED: bool = os.getenv("YOUTRACK_LLM_ENABLED", "true").lower() in ("true", "1", "yes")
    
    # Hugging Face Transformers
    HF_MODEL: str = os.getenv("YOUTRACK_HF_MODEL", "")
    HF_DEVICE: str = os.getenv("YOUTRACK_HF_DEVICE", "cpu")
    HF_MAX_TOKENS: int = int(os.getenv("YOUTRACK_HF_MAX_TOKENS", "1000"))
    HF_TEMPERATURE: float = float(os.getenv("YOUTRACK_HF_TEMPERATURE", "0.3"))
    HF_TORCH_DTYPE: str = os.getenv("YOUTRACK_HF_TORCH_DTYPE", "")
    HF_4BIT: bool = os.getenv("YOUTRACK_HF_4BIT", "false").lower() in ("true", "1", "yes")
    HF_8BIT: bool = os.getenv("YOUTRACK_HF_8BIT", "false").lower() in ("true", "1", "yes")
    HF_TRUST_REMOTE_CODE: bool = os.getenv("YOUTRACK_HF_TRUST_REMOTE_CODE", "false").lower() in ("true", "1", "yes")
    HF_ENABLED: bool = os.getenv("YOUTRACK_HF_ENABLED", "false").lower() in ("true", "1", "yes")
    
    # Local model configuration (future)
    LOCAL_MODEL_PATH: str = os.getenv("YOUTRACK_LOCAL_MODEL_PATH", "")
    LOCAL_MODEL_ENABLED: bool = os.getenv("YOUTRACK_LOCAL_MODEL_ENABLED", "false").lower() in ("true", "1", "yes")
    
    @classmethod
    def load_yaml_config(cls, config_path: Optional[str] = None) -> None:
        """
        Load configuration from YAML file with environment variable overrides.
        
        Args:
            config_path: Path to YAML config file. If None, searches for config.yaml
        """
        
        # Find config file
        if config_path is None:
            # Look for config.yaml in current directory or parent directory
            current_dir = Path.cwd()
            config_paths = [
                current_dir / "config.yaml",
                current_dir.parent / "config.yaml",
                Path(__file__).parent.parent / "config.yaml"
            ]
            config_path = None
            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if not config_path or not Path(config_path).exists():
            raise FileNotFoundError(f"YAML configuration file not found. Searched: {[str(p) for p in config_paths]}")
        
        # Load YAML configuration
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        
        if not yaml_config:
            raise ValueError(f"Empty or invalid YAML configuration file: {config_path}")
        
        # Apply YAML configuration with environment variable overrides
        cls._apply_yaml_config(yaml_config)
        logger.info(f"Configuration loaded from: {config_path}")
    
    @classmethod
    def _apply_yaml_config(cls, yaml_config: Dict[str, Any]) -> None:
        """
        Apply YAML configuration with environment variable overrides.
        
        Args:
            yaml_config: The loaded YAML configuration
        """
        # YouTrack configuration
        if 'youtrack' in yaml_config:
            youtrack = yaml_config['youtrack']
            cls.YOUTRACK_URL = os.getenv("YOUTRACK_URL", youtrack.get('url', ''))
            cls.YOUTRACK_API_TOKEN = os.getenv("YOUTRACK_API_TOKEN", youtrack.get('api_token', ''))
            cls.YOUTRACK_TOKEN_FILE = os.getenv("YOUTRACK_TOKEN_FILE", youtrack.get('token_file', ''))
            cls.VERIFY_SSL = os.getenv("YOUTRACK_VERIFY_SSL", str(youtrack.get('verify_ssl', True))).lower() in ("true", "1", "yes")
            cls.YOUTRACK_CLOUD = os.getenv("YOUTRACK_CLOUD", str(youtrack.get('cloud', False))).lower() in ("true", "1", "yes")
        
        # API configuration
        if 'api' in yaml_config:
            api = yaml_config['api']
            cls.MAX_RETRIES = int(os.getenv("YOUTRACK_MAX_RETRIES", str(api.get('max_retries', 3))))
            cls.RETRY_DELAY = float(os.getenv("YOUTRACK_RETRY_DELAY", str(api.get('retry_delay', 1.0))))
        
        # MCP configuration
        if 'mcp' in yaml_config:
            mcp = yaml_config['mcp']
            cls.MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", mcp.get('server_name', 'youtrack-mcp'))
            cls.MCP_SERVER_DESCRIPTION = os.getenv("MCP_SERVER_DESCRIPTION", mcp.get('server_description', 'YouTrack MCP Server'))
            cls.MCP_DEBUG = os.getenv("MCP_DEBUG", str(mcp.get('debug', False))).lower() in ("true", "1", "yes")
        
        # OAuth2 configuration
        if 'oauth2' in yaml_config:
            oauth2 = yaml_config['oauth2']
            cls.OAUTH2_ENABLED = os.getenv("OAUTH2_ENABLED", str(oauth2.get('enabled', False))).lower() in ("true", "1", "yes")
            cls.OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", oauth2.get('client_id', ''))
            cls.OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", oauth2.get('client_secret', ''))
            cls.OAUTH2_TOKEN_ENDPOINT = os.getenv("OAUTH2_TOKEN_ENDPOINT", oauth2.get('token_endpoint', ''))
            cls.OAUTH2_AUTHORIZATION_ENDPOINT = os.getenv("OAUTH2_AUTHORIZATION_ENDPOINT", oauth2.get('authorization_endpoint', ''))
            cls.OAUTH2_USERINFO_ENDPOINT = os.getenv("OAUTH2_USERINFO_ENDPOINT", oauth2.get('userinfo_endpoint', ''))
            cls.OAUTH2_JWKS_URI = os.getenv("OAUTH2_JWKS_URI", oauth2.get('jwks_uri', ''))
            cls.OAUTH2_ISSUER = os.getenv("OAUTH2_ISSUER", oauth2.get('issuer', ''))
            cls.OAUTH2_SCOPE = os.getenv("OAUTH2_SCOPE", oauth2.get('scope', 'openid profile'))
            cls.OAUTH2_GRANT_TYPE = os.getenv("OAUTH2_GRANT_TYPE", oauth2.get('grant_type', 'client_credentials'))
        
        # Quirks configuration
        if 'quirks' in yaml_config:
            quirks = yaml_config['quirks']
            cls.NO_EPOCH = os.getenv("YOUTRACK_NO_EPOCH", str(quirks.get('no_epoch', True))).lower() in ("true", "1", "yes")
        
        # Suggestions configuration
        if 'suggestions' in yaml_config:
            suggestions = yaml_config['suggestions']
            cls.SUGGESTIONS_ENABLED = os.getenv("YOUTRACK_SUGGESTIONS_ENABLED", str(suggestions.get('enabled', True))).lower() in ("true", "1", "yes")
            cls.SUGGESTIONS_CONFIG = suggestions
        
        # AI/LLM configuration
        if 'ai' in yaml_config:
            ai = yaml_config['ai']
            cls.AI_ENABLED = os.getenv("YOUTRACK_AI_ENABLED", str(ai.get('enabled', True))).lower() in ("true", "1", "yes")
            cls.AI_MAX_MEMORY_MB = int(os.getenv("YOUTRACK_AI_MAX_MEMORY_MB", str(ai.get('max_memory_mb', 2048))))
            
            # OpenAI-compatible provider
            if 'llm' in ai:
                llm = ai['llm']
                cls.LLM_API_URL = os.getenv("YOUTRACK_LLM_API_URL", llm.get('api_url', ''))
                cls.LLM_API_KEY = os.getenv("YOUTRACK_LLM_API_KEY", llm.get('api_key', ''))
                cls.LLM_MODEL = os.getenv("YOUTRACK_LLM_MODEL", llm.get('model', 'gpt-3.5-turbo'))
                cls.LLM_MAX_TOKENS = int(os.getenv("YOUTRACK_LLM_MAX_TOKENS", str(llm.get('max_tokens', 1000))))
                cls.LLM_TEMPERATURE = float(os.getenv("YOUTRACK_LLM_TEMPERATURE", str(llm.get('temperature', 0.3))))
                cls.LLM_TIMEOUT = int(os.getenv("YOUTRACK_LLM_TIMEOUT", str(llm.get('timeout', 30))))
                cls.LLM_ENABLED = os.getenv("YOUTRACK_LLM_ENABLED", str(llm.get('enabled', True))).lower() in ("true", "1", "yes")
            
            # Hugging Face Transformers
            if 'huggingface' in ai:
                hf = ai['huggingface']
                cls.HF_MODEL = os.getenv("YOUTRACK_HF_MODEL", hf.get('model', ''))
                cls.HF_DEVICE = os.getenv("YOUTRACK_HF_DEVICE", hf.get('device', 'cpu'))
                cls.HF_MAX_TOKENS = int(os.getenv("YOUTRACK_HF_MAX_TOKENS", str(hf.get('max_tokens', 1000))))
                cls.HF_TEMPERATURE = float(os.getenv("YOUTRACK_HF_TEMPERATURE", str(hf.get('temperature', 0.3))))
                cls.HF_TORCH_DTYPE = os.getenv("YOUTRACK_HF_TORCH_DTYPE", hf.get('torch_dtype', ''))
                cls.HF_4BIT = os.getenv("YOUTRACK_HF_4BIT", str(hf.get('quantization_4bit', False))).lower() in ("true", "1", "yes")
                cls.HF_8BIT = os.getenv("YOUTRACK_HF_8BIT", str(hf.get('quantization_8bit', False))).lower() in ("true", "1", "yes")
                cls.HF_TRUST_REMOTE_CODE = os.getenv("YOUTRACK_HF_TRUST_REMOTE_CODE", str(hf.get('trust_remote_code', False))).lower() in ("true", "1", "yes")
                cls.HF_ENABLED = os.getenv("YOUTRACK_HF_ENABLED", str(hf.get('enabled', False))).lower() in ("true", "1", "yes")
            
            # Local model (future)
            if 'local' in ai:
                local = ai['local']
                cls.LOCAL_MODEL_PATH = os.getenv("YOUTRACK_LOCAL_MODEL_PATH", local.get('model_path', ''))
                cls.LOCAL_MODEL_ENABLED = os.getenv("YOUTRACK_LOCAL_MODEL_ENABLED", str(local.get('enabled', False))).lower() in ("true", "1", "yes")
    
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


# Create a global config instance and load YAML configuration
config = Config()

# Auto-load YAML configuration if available
try:
    config.load_yaml_config()
except FileNotFoundError:
    logger.warning("No YAML configuration file found, using environment variables and defaults")
except Exception as e:
    logger.error(f"Failed to load YAML configuration: {e}")
    # Continue with environment variables and defaults 