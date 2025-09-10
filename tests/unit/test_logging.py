"""
Tests for logging configuration functionality.
"""

import os
import sys
import tempfile
import logging
import pytest
from unittest.mock import patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from youtrack_mcp.config import Config


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_default_logging_config(self):
        """Test default logging configuration values."""
        config = Config()

        assert config.LOG_LEVEL == "INFO"
        assert config.LOG_FILE is None
        assert config.LOG_CONSOLE_DISABLE is False

    def test_environment_logging_config(self):
        """Test logging configuration from environment variables."""
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': '/tmp/test.log',
            'LOG_CONSOLE_DISABLE': 'true'
        }):
            config = Config()
            assert config.LOG_LEVEL == "DEBUG"
            assert config.LOG_FILE == "/tmp/test.log"
            assert config.LOG_CONSOLE_DISABLE is True

    def test_yaml_logging_config(self):
        """Test logging configuration from YAML."""
        yaml_content = """
logging:
  level: WARNING
  file: /tmp/yaml_test.log
  console_disable: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                Config.load_from_yaml(f.name)
                assert Config.LOG_LEVEL == "WARNING"
                assert Config.LOG_FILE == "/tmp/yaml_test.log"
                assert Config.LOG_CONSOLE_DISABLE is True
            finally:
                os.unlink(f.name)

    @patch('main.setup_logging')
    @patch('main.load_config')
    def test_main_calls_setup_logging(self, mock_load_config, mock_setup_logging):
        """Test that main function calls setup_logging after config loading."""
        import main
        import sys
        from unittest.mock import patch

        # Mock command line arguments
        test_args = ['--version']
        with patch.object(sys, 'argv', ['main.py'] + test_args):
            with patch('main.parse_args') as mock_parse_args:
                mock_args = MagicMock()
                mock_args.version = True
                mock_parse_args.return_value = mock_args

                # Mock the version print and exit
                with patch('builtins.print'):
                    with patch('sys.exit'):
                        main.main()

                # Verify setup_logging was called
                mock_setup_logging.assert_called_once()


class TestLoggingSetup:
    """Test the logging setup functionality."""

    @patch('main.structlog_available', False)
    @patch('logging.basicConfig')
    def test_setup_logging_standard_only(self, mock_basic_config):
        """Test logging setup with standard logging only."""
        import main
        from youtrack_mcp.config import config

        # Set up test config
        config.LOG_LEVEL = "INFO"
        config.LOG_FILE = None
        config.LOG_CONSOLE_DISABLE = False

        main.setup_logging()

        # Verify basicConfig was called
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        assert kwargs['level'] == logging.INFO
        assert len(kwargs['handlers']) == 1  # Console handler only

    @patch('main.structlog_available', False)
    @patch('logging.basicConfig')
    @patch('os.makedirs')
    @patch('logging.FileHandler')
    def test_setup_logging_with_file(self, mock_file_handler, mock_makedirs, mock_basic_config):
        """Test logging setup with file output."""
        import main
        from youtrack_mcp.config import config

        # Set up test config
        config.LOG_LEVEL = "DEBUG"
        config.LOG_FILE = "/tmp/test.log"
        config.LOG_CONSOLE_DISABLE = False

        mock_handler = MagicMock()
        mock_file_handler.return_value = mock_handler

        main.setup_logging()

        # Verify file handler was created
        mock_file_handler.assert_called_once_with("/tmp/test.log")
        mock_makedirs.assert_called_once()

        # Verify basicConfig was called with both handlers
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        assert len(kwargs['handlers']) == 2  # Console + file handlers

    @patch('main.structlog_available', False)
    @patch('logging.basicConfig')
    def test_setup_logging_console_disabled(self, mock_basic_config):
        """Test logging setup with console disabled."""
        import main
        from youtrack_mcp.config import config

        # Set up test config
        config.LOG_LEVEL = "INFO"
        config.LOG_FILE = "/tmp/test.log"
        config.LOG_CONSOLE_DISABLE = True

        with patch('os.makedirs'), patch('logging.FileHandler'):
            main.setup_logging()

        # Verify basicConfig was called with only file handler
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        assert len(kwargs['handlers']) == 1  # File handler only (console disabled)