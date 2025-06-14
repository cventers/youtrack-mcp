"""
Test configuration and fixtures for YouTrack MCP Server tests.
"""
import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_youtrack_config():
    """Mock YouTrack configuration for testing."""
    with patch('youtrack_mcp.config.config') as mock_config:
        mock_config.YOUTRACK_URL = "https://test.youtrack.cloud"
        mock_config.YOUTRACK_API_TOKEN = "perm:test.workspace.mocktokenhash"
        mock_config.VERIFY_SSL = True
        mock_config.YOUTRACK_CLOUD = True
        mock_config.get_base_url.return_value = "https://test.youtrack.cloud/api"
        mock_config.is_cloud_instance.return_value = True
        yield mock_config


@pytest.fixture
def mock_youtrack_client():
    """Mock YouTrack API client for testing."""
    client = AsyncMock()
    
    # Default successful responses
    client.get.return_value = {
        "id": "TEST-123",
        "summary": "Mock Issue",
        "description": "Mock Description",
        "created": 1640995200000,
        "updated": 1640995200000,
        "project": {"id": "0-0", "name": "Test Project", "shortName": "TEST"},
        "reporter": {"id": "user-1", "login": "reporter", "name": "Reporter"},
        "customFields": []
    }
    
    client.post.return_value = {
        "id": "TEST-124",
        "summary": "Created Issue"
    }
    
    client.put.return_value = {"success": True}
    client.delete.return_value = {"success": True}
    
    return client


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    return {
        "id": "TEST-123",
        "idReadable": "TEST-123",
        "summary": "Sample Test Issue",
        "description": "This is a sample test issue for testing purposes",
        "created": 1640995200000,
        "updated": 1640995201000,
        "project": {
            "id": "0-0",
            "name": "Test Project",
            "shortName": "TEST"
        },
        "reporter": {
            "id": "user-1",
            "login": "reporter",
            "name": "Reporter User",
            "email": "reporter@example.com"
        },
        "assignee": {
            "id": "user-2",
            "login": "assignee",
            "name": "Assignee User",
            "email": "assignee@example.com"
        },
        "customFields": [
            {
                "id": "field-1",
                "name": "Priority",
                "value": {"id": "high", "name": "High"}
            },
            {
                "id": "field-2",
                "name": "State",
                "value": {"id": "open", "name": "Open"}
            }
        ]
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "user-123",
        "login": "testuser",
        "name": "Test User",
        "email": "test@example.com",
        "jabber": "test@jabber.example.com",
        "ringId": "ring-123",
        "guest": False,
        "online": True,
        "banned": False,
        "avatarUrl": "https://example.com/avatar.jpg"
    }


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "id": "project-123",
        "name": "Sample Test Project",
        "shortName": "SAMPLE",
        "description": "A sample project for testing",
        "archived": False,
        "created": 1640995200000,
        "updated": 1640995201000,
        "leader": {
            "id": "user-1",
            "login": "projectlead",
            "name": "Project Lead"
        }
    }


@pytest.fixture
def mock_security_components():
    """Mock security components for testing."""
    with patch('youtrack_mcp.security.KEYRING_AVAILABLE', True):
        with patch('youtrack_mcp.security.keyring') as mock_keyring:
            mock_keyring.get_password.return_value = "mock-token"
            mock_keyring.set_password.return_value = None
            mock_keyring.delete_password.return_value = None
            yield mock_keyring


@pytest.fixture
def temp_token_file(tmp_path):
    """Create a temporary token file for testing."""
    token_file = tmp_path / "test_token"
    token_file.write_text("perm:test.workspace.temporarytoken")
    token_file.chmod(0o600)
    return str(token_file)


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('youtrack_mcp.api.issues.logger') as mock_logger:
        yield mock_logger


class AsyncIterator:
    """Helper class for creating async iterators in tests."""
    
    def __init__(self, items):
        self.items = iter(items)
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.fixture
def async_iterator():
    """Factory for creating async iterators."""
    return AsyncIterator