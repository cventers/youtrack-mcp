"""Logging configuration for YouTrack MCP Server."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Centralized logging configuration.

    This configuration supports:
    - Global log level control
    - Separate console and file output configurations
    - Module-specific log levels
    - Rotation and size limits for file logging
    """

    # Global settings
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Console output
    console_enabled: bool = True
    console_format: Literal["color", "plain", "json"] = "color"
    console_level: Optional[str] = None  # Inherits from global if not set

    # File output
    file: Optional[Path] = None
    file_format: Literal["json", "text"] = "json"
    file_level: Optional[str] = None  # Inherits from global if not set
    file_rotation: bool = True
    file_max_bytes: int = 10_485_760  # 10MB
    file_backup_count: int = 5

    # Module-specific levels
    module_levels: dict[str, str] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True