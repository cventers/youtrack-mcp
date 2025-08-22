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
    HUGGINGFACE = "huggingface"              # Hugging Face Transformers models
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
    # Hugging Face specific options
    device: str = "cpu"                        # cpu, cuda, mps
    torch_dtype: Optional[str] = None          # auto, float16, bfloat16
    load_in_8bit: bool = False                 # Use 8-bit quantization
    load_in_4bit: bool = False                 # Use 4-bit quantization
    trust_remote_code: bool = False            # Allow custom model code


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
    
    def __init__(self, configs: List[LLMConfig]):
        """
        Initialize LLM client with provider configurations.
        
        Args:
            configs: List of LLM configurations in priority order
        """
        self.configs = configs
        self.http_client = None
        self._initialize_http_client()
        
        # Hugging Face models cache
        self._hf_models = {}
        self._hf_tokenizers = {}
        
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
                elif config.provider == AIProvider.HUGGINGFACE:
                    response = await self._call_huggingface(
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
    
    async def _call_huggingface(self,
                              config: LLMConfig,
                              prompt: str,
                              system_prompt: Optional[str] = None,
                              max_tokens: Optional[int] = None,
                              temperature: Optional[float] = None) -> LLMResponse:
        """Call Hugging Face Transformers model."""
        try:
            # Import here to make it optional
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            import transformers
            
        except ImportError:
            return LLMResponse(
                content="",
                provider_used=AIProvider.HUGGINGFACE,
                success=False,
                error="transformers library not installed. Run: pip install transformers torch",
                confidence=0.0
            )
        
        if not config.model_name:
            return LLMResponse(
                content="",
                provider_used=AIProvider.HUGGINGFACE,
                success=False,
                error="model_name required for Hugging Face provider",
                confidence=0.0
            )
        
        try:
            # Load model and tokenizer (cached)
            model_key = f"{config.model_name}_{config.device}"
            
            if model_key not in self._hf_models:
                logger.info(f"Loading Hugging Face model: {config.model_name}")
                
                # Prepare model loading arguments
                model_kwargs = {
                    "trust_remote_code": config.trust_remote_code,
                    "device_map": "auto" if config.device != "cpu" else None,
                }
                
                # Add quantization if specified
                if config.load_in_4bit:
                    from transformers import BitsAndBytesConfig
                    model_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                elif config.load_in_8bit:
                    model_kwargs["load_in_8bit"] = True
                
                # Set torch dtype
                if config.torch_dtype:
                    if config.torch_dtype == "auto":
                        model_kwargs["torch_dtype"] = "auto"
                    elif config.torch_dtype == "float16":
                        model_kwargs["torch_dtype"] = torch.float16
                    elif config.torch_dtype == "bfloat16":
                        model_kwargs["torch_dtype"] = torch.bfloat16
                
                # Load tokenizer and model
                tokenizer = AutoTokenizer.from_pretrained(
                    config.model_name,
                    trust_remote_code=config.trust_remote_code
                )
                
                # Add pad token if missing
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
                
                model = AutoModelForCausalLM.from_pretrained(
                    config.model_name,
                    **model_kwargs
                )
                
                # Move to device if CPU
                if config.device == "cpu":
                    model = model.to("cpu")
                
                self._hf_tokenizers[model_key] = tokenizer
                self._hf_models[model_key] = model
                
                logger.info(f"Model {config.model_name} loaded successfully on {config.device}")
            
            tokenizer = self._hf_tokenizers[model_key]
            model = self._hf_models[model_key]
            
            # Prepare full prompt
            full_prompt = prompt
            if system_prompt:
                # Format depends on model, this is a generic approach
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
            
            # Tokenize input
            inputs = tokenizer.encode(full_prompt, return_tensors="pt")
            if config.device == "cuda" and torch.cuda.is_available():
                inputs = inputs.to("cuda")
            elif config.device == "cpu":
                inputs = inputs.to("cpu")
            
            # Generate response
            max_new_tokens = max_tokens or config.max_tokens
            temp = temperature or config.temperature
            
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temp,
                    do_sample=temp > 0.0,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    attention_mask=torch.ones_like(inputs)
                )
            
            # Decode response
            response_tokens = outputs[0][inputs.shape[-1]:]
            response_text = tokenizer.decode(response_tokens, skip_special_tokens=True)
            
            # Clean up response
            response_text = response_text.strip()
            
            return LLMResponse(
                content=response_text,
                provider_used=AIProvider.HUGGINGFACE,
                success=True,
                tokens_used=len(outputs[0]),
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error with Hugging Face model {config.model_name}: {e}")
            return LLMResponse(
                content="",
                provider_used=AIProvider.HUGGINGFACE,
                success=False,
                error=f"Model execution failed: {str(e)}",
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
                return "project: {PROJECT_NAME}"
        
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
    
    # 2. Hugging Face Transformers model (second priority if configured)
    if config.HF_MODEL:
        configs.append(LLMConfig(
            provider=AIProvider.HUGGINGFACE,
            model_name=config.HF_MODEL,
            max_tokens=config.HF_MAX_TOKENS,
            temperature=config.HF_TEMPERATURE,
            device=config.HF_DEVICE,
            torch_dtype=config.HF_TORCH_DTYPE if config.HF_TORCH_DTYPE else None,
            load_in_4bit=config.HF_4BIT,
            load_in_8bit=config.HF_8BIT,
            trust_remote_code=config.HF_TRUST_REMOTE_CODE,
            enabled=config.HF_ENABLED
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


def create_huggingface_config(model_name: str, 
                            device: str = "cpu",
                            quantization: str = None,
                            torch_dtype: str = None) -> LLMConfig:
    """
    Create Hugging Face Transformers configuration.
    
    Args:
        model_name: Hugging Face model name (e.g., "microsoft/DialoGPT-medium")
        device: Device to run on ("cpu", "cuda", "mps")
        quantization: Quantization type ("4bit", "8bit", None)
        torch_dtype: Torch data type ("auto", "float16", "bfloat16", None)
    """
    return LLMConfig(
        provider=AIProvider.HUGGINGFACE,
        model_name=model_name,
        device=device,
        torch_dtype=torch_dtype,
        load_in_4bit=quantization == "4bit",
        load_in_8bit=quantization == "8bit",
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

# Recommended Hugging Face models for CPU inference on modest hardware
RECOMMENDED_CPU_MODELS = {
    # Small, fast models (good for basic tasks)
    "lightweight": {
        "microsoft/DialoGPT-small": {
            "size": "117M parameters",
            "ram_usage": "~500MB",
            "use_case": "Basic query translation and error enhancement",
            "performance": "Fast inference, good for simple patterns"
        },
        "distilgpt2": {
            "size": "82M parameters", 
            "ram_usage": "~400MB",
            "use_case": "Very fast responses for simple tasks",
            "performance": "Excellent CPU performance, limited capability"
        },
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {
            "size": "1.1B parameters",
            "ram_usage": "~2GB",
            "use_case": "Chat-oriented tasks with better understanding",
            "performance": "Good balance of speed and capability"
        }
    },
    
    # Medium models (balanced performance and capability)
    "balanced": {
        "microsoft/DialoGPT-medium": {
            "size": "345M parameters",
            "ram_usage": "~1.5GB", 
            "use_case": "Query translation with good context understanding",
            "performance": "Good CPU performance with better responses"
        },
        "Qwen/Qwen1.5-0.5B-Chat": {
            "size": "500M parameters",
            "ram_usage": "~2GB",
            "use_case": "General purpose with good instruction following",
            "performance": "Excellent for technical tasks like YouTrack queries"
        },
        "stabilityai/stablelm-2-zephyr-1_6b": {
            "size": "1.6B parameters",
            "ram_usage": "~3GB",
            "use_case": "Strong instruction following for complex tasks",
            "performance": "Good CPU performance, excellent quality"
        }
    },
    
    # Larger models (better capability, higher resource usage)
    "capable": {
        "microsoft/DialoGPT-large": {
            "size": "762M parameters",
            "ram_usage": "~3GB",
            "use_case": "High-quality query translation and analysis",
            "performance": "Slower but more accurate responses"
        },
        "Qwen/Qwen1.5-1.8B-Chat": {
            "size": "1.8B parameters", 
            "ram_usage": "~4GB",
            "use_case": "Complex reasoning for activity pattern analysis",
            "performance": "Best quality for technical tasks on CPU"
        },
        "microsoft/Phi-3-mini-4k-instruct": {
            "size": "3.8B parameters",
            "ram_usage": "~8GB with 4-bit quantization",
            "use_case": "High-quality instruction following and reasoning",
            "performance": "Excellent quality, requires quantization for CPU"
        }
    }
}

# Specific model recommendations for YouTrack MCP tasks
YOUTRACK_TASK_MODELS = {
    "query_translation": [
        "Qwen/Qwen1.5-0.5B-Chat",           # Best balance for query tasks
        "microsoft/DialoGPT-medium",        # Good fallback
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0"  # Fast option
    ],
    "error_enhancement": [
        "stabilityai/stablelm-2-zephyr-1_6b",  # Excellent instruction following
        "Qwen/Qwen1.5-1.8B-Chat",             # Good reasoning
        "microsoft/DialoGPT-large"             # Detailed responses
    ],
    "pattern_analysis": [
        "Qwen/Qwen1.5-1.8B-Chat",             # Best reasoning for patterns
        "microsoft/Phi-3-mini-4k-instruct",   # High quality (needs 4-bit)
        "stabilityai/stablelm-2-zephyr-1_6b"  # Good analysis capability
    ]
}


def get_recommended_model(task: str = "query_translation", 
                         hardware: str = "modest",
                         quantization: bool = True) -> str:
    """
    Get recommended model for specific YouTrack tasks.
    
    Args:
        task: Task type ("query_translation", "error_enhancement", "pattern_analysis")
        hardware: Hardware capability ("modest", "good", "powerful")  
        quantization: Whether to use quantization for larger models
        
    Returns:
        Recommended model name
    """
    models = YOUTRACK_TASK_MODELS.get(task, YOUTRACK_TASK_MODELS["query_translation"])
    
    if hardware == "modest":
        # Prefer smallest, fastest models
        return models[-1] if len(models) > 2 else models[0]
    elif hardware == "good":
        # Prefer balanced models
        return models[0] if len(models) > 1 else models[0]
    else:  # powerful
        # Prefer most capable models
        return models[0]


def create_recommended_config(task: str = "query_translation",
                            hardware: str = "modest") -> LLMConfig:
    """
    Create a recommended Hugging Face configuration for YouTrack tasks.
    
    Args:
        task: YouTrack task type
        hardware: Hardware capability level
        
    Returns:
        Optimized LLMConfig for the task and hardware
    """
    model_name = get_recommended_model(task, hardware)
    
    # Configure based on hardware capability
    if hardware == "modest":
        return create_huggingface_config(
            model_name=model_name,
            device="cpu",
            quantization="4bit" if "Phi-3" in model_name else None,
            torch_dtype="auto"
        )
    elif hardware == "good":
        return create_huggingface_config(
            model_name=model_name,
            device="cpu",
            quantization="4bit" if any(x in model_name for x in ["Phi-3", "1.8B"]) else None,
            torch_dtype="auto"
        )
    else:  # powerful
        return create_huggingface_config(
            model_name=model_name,
            device="cuda" if torch.cuda.is_available() else "cpu",
            quantization=None,
            torch_dtype="auto"
        )


# Example usage configurations
EXAMPLE_CONFIGS = {
    "cpu_lightweight": create_huggingface_config("TinyLlama/TinyLlama-1.1B-Chat-v1.0"),
    "cpu_balanced": create_huggingface_config("Qwen/Qwen1.5-0.5B-Chat"),
    "cpu_capable": create_huggingface_config("Qwen/Qwen1.5-1.8B-Chat", quantization="4bit"),
    "openai": create_openai_config("https://api.openai.com/v1", "your-api-key"),
    "ollama": create_openai_config("http://localhost:11434/v1", "ollama", "llama2")
}