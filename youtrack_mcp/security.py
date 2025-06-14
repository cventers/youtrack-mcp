"""
Security utilities for YouTrack MCP server.
Provides secure token storage, validation, and credential management.
"""
import os
import re
import logging
import hashlib
import base64
from typing import Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Optional keyring support for secure credential storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.info("keyring not available - secure credential storage disabled")


class TokenValidator:
    """Validates YouTrack API tokens and provides security utilities."""
    
    # YouTrack token patterns
    PERMANENT_TOKEN_PATTERN = re.compile(r'^perm:[a-zA-Z0-9._-]+$')
    LEGACY_TOKEN_PATTERN = re.compile(r'^perm-[a-zA-Z0-9+/=._-]+$')
    
    @classmethod
    def validate_token_format(cls, token: str) -> Dict[str, Any]:
        """
        Validate the format of a YouTrack API token.
        
        Args:
            token: The API token to validate
            
        Returns:
            Dictionary with validation results and token information
        """
        if not token or not isinstance(token, str):
            return {
                "valid": False,
                "error": "Token is empty or not a string",
                "token_type": None
            }
        
        # Remove whitespace
        token = token.strip()
        
        if len(token) < 10:
            return {
                "valid": False,
                "error": "Token is too short",
                "token_type": None
            }
        
        # Check for permanent token format
        if cls.PERMANENT_TOKEN_PATTERN.match(token):
            # Extract workspace if possible
            workspace = None
            if "." in token:
                parts = token.split(".")
                if len(parts) >= 2:
                    workspace = parts[1]
            
            return {
                "valid": True,
                "token_type": "permanent",
                "workspace": workspace,
                "format": "perm:username.workspace.hash"
            }
        
        # Check for legacy token format
        if cls.LEGACY_TOKEN_PATTERN.match(token):
            return {
                "valid": True,
                "token_type": "permanent_legacy",
                "workspace": None,
                "format": "perm-base64.encoded.parts"
            }
        
        # Check if it looks like a valid token but doesn't match known patterns
        if token.startswith("perm"):
            return {
                "valid": False,
                "error": "Token appears to be a YouTrack token but format is unrecognized",
                "token_type": "unknown_perm"
            }
        
        return {
            "valid": False,
            "error": "Token does not match known YouTrack token formats",
            "token_type": "unknown"
        }
    
    @classmethod
    def mask_token(cls, token: str, show_chars: int = 4) -> str:
        """
        Mask a token for safe logging and display.
        
        Args:
            token: The token to mask
            show_chars: Number of characters to show at the end
            
        Returns:
            Masked token string
        """
        if not token or len(token) <= show_chars:
            return "***"
        
        return f"***{token[-show_chars:]}"
    
    @classmethod
    def get_token_hash(cls, token: str) -> str:
        """
        Get a hash of the token for identification purposes.
        
        Args:
            token: The token to hash
            
        Returns:
            SHA256 hash of the token (first 8 characters)
        """
        if not token:
            return "empty"
        
        hash_obj = hashlib.sha256(token.encode('utf-8'))
        return hash_obj.hexdigest()[:8]


class SecureCredentialManager:
    """Manages secure storage and retrieval of API credentials."""
    
    def __init__(self, service_name: str = "youtrack-mcp"):
        self.service_name = service_name
        self.keyring_available = KEYRING_AVAILABLE
        
    def store_token(self, username: str, token: str) -> bool:
        """
        Store a token securely using keyring if available.
        
        Args:
            username: Username or identifier for the token
            token: The API token to store
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.keyring_available:
            logger.warning("Keyring not available - cannot store token securely")
            return False
        
        try:
            keyring.set_password(self.service_name, username, token)
            logger.info(f"Token stored securely for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to store token securely: {e}")
            return False
    
    def retrieve_token(self, username: str) -> Optional[str]:
        """
        Retrieve a token securely using keyring if available.
        
        Args:
            username: Username or identifier for the token
            
        Returns:
            The API token if found, None otherwise
        """
        if not self.keyring_available:
            return None
        
        try:
            token = keyring.get_password(self.service_name, username)
            if token:
                logger.info(f"Token retrieved securely for user: {username}")
            return token
        except Exception as e:
            logger.error(f"Failed to retrieve token securely: {e}")
            return None
    
    def delete_token(self, username: str) -> bool:
        """
        Delete a stored token securely.
        
        Args:
            username: Username or identifier for the token
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.keyring_available:
            return False
        
        try:
            keyring.delete_password(self.service_name, username)
            logger.info(f"Token deleted securely for user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete token securely: {e}")
            return False


class TokenFileManager:
    """Manages secure token file operations with proper permissions."""
    
    @staticmethod
    def read_token_file(file_path: str) -> Optional[str]:
        """
        Read token from file with security checks.
        
        Args:
            file_path: Path to the token file
            
        Returns:
            Token content if valid, None otherwise
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.error(f"Token file does not exist: {file_path}")
                return None
            
            # Check file permissions (should not be world-readable)
            stat_info = path.stat()
            if stat_info.st_mode & 0o044:  # Check if group or others can read
                logger.warning(f"Token file has overly permissive permissions: {file_path}")
            
            # Read token
            with open(path, 'r', encoding='utf-8') as f:
                token = f.read().strip()
            
            if not token:
                logger.error(f"Token file is empty: {file_path}")
                return None
            
            logger.info(f"Token loaded from file: {file_path}")
            return token
            
        except PermissionError:
            logger.error(f"Permission denied reading token file: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading token file {file_path}: {e}")
            return None
    
    @staticmethod
    def write_token_file(file_path: str, token: str) -> bool:
        """
        Write token to file with secure permissions.
        
        Args:
            file_path: Path to write the token file
            token: Token content to write
            
        Returns:
            True if written successfully, False otherwise
        """
        try:
            path = Path(file_path)
            
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write token with restrictive permissions
            with open(path, 'w', encoding='utf-8') as f:
                f.write(token)
            
            # Set secure permissions (owner read/write only)
            path.chmod(0o600)
            
            logger.info(f"Token written securely to file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing token file {file_path}: {e}")
            return False


class SecurityAuditLog:
    """Logs security-related events for audit purposes."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        if log_file:
            self.log_file_path = Path(log_file)
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_token_access(self, event: str, token_hash: str, source: str, success: bool):
        """
        Log token access events for security auditing.
        
        Args:
            event: Type of event (e.g., "token_validation", "token_load")
            token_hash: Hash of the token for identification
            source: Source of the token (e.g., "env_var", "file", "keyring")
            success: Whether the operation was successful
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "token_hash": token_hash,
            "source": source,
            "success": success,
            "pid": os.getpid()
        }
        
        # Log to Python logger
        logger.info(f"Security audit: {event} - token_hash:{token_hash} source:{source} success:{success}")
        
        # Log to audit file if configured
        if self.log_file:
            try:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                logger.error(f"Failed to write security audit log: {e}")


# Global instances
token_validator = TokenValidator()
credential_manager = SecureCredentialManager()
audit_log = SecurityAuditLog(os.getenv("YOUTRACK_SECURITY_AUDIT_LOG"))