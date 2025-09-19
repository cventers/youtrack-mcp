# LLM Prompting Enhancement Plan for YouTrack MCP

**Version**: 1.0
**Date**: 2025-01-19
**Author**: AI Assistant
**Status**: DRAFT

## Executive Summary

This plan outlines comprehensive enhancements to the LLM prompting system for the YouTrack MCP server. The current implementation uses basic prompts that assume LLMs have inherent knowledge of YouTrack Query Language (YQL). This plan proposes detailed, structured prompts with examples, confidence scoring, and retry mechanisms to significantly improve accuracy and reliability.

## Current State Analysis

**Note**: This plan implements a complete replacement of the existing prompting system without backward compatibility. All existing integrations will need to adapt to the new structured JSON response format.

### Identified Issues

1. **Minimal Prompt Content**: Current prompts are barebones, lacking:
   - Detailed YQL syntax documentation
   - Examples of common query patterns
   - Structured response requirements
   - Confidence scoring guidelines

2. **No Response Validation**: The system doesn't validate JSON responses or retry on malformed outputs

3. **Missing Context**: Prompts don't include:
   - Available fields and custom fields
   - Project-specific context
   - Common error patterns

4. **Inconsistent Error Handling**: No structured approach to parsing LLM responses

## Proposed Enhancements

### 1. Enhanced Prompt Templates

#### 1.1 YQL Translation Enhancement

**File**: `prompts/yql_translation.j2` (UPDATE EXISTING)

```jinja2
You are a YouTrack Query Language (YQL) expert. Your task is to convert natural language queries to precise YQL syntax.

## YQL SYNTAX REFERENCE

### Basic Structure
- Attribute-value pairs: `attribute: value`
- Multiple values: `state: Open, In Progress`
- Values with spaces: `{Multi Word Value}`
- Exclusions: `-attribute: value`
- Ranges: `created: 2025-01-01 .. 2025-01-31`

### Common Attributes
- **Project**: `project: ProjectKey` or `project: {Project Name}`
- **Assignee**: `assignee: username`, `assignee: me`, `assignee: Unassigned`
- **State**: `state: Open`, `state: {In Progress}`, `state: Resolved`
- **Priority**: `priority: Critical`, `priority: High`, `priority: Normal`
- **Type**: `type: Bug`, `type: Feature`, `type: Task`
- **Created**: `created: 2025-01-15`, `created: {minus 7d} .. *`
- **Updated**: `updated: {Last week} .. *`
- **Reporter**: `reporter: username`
- **Summary**: `summary: "search text"` or `summary: bug*`
- **Description**: `description: "error message"`

### Date Formats
- Absolute: `YYYY-MM-DD` (e.g., `2025-01-19`)
- Relative: `{Today}`, `{Yesterday}`, `{Last week}`, `{This month}`
- Relative math: `{minus 7d}`, `{plus 1w}`, `{minus 1m}`
- Ranges: `date: start .. end`, use `*` for open-ended

### Custom Fields
- Format: `{Field Name}: value`
- Examples: `{Priority}: High`, `{Component}: Backend`, `{Due Date}: 2025-02-01`

### Logical Operators
- AND (implicit): `project: DEMO assignee: john`
- OR: `state: Open OR state: {In Progress}`
- Grouping: `(state: Open OR state: {In Progress}) AND priority: High`
- NOT: `-state: Resolved`

## EXAMPLES

### Example 1: Issues assigned to me in project DEMO
Input: "my open issues in demo project"
Output: `project: DEMO assignee: me state: Open`

### Example 2: High priority bugs created last week
Input: "critical bugs from last week"
Output: `type: Bug priority: Critical created: {minus 7d} .. *`

### Example 3: Unassigned issues in multiple projects
Input: "unassigned tasks in projects A or B"
Output: `(project: A OR project: B) assignee: Unassigned type: Task`

### Example 4: Issues with custom field
Input: "backend issues with high customer impact"
Output: `{Component}: Backend {Customer Impact}: High`

### Example 5: Complex date range
Input: "issues updated between January 1st and 15th 2025"
Output: `updated: 2025-01-01 .. 2025-01-15`

## RESPONSE FORMAT

You MUST respond with a JSON object in this exact format:

```json
{
  "yql_query": "the generated YQL query string",
  "confidence": 0.95,
  "reasoning": "Brief explanation of the translation logic",
  "detected_entities": {
    "projects": ["DEMO"],
    "users": ["john.doe"],
    "states": ["Open"],
    "dates": ["2025-01-19"],
    "custom_fields": ["Priority", "Component"]
  },
  "alternative_queries": [
    "alternative query if interpretation is ambiguous"
  ],
  "warnings": [
    "any potential issues with the query"
  ]
}
```

## CONFIDENCE SCORING RULES

Rate your confidence from 0.0 to 1.0 based on:
- 1.0: Exact match to examples, all entities clearly identified
- 0.9: Clear intent with standard YQL patterns
- 0.8: Minor ambiguity in one parameter
- 0.7: Multiple interpretations possible
- 0.6: Significant ambiguity requiring clarification
- 0.5 or below: Unable to construct valid query

## IMPORTANT RULES

1. ALWAYS use curly braces `{}` for multi-word values
2. NEVER use equals sign `=`, always use colon `:`
3. Project names and usernames are case-sensitive
4. When time period is mentioned without specific dates, use relative dates
5. If project is not specified, don't add a project filter
6. For "my" queries, use `assignee: me`
7. For "unassigned" queries, use `assignee: Unassigned`
```

#### 1.2 Error Enhancement Improvement

**File**: `prompts/error_enhancement.j2` (UPDATE EXISTING)

```jinja2
You are a YouTrack API expert helping users understand and fix API errors.

## ERROR CONTEXT
Error Type: {{ error_type }}
Error Message: {{ error_message }}
Operation: {{ operation }}
Parameters: {{ parameters | tojson }}

## COMMON ERROR PATTERNS AND SOLUTIONS

### Authentication Errors (401, 403)
- **Issue**: Invalid or expired token
- **Solution**: Verify YOUTRACK_API_TOKEN environment variable
- **Example**: `export YOUTRACK_API_TOKEN="perm:xxx"`

### Not Found Errors (404)
- **Issue**: Resource doesn't exist or wrong ID format
- **Solution**: Check ID format (e.g., "PROJECT-123" not "123")
- **Example**: Use `DEMO-1` instead of `1`

### Bad Request Errors (400)
- **Issue**: Invalid query syntax or parameters
- **Common Causes**:
  - Missing quotes around multi-word values
  - Wrong date format
  - Invalid field names
- **Solutions**:
  - Use `{Multi Word}` for values with spaces
  - Use YYYY-MM-DD date format
  - Verify field names in project settings

### Custom Field Errors
- **Issue**: Field doesn't exist or wrong value type
- **Solution**: Check project's custom fields configuration
- **Example**: `{Priority}: High` not `Priority: High`

## RESPONSE FORMAT

Provide a JSON response with this structure:

```json
{
  "error_category": "authentication|syntax|not_found|permission|validation|server",
  "enhanced_explanation": "Clear explanation of what went wrong",
  "root_cause": "The fundamental issue causing this error",
  "immediate_fix": "Step-by-step solution to fix this exact error",
  "example_correction": {
    "wrong": "the incorrect usage",
    "correct": "the corrected usage",
    "explanation": "why this correction works"
  },
  "prevention_tips": [
    "How to avoid this error in the future",
    "Best practices to follow"
  ],
  "related_documentation": [
    "Relevant API endpoint documentation",
    "YQL syntax guide section"
  ],
  "confidence": 0.95,
  "requires_admin": false,
  "estimated_fix_time": "immediate|minutes|hours|needs_investigation"
}
```

## CONFIDENCE SCORING FOR ERRORS

- 1.0: Exact error pattern match with known solution
- 0.9: Clear error category with standard fix
- 0.8: Common error with multiple possible causes
- 0.7: Uncommon error with educated guess
- 0.6: Ambiguous error requiring more context
- 0.5 or below: Unknown error pattern

## ANALYSIS APPROACH

1. Identify the error category from status code and message
2. Match against known error patterns
3. Consider the operation context
4. Provide specific, actionable solutions
5. Include preventive measures
```

#### 1.3 Intent Analysis Enhancement

**File**: `prompts/intent_analysis.j2` (UPDATE EXISTING)

```jinja2
You are a YouTrack automation expert. Analyze user intent and create detailed execution plans.

## AVAILABLE TOOLS AND CAPABILITIES

### Issue Management
- **issues.create**: Create new issues
  - Required: project (string), summary (string)
  - Optional: description, assignee, state, priority, custom_fields (object)
  
- **issues.get**: Retrieve issue details
  - Required: issue_id (string)
  - Optional: include (array) - ["customFields", "comments", "attachments", "links"]
  
- **issues.patch**: Update issues
  - Required: issue_id (string)
  - Optional: fields (object) or ops (array)
  - Supports: /fields/<FieldName> paths for updates
  
- **issues.delete**: Delete issues
  - Required: issue_id (string)

### Search Operations
- **search.query**: Execute YQL queries
  - Required: query (string)
  - Optional: limit (number), sort_by (string), sort_order (string)
  
- **search.autosearch**: Natural language search
  - Required: natural_language_query (string)
  - Optional: project_context (string), limit (number)

### Project Management
- **projects.list**: List all projects
  - Optional: include_archived (boolean), limit (number)
  
- **projects.get**: Get project details
  - Required: project_id (string)
  - Optional: include (array) - ["customFields", "schema", "issues"]
  
- **projects.create**: Create new project
  - Required: name, short_name, lead_id (strings)
  - Optional: description (string)

### User Management
- **users.search**: Search for users
  - Required: query (string)
  - Optional: limit (number)

## INTENT PATTERNS

### Creation Intents
Keywords: create, new, add, make, generate
Example: "Create a bug report for login issue"
Tools: issues.create

### Update Intents
Keywords: update, modify, change, edit, set, assign
Example: "Assign DEMO-123 to John"
Tools: issues.get (first), then issues.patch

### Search Intents
Keywords: find, search, list, show, get, display
Example: "Find all open bugs"
Tools: search.query or search.autosearch

### Bulk Operations
Keywords: all, multiple, batch, every
Example: "Close all resolved issues"
Tools: search.query (first), then multiple issues.patch

### Analysis Intents
Keywords: analyze, report, summary, statistics
Example: "Show issue statistics for this month"
Tools: search.query with aggregation

## RESPONSE FORMAT

Return a JSON object with this exact structure:

```json
{
  "intent": "user's original intent statement",
  "intent_category": "create|read|update|delete|search|bulk|analysis",
  "confidence": 0.95,
  "detected_entities": {
    "projects": ["DEMO"],
    "issue_ids": ["DEMO-123"],
    "users": ["john.doe"],
    "fields": ["state", "assignee"],
    "values": ["Open", "High"],
    "time_ranges": ["this week", "2025-01-19"]
  },
  "requires_confirmation": true,
  "validation_required": {
    "project_exists": ["DEMO"],
    "user_exists": ["john.doe"],
    "field_exists": ["customField1"]
  },
  "plan": [
    {
      "step": 1,
      "tool": "search.query",
      "description": "Find target issues",
      "parameters": {
        "query": "project: DEMO state: Open"
      },
      "expected_result": "List of issue IDs",
      "error_handling": "If no issues found, inform user"
    },
    {
      "step": 2,
      "tool": "issues.patch",
      "description": "Update each issue",
      "parameters": {
        "issue_id": "${from_step_1}",
        "fields": {
          "state": "In Progress",
          "assignee": "john.doe"
        }
      },
      "expected_result": "Updated issue",
      "error_handling": "Log failed updates, continue with others"
    }
  ],
  "alternative_interpretations": [
    "Alternative understanding of the request if ambiguous"
  ],
  "warnings": [
    "Bulk operation will affect 50+ issues",
    "Requires project admin permissions"
  ],
  "estimated_complexity": "low|medium|high",
  "estimated_api_calls": 5,
  "rollback_plan": {
    "supported": true,
    "method": "Store original values before update"
  }
}
```

## CONFIDENCE SCORING RULES

- 1.0: Clear intent matching exact tool capabilities
- 0.9: Standard operation with all parameters identified
- 0.8: Minor ambiguity in parameters
- 0.7: Multiple valid interpretations
- 0.6: Significant ambiguity requiring clarification
- 0.5 or below: Unable to determine clear action

## COMPLEXITY ASSESSMENT

- **Low**: Single API call, read-only operation
- **Medium**: 2-5 API calls, simple updates
- **High**: 5+ API calls, bulk operations, or complex logic

## SAFETY RULES

1. Always set `requires_confirmation: true` for destructive operations
2. Include rollback plans for bulk updates
3. Validate entities exist before operations
4. Warn about operations affecting many items
5. Check permissions requirements
6. Estimate API call impact
```

### 2. Implementation Enhancements

#### 2.1 Response Validation and Retry Logic

**File**: `youtrack_mcp/ai/response_validator.py`

```python
"""
Response validation and retry logic for LLM outputs.
"""

import json
import logging
from typing import Any, Dict, Optional, Callable
from jsonschema import validate, ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for response validation."""
    max_retries: int = 3
    require_json: bool = True
    require_confidence: bool = True
    min_confidence: float = 0.5
    schema: Optional[Dict[str, Any]] = None


class ResponseValidator:
    """Validates and retries LLM responses."""
    
    # JSON Schema for YQL Translation Response
    YQL_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["yql_query", "confidence", "reasoning"],
        "properties": {
            "yql_query": {"type": "string", "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
            "detected_entities": {"type": "object"},
            "alternative_queries": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}}
        }
    }
    
    # JSON Schema for Error Enhancement Response
    ERROR_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["error_category", "enhanced_explanation", "immediate_fix", "confidence"],
        "properties": {
            "error_category": {
                "type": "string",
                "enum": ["authentication", "syntax", "not_found", "permission", "validation", "server"]
            },
            "enhanced_explanation": {"type": "string"},
            "root_cause": {"type": "string"},
            "immediate_fix": {"type": "string"},
            "example_correction": {
                "type": "object",
                "properties": {
                    "wrong": {"type": "string"},
                    "correct": {"type": "string"},
                    "explanation": {"type": "string"}
                }
            },
            "prevention_tips": {"type": "array", "items": {"type": "string"}},
            "related_documentation": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "requires_admin": {"type": "boolean"},
            "estimated_fix_time": {
                "type": "string",
                "enum": ["immediate", "minutes", "hours", "needs_investigation"]
            }
        }
    }
    
    # JSON Schema for Intent Analysis Response
    INTENT_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["intent", "intent_category", "confidence", "plan"],
        "properties": {
            "intent": {"type": "string"},
            "intent_category": {
                "type": "string",
                "enum": ["create", "read", "update", "delete", "search", "bulk", "analysis"]
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "detected_entities": {"type": "object"},
            "requires_confirmation": {"type": "boolean"},
            "validation_required": {"type": "object"},
            "plan": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["step", "tool", "description", "parameters"],
                    "properties": {
                        "step": {"type": "integer"},
                        "tool": {"type": "string"},
                        "description": {"type": "string"},
                        "parameters": {"type": "object"},
                        "expected_result": {"type": "string"},
                        "error_handling": {"type": "string"}
                    }
                }
            },
            "alternative_interpretations": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
            "estimated_complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            },
            "estimated_api_calls": {"type": "integer"},
            "rollback_plan": {"type": "object"}
        }
    }
    
    @staticmethod
    def extract_json(response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.
        
        Handles responses that may include markdown code blocks or extra text.
        """
        # Try direct parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        import re
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_start = response.find('{')
        json_end = response.rfind('}')
        if json_start != -1 and json_end != -1:
            try:
                return json.loads(response[json_start:json_end + 1])
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def validate_response(
        response: str,
        config: ValidationConfig
    ) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate LLM response against configuration.
        
        Returns:
            Tuple of (is_valid, parsed_response, error_message)
        """
        # Extract JSON if required
        if config.require_json:
            parsed = ResponseValidator.extract_json(response)
            if parsed is None:
                return False, None, "Failed to extract valid JSON from response"
        else:
            parsed = {"content": response}
        
        # Validate against schema if provided
        if config.schema:
            try:
                validate(instance=parsed, schema=config.schema)
            except ValidationError as e:
                return False, parsed, f"Schema validation failed: {e.message}"
        
        # Check confidence if required
        if config.require_confidence:
            confidence = parsed.get("confidence")
            if confidence is None:
                return False, parsed, "Missing required 'confidence' field"
            if confidence < config.min_confidence:
                return False, parsed, f"Confidence {confidence} below minimum {config.min_confidence}"
        
        return True, parsed, None
    
    @staticmethod
    async def retry_with_validation(
        llm_func: Callable,
        prompt: str,
        config: ValidationConfig,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retry LLM call with validation.
        
        Args:
            llm_func: LLM completion function
            prompt: User prompt
            config: Validation configuration
            system_prompt: Optional system prompt
            **kwargs: Additional arguments for LLM function
        
        Returns:
            Validated response dictionary
        
        Raises:
            RuntimeError: If all retries fail
        """
        last_error = None
        
        for attempt in range(config.max_retries):
            try:
                # Add retry context to prompt if not first attempt
                if attempt > 0:
                    retry_prompt = f"{prompt}\n\nPrevious attempt failed: {last_error}\nPlease ensure response is valid JSON matching the required schema."
                else:
                    retry_prompt = prompt
                
                # Call LLM
                response = await llm_func(
                    prompt=retry_prompt,
                    system=system_prompt,
                    **kwargs
                )
                
                # Validate response
                is_valid, parsed, error_msg = ResponseValidator.validate_response(
                    response,
                    config
                )
                
                if is_valid:
                    logger.info(f"Response validated successfully on attempt {attempt + 1}")
                    return parsed
                
                last_error = error_msg
                logger.warning(f"Validation failed on attempt {attempt + 1}: {error_msg}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"LLM call failed on attempt {attempt + 1}: {e}")
        
        raise RuntimeError(
            f"Failed to get valid response after {config.max_retries} attempts. "
            f"Last error: {last_error}"
        )
```

#### 2.2 Configuration Management

**File**: `youtrack_mcp/config.py` (additions)

```python
class LLMConfig(BaseSettings):
    """LLM-specific configuration for enhanced prompting."""
    
    model_config = ConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
    )
    
    # Retry configuration
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts for LLM calls")
    min_confidence: float = Field(0.6, ge=0.0, le=1.0, description="Minimum confidence threshold")
    require_json: bool = Field(True, description="Require JSON responses from LLM")
    
    # Token limits per operation type
    max_tokens_yql: int = Field(500, ge=100, description="Max tokens for YQL translation")
    max_tokens_error: int = Field(800, ge=100, description="Max tokens for error enhancement")
    max_tokens_intent: int = Field(1500, ge=100, description="Max tokens for intent analysis")
    
    # Cache settings
    cache_ttl: int = Field(3600, ge=60, description="Cache TTL in seconds (default 1 hour)")
    
    # Validation settings
    validate_json_schema: bool = Field(True, description="Validate responses against JSON schema")
    extract_json_from_markdown: bool = Field(True, description="Try to extract JSON from markdown blocks")

# Add to Settings class
class Settings(BaseSettings):
    # ... existing nested configurations ...
    llm: LLMConfig = Field(default_factory=LLMConfig)
```

### 3. Testing Strategy

#### 3.1 Prompt Testing Framework

**File**: `tests/prompts/test_prompt_responses.py`

```python
"""
Test framework for validating prompt responses.
"""

import pytest
import json
from youtrack_mcp.ai.response_validator import ResponseValidator, ValidationConfig

class TestPromptResponses:
    """Test prompt response validation."""
    
    @pytest.mark.parametrize("query,expected_yql", [
        ("my open issues in demo", "project: demo assignee: me state: Open"),
        ("critical bugs last week", "type: Bug priority: Critical created: {minus 7d} .. *"),
        ("unassigned tasks", "assignee: Unassigned type: Task"),
    ])
    def test_yql_translation_examples(self, query, expected_yql):
        """Test YQL translation with known examples."""
        # This would test against actual LLM or mock responses
        pass
    
    @pytest.mark.parametrize("response,should_validate", [
        ('{"yql_query": "test", "confidence": 0.8, "reasoning": "test"}', True),
        ('{"yql_query": "", "confidence": 0.8, "reasoning": "test"}', False),
        ('{"confidence": 0.8, "reasoning": "test"}', False),
        ('not json at all', False),
    ])
    def test_response_validation(self, response, should_validate):
        """Test response validation logic."""
        config = ValidationConfig(
            schema=ResponseValidator.YQL_RESPONSE_SCHEMA
        )
        is_valid, _, _ = ResponseValidator.validate_response(response, config)
        assert is_valid == should_validate
```

### 4. Implementation Checklist

#### Phase 1: Update Existing Templates

**AI Agent Instructions**: Use TodoWrite to track progress. Mark each item as completed after implementation.

- [ ] Update `prompts/yql_translation.j2` with comprehensive YQL syntax reference
  - Include all YQL operators, date formats, and custom field syntax
  - Add 5+ concrete examples with various query patterns
  - Define JSON response schema with confidence scoring rules
  
- [ ] Update `prompts/yql_user_prompt.j2` to pass structured context
  - Include project context when available
  - Pass custom fields list if known
  
- [ ] Update `prompts/error_enhancement.j2` with error categorization
  - Add common error patterns and solutions
  - Include structured JSON response format
  - Define confidence scoring for error types
  
- [ ] Update `prompts/error_user_prompt.j2` with error context
  - Pass error type, message, operation, and parameters
  
- [ ] Update `prompts/intent_analysis.j2` with tool capabilities
  - Document all available tools and their parameters
  - Add intent pattern matching examples
  - Define execution plan JSON structure
  
- [ ] Update `prompts/intent_user_prompt.j2` with intent context
  - Pass available context and entities

#### Phase 2: Implement Validation

**AI Agent Instructions**: Create new files and integrate with existing codebase. Run tests after each component.

- [ ] Create `youtrack_mcp/ai/response_validator.py`
  - Implement ResponseValidator class with JSON extraction
  - Add schema validation for each response type
  - Implement retry_with_validation method
  
- [ ] Add JSON schemas for all response types
  - YQL_RESPONSE_SCHEMA with required fields
  - ERROR_RESPONSE_SCHEMA with categorization
  - INTENT_RESPONSE_SCHEMA with plan structure
  
- [ ] Create unit tests for response validation
  - Test JSON extraction from various formats
  - Test schema validation pass/fail cases
  - Test retry logic with mock responses

#### Phase 3: Update AI Service

**AI Agent Instructions**: Modify existing AIService class. Replace existing implementation completely.

- [ ] Update `youtrack_mcp/ai/service.py` to use ResponseValidator
  - Import ResponseValidator and ValidationConfig
  - Wrap LLM calls with retry_with_validation
  - Handle validation failures gracefully
  
- [ ] Implement confidence thresholds
  - Check confidence scores in responses
  - Retry if confidence below threshold
  - Return structured error if all retries fail
  
- [ ] Update cache key generation
  - Clear all existing caches on deployment
  - Use new cache key format

#### Phase 4: Configuration Updates

**AI Agent Instructions**: Update configuration files to use new pydantic-settings framework.

- [ ] Add LLMConfig class to `youtrack_mcp/config.py`
  - Create LLMConfig with BaseSettings
  - Add all LLM-specific settings with Field validators
  - Integrate with Settings class as nested configuration
  - Update backward compatibility layer if needed
  
- [ ] Update `.env.example` with new variables
  - Document all LLM configuration options
  - Provide recommended values
  
- [ ] Update configuration documentation
  - Add section on LLM configuration
  - Include troubleshooting guide

#### Phase 5: Testing & Documentation

**AI Agent Instructions**: Create comprehensive tests and documentation. Verify all functionality.

- [ ] Create integration tests with mock LLM
  - Test complete flow with validation
  - Test retry scenarios
  - Test confidence thresholds
  
- [ ] Update API documentation
  - Document enhanced response formats
  - Add confidence score explanations
  - Include retry behavior
  
- [ ] Create migration guide for users
  - Explain new response formats
  - Document configuration options
  - Provide troubleshooting steps

### 5. Success Metrics

1. **Accuracy Improvement**
   - Target: 90%+ accuracy on common queries
   - Measure: Test suite pass rate

2. **Confidence Scoring**
   - Target: 85%+ of responses with confidence > 0.7
   - Measure: Average confidence scores

3. **Retry Success Rate**
   - Target: 95%+ success within 3 retries
   - Measure: Retry statistics

4. **Response Time**
   - Target: < 2 seconds average
   - Measure: API response times

5. **Error Reduction**
   - Target: 50% reduction in malformed responses
   - Measure: Validation failure rate

### 6. Risk Mitigation

1. **Increased Token Usage**
   - Risk: Enhanced prompts use more tokens
   - Mitigation: Implement token counting and limits
   - Fallback: Use condensed prompts for simple queries

2. **Breaking Changes**
   - Risk: Existing integrations will need updates
   - Mitigation: Clear migration documentation
   - Approach: Clean replacement of all prompts and validation

3. **LLM Variability**
   - Risk: Different LLMs respond differently
   - Mitigation: Test with multiple models
   - Fallback: Model-specific prompt variants

### 7. Appendices

#### A. Example Enhanced Responses

##### YQL Translation Example
```json
{
  "yql_query": "project: DEMO assignee: me state: Open created: {minus 7d} .. *",
  "confidence": 0.95,
  "reasoning": "User wants their open issues in DEMO project from last week. Used 'me' for personal assignment, Open state filter, and relative date range.",
  "detected_entities": {
    "projects": ["DEMO"],
    "users": ["me"],
    "states": ["Open"],
    "dates": ["last 7 days"],
    "custom_fields": []
  },
  "alternative_queries": [
    "project: DEMO for: me #Unresolved created: {minus 7d} .. *"
  ],
  "warnings": []
}
```

##### Error Enhancement Example
```json
{
  "error_category": "syntax",
  "enhanced_explanation": "The YQL query has invalid syntax. Multi-word state values must be enclosed in curly braces.",
  "root_cause": "Missing curly braces around 'In Progress'",
  "immediate_fix": "Change 'state: In Progress' to 'state: {In Progress}'",
  "example_correction": {
    "wrong": "state: In Progress",
    "correct": "state: {In Progress}",
    "explanation": "YouTrack requires curly braces around values containing spaces"
  },
  "prevention_tips": [
    "Always use {} for multi-word values",
    "Test queries in YouTrack UI first",
    "Use the query builder for complex filters"
  ],
  "related_documentation": [
    "YQL Syntax Guide: Special Characters",
    "API Query Documentation"
  ],
  "confidence": 0.98,
  "requires_admin": false,
  "estimated_fix_time": "immediate"
}
```

### 8. References

1. YouTrack Query Language Documentation
2. OpenAI JSON Mode Best Practices
3. JSON Schema Validation Standards
4. Prompt Engineering Guidelines