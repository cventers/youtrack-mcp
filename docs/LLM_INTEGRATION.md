# YouTrack MCP - LLM Integration Guide

## Overview

The YouTrack MCP now supports multiple AI providers for enhanced natural language processing capabilities. The system provides intelligent query translation, error enhancement, and activity pattern analysis using either external LLM APIs or local CPU models.

## Supported AI Providers

### 1. OpenAI-Compatible APIs (Highest Priority)
- **OpenAI**: Official OpenAI API
- **Anthropic**: Claude API  
- **Local Servers**: Ollama, OpenAI-compatible endpoints
- **Other Providers**: Any OpenAI-compatible API

### 2. Hugging Face Transformers (Second Priority)
- **Local Models**: CPU inference with quantization
- **Privacy-First**: No external API calls
- **Optimized**: 4-bit and 8-bit quantization support

### 3. Rule-Based Fallback (Always Available)
- **No Dependencies**: Works without any AI models
- **Pattern Matching**: Handles common YouTrack query patterns
- **Reliable**: Always provides results

## Configuration

You can configure LLM providers using either **YAML configuration files** or **environment variables**. YAML configuration is recommended for complex setups, while environment variables are better for simple deployments or Docker containers.

### YAML Configuration (Recommended)

Create a `config.yaml` file with your LLM settings:

```yaml
# AI/LLM Configuration
ai:
  enabled: true
  max_memory_mb: 2048
  
  # OpenAI-compatible API provider
  llm:
    api_url: "https://api.openai.com/v1"
    api_key: "sk-your-openai-key"
    model: "gpt-3.5-turbo"
    max_tokens: 1000
    temperature: 0.3
    timeout: 30
    enabled: true
  
  # Hugging Face Transformers (local CPU)
  huggingface:
    model: "Qwen/Qwen1.5-0.5B-Chat"
    device: "cpu"
    max_tokens: 1000
    temperature: 0.3
    torch_dtype: "auto"
    quantization_4bit: false
    quantization_8bit: false
    trust_remote_code: false
    enabled: false
```

See the following documentation for detailed configuration guidance:
- **[YAML Configuration Guide](YAML_CONFIGURATION.md)** - Complete YAML configuration reference
- **[CPU Model Guide](CPU_MODELS.md)** - CPU-only model recommendations and hardware requirements
- `config.example.yaml` - Example configuration file with multiple scenarios

### Environment Variables

#### OpenAI-Compatible Provider
```bash
# Basic configuration
YOUTRACK_LLM_API_URL=https://api.openai.com/v1
YOUTRACK_LLM_API_KEY=your_api_key_here
YOUTRACK_LLM_MODEL=gpt-3.5-turbo

# Optional parameters
YOUTRACK_LLM_MAX_TOKENS=1000
YOUTRACK_LLM_TEMPERATURE=0.3
YOUTRACK_LLM_TIMEOUT=30
YOUTRACK_LLM_ENABLED=true
```

#### Hugging Face Transformers
```bash
# Model configuration
YOUTRACK_HF_MODEL=Qwen/Qwen1.5-0.5B-Chat
YOUTRACK_HF_DEVICE=cpu
YOUTRACK_HF_ENABLED=true

# Quantization (optional)
YOUTRACK_HF_4BIT=true          # Use 4-bit quantization
YOUTRACK_HF_8BIT=false         # Use 8-bit quantization
YOUTRACK_HF_TORCH_DTYPE=auto   # auto, float16, bfloat16

# Advanced options
YOUTRACK_HF_MAX_TOKENS=1000
YOUTRACK_HF_TEMPERATURE=0.3
YOUTRACK_HF_TRUST_REMOTE_CODE=false
```

#### General AI Settings
```bash
# AI processor configuration
YOUTRACK_AI_ENABLED=true
YOUTRACK_AI_MAX_MEMORY_MB=2048
```

## Provider Examples

### OpenAI
```bash
export YOUTRACK_LLM_API_URL="https://api.openai.com/v1"
export YOUTRACK_LLM_API_KEY="sk-your-openai-key"
export YOUTRACK_LLM_MODEL="gpt-3.5-turbo"
export YOUTRACK_LLM_ENABLED="true"
```

### Anthropic Claude
```bash
export YOUTRACK_LLM_API_URL="https://api.anthropic.com/v1"
export YOUTRACK_LLM_API_KEY="sk-ant-your-anthropic-key"
export YOUTRACK_LLM_MODEL="claude-3-haiku-20240307"
export YOUTRACK_LLM_ENABLED="true"
```

### Ollama (Local)
```bash
export YOUTRACK_LLM_API_URL="http://localhost:11434/v1"
export YOUTRACK_LLM_API_KEY="ollama"
export YOUTRACK_LLM_MODEL="llama2"
export YOUTRACK_LLM_ENABLED="true"
```

### Hugging Face (Local CPU)
```bash
export YOUTRACK_HF_MODEL="Qwen/Qwen1.5-0.5B-Chat"
export YOUTRACK_HF_DEVICE="cpu"
export YOUTRACK_HF_4BIT="true"
export YOUTRACK_HF_ENABLED="true"
```

## Recommended Models for CPU Inference

### Lightweight Models (≤2GB RAM)
- **TinyLlama/TinyLlama-1.1B-Chat-v1.0**: 1.1B parameters, fast inference
- **Qwen/Qwen1.5-0.5B-Chat**: 500M parameters, excellent for technical tasks
- **distilgpt2**: 82M parameters, very fast but limited capability

### Balanced Models (2-4GB RAM)
- **Qwen/Qwen1.5-0.5B-Chat**: Best balance for YouTrack queries
- **microsoft/DialoGPT-medium**: 345M parameters, good context understanding
- **stabilityai/stablelm-2-zephyr-1_6b**: 1.6B parameters, excellent instruction following

### Capable Models (4-8GB RAM with quantization)
- **Qwen/Qwen1.5-1.8B-Chat**: Best reasoning for complex tasks
- **microsoft/Phi-3-mini-4k-instruct**: 3.8B parameters, requires 4-bit quantization
- **microsoft/DialoGPT-large**: 762M parameters, high-quality responses

## Task-Specific Recommendations

### Query Translation
```bash
# Best: Qwen/Qwen1.5-0.5B-Chat
export YOUTRACK_HF_MODEL="Qwen/Qwen1.5-0.5B-Chat"
export YOUTRACK_HF_DEVICE="cpu"
export YOUTRACK_HF_ENABLED="true"
```

### Error Enhancement
```bash
# Best: stabilityai/stablelm-2-zephyr-1_6b
export YOUTRACK_HF_MODEL="stabilityai/stablelm-2-zephyr-1_6b"
export YOUTRACK_HF_DEVICE="cpu"
export YOUTRACK_HF_ENABLED="true"
```

### Pattern Analysis
```bash
# Best: Qwen/Qwen1.5-1.8B-Chat with 4-bit quantization
export YOUTRACK_HF_MODEL="Qwen/Qwen1.5-1.8B-Chat"
export YOUTRACK_HF_DEVICE="cpu"
export YOUTRACK_HF_4BIT="true"
export YOUTRACK_HF_ENABLED="true"
```

## Installation Requirements

### For OpenAI-Compatible APIs
```bash
# Already included in base requirements
pip install httpx
```

### For Hugging Face Transformers
```bash
# CPU inference
pip install transformers torch

# With quantization support
pip install transformers torch bitsandbytes

# For optimal CPU performance
pip install transformers torch accelerate
```

## Usage Examples

### Natural Language Query Translation
```python
# Input: "Show me critical bugs from last week"
# Output: "Priority: Critical created: -7d .. *"

# The AI will automatically translate natural language to YouTrack Query Language
result = await smart_search_issues("critical bugs from last week")
```

### Error Enhancement
```python
# Input: "Unknown field 'priority' in query"
# Output: Enhanced explanation with fix suggestions and learning tips

result = await enhance_error_context(
    error_message="Unknown field 'priority'",
    context={"query": "priority = High"}
)
```

### Activity Pattern Analysis
```python
# Analyze user activity patterns with AI insights
result = await analyze_user_activity_patterns(
    user_id="john.doe",
    analysis_types=["productivity_trends", "collaboration_patterns"]
)
```

## Performance Characteristics

### OpenAI-Compatible APIs
- **Latency**: 1-3 seconds (network dependent)
- **Quality**: Excellent
- **Cost**: Pay per token
- **Privacy**: Data sent to external service

### Hugging Face Transformers (CPU)
- **Latency**: 2-10 seconds (model size dependent)
- **Quality**: Good to excellent (model dependent)
- **Cost**: Free after initial download
- **Privacy**: Complete - no external calls

### Rule-Based Fallback
- **Latency**: <100ms
- **Quality**: Moderate
- **Cost**: Free
- **Privacy**: Complete

## Fallback Hierarchy

The system automatically falls back through providers:

1. **OpenAI-Compatible** (if configured and available)
2. **Hugging Face** (if configured and model loaded)
3. **Rule-Based** (always available)

This ensures the system always provides results, even if AI providers fail.

## Troubleshooting

### Common Issues

#### "transformers library not installed"
```bash
pip install transformers torch
```

#### "Model loading failed"
- Check available RAM (models need 2-8GB)
- Try smaller model or enable quantization
- Verify model name is correct

#### "API authentication failed"
- Verify API key is correct
- Check API URL format
- Ensure sufficient API credits

#### "All LLM providers failed"
- System falls back to rule-based processing
- Check environment variables
- Verify network connectivity for external APIs

### Debugging

Enable debug logging:
```bash
export YOUTRACK_DEBUG=true
python main.py
```

Check provider status:
```python
# The system logs provider initialization
# Look for: "LLM client initialized with X provider(s)"
```

## Security Considerations

### API Keys
- Store in environment variables, never in code
- Use restricted API keys when possible
- Monitor API usage and costs

### Local Models
- Models are downloaded once and cached
- No external network calls during inference
- Complete privacy for sensitive data

### Token Masking
- API tokens are masked in logs
- Error messages don't expose sensitive data
- Audit logging for token access

## Advanced Configuration

### Custom Provider Priority
The system uses environment variables to determine provider priority. Configure only the providers you want to use:

```bash
# External API only
export YOUTRACK_LLM_API_URL="..."
export YOUTRACK_LLM_API_KEY="..."

# Local model only  
export YOUTRACK_HF_MODEL="..."
export YOUTRACK_HF_ENABLED="true"

# Both (external API takes priority)
export YOUTRACK_LLM_API_URL="..."
export YOUTRACK_LLM_API_KEY="..."
export YOUTRACK_HF_MODEL="..."
export YOUTRACK_HF_ENABLED="true"
```

### Performance Tuning

#### For Low Memory Systems
```bash
export YOUTRACK_HF_MODEL="distilgpt2"
export YOUTRACK_AI_MAX_MEMORY_MB="1024"
```

#### For High Performance
```bash
export YOUTRACK_HF_MODEL="Qwen/Qwen1.5-1.8B-Chat"
export YOUTRACK_HF_4BIT="true"
export YOUTRACK_AI_MAX_MEMORY_MB="4096"
```

## Integration with YouTrack MCP Tools

The LLM integration enhances these MCP tools:

- **`smart_search_issues()`**: Natural language query translation
- **`enhance_error_context()`**: AI-powered error explanations
- **`analyze_user_activity_patterns()`**: Intelligent activity analysis
- **All search tools**: Enhanced error messages when queries fail

The integration is seamless - existing tools work better with AI, but still function without it.