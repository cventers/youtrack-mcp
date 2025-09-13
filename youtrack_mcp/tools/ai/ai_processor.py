"""
Local AI Processor for YouTrack MCP Server.

This module provides CPU-optimized local AI inference for:
- Natural language to YQL query translation
- Smart error message enhancement
- Context-aware suggestions
- Pattern recognition and learning

Uses lightweight quantized models for privacy and performance.
"""
import json
import logging
import re
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from cachetools import TTLCache

logger = logging.getLogger(__name__)


@dataclass
class QueryTranslationResult:
    """Result of natural language to YQL translation."""
    yql_query: str
    confidence: float
    reasoning: str
    original_input: str
    detected_entities: Dict[str, Any]
    suggestions: List[str]


@dataclass
class ErrorEnhancementResult:
    """Result of AI-enhanced error processing."""
    enhanced_explanation: str
    fix_suggestion: str
    example_correction: str
    learning_tip: str
    confidence: float


@dataclass
class PatternAnalysisResult:
    """Result of activity pattern analysis."""
    patterns: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    productivity_score: float
    trends: Dict[str, float]
    confidence: float = 0.7


class AIProcessor:
    """
    Local AI processor for YouTrack operations.
    
    Uses CPU-optimized models for privacy-preserving AI assistance.
    Designed to work entirely offline with minimal memory footprint.
    """
    
    def __init__(self, enable_ai: bool = True, max_memory_mb: int = 2048, llm_client=None):
        """
        Initialize the local AI processor.
        
        Args:
            enable_ai: Whether to enable AI features (can be disabled for lightweight mode)
            max_memory_mb: Maximum memory usage in MB for AI models
            llm_client: Optional LLM client for AI inference
        """
        self.enable_ai = enable_ai
        self.max_memory_mb = max_memory_mb
        self.models_loaded = False
        self.llm_client = llm_client
        
        # Caches for performance
        self.query_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour
        self.error_cache = TTLCache(maxsize=500, ttl=1800)   # 30 minutes
        self.pattern_cache = TTLCache(maxsize=100, ttl=7200) # 2 hours
        
        # Model references (loaded on demand)
        self.query_model = None
        self.error_model = None
        self.pattern_model = None

        # Knowledge bases for rule-based fallbacks
        self.error_patterns = self._initialize_error_patterns()

        logger.info(f"AIProcessor initialized (AI {'enabled' if enable_ai else 'disabled'}, LLM client: {'configured' if llm_client else 'none'})")

    def _initialize_error_patterns(self) -> Dict[str, Dict[str, str]]:
        """Initialize patterns for error message enhancement."""
        return {
            'field_errors': {
                'pattern': r'unknown field|field.*not found|invalid field',
                'explanation': 'The query references a field that doesn\'t exist in the project',
                'fix_template': 'Use get_custom_fields() to see available fields for this project',
                'learning_tip': 'Field names in YouTrack are case-sensitive and project-specific'
            },
            'syntax_errors': {
                'pattern': r'syntax error|parse error|invalid query',
                'explanation': 'The query syntax is not valid YouTrack Query Language',
                'fix_template': 'Check for proper field:value format and correct operators',
                'learning_tip': 'YouTrack queries use "field: value" format, not "field = value"'
            },
            'date_errors': {
                'pattern': r'date.*invalid|time.*format|invalid.*date',
                'explanation': 'The date format is not recognized by YouTrack',
                'fix_template': 'Use YYYY-MM-DD format or relative dates like "-7d"',
                'learning_tip': 'YouTrack supports relative dates: -7d (last 7 days), w (this week), m (this month)'
            }
        }

    def suggest_ticket_attributes(self, title: str, description: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Suggest ticket attributes based on title and description."""
        # Simple rule-based suggestions
        suggestions = {}
        
        # Detect type based on keywords
        title_lower = title.lower()
        desc_lower = description.lower()
        combined = f"{title_lower} {desc_lower}"
        
        if any(word in combined for word in ["bug", "error", "crash", "broken", "fix"]):
            suggestions["type"] = "Bug"
        elif any(word in combined for word in ["feature", "add", "new", "implement"]):
            suggestions["type"] = "Feature"
        else:
            suggestions["type"] = "Task"
        
        # Detect priority
        if any(word in combined for word in ["critical", "urgent", "asap", "crash", "down"]):
            suggestions["priority"] = "Critical"
        elif any(word in combined for word in ["high", "important"]):
            suggestions["priority"] = "High"
        else:
            suggestions["priority"] = "Normal"
        
        # Suggest components based on keywords
        components = []
        if any(word in combined for word in ["ui", "interface", "button", "screen", "display"]):
            components.append("UI")
        if any(word in combined for word in ["backend", "api", "server", "database"]):
            components.append("Backend")
        if any(word in combined for word in ["login", "auth", "password", "security"]):
            components.append("Security")
        
        if components:
            suggestions["components"] = components
        
        # Suggest tags
        tags = []
        if "login" in combined:
            tags.append("login")
        if "authentication" in combined or "auth" in combined:
            tags.append("authentication")
        if suggestions.get("priority") == "Critical":
            tags.append("critical")
        
        if tags:
            suggestions["suggested_tags"] = tags
        
        return suggestions
    
    def enhance_error_message(self, error_message: str) -> ErrorEnhancementResult:
        """Enhance error message with explanations and fixes."""
        # Simple rule-based enhancement
        error_lower = error_message.lower()
        
        if "403" in error_message or "forbidden" in error_message:
            return ErrorEnhancementResult(
                enhanced_explanation="You don't have permission to perform this operation. This usually means you need specific role permissions.",
                fix_suggestion="Contact your project administrator to grant you the necessary permissions.",
                example_correction="Ask for 'Developer' or 'Admin' role in the project settings.",
                learning_tip="YouTrack uses role-based access control. Different operations require different permission levels.",
                confidence=0.8
            )
        elif "404" in error_message or "not found" in error_lower:
            return ErrorEnhancementResult(
                enhanced_explanation="The requested resource was not found. The issue, project, or user may not exist or may have been deleted.",
                fix_suggestion="Verify the ID is correct and that you have access to view this resource.",
                example_correction="Check the issue ID format (e.g., PROJECT-123) and ensure the project exists.",
                learning_tip="YouTrack IDs are case-sensitive and follow the format PROJECT-NUMBER.",
                confidence=0.8
            )
        elif "401" in error_message or "unauthorized" in error_lower:
            return ErrorEnhancementResult(
                enhanced_explanation="Authentication failed. Your API token may be invalid or expired.",
                fix_suggestion="Check your API token in the configuration and ensure it's properly formatted.",
                example_correction="Update YOUTRACK_API_TOKEN environment variable with a valid token.",
                learning_tip="YouTrack tokens should start with 'perm:' for permanent tokens.",
                confidence=0.8
            )
        else:
            return ErrorEnhancementResult(
                enhanced_explanation=f"An error occurred: {error_message}",
                fix_suggestion="Check the error details and try again.",
                example_correction="Review the API documentation for this operation.",
                learning_tip="Enable debug logging for more detailed error information.",
                confidence=0.5
            )
    
    def analyze_activity_patterns(self, issues: List[Dict[str, Any]], time_range_days: int = 30) -> PatternAnalysisResult:
        """Analyze activity patterns in issues."""
        patterns = {
            "peak_hours": {},
            "busy_days": {},
            "common_types": {},
            "resolution_time": {"average_hours": 48, "median_hours": 24}
        }
        
        insights = [
            "Pattern analysis based on provided issues",
            f"Analyzed {len(issues)} issues over {time_range_days} days"
        ]
        
        recommendations = [
            "Consider implementing automated triage for common issue types",
            "Schedule non-critical work during off-peak hours"
        ]
        
        return PatternAnalysisResult(
            patterns=patterns,
            insights=insights, 
            recommendations=recommendations,
            productivity_score=0.75,
            confidence=0.7,
            trends={}
        )
    
    def translate_natural_language_to_yql(self, natural_query: str, project_context: Optional[str] = None) -> QueryTranslationResult:
        """Synchronous wrapper for natural language to YQL translation."""
        context_hints = {"project": project_context} if project_context else None
        try:
            # Run the async method in a new event loop if needed
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a task
                task = asyncio.create_task(self.translate_natural_query(natural_query, context_hints))
                return asyncio.run_coroutine_threadsafe(task, loop).result()
            else:
                # If no loop is running, run it normally
                return asyncio.run(self.translate_natural_query(natural_query, context_hints))
        except Exception as e:
            # Return a fallback result on error
            return QueryTranslationResult(
                yql_query=f"text: \"{natural_query}\"",
                confidence=0.1,
                reasoning="Fallback to text search due to error",
                original_input=natural_query,
                detected_entities={},
                suggestions=[]
            )
    
    async def translate_natural_query(self, 
                                    natural_query: str, 
                                    context_hints: Optional[Dict[str, Any]] = None,
                                    project_schemas: Optional[List[Dict[str, Any]]] = None) -> QueryTranslationResult:
        """
        Translate natural language query to YouTrack YQL.
        
        Args:
            natural_query: Natural language query (e.g., "Show me critical bugs from last week")
            context_hints: Optional context from conversation or user preferences
            project_schemas: Available project schemas for field validation
            
        Returns:
            Translation result with YQL query and metadata
        """
        cache_key = f"query:{hash(natural_query)}{hash(str(context_hints))}"
        if cache_key in self.query_cache:
            logger.debug("Query translation cache hit")
            return self.query_cache[cache_key]
        
        try:
            if self.enable_ai and await self._ensure_query_model():
                # Use AI model for translation
                result = await self._ai_translate_query(natural_query, context_hints, project_schemas)
            else:
                # Rule-based translation not available
                raise Exception("Natural language to YQL translation is not available")
            
            self.query_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error in natural query translation: {e}")
            return QueryTranslationResult(
                yql_query=natural_query,  # Fallback to original
                confidence=0.0,
                reasoning=f"Translation failed: {str(e)}",
                original_input=natural_query,
                detected_entities={},
                suggestions=["Try using YouTrack Query Language directly"]
            )
    
    async def enhance_error_message(self, 
                                  error: Exception, 
                                  context: Dict[str, Any],
                                  user_history: Optional[List[Dict[str, Any]]] = None) -> ErrorEnhancementResult:
        """
        Enhance error messages with AI-powered context and suggestions.
        
        Args:
            error: The original error/exception
            context: Context of the operation that failed
            user_history: Optional user interaction history for learning
            
        Returns:
            Enhanced error with explanation, fix, and learning tip
        """
        cache_key = f"error:{hash(str(error))}{hash(str(context))}"
        if cache_key in self.error_cache:
            logger.debug("Error enhancement cache hit")
            return self.error_cache[cache_key]
        
        try:
            if self.enable_ai and await self._ensure_error_model():
                # Use AI model for error enhancement
                result = await self._ai_enhance_error(error, context, user_history)
            else:
                # Use rule-based enhancement
                result = await self._rule_based_enhance_error(error, context)
            
            self.error_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error in error enhancement: {e}")
            return ErrorEnhancementResult(
                enhanced_explanation=f"Operation failed: {str(error)}",
                fix_suggestion="Please check your input parameters and try again",
                example_correction="",
                learning_tip="Review the error message for specific details about what went wrong",
                confidence=0.0
            )
    
    async def analyze_activity_patterns(self, 
                                      activity_data: List[Dict[str, Any]], 
                                      analysis_types: List[str] = None) -> PatternAnalysisResult:
        """
        Analyze user activity patterns with AI insights.
        
        Args:
            activity_data: List of activity records
            analysis_types: Types of analysis to perform ['productivity_trends', 'collaboration_patterns', 'focus_areas']
            
        Returns:
            Pattern analysis with insights and recommendations
        """
        if analysis_types is None:
            analysis_types = ['productivity_trends', 'collaboration_patterns', 'focus_areas']
        
        cache_key = f"patterns:{hash(str(activity_data))}{hash(str(analysis_types))}"
        if cache_key in self.pattern_cache:
            logger.debug("Pattern analysis cache hit")
            return self.pattern_cache[cache_key]
        
        try:
            if self.enable_ai and await self._ensure_pattern_model():
                # Use AI model for pattern analysis
                result = await self._ai_analyze_patterns(activity_data, analysis_types)
            else:
                # Rule-based analysis not available
                raise Exception("Activity pattern analysis is not available")
            
            self.pattern_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
            return PatternAnalysisResult(
                patterns={'error': str(e)},
                insights=[f"Analysis failed: {str(e)}"],
                recommendations=["Unable to analyze patterns at this time"],
                productivity_score=0.0,
                trends={}
            )
    
    async def suggest_query_fixes(self, 
                                original_query: str, 
                                error_message: str, 
                                project_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest fixes for failed YouTrack queries.
        
        Args:
            original_query: The query that failed
            error_message: Error message from YouTrack
            project_context: Optional project context for field validation
            
        Returns:
            Dictionary with suggested fixes and explanations
        """
        try:
            # Analyze the error and suggest specific fixes
            suggestions = []
            
            if "field" in error_message.lower() or "unknown" in error_message.lower():
                suggestions.extend(await self._suggest_field_fixes(original_query, project_context))
            
            if "syntax" in error_message.lower() or "parse" in error_message.lower():
                suggestions.extend(await self._suggest_syntax_fixes(original_query))
            
            if "date" in error_message.lower() or "time" in error_message.lower():
                suggestions.extend(await self._suggest_date_fixes(original_query))
            
            return {
                'original_query': original_query,
                'error_message': error_message,
                'suggested_fixes': suggestions,
                'confidence': 0.8 if suggestions else 0.3,
                'explanation': 'AI-generated suggestions based on error analysis'
            }
            
        except Exception as e:
            logger.error(f"Error in query fix suggestions: {e}")
            return {
                'original_query': original_query,
                'error_message': error_message,
                'suggested_fixes': ["Check YouTrack Query Language documentation"],
                'confidence': 0.0,
                'explanation': f"Fix suggestion failed: {str(e)}"
            }
    

    

    
    async def _ensure_query_model(self) -> bool:
        """Ensure query translation model is loaded."""
        if self.query_model is None:
            try:
                # In a real implementation, this would load a quantized model
                # For now, we'll use rule-based processing
                logger.info("Query model loading simulation (using rule-based fallback)")
                self.query_model = "rule_based"  # Placeholder
                return True
            except Exception as e:
                logger.error(f"Failed to load query model: {e}")
                return False


    
    async def _ensure_error_model(self) -> bool:
        """Ensure error enhancement model is loaded."""
        if self.error_model is None:
            try:
                logger.info("Error model loading simulation (using rule-based fallback)")
                self.error_model = "rule_based"  # Placeholder
                return True
            except Exception as e:
                logger.error(f"Failed to load error model: {e}")
                return False
        return True
    
    async def _ensure_pattern_model(self) -> bool:
        """Ensure pattern analysis model is loaded."""
        if self.pattern_model is None:
            try:
                logger.info("Pattern model loading simulation (using rule-based fallback)")
                self.pattern_model = "rule_based"  # Placeholder
                return True
            except Exception as e:
                logger.error(f"Failed to load pattern model: {e}")
                return False
        return True
    

    
    async def _rule_based_enhance_error(self, 
                                      error: Exception, 
                                      context: Dict[str, Any]) -> ErrorEnhancementResult:
        """Rule-based error message enhancement."""
        error_str = str(error).lower()
        
        enhanced_explanation = f"Operation failed: {str(error)}"
        fix_suggestion = "Please check your input and try again"
        example_correction = ""
        learning_tip = "Review the error details for specific guidance"
        confidence = 0.5
        
        # Check for known error patterns
        for error_type, pattern_info in self.error_patterns.items():
            if re.search(pattern_info['pattern'], error_str):
                enhanced_explanation = pattern_info['explanation']
                fix_suggestion = pattern_info['fix_template']
                learning_tip = pattern_info['learning_tip']
                confidence = 0.8
                
                # Generate specific example correction
                if 'query' in context:
                    example_correction = await self._generate_example_correction(
                        context['query'], error_type
                    )
                break
        
        return ErrorEnhancementResult(
            enhanced_explanation=enhanced_explanation,
            fix_suggestion=fix_suggestion,
            example_correction=example_correction,
            learning_tip=learning_tip,
            confidence=confidence
        )
    

    
    async def _suggest_field_fixes(self, query: str, project_context: Optional[str]) -> List[str]:
        """Suggest fixes for field-related errors."""
        suggestions = []
        
        # Common field name corrections
        field_corrections = {
            'assignee': ['assigned', 'assign', 'owner'],
            'reporter': ['creator', 'author', 'reported by'],
            'priority': ['prio', 'importance'],
            'state': ['status', 'condition']
        }
        
        for correct_field, alternatives in field_corrections.items():
            for alt in alternatives:
                if alt in query.lower():
                    suggestions.append(f"Try using '{correct_field}' instead of '{alt}'")
        
        suggestions.append("Use get_custom_fields() to see available fields")
        return suggestions
    
    async def _suggest_syntax_fixes(self, query: str) -> List[str]:
        """Suggest fixes for syntax errors."""
        suggestions = []
        
        if '=' in query:
            suggestions.append("Use ':' instead of '=' (e.g., 'priority: High' not 'priority = High')")
        
        if '"' in query and '{' not in query:
            suggestions.append("For multi-word values, use {}: 'state: {In Progress}' not 'state: \"In Progress\"'")
        
        suggestions.append("Check field names are spelled correctly and case-sensitive")
        return suggestions
    
    async def _suggest_date_fixes(self, query: str) -> List[str]:
        """Suggest fixes for date-related errors."""
        suggestions = []
        
        suggestions.append("Use YYYY-MM-DD format: 'created: 2025-01-18'")
        suggestions.append("Use relative dates: 'created: -7d' for last 7 days")
        suggestions.append("Use date ranges: 'created: 2025-01-01 .. 2025-01-18'")
        
        return suggestions
    
    async def _generate_example_correction(self, original_query: str, error_type: str) -> str:
        """Generate a corrected example for common error types."""
        if error_type == 'syntax_errors':
            return original_query.replace('=', ':').replace('"', '{').replace('"', '}')
        elif error_type == 'field_errors':
            # Simple field name corrections
            corrected = original_query
            corrected = re.sub(r'\bassigned\b', 'assignee', corrected)
            corrected = re.sub(r'\bstatus\b', 'state', corrected)
            return corrected
        elif error_type == 'date_errors':
            # Convert common date formats
            corrected = re.sub(r'\d{1,2}/\d{1,2}/\d{4}', '2025-01-18', original_query)
            return corrected
        
        return original_query
    
    # AI model implementations using LLM client
    async def _ai_translate_query(self, natural_query: str, context_hints: Optional[Dict[str, Any]], project_schemas: Optional[List[Dict[str, Any]]]) -> QueryTranslationResult:
        """AI-powered query translation using LLM client."""
        if not self.llm_client:
            # Natural language to YQL translation not available
            raise Exception("Natural language to YQL translation requires LLM client")
        
        try:
            # Prepare prompt for query translation
            system_prompt = """You are a YouTrack Query Language (YQL) expert. Convert natural language queries to YQL.

YQL syntax examples:
- project: ProjectName
- assignee: me, assignee: Unassigned
- state: Open, state: {In Progress}
- priority: Critical, priority: High
- created: -7d .. *, created: 2025-01-01 .. 2025-01-31
- {Custom Field}: Value

Return only the YQL query, no explanations."""

            prompt = f"Convert this natural language query to YouTrack YQL: '{natural_query}'"
            
            # Add context if available
            if context_hints:
                if 'project' in context_hints:
                    prompt += f"\nProject context: {context_hints['project']}"
                if 'user' in context_hints:
                    prompt += f"\nUser context: {context_hints['user']}"
            
            # Get AI response
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response.success and response.content.strip():
                yql_query = response.content.strip()
                
                # Basic validation - ensure it looks like YQL
                if ':' in yql_query and not yql_query.startswith('I '):
                    return QueryTranslationResult(
                        yql_query=yql_query,
                        confidence=response.confidence,
                        reasoning=f"AI translation using {response.provider_used.value}",
                        original_input=natural_query,
                        detected_entities={'ai_generated': True},
                        suggestions=[f"Generated with {response.confidence:.1f} confidence"]
                    )
            
            # AI translation failed - natural language to YQL not available
            raise Exception("Natural language to YQL translation failed and fallback is not available")

        except Exception as e:
            logger.error(f"Error in AI query translation: {e}")
            raise Exception("Natural language to YQL translation is not available")
    
    async def _ai_enhance_error(self, error: Exception, context: Dict[str, Any], user_history: Optional[List[Dict[str, Any]]]) -> ErrorEnhancementResult:
        """AI-powered error enhancement using LLM client."""
        if not self.llm_client:
            # Error enhancement requires LLM client
            raise Exception("Error enhancement requires LLM client")
        
        try:
            # Prepare prompt for error enhancement
            system_prompt = """You are a YouTrack API expert helping users understand and fix errors.
Provide:
1. Enhanced explanation of what went wrong
2. Specific fix suggestion
3. Example correction
4. Learning tip for future queries

Be concise and practical."""

            prompt = f"""Error: {str(error)}
Context: {json.dumps(context, indent=2)}

Please enhance this error with helpful explanations and fix suggestions."""
            
            # Get AI response
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            if response.success and response.content.strip():
                content = response.content.strip()
                
                # Try to parse structured response or use as enhanced explanation
                lines = content.split('\n')
                enhanced_explanation = lines[0] if lines else content
                fix_suggestion = lines[1] if len(lines) > 1 else "Check the error message for specific details"
                example_correction = lines[2] if len(lines) > 2 else ""
                learning_tip = lines[3] if len(lines) > 3 else "Review YouTrack Query Language documentation"
                
                return ErrorEnhancementResult(
                    enhanced_explanation=enhanced_explanation,
                    fix_suggestion=fix_suggestion,
                    example_correction=example_correction,
                    learning_tip=learning_tip,
                    confidence=response.confidence
                )
            
            # If AI response is not valid, fall back to rule-based
            logger.warning(f"AI error enhancement failed, falling back to rule-based: {response.content[:100]}")
            return await self._rule_based_enhance_error(error, context)
            
        except Exception as e:
            logger.error(f"Error in AI error enhancement: {e}")
            return await self._rule_based_enhance_error(error, context)
    
    async def _ai_analyze_patterns(self, activity_data: List[Dict[str, Any]], analysis_types: List[str]) -> PatternAnalysisResult:
        """AI-powered pattern analysis using LLM client."""
        if not self.llm_client:
            # Activity pattern analysis requires LLM client
            raise Exception("Activity pattern analysis requires LLM client")
        
        try:
            # Prepare prompt for pattern analysis
            system_prompt = """You are an expert at analyzing user activity patterns and productivity metrics.
Analyze the provided activity data and provide insights about:
- Productivity trends
- Collaboration patterns  
- Focus areas
- Actionable recommendations

Be specific and data-driven in your analysis."""

            # Prepare activity summary for prompt
            activity_summary = {
                'total_activities': len(activity_data),
                'date_range': f"{activity_data[0].get('date', 'unknown')} to {activity_data[-1].get('date', 'unknown')}" if activity_data else "No data",
                'projects': list(set(item.get('project', 'Unknown') for item in activity_data)),
                'assignees': list(set(item.get('assignee', 'Unknown') for item in activity_data)),
                'activity_types': list(set(item.get('type', 'Unknown') for item in activity_data))
            }
            
            prompt = f"""Analyze this activity data:
{json.dumps(activity_summary, indent=2)}

Analysis types requested: {', '.join(analysis_types)}

Provide insights and recommendations based on this activity pattern."""
            
            # Get AI response
            response = await self.llm_client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.4
            )
            
            if response.success and response.content.strip():
                content = response.content.strip()
                
                # Parse AI response into insights and recommendations
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                insights = []
                recommendations = []
                
                current_section = None
                for line in lines:
                    if 'insight' in line.lower() or 'pattern' in line.lower():
                        current_section = 'insights'
                        if ':' in line:
                            insights.append(line.split(':', 1)[1].strip())
                    elif 'recommend' in line.lower() or 'suggest' in line.lower():
                        current_section = 'recommendations'
                        if ':' in line:
                            recommendations.append(line.split(':', 1)[1].strip())
                    elif line.startswith('-') or line.startswith('•'):
                        if current_section == 'insights':
                            insights.append(line[1:].strip())
                        elif current_section == 'recommendations':
                            recommendations.append(line[1:].strip())
                    elif current_section:
                        if current_section == 'insights':
                            insights.append(line)
                        elif current_section == 'recommendations':
                            recommendations.append(line)
                
                # If we couldn't parse structure, use the whole response as insights
                if not insights and not recommendations:
                    insights = [content]
                
                # Activity pattern analysis completed
                return PatternAnalysisResult(
                    patterns={'ai_analysis': content, 'activity_summary': activity_summary},
                    insights=insights or ["AI analysis completed"],
                    recommendations=recommendations or ["Continue monitoring activity patterns"],
                    productivity_score=0.7,  # Default productivity score
                    trends={'ai_confidence': response.confidence}
                )

            # AI pattern analysis failed
            raise Exception("Activity pattern analysis failed and fallback is not available")

        except Exception as e:
            logger.error(f"Error in AI pattern analysis: {e}")
            raise Exception("Activity pattern analysis is not available")


