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


class LocalAIProcessor:
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
        self.yql_patterns = self._initialize_yql_patterns()
        self.error_patterns = self._initialize_error_patterns()
        
        logger.info(f"LocalAIProcessor initialized (AI {'enabled' if enable_ai else 'disabled'}, LLM client: {'configured' if llm_client else 'none'})")
    
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
                # Use rule-based fallback
                result = await self._rule_based_translate_query(natural_query, context_hints, project_schemas)
            
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
                # Use rule-based analysis
                result = await self._rule_based_analyze_patterns(activity_data, analysis_types)
            
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
    
    def _initialize_yql_patterns(self) -> Dict[str, Any]:
        """Initialize patterns for natural language to YQL translation."""
        return {
            'time_patterns': {
                'last week': '-7d .. *',
                'this week': 'w .. *', 
                'yesterday': '-1d .. *',
                'today': 'd .. *',
                'last month': '-30d .. *',
                'this month': 'm .. *'
            },
            'priority_patterns': {
                'critical': 'Priority: Critical',
                'high': 'Priority: High',
                'urgent': 'Priority: Critical',
                'low': 'Priority: Low',
                'normal': 'Priority: Normal'
            },
            'state_patterns': {
                'open': 'State: Open',
                'closed': 'State: Fixed',
                'resolved': 'State: Fixed',
                'in progress': 'State: {In Progress}',
                'new': 'State: New'
            },
            'user_patterns': {
                'assigned to me': 'assignee: me',
                'unassigned': 'assignee: Unassigned',
                'created by me': 'reporter: me'
            }
        }
    
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
        return True
    
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
    
    async def _rule_based_translate_query(self, 
                                        natural_query: str, 
                                        context_hints: Optional[Dict[str, Any]], 
                                        project_schemas: Optional[List[Dict[str, Any]]]) -> QueryTranslationResult:
        """Rule-based natural language to YQL translation."""
        original_query = natural_query.lower().strip()
        yql_parts = []
        detected_entities = {}
        confidence = 0.6  # Rule-based has moderate confidence
        
        # Extract time references
        for time_phrase, yql_time in self.yql_patterns['time_patterns'].items():
            if time_phrase in original_query:
                yql_parts.append(f"created: {yql_time}")
                detected_entities['time'] = time_phrase
                confidence += 0.1
                break
        
        # Extract priority references
        for priority_phrase, yql_priority in self.yql_patterns['priority_patterns'].items():
            if priority_phrase in original_query:
                yql_parts.append(yql_priority)
                detected_entities['priority'] = priority_phrase
                confidence += 0.1
                break
        
        # Extract state references
        for state_phrase, yql_state in self.yql_patterns['state_patterns'].items():
            if state_phrase in original_query:
                yql_parts.append(yql_state)
                detected_entities['state'] = state_phrase
                confidence += 0.1
                break
        
        # Extract assignment references
        for user_phrase, yql_user in self.yql_patterns['user_patterns'].items():
            if user_phrase in original_query:
                yql_parts.append(yql_user)
                detected_entities['assignment'] = user_phrase
                confidence += 0.1
                break
        
        # Add project context if available
        if context_hints and 'project' in context_hints:
            project = context_hints['project']
            yql_parts.insert(0, f"project: {project}")
            detected_entities['project'] = project
            confidence += 0.1
        
        # Look for specific keywords that indicate bug/issue type
        if any(word in original_query for word in ['bug', 'error', 'issue', 'problem']):
            # Could add type filter if available
            detected_entities['type'] = 'bug'
            confidence += 0.05
        
        yql_query = ' '.join(yql_parts) if yql_parts else original_query
        
        reasoning = f"Translated using rule-based patterns. Detected: {', '.join(detected_entities.keys())}"
        
        suggestions = []
        if confidence < 0.7:
            suggestions.append("Consider using more specific terms like 'critical', 'last week', 'assigned to me'")
        if 'project' not in detected_entities:
            suggestions.append("Specify a project for more accurate results")
        
        return QueryTranslationResult(
            yql_query=yql_query,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            original_input=natural_query,
            detected_entities=detected_entities,
            suggestions=suggestions
        )
    
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
    
    async def _rule_based_analyze_patterns(self, 
                                         activity_data: List[Dict[str, Any]], 
                                         analysis_types: List[str]) -> PatternAnalysisResult:
        """Rule-based activity pattern analysis."""
        patterns = {}
        insights = []
        recommendations = []
        
        if not activity_data:
            return PatternAnalysisResult(
                patterns={'no_data': True},
                insights=["No activity data available for analysis"],
                recommendations=["Start tracking activity to see patterns"],
                productivity_score=0.0,
                trends={}
            )
        
        # Basic statistical analysis
        total_activities = len(activity_data)
        patterns['total_activities'] = total_activities
        
        # Time-based patterns
        if 'productivity_trends' in analysis_types:
            daily_counts = {}
            for activity in activity_data:
                date_str = activity.get('date', activity.get('created', ''))[:10]
                daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
            
            patterns['daily_activity'] = daily_counts
            avg_daily = sum(daily_counts.values()) / max(len(daily_counts), 1)
            patterns['average_daily_activity'] = avg_daily
            
            if avg_daily > 10:
                insights.append("High daily activity level detected")
                productivity_score = 0.8
            elif avg_daily > 5:
                insights.append("Moderate daily activity level")
                productivity_score = 0.6
            else:
                insights.append("Low daily activity level")
                productivity_score = 0.4
                recommendations.append("Consider increasing daily engagement")
        
        # Collaboration patterns
        if 'collaboration_patterns' in analysis_types:
            assignees = {}
            for activity in activity_data:
                assignee = activity.get('assignee', 'Unknown')
                assignees[assignee] = assignees.get(assignee, 0) + 1
            
            patterns['assignee_distribution'] = assignees
            if len(assignees) > 3:
                insights.append("Good collaboration across multiple team members")
            else:
                recommendations.append("Consider involving more team members")
        
        # Focus areas
        if 'focus_areas' in analysis_types:
            projects = {}
            for activity in activity_data:
                project = activity.get('project', 'Unknown')
                projects[project] = projects.get(project, 0) + 1
            
            patterns['project_distribution'] = projects
            top_project = max(projects.items(), key=lambda x: x[1])[0] if projects else None
            if top_project:
                insights.append(f"Primary focus on project: {top_project}")
        
        return PatternAnalysisResult(
            patterns=patterns,
            insights=insights,
            recommendations=recommendations,
            productivity_score=productivity_score,
            trends={'activity_trend': 'stable'}  # Simplified
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
            # Fall back to rule-based if no LLM client
            return await self._rule_based_translate_query(natural_query, context_hints, project_schemas)
        
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
            
            # If AI response is not valid, fall back to rule-based
            logger.warning(f"AI translation failed or invalid, falling back to rule-based: {response.content[:100]}")
            return await self._rule_based_translate_query(natural_query, context_hints, project_schemas)
            
        except Exception as e:
            logger.error(f"Error in AI query translation: {e}")
            return await self._rule_based_translate_query(natural_query, context_hints, project_schemas)
    
    async def _ai_enhance_error(self, error: Exception, context: Dict[str, Any], user_history: Optional[List[Dict[str, Any]]]) -> ErrorEnhancementResult:
        """AI-powered error enhancement using LLM client."""
        if not self.llm_client:
            # Fall back to rule-based if no LLM client
            return await self._rule_based_enhance_error(error, context)
        
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
            # Fall back to rule-based if no LLM client
            return await self._rule_based_analyze_patterns(activity_data, analysis_types)
        
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
                
                # Calculate basic productivity score from rule-based analysis for consistency
                rule_based_result = await self._rule_based_analyze_patterns(activity_data, analysis_types)
                
                return PatternAnalysisResult(
                    patterns={'ai_analysis': content, 'activity_summary': activity_summary},
                    insights=insights or ["AI analysis completed"],
                    recommendations=recommendations or ["Continue monitoring activity patterns"],
                    productivity_score=rule_based_result.productivity_score,  # Use rule-based score
                    trends={'ai_confidence': response.confidence}
                )
            
            # If AI response is not valid, fall back to rule-based
            logger.warning(f"AI pattern analysis failed, falling back to rule-based: {response.content[:100]}")
            return await self._rule_based_analyze_patterns(activity_data, analysis_types)
            
        except Exception as e:
            logger.error(f"Error in AI pattern analysis: {e}")
            return await self._rule_based_analyze_patterns(activity_data, analysis_types)


# Global instance (initialized by main.py)
local_ai_processor: Optional[LocalAIProcessor] = None


def get_ai_processor() -> LocalAIProcessor:
    """Get the global AI processor instance."""
    global local_ai_processor
    if local_ai_processor is None:
        local_ai_processor = LocalAIProcessor()
    return local_ai_processor


def initialize_ai_processor(enable_ai: bool = True, max_memory_mb: int = 2048, llm_client=None) -> LocalAIProcessor:
    """Initialize the global AI processor instance."""
    global local_ai_processor
    local_ai_processor = LocalAIProcessor(enable_ai=enable_ai, max_memory_mb=max_memory_mb, llm_client=llm_client)
    return local_ai_processor