# AI Prompts Directory

This directory contains Jinja2 templates for AI prompts used throughout the YouTrack MCP server.

## Template Files

### System Prompts
- `yql_translation.j2` - System prompt for natural language to YQL translation
- `error_enhancement.j2` - System prompt for error message enhancement
- `intent_analysis.j2` - System prompt for user intent analysis and planning

### User Prompts
- `yql_user_prompt.j2` - User prompt template for YQL translation with variables
- `error_user_prompt.j2` - User prompt template for error enhancement with variables
- `intent_user_prompt.j2` - User prompt template for intent analysis with variables

## Template Variables

### YQL Translation
- `natural_query` - The natural language query to translate
- `project_context` - Optional project context (can be None)

### Error Enhancement
- `error` - The error message string
- `context` - Dictionary containing operation context

### Intent Analysis
- `intent` - The user's natural language intent
- `context` - Dictionary containing additional context

## Usage

Templates are automatically loaded and processed at runtime by the `PromptTemplateLoader` class in `youtrack_mcp/ai/template_loader.py`.

## Customization

To modify prompts:
1. Edit the corresponding `.j2` template file
2. Restart the MCP server
3. Changes will be applied immediately

## Template Syntax

Templates use Jinja2 syntax:
- `{{ variable }}` - Variable substitution
- `{% if condition %}` - Conditional blocks
- `{% endif %}` - End conditional blocks
- `{{ variable|tojson }}` - JSON formatting filter