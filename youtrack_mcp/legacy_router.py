"""
Legacy router for backward compatibility during tool calls refactor.

This module provides backward compatibility for the old args/kwargs + repair
pattern while logging deprecation warnings and routing to the new strict server.
"""

import json
import logging
import re
from typing import Dict, List, Any, Tuple, Optional

# Use structlog if available, otherwise fall back to standard logging
try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class LegacyParameterProcessor:
    """
    Processes legacy parameter formats and converts them to canonical form.

    This class handles all the complex repair logic from the original wrappers
    but routes to the new strict validation system.
    """

    def __init__(self):
        """Initialize the legacy parameter processor."""
        self.deprecation_warnings: Dict[str, bool] = {}

        # Common parameter name mappings from legacy system
        self.param_mappings = {
            "project": "project_id",
            "name": "project_name",
            "user": "user_id",
            "issue": "issue_id",
            "login": "user_login",
            "custom_field_id": "field_id",
        }

        # Tool-specific parameter mappings
        self.tool_mappings = {
            "issues.get": {
                "positional": ["issue_id"],
                "required": ["issue_id"]
            },
            "issues.create": {
                "positional": ["project", "summary", "description"],
                "required": ["project", "summary"]
            },
            "issues.patch": {
                "positional": ["issue_id"],
                "required": ["issue_id"]
            },
            "projects.get": {
                "positional": ["project_id"],
                "required": ["project_id"]
            },
            "projects.schema": {
                "positional": ["project_id"],
                "required": ["project_id"]
            },
            "search.query": {
                "positional": ["query"],
                "required": ["query"]
            },
            "search.autosearch": {
                "positional": ["natural_language_query"],
                "required": ["natural_language_query"]
            },
            "users.search": {
                "positional": ["query"],
                "required": ["query"]
            },
            "ai.plan": {
                "positional": ["intent"],
                "required": ["intent"]
            },
            "resources.read": {
                "positional": ["uri"],
                "required": ["uri"]
            }
        }

    def process_legacy_call(
        self,
        tool_name: str,
        args: Tuple,
        kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a legacy tool call and convert to canonical format.

        Args:
            tool_name: The tool name
            args: Legacy positional arguments
            kwargs: Legacy keyword arguments

        Returns:
            Canonical arguments dictionary
        """
        # Log deprecation warning (once per tool)
        if tool_name not in self.deprecation_warnings:
            logger.warning(
                f"DEPRECATED: Legacy tool call format detected for '{tool_name}'. "
                f"Please migrate to canonical JSON format: "
                f'{{"tool_name": "{tool_name}", "arguments": {{...}}}}'
            )
            self.deprecation_warnings[tool_name] = True

        # Process the legacy parameters
        processed_args, processed_kwargs = self._process_parameters(args, kwargs)

        # Apply tool-specific mappings
        canonical_kwargs = self._apply_tool_mappings(tool_name, processed_args, processed_kwargs)

        # Apply global parameter name mappings
        canonical_kwargs = self._apply_global_mappings(canonical_kwargs)

        # Clean up the result
        canonical_kwargs = self._cleanup_parameters(canonical_kwargs)

        logger.debug(f"Converted legacy call for {tool_name}: {canonical_kwargs}")
        return canonical_kwargs

    def _process_parameters(
        self,
        args: Tuple,
        kwargs: Dict[str, Any]
    ) -> Tuple[Tuple, Dict[str, Any]]:
        """
        Process legacy parameters with repair logic.

        This replicates the complex parameter processing from the original wrappers.
        """
        processed_args = list(args)
        processed_kwargs = kwargs.copy()

        # Handle 'args' parameter specially (common in MCP calls)
        if "args" in processed_kwargs:
            args_value = processed_kwargs.pop("args")
            processed_args, processed_kwargs = self._process_args_parameter(
                args_value, processed_args, processed_kwargs
            )

        # Handle 'kwargs' parameter specially
        if "kwargs" in processed_kwargs:
            kwargs_value = processed_kwargs.pop("kwargs")
            processed_kwargs = self._process_kwargs_parameter(
                kwargs_value, processed_kwargs
            )

        return tuple(processed_args), processed_kwargs

    def _process_args_parameter(
        self,
        args_value: Any,
        processed_args: List,
        processed_kwargs: Dict[str, Any]
    ) -> Tuple[Tuple, Dict[str, Any]]:
        """Process the 'args' parameter from legacy calls."""
        if isinstance(args_value, str):
            # Try to parse as JSON
            if args_value.strip().startswith("{") and args_value.strip().endswith("}"):
                try:
                    # Clean up JSON formatting issues
                    cleaned_json = self._clean_json_string(args_value)
                    args_dict = json.loads(cleaned_json)
                    if isinstance(args_dict, dict):
                        # Merge into kwargs
                        for k, v in args_dict.items():
                            processed_kwargs[k] = v
                    else:
                        processed_args.insert(0, args_dict)
                except json.JSONDecodeError:
                    # Try parsing as key=value pairs
                    processed_args, processed_kwargs = self._parse_key_value_string(
                        args_value, processed_args, processed_kwargs
                    )
            else:
                # Try parsing as Python literal or key=value
                processed_args, processed_kwargs = self._parse_key_value_string(
                    args_value, processed_args, processed_kwargs
                )
        elif isinstance(args_value, (list, tuple)):
            processed_args.extend(args_value)
        else:
            processed_args.insert(0, args_value)

        return tuple(processed_args), processed_kwargs

    def _process_kwargs_parameter(
        self,
        kwargs_value: Any,
        processed_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the 'kwargs' parameter from legacy calls."""
        if isinstance(kwargs_value, str):
            if kwargs_value.strip().startswith("{") and kwargs_value.strip().endswith("}"):
                try:
                    cleaned_json = self._clean_json_string(kwargs_value)
                    kwargs_dict = json.loads(cleaned_json)
                    if isinstance(kwargs_dict, dict):
                        processed_kwargs.update(kwargs_dict)
                except json.JSONDecodeError:
                    # Try parsing as key=value format
                    processed_kwargs = self._parse_kwargs_string(kwargs_value, processed_kwargs)
            else:
                processed_kwargs = self._parse_kwargs_string(kwargs_value, processed_kwargs)
        elif isinstance(kwargs_value, dict):
            processed_kwargs.update(kwargs_value)

        return processed_kwargs

    def _clean_json_string(self, json_str: str) -> str:
        """Clean up common JSON formatting issues from legacy calls."""
        cleaned = json_str.strip()

        # Remove extra closing braces
        if cleaned.count('}') > cleaned.count('{'):
            logger.debug("Fixing JSON with extra closing braces")
            while cleaned.endswith('}}') and cleaned.count('}') > cleaned.count('{'):
                cleaned = cleaned[:-1]

        return cleaned

    def _parse_key_value_string(
        self,
        value_str: str,
        processed_args: List,
        processed_kwargs: Dict[str, Any]
    ) -> Tuple[Tuple, Dict[str, Any]]:
        """Parse a string as key=value pairs or positional arguments."""
        try:
            import shlex
            split_args = shlex.split(value_str)

            for arg in split_args:
                if "=" in arg and not arg.startswith("{"):
                    # Parse as key=value pair
                    key, value = arg.split("=", 1)
                    value = self._clean_value_string(value)
                    processed_kwargs[key] = value
                else:
                    # Treat as positional argument
                    clean_arg = self._clean_value_string(arg)
                    processed_args.append(clean_arg)
        except Exception:
            # If parsing fails, treat as single positional argument
            if value_str.strip():
                processed_args.append(value_str.strip())

        return tuple(processed_args), processed_kwargs

    def _parse_kwargs_string(
        self,
        kwargs_str: str,
        processed_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse a kwargs string into a dictionary."""
        parts = kwargs_str.split(",")
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = self._clean_value_string(v)
                processed_kwargs[k] = v

        return processed_kwargs

    def _clean_value_string(self, value: str) -> Any:
        """Clean up a value string and convert types."""
        value = value.strip()

        # Remove quotes
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        # Remove trailing commas
        value = value.rstrip(",")

        # Convert types
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        elif value.isdigit():
            return int(value)
        elif value.replace(".", "", 1).isdigit():
            return float(value)

        return value

    def _apply_tool_mappings(
        self,
        tool_name: str,
        processed_args: Tuple,
        processed_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply tool-specific parameter mappings."""
        if tool_name not in self.tool_mappings:
            # For unknown tools, just merge everything into kwargs
            canonical = dict(processed_kwargs)
            if processed_args:
                # Use first positional arg as primary parameter
                canonical["arg_value"] = processed_args[0]
            return canonical

        mapping = self.tool_mappings[tool_name]
        canonical = {}

        # Map positional arguments
        positional_params = mapping["positional"]
        for i, param_name in enumerate(positional_params):
            if i < len(processed_args):
                canonical[param_name] = processed_args[i]

        # Add keyword arguments
        canonical.update(processed_kwargs)

        return canonical

    def _apply_global_mappings(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply global parameter name mappings."""
        mapped = {}
        for key, value in kwargs.items():
            # Apply parameter name mapping if applicable
            target_key = self.param_mappings.get(key, key)
            mapped[target_key] = value

        return mapped

    def _cleanup_parameters(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up and validate parameters."""
        # Remove None values (treat as missing)
        cleaned = {k: v for k, v in kwargs.items() if v is not None}

        # Apply type conversions for common patterns
        for param_name, param_value in list(cleaned.items()):
            if isinstance(param_value, str):
                # Convert boolean strings
                if param_value.lower() in ("true", "false"):
                    cleaned[param_name] = param_value.lower() == "true"
                # Convert integer strings
                elif param_value.isdigit():
                    cleaned[param_name] = int(param_value)
                # Convert float strings
                elif param_value.replace(".", "", 1).isdigit():
                    cleaned[param_name] = float(param_value)

        return cleaned


class LegacyRouter:
    """
    Legacy router that provides backward compatibility.

    This router accepts old args/kwargs patterns and converts them
    to canonical format for the strict server.
    """

    def __init__(self, strict_server: Any):
        """
        Initialize the legacy router.

        Args:
            strict_server: The strict server instance to route to
        """
        self.strict_server = strict_server
        self.processor = LegacyParameterProcessor()

    def route_legacy_tool_call(
        self,
        tool_name: str,
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Route a legacy tool call to the strict server.

        Args:
            tool_name: The tool name
            args: Legacy positional arguments
            kwargs: Legacy keyword arguments

        Returns:
            The result from the strict server
        """
        if kwargs is None:
            kwargs = {}

        # Convert legacy format to canonical
        canonical_kwargs = self.processor.process_legacy_call(tool_name, args, kwargs)

        # Route to strict server
        # This assumes the strict server has a method to handle canonical calls
        return self._call_strict_server(tool_name, canonical_kwargs)

    def _call_strict_server(self, tool_name: str, canonical_kwargs: Dict[str, Any]) -> Any:
        """
        Call the strict server with canonical arguments.

        This is a placeholder - actual implementation would depend on
        how the strict server exposes its tools.
        """
        # For now, return a mock response
        # In real implementation, this would call the actual tool function
        logger.info(f"Routing legacy call for {tool_name} to strict server with: {canonical_kwargs}")

        return {
            "tool": tool_name,
            "canonical_args": canonical_kwargs,
            "legacy_routed": True,
            "message": "Legacy call successfully routed to strict server"
        }


# Environment variable to control legacy router behavior
MCP_PARAM_REPAIR = "MCP_PARAM_REPAIR"

def should_enable_legacy_router() -> bool:
    """
    Check if legacy router should be enabled.

    Returns:
        True if legacy router should be enabled, False otherwise
    """
    import os
    return os.getenv(MCP_PARAM_REPAIR, "false").lower() in ("true", "1", "yes")


__all__ = [
    "LegacyParameterProcessor",
    "LegacyRouter",
    "should_enable_legacy_router",
    "MCP_PARAM_REPAIR"
]