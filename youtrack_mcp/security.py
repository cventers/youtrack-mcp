"""
Security utilities for YouTrack MCP Server.

Provides security audit logging and credential management.
"""
from youtrack_mcp.logging import get_logger
from datetime import datetime
from typing import Any, Dict, Optional

logger = get_logger(__name__)


class SecurityAuditLog:
    """Security audit logging for OAuth2/OIDC operations."""
    
    def __init__(self, log_file: Optional[str] = None):
        """Initialize security audit log."""
        self.log_file = log_file
        self.logger = logging.getLogger(f"{__name__}.audit")
        
    def log_event(self, event_type: str, details: Dict[str, Any], 
                  severity: str = "INFO", user: Optional[str] = None) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
            user: User associated with event
        """
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            "timestamp": timestamp,
            "event_type": event_type,
            "severity": severity,
            "user": user,
            "details": details
        }
        
        # Log to standard logger
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(f"Security Event: {event_type} - {details}")
        
        # If log file specified, append to file
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(f"{timestamp} - {severity} - {event_type}: {details}\n")
            except Exception as e:
                logger.error("failed_to_write_to_audit_log_file_e", e=e)
    
    def log_authentication_success(self, client_id: str, token_type: str) -> None:
        """Log successful authentication."""
        self.log_event(
            "authentication_success",
            {"client_id": client_id, "token_type": token_type},
            severity="INFO"
        )
    
    def log_authentication_failure(self, client_id: str, error: str) -> None:
        """Log authentication failure."""
        self.log_event(
            "authentication_failure", 
            {"client_id": client_id, "error": error},
            severity="WARNING"
        )
    
    def log_token_refresh(self, client_id: str, old_token_exp: Optional[float] = None) -> None:
        """Log token refresh event."""
        self.log_event(
            "token_refresh",
            {"client_id": client_id, "old_token_exp": old_token_exp},
            severity="INFO"
        )
    
    def log_token_validation_failure(self, reason: str, token_claims: Optional[Dict] = None) -> None:
        """Log token validation failure."""
        self.log_event(
            "token_validation_failure",
            {"reason": reason, "claims": token_claims},
            severity="WARNING"
        )


__all__ = ["SecurityAuditLog"]