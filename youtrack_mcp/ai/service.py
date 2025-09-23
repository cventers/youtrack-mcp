"""
AI Service for YouTrack MCP Server.

Async service using LiteLLM + Instructor for structured outputs.
"""

from typing import Dict, Optional, Any, List
from cachetools import TTLCache
import structlog

from .llm_client import LLMClient
from .template_manager import TemplateManager
from .models import (
    YQLTranslationResponse,
    ErrorEnhancementResponse,
    IntentAnalysisResponse
)
from ..utils import ErrorHandler

logger = structlog.get_logger(__name__)


def get_mcp_tools_info(mcp_instance: Any) -> str:
    """Extract and format MCP tool information for LLM prompts.

    Args:
        mcp_instance: FastMCP server instance

    Returns:
        Formatted string describing available tools
    """
    try:
        # Try to get tools from FastMCP's tool manager
        if hasattr(mcp_instance, '_tool_manager') and hasattr(mcp_instance._tool_manager, 'list_tools'):
            tools = mcp_instance._tool_manager.list_tools()

            lines = ["Available MCP Tools:\n"]
            for tool in tools:
                lines.append(f"- {tool.name}: {tool.description or 'No description'}")
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if 'required' in schema:
                        lines.append(f"  Required: {', '.join(schema['required'])}")
                    if 'properties' in schema:
                        optional = set(schema['properties'].keys()) - set(schema.get('required', []))
                        if optional:
                            lines.append(f"  Optional: {', '.join(optional)}")

            return '\n'.join(lines)
    except Exception as e:
        logger.warning(f"Could not extract tool info: {e}")

    # Fallback: return basic tool list
    return """Available MCP Tools:
- search_query: Execute YouTrack Query Language
- search_autosearch: Natural language search (if AI enabled)
- issues_get: Get issue details
- issues_create: Create new issue
- issues_patch: Update issue
- projects_list: List projects
- projects_get: Get project details
- projects_create: Create project
- projects_patch: Update project
- users_search: Search users
- ai_plan: Plan intent execution (if AI enabled)"""


class AIService:
    """Unified AI service with async operations."""

    def __init__(
        self,
        llm_client: LLMClient,
        template_manager: Optional[TemplateManager] = None,
        error_handler: Optional[ErrorHandler] = None,
        mcp_instance: Optional[Any] = None
    ):
        """Initialize AI service.

        Args:
            llm_client: LLMClient instance for structured outputs
            template_manager: Optional template manager (will create if not provided)
            error_handler: Optional error handler for rule-based enhancement
            mcp_instance: Optional FastMCP instance for tool introspection
        """
        self.llm_client = llm_client
        self.template_manager = template_manager or TemplateManager()
        self.error_handler = error_handler or ErrorHandler()
        self.mcp_instance = mcp_instance

        # Caches
        self.query_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour
        self.error_cache = TTLCache(maxsize=500, ttl=1800)  # 30 minutes

        logger.info("AIService initialized")

    async def translate_nl_to_yql(
        self,
        natural_query: str,
        project_context: Optional[str] = None
    ) -> YQLTranslationResponse:
        """Translate natural language to YQL using LLM.

        Args:
            natural_query: Natural language query
            project_context: Optional project context

        Returns:
            YQLTranslationResponse with query and metadata
        """
        # Check cache
        cache_key = f"{natural_query}:{project_context}"
        if cache_key in self.query_cache:
            logger.debug("Using cached YQL translation", query=natural_query[:50])
            return self.query_cache[cache_key]

        try:
            # Render template
            messages = self.template_manager.render_messages(
                "yql/translation.j2",
                natural_query=natural_query,
                project_context=project_context
            )

            # Get structured response
            response = await self.llm_client.complete_structured(
                response_model=YQLTranslationResponse,
                messages=messages
            )

            # Cache result
            self.query_cache[cache_key] = response

            logger.info(
                "Translated natural language to YQL",
                query_preview=natural_query[:50],
                yql_preview=response.yql_query[:50],
                confidence=response.confidence
            )

            return response

        except Exception as e:
            logger.error(
                "YQL translation failed",
                query=natural_query,
                error=str(e)
            )
            # Return fallback response
            return YQLTranslationResponse(
                yql_query=f'text: "{natural_query}"',  # Fallback to text search
                confidence=0.1,
                reasoning=f"Translation failed: {str(e)}. Falling back to text search.",
                warnings=[f"Translation error: {str(e)}"]
            )

    async def enhance_error_with_llm(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> ErrorEnhancementResponse:
        """Enhance error message using LLM for better user guidance.

        Args:
            error: Exception that occurred
            context: Operation context

        Returns:
            ErrorEnhancementResponse with detailed guidance
        """
        # First try rule-based enhancement
        rule_based = self.error_handler.enhance_error(error, context)

        # Create cache key
        error_str = str(error)
        cache_key = f"{error_str[:100]}:{context.get('operation', 'unknown')}"

        if cache_key in self.error_cache:
            logger.debug("Using cached error enhancement")
            return self.error_cache[cache_key]

        try:
            # Render template
            messages = self.template_manager.render_messages(
                "error/enhancement.j2",
                error_type=type(error).__name__,
                error_message=error_str,
                context=str(context),
                operation=context.get('operation', 'Unknown')
            )

            # Get structured response
            response = await self.llm_client.complete_structured(
                response_model=ErrorEnhancementResponse,
                messages=messages
            )

            # Cache result
            self.error_cache[cache_key] = response

            logger.info(
                "Enhanced error with LLM",
                error_category=response.error_category,
                fix_time=response.estimated_fix_time
            )

            return response

        except Exception as llm_error:
            logger.warning(
                "LLM error enhancement failed, using rule-based",
                error=str(llm_error)
            )

            # Fall back to rule-based enhancement
            return ErrorEnhancementResponse(
                error_category="server",
                enhanced_explanation=rule_based.explanation,
                root_cause=rule_based.category,
                immediate_fix=rule_based.recommendation,
                prevention_tips=rule_based.learn_from_this.split('. ') if rule_based.learn_from_this else [],
                confidence=0.5,
                estimated_fix_time="needs_investigation"
            )

    async def analyze_intent(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysisResponse:
        """Analyze user intent and create execution plan.

        Args:
            intent: User's stated intent
            context: Optional context information

        Returns:
            IntentAnalysisResponse with execution plan
        """
        try:
            # Get available tools for the prompt
            tools_info = get_mcp_tools_info(self.mcp_instance) if self.mcp_instance else """Available MCP Tools:
- search_query: Execute YouTrack Query Language
- issues_get: Get issue details
- issues_create: Create new issue
- issues_patch: Update issue
- projects_list: List projects
- projects_get: Get project details
- users_search: Search users"""

            # Render template with tool information
            messages = self.template_manager.render_messages(
                "intent/analysis.j2",
                intent=intent,
                context=context or {},
                available_tools=tools_info
            )

            # Get structured response
            response = await self.llm_client.complete_structured(
                response_model=IntentAnalysisResponse,
                messages=messages
            )

            logger.info(
                "Analyzed user intent",
                intent_preview=intent[:50],
                category=response.intent_category,
                steps=len(response.plan),
                complexity=response.estimated_complexity
            )

            return response

        except Exception as e:
            logger.error(
                "Intent analysis failed",
                intent=intent,
                error=str(e)
            )
            raise

    def enhance_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based error enhancement (synchronous fallback).

        Args:
            error: Exception that occurred
            context: Operation context

        Returns:
            Enhanced error dictionary
        """
        result = self.error_handler.enhance_error(error, context)
        return {
            "explanation": result.explanation,
            "category": result.category,
            "recommendation": result.recommendation,
            "learn_from_this": result.learn_from_this
        }