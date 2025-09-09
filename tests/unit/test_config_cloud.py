"""
Test cloud instance configuration and URL construction.
"""

import pytest
from unittest.mock import patch
from youtrack_mcp.config import Config


class TestCloudConfiguration:
    """Test cloud instance configuration logic."""

    def test_cloud_instance_detection_no_url(self):
        """Test that instance is detected as cloud when no URL is set."""
        with patch.object(Config, 'YOUTRACK_URL', None):
            with patch.object(Config, 'YOUTRACK_CLOUD', False):
                assert Config.is_cloud_instance() is True

    def test_cloud_instance_detection_explicit_cloud(self):
        """Test that instance is detected as cloud when explicitly set."""
        with patch.object(Config, 'YOUTRACK_URL', 'https://selfhosted.com'):
            with patch.object(Config, 'YOUTRACK_CLOUD', True):
                assert Config.is_cloud_instance() is True

    def test_self_hosted_instance_detection(self):
        """Test that instance is detected as self-hosted when URL is set."""
        with patch.object(Config, 'YOUTRACK_URL', 'https://selfhosted.com'):
            with patch.object(Config, 'YOUTRACK_CLOUD', False):
                assert Config.is_cloud_instance() is False

    def test_cloud_url_construction_perm_format(self):
        """Test URL construction from perm: token format."""
        token = "perm:testuser.testworkspace.abc123def456"

        with patch.object(Config, 'YOUTRACK_URL', None):
            with patch.object(Config, 'YOUTRACK_API_TOKEN', token):
                with patch.object(Config, 'YOUTRACK_CLOUD', True):
                    url = Config.get_base_url()
                    assert url == "https://testworkspace.youtrack.cloud/api"

    def test_cloud_url_construction_with_workspace_env(self):
        """Test URL construction using YOUTRACK_WORKSPACE environment variable."""
        token = "perm-abc123.def456.ghi789"  # Newer token format

        with patch.object(Config, 'YOUTRACK_URL', None):
            with patch.object(Config, 'YOUTRACK_API_TOKEN', token):
                with patch.object(Config, 'YOUTRACK_CLOUD', True):
                    with patch('os.getenv') as mock_getenv:
                        mock_getenv.return_value = "myworkspace"
                        url = Config.get_base_url()
                        assert url == "https://myworkspace.youtrack.cloud/api"

    def test_explicit_url_takes_precedence(self):
        """Test that explicit YOUTRACK_URL takes precedence over cloud detection."""
        with patch.object(Config, 'YOUTRACK_URL', 'https://custom.youtrack.cloud'):
            with patch.object(Config, 'YOUTRACK_API_TOKEN', 'perm:testuser.testworkspace.abc123'):
                with patch.object(Config, 'YOUTRACK_CLOUD', True):
                    url = Config.get_base_url()
                    assert url == "https://custom.youtrack.cloud/api"