"""
Security Tests for YouTrack MCP Server.

Tests token validation, secure storage, and security audit functionality.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import security components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtrack_mcp.security import (
    TokenValidator,
    SecureCredentialManager,
    TokenFileManager,
    SecurityAuditLog,
    token_validator,
    credential_manager,
    audit_log
)


class TestTokenValidator:
    """Test token validation functionality."""
    
    def test_valid_permanent_token(self):
        """Test validation of valid permanent tokens."""
        valid_tokens = [
            "perm:user.workspace.abcd1234efgh5678",
            "perm:testuser.myworkspace.hash123456",
            "perm:user123.workspace-test.verylonghash"
        ]
        
        for token in valid_tokens:
            result = TokenValidator.validate_token_format(token)
            assert result["valid"] is True
            assert result["token_type"] == "permanent"
            assert "workspace" in result
    
    def test_valid_legacy_token(self):
        """Test validation of valid legacy tokens."""
        legacy_tokens = [
            "perm-base64encoded.morebase64.hash",
            "perm-VGVzdA==.VGVzdA==.abcd1234"
        ]
        
        for token in legacy_tokens:
            result = TokenValidator.validate_token_format(token)
            assert result["valid"] is True
            assert result["token_type"] == "permanent_legacy"
    
    def test_invalid_tokens(self):
        """Test validation of invalid tokens."""
        invalid_tokens = [
            "",
            "invalid",
            "perm:",
            "perm-",
            "bearer:token",
            "short",
            None,
            123
        ]
        
        for token in invalid_tokens:
            result = TokenValidator.validate_token_format(token)
            assert result["valid"] is False
            assert "error" in result
    
    def test_token_masking(self):
        """Test token masking functionality."""
        test_cases = [
            ("perm:user.workspace.abcd1234", "***1234"),
            ("verylongtoken12345", "***2345"),
            ("short", "***"),
            ("", "***"),
            (None, "***")
        ]
        
        for token, expected in test_cases:
            masked = TokenValidator.mask_token(token)
            assert masked == expected
    
    def test_token_hashing(self):
        """Test token hashing functionality."""
        token = "perm:user.workspace.abcd1234"
        hash1 = TokenValidator.get_token_hash(token)
        hash2 = TokenValidator.get_token_hash(token)
        
        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 8
        assert hash1.isalnum()
        
        # Different tokens should have different hashes
        different_token = "perm:other.workspace.efgh5678"
        hash3 = TokenValidator.get_token_hash(different_token)
        assert hash1 != hash3
    
    def test_workspace_extraction(self):
        """Test workspace extraction from tokens."""
        test_cases = [
            ("perm:user.myworkspace.hash", "myworkspace"),
            ("perm:testuser.test-workspace.hash", "test-workspace"),
            ("perm-base64.encoded.hash", None)
        ]
        
        for token, expected_workspace in test_cases:
            result = TokenValidator.validate_token_format(token)
            if expected_workspace:
                assert result["workspace"] == expected_workspace
            else:
                assert result.get("workspace") is None


class TestSecureCredentialManager:
    """Test secure credential management."""
    
    @pytest.fixture
    def credential_manager_instance(self):
        """Create credential manager instance for testing."""
        return SecureCredentialManager("test-youtrack-mcp")
    
    def test_credential_manager_initialization(self, credential_manager_instance):
        """Test credential manager initialization."""
        assert credential_manager_instance.service_name == "test-youtrack-mcp"
        assert hasattr(credential_manager_instance, 'keyring_available')
    
    @patch('youtrack_mcp.security.keyring')
    def test_store_token_with_keyring(self, mock_keyring, credential_manager_instance):
        """Test token storage with keyring available."""
        credential_manager_instance.keyring_available = True
        
        result = credential_manager_instance.store_token("testuser", "test-token")
        
        assert result is True
        mock_keyring.set_password.assert_called_once_with(
            "test-youtrack-mcp", "testuser", "test-token"
        )
    
    def test_store_token_without_keyring(self, credential_manager_instance):
        """Test token storage without keyring available."""
        credential_manager_instance.keyring_available = False
        
        result = credential_manager_instance.store_token("testuser", "test-token")
        
        assert result is False
    
    @patch('youtrack_mcp.security.keyring')
    def test_retrieve_token_with_keyring(self, mock_keyring, credential_manager_instance):
        """Test token retrieval with keyring available."""
        credential_manager_instance.keyring_available = True
        mock_keyring.get_password.return_value = "retrieved-token"
        
        result = credential_manager_instance.retrieve_token("testuser")
        
        assert result == "retrieved-token"
        mock_keyring.get_password.assert_called_once_with(
            "test-youtrack-mcp", "testuser"
        )
    
    def test_retrieve_token_without_keyring(self, credential_manager_instance):
        """Test token retrieval without keyring available."""
        credential_manager_instance.keyring_available = False
        
        result = credential_manager_instance.retrieve_token("testuser")
        
        assert result is None


class TestTokenFileManager:
    """Test secure token file operations."""
    
    def test_write_and_read_token_file(self):
        """Test writing and reading token files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = os.path.join(tmpdir, "test_token")
            test_token = "perm:user.workspace.testtoken"
            
            # Write token
            result = TokenFileManager.write_token_file(token_file, test_token)
            assert result is True
            
            # Check file exists and has correct permissions
            path = Path(token_file)
            assert path.exists()
            stat_info = path.stat()
            # Check that only owner can read/write (600 permissions)
            assert stat_info.st_mode & 0o777 == 0o600
            
            # Read token
            retrieved_token = TokenFileManager.read_token_file(token_file)
            assert retrieved_token == test_token
    
    def test_read_nonexistent_file(self):
        """Test reading a non-existent token file."""
        result = TokenFileManager.read_token_file("/nonexistent/path")
        assert result is None
    
    def test_read_empty_file(self):
        """Test reading an empty token file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            result = TokenFileManager.read_token_file(temp_path)
            assert result is None
        finally:
            os.unlink(temp_path)
    
    def test_file_permission_warning(self):
        """Test warning for overly permissive file permissions."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test-token")
            temp_path = f.name
        
        try:
            # Make file world-readable
            os.chmod(temp_path, 0o644)
            
            # Should still read but log warning
            with patch('youtrack_mcp.security.logger') as mock_logger:
                result = TokenFileManager.read_token_file(temp_path)
                assert result == "test-token"
                mock_logger.warning.assert_called()
        finally:
            os.unlink(temp_path)


class TestSecurityAuditLog:
    """Test security audit logging."""
    
    def test_audit_log_initialization(self):
        """Test audit log initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "audit.log")
            audit = SecurityAuditLog(log_file)
            
            assert audit.log_file == log_file
            assert audit.log_file_path == Path(log_file)
    
    def test_audit_log_without_file(self):
        """Test audit log without file logging."""
        audit = SecurityAuditLog()
        
        # Should not raise exception
        audit.log_token_access("test_event", "hash123", "test_source", True)
    
    def test_audit_log_with_file(self):
        """Test audit log with file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "audit.log")
            audit = SecurityAuditLog(log_file)
            
            audit.log_token_access("test_event", "hash123", "test_source", True)
            
            # Check log file was created and contains entry
            assert Path(log_file).exists()
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "test_event" in log_content
                assert "hash123" in log_content
                assert "test_source" in log_content
                
                # Should be valid JSON
                import json
                log_entry = json.loads(log_content.strip())
                assert log_entry["event"] == "test_event"
                assert log_entry["token_hash"] == "hash123"
                assert log_entry["source"] == "test_source"
                assert log_entry["success"] is True


class TestSecurityIntegration:
    """Test security component integration."""
    
    def test_global_instances(self):
        """Test that global security instances are available."""
        assert token_validator is not None
        assert credential_manager is not None
        assert audit_log is not None
    
    def test_token_validation_integration(self):
        """Test token validation through global instance."""
        test_token = "perm:user.workspace.testhash"
        
        result = token_validator.validate_token_format(test_token)
        assert result["valid"] is True
        
        masked = token_validator.mask_token(test_token)
        assert masked.endswith("hash")
        
        hash_val = token_validator.get_token_hash(test_token)
        assert len(hash_val) == 8
    
    @patch.dict(os.environ, {'YOUTRACK_SECURITY_AUDIT_LOG': ''})
    def test_audit_log_environment_config(self):
        """Test audit log configuration from environment."""
        # This tests that the module initializes correctly with env vars
        from youtrack_mcp.security import SecurityAuditLog
        
        # Should handle empty log file path gracefully
        audit = SecurityAuditLog(os.getenv("YOUTRACK_SECURITY_AUDIT_LOG"))
        assert audit.log_file == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])