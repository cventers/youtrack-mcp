"""
Pydantic Model Tests for YouTrack MCP Server.

Tests the enhanced Pydantic v2 models for validation and functionality.
"""
import pytest
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from youtrack_mcp.api.issues import Issue
from youtrack_mcp.api.users import User
from youtrack_mcp.api.projects import Project
from youtrack_mcp.api.client import YouTrackModel


class TestYouTrackModel:
    """Test base YouTrack model functionality."""
    
    def test_base_model_configuration(self):
        """Test base model configuration."""
        # Create a simple test model
        test_data = {
            "id": "test-123",
            "extra_field": "extra_value"
        }
        
        model = YouTrackModel(**test_data)
        
        assert model.id == "test-123"
        assert hasattr(model, 'extra_field')
        assert model.extra_field == "extra_value"  # Should allow extra fields
    
    def test_model_config_settings(self):
        """Test model configuration settings."""
        config = YouTrackModel.model_config
        
        assert config["extra"] == "allow"
        assert config["populate_by_name"] is True
        assert config["validate_assignment"] is True
        assert config["use_enum_values"] is True
        assert config["str_strip_whitespace"] is True


class TestIssueModel:
    """Test Issue model validation and functionality."""
    
    def test_issue_creation_minimal(self):
        """Test creating issue with minimal data."""
        issue_data = {"id": "TEST-123"}
        issue = Issue(**issue_data)
        
        assert issue.id == "TEST-123"
        assert issue.summary is None
        assert issue.description is None
        assert issue.custom_fields == []
    
    def test_issue_creation_full(self):
        """Test creating issue with full data."""
        issue_data = {
            "id": "TEST-123",
            "idReadable": "TEST-123",
            "summary": "Test Issue Summary",
            "description": "Test issue description",
            "created": 1640995200000,
            "updated": 1640995201000,
            "resolved": 1640995202000,
            "project": {"id": "0-0", "name": "Test Project", "shortName": "TEST"},
            "reporter": {"id": "user-1", "login": "reporter", "name": "Reporter User"},
            "assignee": {"id": "user-2", "login": "assignee", "name": "Assignee User"},
            "customFields": [
                {"id": "field-1", "name": "Priority", "value": {"name": "High"}},
                {"id": "field-2", "name": "State", "value": {"name": "Open"}}
            ]
        }
        
        issue = Issue(**issue_data)
        
        assert issue.id == "TEST-123"
        assert issue.id_readable == "TEST-123"
        assert issue.summary == "Test Issue Summary"
        assert issue.description == "Test issue description"
        assert issue.created == 1640995200000
        assert issue.updated == 1640995201000
        assert issue.resolved == 1640995202000
        assert len(issue.custom_fields) == 2
        assert issue.project["shortName"] == "TEST"
    
    def test_text_field_validation(self):
        """Test text field validation and cleaning."""
        issue_data = {
            "id": "TEST-123",
            "summary": "  Test   Issue   Summary  ",
            "description": "Test\n\n\ndescription\t\twith\textra\twhitespace  "
        }
        
        issue = Issue(**issue_data)
        
        # Should clean up whitespace
        assert issue.summary == "Test Issue Summary"
        assert issue.description == "Test description with extra whitespace"
    
    def test_timestamp_validation(self):
        """Test timestamp validation."""
        # Valid timestamps
        issue_data = {
            "id": "TEST-123",
            "created": 1640995200000,
            "updated": 1640995201000
        }
        issue = Issue(**issue_data)
        assert issue.created == 1640995200000
        assert issue.updated == 1640995201000
        
        # Invalid negative timestamp
        with pytest.raises(ValueError, match="Timestamp cannot be negative"):
            Issue(id="TEST-123", created=-1)
    
    def test_issue_integrity_validation(self):
        """Test issue data integrity validation."""
        # Valid: created before updated
        issue = Issue(
            id="TEST-123",
            created=1640995200000,
            updated=1640995201000,
            resolved=1640995202000
        )
        assert issue.created < issue.updated < issue.resolved
        
        # Invalid but allowed: created after updated (logs warning)
        with patch('youtrack_mcp.api.issues.logger') as mock_logger:
            issue = Issue(
                id="TEST-123",
                created=1640995201000,
                updated=1640995200000
            )
            mock_logger.warning.assert_called()
    
    def test_custom_field_methods(self):
        """Test custom field utility methods."""
        issue_data = {
            "id": "TEST-123",
            "customFields": [
                {"name": "Priority", "value": {"name": "High"}},
                {"name": "State", "value": {"name": "Open"}},
                {"name": "Estimate", "value": 5}
            ]
        }
        
        issue = Issue(**issue_data)
        
        # Test get_custom_field_value
        priority_value = issue.get_custom_field_value("Priority")
        assert priority_value == {"name": "High"}
        
        estimate_value = issue.get_custom_field_value("Estimate")
        assert estimate_value == 5
        
        nonexistent_value = issue.get_custom_field_value("NonExistent")
        assert nonexistent_value is None
    
    def test_assignee_methods(self):
        """Test assignee utility methods."""
        # Issue with assignee
        issue_with_assignee = Issue(
            id="TEST-123",
            assignee={"id": "user-1", "login": "testuser"}
        )
        assert issue_with_assignee.has_assignee() is True
        
        # Issue without assignee
        issue_without_assignee = Issue(id="TEST-124")
        assert issue_without_assignee.has_assignee() is False
        
        # Issue with empty assignee
        issue_empty_assignee = Issue(
            id="TEST-125",
            assignee={}
        )
        assert issue_empty_assignee.has_assignee() is False


class TestUserModel:
    """Test User model validation and functionality."""
    
    def test_user_creation_minimal(self):
        """Test creating user with minimal data."""
        user_data = {"id": "user-123"}
        user = User(**user_data)
        
        assert user.id == "user-123"
        assert user.login is None
        assert user.name is None
        assert user.email is None
    
    def test_user_creation_full(self):
        """Test creating user with full data."""
        user_data = {
            "id": "user-123",
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "jabber": "test@jabber.com",
            "ringId": "ring-123",
            "guest": False,
            "online": True,
            "banned": False,
            "avatarUrl": "https://example.com/avatar.jpg",
            "tags": ["developer", "admin"],
            "groups": [{"id": "group-1", "name": "Developers"}]
        }
        
        user = User(**user_data)
        
        assert user.id == "user-123"
        assert user.login == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.ring_id == "ring-123"
        assert user.guest is False
        assert user.online is True
        assert user.banned is False
        assert len(user.tags) == 2
        assert len(user.groups) == 1
    
    def test_email_validation(self):
        """Test email validation."""
        # Valid email
        user = User(id="user-123", email="test@example.com")
        assert user.email == "test@example.com"
        
        # Email case normalization and trimming
        user = User(id="user-123", email="  TEST@EXAMPLE.COM  ")
        assert user.email == "test@example.com"
        
        # Invalid email formats
        with pytest.raises(ValueError, match="Invalid email format"):
            User(id="user-123", email="invalid-email")
        
        with pytest.raises(ValueError, match="Invalid email format"):
            User(id="user-123", email="no-at-sign")
    
    def test_text_field_validation(self):
        """Test text field validation and cleaning."""
        user_data = {
            "id": "user-123",
            "login": "  testuser  ",
            "name": "\tTest User\n"
        }
        
        user = User(**user_data)
        
        assert user.login == "testuser"
        assert user.name == "Test User"
    
    def test_user_utility_methods(self):
        """Test user utility methods."""
        # Active user
        active_user = User(
            id="user-1",
            login="active",
            guest=False,
            banned=False
        )
        assert active_user.is_active() is True
        assert active_user.get_display_name() == "active"
        
        # Guest user
        guest_user = User(
            id="user-2",
            login="guest",
            guest=True
        )
        assert guest_user.is_active() is False
        
        # Banned user
        banned_user = User(
            id="user-3",
            login="banned",
            banned=True
        )
        assert banned_user.is_active() is False
        
        # User with name
        named_user = User(
            id="user-4",
            login="user",
            name="Display Name"
        )
        assert named_user.get_display_name() == "Display Name"


class TestProjectModel:
    """Test Project model validation and functionality."""
    
    def test_project_creation_minimal(self):
        """Test creating project with minimal data."""
        project_data = {
            "id": "project-123",
            "name": "Test Project",
            "shortName": "TEST"
        }
        project = Project(**project_data)
        
        assert project.id == "project-123"
        assert project.name == "Test Project"
        assert project.short_name == "TEST"
        assert project.archived is False
    
    def test_project_creation_full(self):
        """Test creating project with full data."""
        project_data = {
            "id": "project-123",
            "name": "Test Project",
            "shortName": "test",
            "description": "A test project",
            "archived": False,
            "created": 1640995200000,
            "updated": 1640995201000,
            "lead": {"id": "user-1", "login": "lead"},
            "leader": {"id": "user-1", "login": "leader"},
            "customFields": [{"id": "field-1", "name": "Priority"}],
            "team": [{"id": "user-1", "login": "member1"}],
            "issue_count": 42
        }
        
        project = Project(**project_data)
        
        assert project.id == "project-123"
        assert project.name == "Test Project"
        assert project.short_name == "TEST"  # Should be uppercased
        assert project.description == "A test project"
        assert project.archived is False
        assert project.created == 1640995200000
        assert project.updated == 1640995201000
        assert len(project.custom_fields) == 1
        assert len(project.team) == 1
        assert project.issue_count == 42
    
    def test_short_name_validation(self):
        """Test project short name validation."""
        # Valid short names
        valid_names = ["TEST", "proj", "MY-PROJ", "PROJ_1", "test123"]
        for name in valid_names:
            project = Project(
                id="proj-1",
                name="Test",
                shortName=name
            )
            assert project.short_name == name.upper()
        
        # Invalid short names
        with pytest.raises(ValueError, match="Project short name cannot be empty"):
            Project(id="proj-1", name="Test", shortName="")
        
        with pytest.raises(ValueError, match="can only contain letters, numbers"):
            Project(id="proj-1", name="Test", shortName="TEST@#$")
        
        with pytest.raises(ValueError, match="should be 10 characters or less"):
            Project(id="proj-1", name="Test", shortName="VERYLONGPROJECTNAME")
    
    def test_text_field_validation(self):
        """Test text field validation and cleaning."""
        project_data = {
            "id": "project-123",
            "name": "  Test   Project  ",
            "shortName": "test",
            "description": "A\n\ntest\t\tproject\n"
        }
        
        project = Project(**project_data)
        
        assert project.name == "Test Project"
        assert project.description == "A test project"
    
    def test_timestamp_validation(self):
        """Test timestamp validation."""
        # Valid timestamps
        project = Project(
            id="proj-1",
            name="Test",
            shortName="TEST",
            created=1640995200000,
            updated=1640995201000
        )
        assert project.created == 1640995200000
        assert project.updated == 1640995201000
        
        # Invalid negative timestamp
        with pytest.raises(ValueError, match="Timestamp cannot be negative"):
            Project(
                id="proj-1",
                name="Test",
                shortName="TEST",
                created=-1
            )
    
    def test_project_utility_methods(self):
        """Test project utility methods."""
        # Active project
        active_project = Project(
            id="proj-1",
            name="Active Project",
            shortName="ACTIVE",
            archived=False
        )
        assert active_project.is_active() is True
        assert active_project.get_display_name() == "Active Project (ACTIVE)"
        
        # Archived project
        archived_project = Project(
            id="proj-2",
            name="Archived Project",
            shortName="ARCHIVED",
            archived=True
        )
        assert archived_project.is_active() is False


class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_issue_serialization(self):
        """Test issue model serialization."""
        issue_data = {
            "id": "TEST-123",
            "summary": "Test Issue",
            "customFields": [{"name": "Priority", "value": {"name": "High"}}]
        }
        
        issue = Issue(**issue_data)
        
        # Test model_dump
        serialized = issue.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["id"] == "TEST-123"
        assert serialized["summary"] == "Test Issue"
        
        # Test with aliases
        serialized_with_aliases = issue.model_dump(by_alias=True)
        assert "customFields" in serialized_with_aliases
    
    def test_user_serialization(self):
        """Test user model serialization."""
        user_data = {
            "id": "user-123",
            "login": "testuser",
            "ringId": "ring-123"
        }
        
        user = User(**user_data)
        
        serialized = user.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["id"] == "user-123"
        
        # Test with aliases
        serialized_with_aliases = user.model_dump(by_alias=True)
        assert "ringId" in serialized_with_aliases
    
    def test_project_serialization(self):
        """Test project model serialization."""
        project_data = {
            "id": "proj-123",
            "name": "Test Project",
            "shortName": "TEST"
        }
        
        project = Project(**project_data)
        
        serialized = project.model_dump()
        assert isinstance(serialized, dict)
        assert serialized["id"] == "proj-123"
        
        # Test with aliases
        serialized_with_aliases = project.model_dump(by_alias=True)
        assert "shortName" in serialized_with_aliases


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])