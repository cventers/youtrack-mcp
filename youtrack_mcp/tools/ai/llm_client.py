"""
LLM Client for YouTrack MCP with OpenAI-compatible API support.

Provides a unified interface for different AI providers:
1. External OpenAI-compatible APIs (OpenAI, Anthropic, local servers)
2. Local quantized models (future implementation)
3. Rule-based fallback (current implementation)
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI_COMPATIBLE = "openai_compatible"  # OpenAI, Anthropic, local servers
    LOCAL_MODEL = "local_model"              # Local quantized models (future)
    RULE_BASED = "rule_based"                # Fallback rule-based processing


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    provider: AIProvider
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.3
    timeout_seconds: int = 30
    enabled: bool = True


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    provider_used: AIProvider
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    confidence: float = 1.0


class LLMClient:
    """
    Unified LLM client with multiple provider support and fallback hierarchy.
    
    Provider hierarchy:
    1. OpenAI-compatible API (if configured)
    2. Local model (if available)
    3. Rule-based fallback (always available)
    """
    
    def __init__(self, configs: Union[LLMConfig, List[LLMConfig]]):
        """
        Initialize LLM client with provider configurations.
        
        Args:
            configs: Single LLMConfig or list of LLM configurations in priority order
        """
        if isinstance(configs, LLMConfig):
            self.configs = [configs]
        else:
            self.configs = configs if configs else []
        self.http_client = None
        self._initialize_http_client()

        # Sort configs by priority (enabled first, then by provider preference)
        self.configs.sort(key=lambda c: (
            not c.enabled,  # Enabled configs first
            c.provider.value == "rule_based"  # Rule-based last
        ))
        
        logger.info(f"LLM client initialized with {len(self.configs)} providers")
        for i, config in enumerate(self.configs):
            if config.enabled:
                logger.info(f"  {i+1}. {config.provider.value}: {config.model_name or 'default'}")
    
    def _initialize_http_client(self):
        """Initialize HTTP client for API calls."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
    
    async def complete(self, 
                      prompt: str, 
                      system_prompt: Optional[str] = None,
                      max_tokens: Optional[int] = None,
                      temperature: Optional[float] = None) -> LLMResponse:
        """
        Get completion from the first available LLM provider.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override default max tokens
            temperature: Override default temperature
            
        Returns:
            LLM response with content and metadata
        """
        last_error = None
        
        for config in self.configs:
            if not config.enabled:
                continue
                
            try:
                logger.debug(f"Trying provider: {config.provider.value}")
                
                if config.provider == AIProvider.OPENAI_COMPATIBLE:
                    response = await self._call_openai_compatible(
                        config, prompt, system_prompt, max_tokens, temperature
                    )
                elif config.provider == AIProvider.LOCAL_MODEL:
                    response = await self._call_local_model(
                        config, prompt, system_prompt, max_tokens, temperature
                    )
                elif config.provider == AIProvider.RULE_BASED:
                    response = await self._call_rule_based(
                        config, prompt, system_prompt, max_tokens, temperature
                    )
                else:
                    continue
                
                if response.success:
                    logger.debug(f"Success with provider: {config.provider.value}")
                    return response
                else:
                    logger.warning(f"Provider {config.provider.value} failed: {response.error}")
                    last_error = response.error
                    
            except Exception as e:
                logger.error(f"Error with provider {config.provider.value}: {e}")
                last_error = str(e)
                continue
        
        # All providers failed
        return LLMResponse(
            content="",
            provider_used=AIProvider.RULE_BASED,
            success=False,
            error=f"All LLM providers failed. Last error: {last_error}",
            confidence=0.0
        )
    
    async def _call_openai_compatible(self,
                                    config: LLMConfig,
                                    prompt: str,
                                    system_prompt: Optional[str] = None,
                                    max_tokens: Optional[int] = None,
                                    temperature: Optional[float] = None) -> LLMResponse:
        """Call OpenAI-compatible API."""
        if not config.api_url or not config.api_key:
            return LLMResponse(
                content="",
                provider_used=AIProvider.OPENAI_COMPATIBLE,
                success=False,
                error="API URL and key required for OpenAI-compatible provider",
                confidence=0.0
            )
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request
        request_data = {
            "model": config.model_name or "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": max_tokens or config.max_tokens,
            "temperature": temperature or config.temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.http_client.post(
                f"{config.api_url.rstrip('/')}/chat/completions",
                json=request_data,
                headers=headers,
                timeout=config.timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens")
                
                return LLMResponse(
                    content=content,
                    provider_used=AIProvider.OPENAI_COMPATIBLE,
                    success=True,
                    tokens_used=tokens_used,
                    confidence=0.9
                )
            else:
                error_detail = response.text
                return LLMResponse(
                    content="",
                    provider_used=AIProvider.OPENAI_COMPATIBLE,
                    success=False,
                    error=f"API error {response.status_code}: {error_detail}",
                    confidence=0.0
                )
                
        except Exception as e:
            return LLMResponse(
                content="",
                provider_used=AIProvider.OPENAI_COMPATIBLE,
                success=False,
                error=f"Request failed: {str(e)}",
                confidence=0.0
            )
    

    
    async def _call_local_model(self,
                               config: LLMConfig,
                               prompt: str,
                               system_prompt: Optional[str] = None,
                               max_tokens: Optional[int] = None,
                               temperature: Optional[float] = None) -> LLMResponse:
        """Call local quantized model (placeholder for future implementation)."""
        return LLMResponse(
            content="",
            provider_used=AIProvider.LOCAL_MODEL,
            success=False,
            error="Local model support not yet implemented",
            confidence=0.0
        )
    
    async def _call_rule_based(self,
                             config: LLMConfig,
                             prompt: str,
                             system_prompt: Optional[str] = None,
                             max_tokens: Optional[int] = None,
                             temperature: Optional[float] = None) -> LLMResponse:
        """Call rule-based processing (always succeeds as fallback)."""
        # Import here to avoid circular imports
        from youtrack_mcp.ai_processor import LocalAIProcessor
        
        # Simple rule-based response based on prompt content
        content = await self._generate_rule_based_response(prompt, system_prompt)
        
        return LLMResponse(
            content=content,
            provider_used=AIProvider.RULE_BASED,
            success=True,
            confidence=0.6  # Rule-based has moderate confidence
        )
    
    async def _generate_rule_based_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate rule-based response based on prompt analysis."""
        prompt_lower = prompt.lower()
        
        # Query translation patterns
        if "translate" in prompt_lower and "query" in prompt_lower:
            if "last week" in prompt_lower:
                return "created: -7d .. *"
            elif "critical" in prompt_lower:
                return "Priority: Critical"
            elif "assigned to me" in prompt_lower:
                return "assignee: me"
            else:
                return "Please specify a project name for the search query"
        
        # Error enhancement patterns
        elif "enhance" in prompt_lower and "error" in prompt_lower:
            if "field" in prompt_lower:
                return "The field name appears to be invalid. Check spelling and case sensitivity."
            elif "syntax" in prompt_lower:
                return "Query syntax error. Use 'field: value' format instead of 'field = value'."
            elif "date" in prompt_lower:
                return "Date format error. Use YYYY-MM-DD format or relative dates like '-7d'."
            else:
                return "Please check your query syntax and field names."
        
        # Pattern analysis
        elif "analyze" in prompt_lower and "pattern" in prompt_lower:
            return "Based on the activity data, the user shows moderate engagement with focus on specific projects."
        
        # Default response
        else:
            return "I understand your request but need more specific information to provide a detailed response."


def create_llm_client_from_config() -> LLMClient:
    """Create LLM client from configuration (YAML or environment variables)."""
    # Import here to avoid circular imports
    from youtrack_mcp.config import config
    
    configs = []
    
    # 1. OpenAI-compatible provider (highest priority if configured)
    if config.LLM_API_URL and config.LLM_API_KEY:
        configs.append(LLMConfig(
            provider=AIProvider.OPENAI_COMPATIBLE,
            api_url=config.LLM_API_URL,
            api_key=config.LLM_API_KEY,
            model_name=config.LLM_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            temperature=config.LLM_TEMPERATURE,
            timeout_seconds=config.LLM_TIMEOUT,
            enabled=config.LLM_ENABLED
        ))
    

    
    # 3. Local model (future implementation)
    if config.LOCAL_MODEL_PATH:
        configs.append(LLMConfig(
            provider=AIProvider.LOCAL_MODEL,
            model_name=config.LOCAL_MODEL_PATH,
            enabled=config.LOCAL_MODEL_ENABLED
        ))
    
    # 4. Rule-based fallback (always available)
    configs.append(LLMConfig(
        provider=AIProvider.RULE_BASED,
        enabled=True  # Always enabled as fallback
    ))
    
    return LLMClient(configs)


def create_openai_config(api_url: str, api_key: str, model: str = "gpt-3.5-turbo") -> LLMConfig:
    """Create OpenAI-compatible configuration."""
    return LLMConfig(
        provider=AIProvider.OPENAI_COMPATIBLE,
        api_url=api_url,
        api_key=api_key,
        model_name=model,
        max_tokens=1000,
        temperature=0.3,
        timeout_seconds=30,
        enabled=True
    )


def create_local_config(model_path: str) -> LLMConfig:
    """Create local model configuration."""
    return LLMConfig(
        provider=AIProvider.LOCAL_MODEL,
        model_name=model_path,
        enabled=True
    )





# Example configurations for common providers
COMMON_PROVIDERS = {
    "openai": {
        "api_url": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    "anthropic": {
        "api_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-sonnet", "claude-3-haiku"]
    },
    "ollama": {
        "api_url": "http://localhost:11434/v1",
        "models": ["llama2", "codellama", "mistral"]
    },
    "openai_compatible": {
        "api_url": "http://localhost:8000/v1",  # Generic local server
        "models": ["custom-model"]
    }
}












# Example usage configurations
EXAMPLE_CONFIGS = {
    "openai": create_openai_config("https://api.openai.com/v1", "your-api-key"),
    "ollama": create_openai_config("http://localhost:11434/v1", "ollama", "llama2")
}