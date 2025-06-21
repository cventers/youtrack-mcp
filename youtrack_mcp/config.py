"""
Configuration for YouTrack MCP server.
"""
import os
import ssl
import logging
from typing import Optional, Dict, Any, List
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
    
    # Tool Category Configuration
    TOOLS_ENABLED: Dict[str, bool] = {
        # Category-level controls
        "issue_management": os.getenv("YOUTRACK_TOOLS_ISSUE_MANAGEMENT", "true").lower() in ("true", "1", "yes"),
        "search_discovery": os.getenv("YOUTRACK_TOOLS_SEARCH_DISCOVERY", "true").lower() in ("true", "1", "yes"),
        "issue_linking": os.getenv("YOUTRACK_TOOLS_ISSUE_LINKING", "true").lower() in ("true", "1", "yes"),
        "project_management": os.getenv("YOUTRACK_TOOLS_PROJECT_MANAGEMENT", "true").lower() in ("true", "1", "yes"),
        "user_management": os.getenv("YOUTRACK_TOOLS_USER_MANAGEMENT", "true").lower() in ("true", "1", "yes"),
        "ai_analytics": os.getenv("YOUTRACK_TOOLS_AI_ANALYTICS", "true").lower() in ("true", "1", "yes"),
        "system_cache": os.getenv("YOUTRACK_TOOLS_SYSTEM_CACHE", "true").lower() in ("true", "1", "yes"),
    }
    
    # Individual tool controls (overrides category settings)
    INDIVIDUAL_TOOLS_ENABLED: Dict[str, bool] = {}
    
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
        
        # Tool configuration
        if 'tools' in yaml_config:
            tools = yaml_config['tools']
            
            # Category-level settings
            if 'categories' in tools and tools['categories']:
                categories = tools['categories']
                for category, enabled in categories.items():
                    env_key = f"YOUTRACK_TOOLS_{category.upper()}"
                    cls.TOOLS_ENABLED[category] = os.getenv(env_key, str(enabled)).lower() in ("true", "1", "yes")
            
            # Individual tool settings
            if 'individual' in tools and tools['individual']:
                individual = tools['individual']
                for tool_name, enabled in individual.items():
                    env_key = f"YOUTRACK_TOOL_{tool_name.upper()}"
                    cls.INDIVIDUAL_TOOLS_ENABLED[tool_name] = os.getenv(env_key, str(enabled)).lower() in ("true", "1", "yes")
    
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
            # 1. Try keyring first (most secure) - DISABLED due to prompt issues
            if SECURITY_AVAILABLE and os.getenv("YOUTRACK_DISABLE_KEYRING", "false").lower() != "true":
                keyring_username = os.getenv("YOUTRACK_KEYRING_USERNAME", "default")
                try:
                    keyring_token = credential_manager.retrieve_token(keyring_username)
                    if keyring_token:
                        cls.YOUTRACK_API_TOKEN = keyring_token
                        token_source = "keyring"
                        logger.info("Token loaded from secure keyring")
                except Exception as e:
                    logger.warning(f"Keyring access failed, continuing without it: {e}")
            
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
    
    @classmethod
    def get_tool_categories(cls) -> Dict[str, List[str]]:
        """
        Get the mapping of tool categories to tool names.
        
        Returns:
            Dictionary mapping category names to lists of tool names
        """
        return {
            "issue_management": [
                "get_issue", "get_issue_raw", "create_issue", "update_issue", 
                "add_comment", "get_comments", "get_task_comments", "get_project_comments", 
                "get_comment", "update_comment", "delete_comment", "validate_issue_id_format"
            ],
            "search_discovery": [
                "search_issues", "advanced_search", "filter_issues", "search_with_custom_fields",
                "intelligent_search", "search_by_query_builder", "search_suggestions", "smart_search_issues"
            ],
            "issue_linking": [
                "link_issues", "remove_link", "create_dependency", "get_issue_links", 
                "get_available_link_types"
            ],
            "project_management": [
                "create_project", "update_project", "get_project_issues", "get_custom_fields",
                "get_project_by_name", "get_projects", "get_project"
            ],
            "user_management": [
                "get_user", "get_user_groups", "get_current_user", "search_users", "get_user_by_login"
            ],
            "ai_analytics": [
                "analyze_user_activity_patterns", "enhance_error_context"
            ],
            "system_cache": [
                "search_analytics", "clear_search_cache"
            ]
        }
    
    @classmethod
    def is_tool_enabled(cls, tool_name: str) -> bool:
        """
        Check if a specific tool is enabled based on category and individual settings.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if the tool is enabled, False otherwise
        """
        # Check individual tool override first
        if tool_name in cls.INDIVIDUAL_TOOLS_ENABLED:
            return cls.INDIVIDUAL_TOOLS_ENABLED[tool_name]
        
        # Find which category this tool belongs to
        tool_categories = cls.get_tool_categories()
        for category, tools in tool_categories.items():
            if tool_name in tools:
                return cls.TOOLS_ENABLED.get(category, True)
        
        # Default to enabled if tool not found in any category
        logger.warning(f"Tool '{tool_name}' not found in any category, defaulting to enabled")
        return True
    
    @classmethod
    def get_enabled_tools(cls) -> List[str]:
        """
        Get a list of all enabled tools based on current configuration.
        
        Returns:
            List of enabled tool names
        """
        enabled_tools = []
        tool_categories = cls.get_tool_categories()
        
        for category, tools in tool_categories.items():
            if cls.TOOLS_ENABLED.get(category, True):
                for tool in tools:
                    # Check individual overrides
                    if tool in cls.INDIVIDUAL_TOOLS_ENABLED:
                        if cls.INDIVIDUAL_TOOLS_ENABLED[tool]:
                            enabled_tools.append(tool)
                    else:
                        enabled_tools.append(tool)
            else:
                # Category disabled, but check for individual overrides that enable tools
                for tool in tools:
                    if cls.INDIVIDUAL_TOOLS_ENABLED.get(tool, False):
                        enabled_tools.append(tool)
        
        return enabled_tools
    
    @classmethod
    def get_disabled_tools(cls) -> List[str]:
        """
        Get a list of all disabled tools based on current configuration.
        
        Returns:
            List of disabled tool names
        """
        all_tools = []
        tool_categories = cls.get_tool_categories()
        for tools in tool_categories.values():
            all_tools.extend(tools)
        
        enabled_tools = set(cls.get_enabled_tools())
        return [tool for tool in all_tools if tool not in enabled_tools]
    
    @classmethod
    def set_tool_enabled(cls, tool_name: str, enabled: bool) -> None:
        """
        Enable or disable a specific tool.
        
        Args:
            tool_name: Name of the tool to modify
            enabled: True to enable, False to disable
        """
        cls.INDIVIDUAL_TOOLS_ENABLED[tool_name] = enabled
        logger.info(f"Tool '{tool_name}' {'enabled' if enabled else 'disabled'}")
    
    @classmethod
    def set_category_enabled(cls, category: str, enabled: bool) -> None:
        """
        Enable or disable an entire tool category.
        
        Args:
            category: Name of the category to modify
            enabled: True to enable, False to disable
        """
        if category in cls.TOOLS_ENABLED:
            cls.TOOLS_ENABLED[category] = enabled
            logger.info(f"Tool category '{category}' {'enabled' if enabled else 'disabled'}")
        else:
            logger.warning(f"Unknown tool category: {category}")
    
    @classmethod
    def load_tool_config_from_env(cls) -> None:
        """
        Load individual tool configurations from environment variables.
        Environment variables should be in format: YOUTRACK_TOOL_{TOOL_NAME}=true/false
        """
        import os
        
        # Get all environment variables that start with YOUTRACK_TOOL_
        for key, value in os.environ.items():
            if key.startswith("YOUTRACK_TOOL_"):
                tool_name = key[14:].lower()  # Remove YOUTRACK_TOOL_ prefix and lowercase
                enabled = value.lower() in ("true", "1", "yes")
                cls.INDIVIDUAL_TOOLS_ENABLED[tool_name] = enabled
                logger.info(f"Environment override: tool '{tool_name}' {'enabled' if enabled else 'disabled'}")
    
    @classmethod 
    def get_tool_config_summary(cls) -> Dict[str, Any]:
        """
        Get a summary of the current tool configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        enabled_tools = cls.get_enabled_tools()
        disabled_tools = cls.get_disabled_tools()
        
        return {
            "categories": cls.TOOLS_ENABLED,
            "individual_overrides": cls.INDIVIDUAL_TOOLS_ENABLED,
            "enabled_tools": enabled_tools,
            "disabled_tools": disabled_tools,
            "total_tools": len(enabled_tools) + len(disabled_tools),
            "enabled_count": len(enabled_tools),
            "disabled_count": len(disabled_tools)
        }


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

# Load tool configuration from environment variables
config.load_tool_config_from_env() 