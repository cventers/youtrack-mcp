"""
Template Loader for AI Prompts.

Loads and processes Jinja2 templates for AI prompts.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template

import logging

logger = logging.getLogger(__name__)


class PromptTemplateLoader:
    """
    Loads and processes Jinja2 templates for AI prompts.

    Templates are stored in the prompts/ directory at the project root.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize the template loader.

        Args:
            prompts_dir: Path to prompts directory. Defaults to project root/prompts/
        """
        if prompts_dir is None:
            # Default to prompts/ directory at project root
            project_root = Path(__file__).parent.parent.parent
            self.prompts_dir = project_root / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

        self._env: Optional[Environment] = None

        logger.info(f"PromptTemplateLoader initialized with prompts directory: {self.prompts_dir}")

    @property
    def env(self) -> Environment:
        """Get the Jinja2 environment, creating it if necessary."""
        if self._env is None:
            if not self.prompts_dir.exists():
                raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

            self._env = Environment(
                loader=FileSystemLoader(str(self.prompts_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False  # We don't need HTML escaping for prompts
            )

        return self._env

    def load_template(self, template_name: str) -> Template:
        """
        Load a template by name.

        Args:
            template_name: Name of the template file (without .j2 extension)

        Returns:
            Jinja2 Template object
        """
        try:
            return self.env.get_template(f"{template_name}.j2")
        except Exception as e:
            logger.error(f"Failed to load template '{template_name}': {e}")
            raise

    def render_template(self, template_name: str, **kwargs: Any) -> str:
        """
        Load and render a template with the given context.

        Args:
            template_name: Name of the template file (without .j2 extension)
            **kwargs: Template variables

        Returns:
            Rendered template as string
        """
        template = self.load_template(template_name)
        try:
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render template '{template_name}': {e}")
            raise

    def get_system_prompt(self, prompt_type: str) -> str:
        """
        Get a system prompt by type.

        Args:
            prompt_type: Type of prompt (e.g., 'yql_translation', 'error_enhancement', 'intent_analysis')

        Returns:
            System prompt content
        """
        return self.render_template(prompt_type)

    def get_user_prompt(self, prompt_type: str, **kwargs: Any) -> str:
        """
        Get a user prompt by type with context variables.

        Args:
            prompt_type: Type of prompt (e.g., 'yql_user_prompt', 'error_user_prompt', 'intent_user_prompt')
            **kwargs: Template variables

        Returns:
            User prompt content
        """
        return self.render_template(prompt_type, **kwargs)


# Global instance
_template_loader: Optional[PromptTemplateLoader] = None


def get_template_loader() -> PromptTemplateLoader:
    """Get the global template loader instance."""
    global _template_loader
    if _template_loader is None:
        _template_loader = PromptTemplateLoader()
    return _template_loader


__all__ = ["PromptTemplateLoader", "get_template_loader"]