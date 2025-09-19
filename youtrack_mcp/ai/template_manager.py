"""Jinja2 template manager for maintainable prompt management."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
import structlog
import re

logger = structlog.get_logger(__name__)


class TemplateManager:
    """Manages Jinja2 templates for LLM prompts."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            template_dir: Directory containing templates.
                         Defaults to ai/templates relative to this file.
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        logger.info("Initialized template manager", template_dir=str(template_dir))

    def render(self, template_name: str, **context) -> Dict[str, str]:
        """Render a template and parse into messages.

        Args:
            template_name: Name of template file (e.g., "yql/translation.j2")
            **context: Variables to pass to template

        Returns:
            Dictionary with "system" and "user" message content
        """
        try:
            template = self.env.get_template(template_name)
            content = template.render(**context)
            messages = self._parse_messages(content)

            logger.debug(
                "Rendered template",
                template=template_name,
                context_keys=list(context.keys()),
                message_count=len([m for m in messages.values() if m])
            )

            return messages
        except Exception as e:
            logger.error(
                "Template rendering failed",
                template=template_name,
                error=str(e)
            )
            raise

    def render_messages(self, template_name: str, **context) -> List[Dict[str, str]]:
        """Render a template and return as message list.

        Args:
            template_name: Name of template file
            **context: Variables to pass to template

        Returns:
            List of message dictionaries with "role" and "content"
        """
        parsed = self.render(template_name, **context)
        messages = []

        if parsed.get("system"):
            messages.append({
                "role": "system",
                "content": parsed["system"]
            })

        if parsed.get("user"):
            messages.append({
                "role": "user",
                "content": parsed["user"]
            })

        return messages

    def _parse_messages(self, content: str) -> Dict[str, str]:
        """Parse rendered template into system and user messages.

        Args:
            content: Rendered template content

        Returns:
            Dictionary with "system" and "user" keys
        """
        # Split by message separator
        parts = content.split("---MSG_SEPARATOR---")[0].strip()

        # Extract system and user blocks using regex
        system_pattern = r"{# System message block - override in child templates #}\s*(.*?)\s*{# User message block"
        user_pattern = r"{# User message block - override in child templates #}\s*(.*?)$"

        # Try to find blocks
        result = {"system": "", "user": ""}

        # Look for actual content between block markers
        # The template will have replaced the blocks with actual content
        # We need to split based on the structure
        lines = parts.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            # Skip empty lines at section boundaries
            if not line.strip():
                if current_content and current_content[-1].strip():
                    current_content.append(line)
                continue

            # The rendered template should have clear content
            # Since we extend base.j2, the blocks are replaced
            if current_section is None:
                current_section = "system"

            current_content.append(line)

            # Check if we've hit the user section
            # This is a heuristic based on template structure
            if "Task:" in line or "Analyze" in line or "User Intent:" in line:
                if current_section == "system" and current_content:
                    # Save system content up to this point
                    result["system"] = '\n'.join(current_content[:-1]).strip()
                    current_section = "user"
                    current_content = [line]

        # Save remaining content as user section
        if current_section == "user" and current_content:
            result["user"] = '\n'.join(current_content).strip()
        elif current_section == "system" and current_content:
            # If we never found a user section, treat all as system
            # But try to split if there's a clear boundary
            full_content = '\n'.join(current_content).strip()
            if '\n\n' in full_content:
                # Split on double newline
                parts = full_content.split('\n\n', 1)
                if len(parts) == 2:
                    result["system"] = parts[0].strip()
                    result["user"] = parts[1].strip()
                else:
                    result["system"] = full_content
            else:
                result["system"] = full_content

        return result

    def get_template(self, template_name: str) -> Template:
        """Get a raw Jinja2 template object.

        Args:
            template_name: Name of template file

        Returns:
            Jinja2 Template object
        """
        return self.env.get_template(template_name)

    def list_templates(self) -> List[str]:
        """List all available templates.

        Returns:
            List of template names
        """
        templates = []
        for path in self.template_dir.rglob("*.j2"):
            relative = path.relative_to(self.template_dir)
            templates.append(str(relative))
        return sorted(templates)