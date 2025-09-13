"""
Golden tests for core users SEARCH operations.

Tests the user resolution functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from youtrack_mcp.tools.users_tools import UsersTools
from youtrack_mcp.utils import format_json_response


class TestCoreUsersSearch:
    """Test cases for user SEARCH operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tools = UsersTools()
        self.tools.client = Mock()
        self.tools.users_api = Mock()

    def test_search_users_basic(self):
        """Test searching users with a basic query."""
        mock_users = [
            {
                "id": "user-1",
                "login": "admin",
                "fullName": "Administrator",
                "email": "admin@example.com",
                "banned": False
            },
            {
                "id": "user-2",
                "login": "testuser",
                "fullName": "Test User",
                "email": "test@example.com",
                "banned": False
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="admin", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("admin", 10)

        # Parse the JSON result
        result_data = json.loads(result)
        expected = {
            "users": mock_users,
            "count": 2,
            "query": "admin",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_with_limit(self):
        """Test searching users with a custom limit."""
        mock_users = [
            {
                "id": "user-1",
                "login": "john",
                "fullName": "John Doe",
                "email": "john@example.com",
                "banned": False
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="john", limit=5)

        self.tools.users_api.search_users.assert_called_once_with("john", 5)

        result_data = json.loads(result)
        expected = {
            "users": mock_users,
            "count": 1,
            "query": "john",
            "limit": 5
        }
        assert result_data == expected

    def test_search_users_empty_results(self):
        """Test searching users when no users match the query."""
        mock_users = []

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="nonexistent", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("nonexistent", 10)

        result_data = json.loads(result)
        expected = {
            "users": [],
            "count": 0,
            "query": "nonexistent",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_single_result(self):
        """Test searching users that returns a single user."""
        mock_users = [
            {
                "id": "user-1",
                "login": "unique",
                "fullName": "Unique User",
                "email": "unique@example.com",
                "banned": False
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="unique", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("unique", 10)

        result_data = json.loads(result)
        expected = {
            "users": mock_users,
            "count": 1,
            "query": "unique",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_special_characters(self):
        """Test searching users with special characters in query."""
        mock_users = [
            {
                "id": "user-1",
                "login": "user@test",
                "fullName": "User with @",
                "email": "user@test@example.com",
                "banned": False
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="user@test", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("user@test", 10)

        result_data = json.loads(result)
        expected = {
            "users": mock_users,
            "count": 1,
            "query": "user@test",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_unicode_names(self):
        """Test searching users with unicode characters in names."""
        mock_users = [
            {
                "id": "user-1",
                "login": "josé",
                "fullName": "José María",
                "email": "jose@example.com",
                "banned": False
            },
            {
                "id": "user-2",
                "login": "müller",
                "fullName": "Hans Müller",
                "email": "hans@example.com",
                "banned": False
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="josé", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("josé", 10)

        result_data = json.loads(result)
        expected = {
            "users": mock_users,
            "count": 2,
            "query": "josé",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_with_pydantic_models(self):
        """Test searching users that return Pydantic models."""
        class MockUser:
            def __init__(self, id, login, full_name, email, banned=False):
                self.id = id
                self.login = login
                self.fullName = full_name
                self.email = email
                self.banned = banned

            def model_dump(self):
                return {
                    "id": self.id,
                    "login": self.login,
                    "fullName": self.fullName,
                    "email": self.email,
                    "banned": self.banned
                }

        mock_users = [
            MockUser("user-1", "admin", "Administrator", "admin@example.com", False),
            MockUser("user-2", "user", "Regular User", "user@example.com", False)
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="admin", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("admin", 10)

        result_data = json.loads(result)
        expected_users = [
            {"id": "user-1", "login": "admin", "fullName": "Administrator", "email": "admin@example.com", "banned": False},
            {"id": "user-2", "login": "user", "fullName": "Regular User", "email": "user@example.com", "banned": False}
        ]
        expected = {
            "users": expected_users,
            "count": 2,
            "query": "admin",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_with_dict_objects(self):
        """Test searching users that return plain dict objects."""
        class MockUser:
            def __init__(self, id, login, full_name, email, banned=False):
                self.__dict__ = {
                    "id": id,
                    "login": login,
                    "fullName": full_name,
                    "email": email,
                    "banned": banned
                }

        mock_users = [
            MockUser("user-1", "admin", "Administrator", "admin@example.com", False),
            MockUser("user-2", "user", "Regular User", "user@example.com", False)
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="admin", limit=10)

        self.tools.users_api.search_users.assert_called_once_with("admin", 10)

        result_data = json.loads(result)
        expected_users = [
            {"id": "user-1", "login": "admin", "fullName": "Administrator", "email": "admin@example.com", "banned": False},
            {"id": "user-2", "login": "user", "fullName": "Regular User", "email": "user@example.com", "banned": False}
        ]
        expected = {
            "users": expected_users,
            "count": 2,
            "query": "admin",
            "limit": 10
        }
        assert result_data == expected

    def test_search_users_api_error(self):
        """Test error handling when API call fails."""
        self.tools.users_api.search_users = Mock(side_effect=Exception("API Error"))

        result = self.tools.search(query="test", limit=10)

        result_data = json.loads(result)
        assert "error" in result_data
        assert "API Error" in result_data["error"]
        assert result_data["error_type"] == "Exception"
        assert result_data["query"] == "test"

    def test_search_users_limit_zero(self):
        """Test searching users with limit of 0."""
        mock_users = []

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="test", limit=0)

        self.tools.users_api.search_users.assert_called_once_with("test", 0)

        result_data = json.loads(result)
        expected = {
            "users": [],
            "count": 0,
            "query": "test",
            "limit": 0
        }
        assert result_data == expected

    def test_search_users_large_limit(self):
        """Test searching users with a large limit."""
        # Create 100 mock users
        mock_users = []
        for i in range(100):
            mock_users.append({
                "id": f"user-{i}",
                "login": f"user{i}",
                "fullName": f"User {i}",
                "email": f"user{i}@example.com",
                "banned": False
            })

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="user", limit=100)

        self.tools.users_api.search_users.assert_called_once_with("user", 100)

        result_data = json.loads(result)
        assert result_data["count"] == 100
        assert len(result_data["users"]) == 100
        assert result_data["query"] == "user"
        assert result_data["limit"] == 100

        # Verify first and last users
        assert result_data["users"][0]["login"] == "user0"
        assert result_data["users"][99]["login"] == "user99"

    def test_search_users_banned_users(self):
        """Test searching users that includes banned users."""
        mock_users = [
            {
                "id": "user-1",
                "login": "active",
                "fullName": "Active User",
                "email": "active@example.com",
                "banned": False
            },
            {
                "id": "user-2",
                "login": "banned",
                "fullName": "Banned User",
                "email": "banned@example.com",
                "banned": True
            }
        ]

        self.tools.users_api.search_users = Mock(return_value=mock_users)

        result = self.tools.search(query="user", limit=10)

        result_data = json.loads(result)
        assert result_data["count"] == 2
        assert result_data["users"][0]["banned"] is False
        assert result_data["users"][1]["banned"] is True