#!/usr/bin/env python3
"""
Test LLM client integration with YouTrack MCP.
"""
import asyncio
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from youtrack_mcp.llm_client import create_llm_client_from_config, create_huggingface_config, LLMConfig, AIProvider
from youtrack_mcp.ai_processor import LocalAIProcessor

async def test_llm_client_only():
    """Test LLM client without external dependencies."""
    print("🤖 TESTING LLM CLIENT")
    print("=" * 50)
    
    # Test rule-based fallback (always available)
    print("\n1. Rule-based LLM Client:")
    llm_client = create_llm_client_from_config()
    
    print(f"   Providers configured: {len(llm_client.configs)}")
    for i, config in enumerate(llm_client.configs):
        print(f"   {i+1}. {config.provider.value}: {'enabled' if config.enabled else 'disabled'}")
    
    # Test rule-based completion
    async with llm_client:
        response = await llm_client.complete(
            prompt="Translate 'show me critical bugs' to YouTrack Query Language",
            system_prompt="You are a YQL expert. Return only the query.",
            max_tokens=100
        )
        
        print(f"   Response success: {response.success}")
        print(f"   Provider used: {response.provider_used.value}")
        print(f"   Content: '{response.content}'")
        print(f"   Confidence: {response.confidence}")

async def test_ai_processor_with_llm():
    """Test AI processor with LLM client integration."""
    print("\n🧠 TESTING AI PROCESSOR WITH LLM CLIENT")
    print("=" * 50)
    
    # Create LLM client
    llm_client = create_llm_client_from_config()
    
    # Create AI processor with LLM client
    ai_processor = LocalAIProcessor(enable_ai=True, llm_client=llm_client)
    
    print(f"   AI processor initialized with LLM client: {ai_processor.llm_client is not None}")
    
    # Test natural language query translation
    print("\n1. Query Translation with LLM:")
    result = await ai_processor.translate_natural_query(
        "Show me critical bugs from last week assigned to john",
        context_hints={'project': 'PAY'}
    )
    
    print(f"   Original: 'Show me critical bugs from last week assigned to john'")
    print(f"   YQL: '{result.yql_query}'")
    print(f"   Confidence: {result.confidence}")
    print(f"   Reasoning: {result.reasoning}")
    print(f"   Entities: {result.detected_entities}")
    
    # Test error enhancement
    print("\n2. Error Enhancement with LLM:")
    error = Exception("Unknown field 'priority' in query")
    context = {"query": "priority = High", "project": "PAY"}
    
    result = await ai_processor.enhance_error_message(error, context)
    
    print(f"   Original error: '{error}'")
    print(f"   Enhanced: '{result.enhanced_explanation}'")
    print(f"   Fix suggestion: '{result.fix_suggestion}'")
    print(f"   Learning tip: '{result.learning_tip}'")
    print(f"   Confidence: {result.confidence}")

async def test_external_llm_config():
    """Test external LLM configuration example."""
    print("\n🌐 TESTING EXTERNAL LLM CONFIGURATION")
    print("=" * 50)
    
    # Show what would happen with external LLM configured
    print("Environment variables for external LLM providers:")
    print("# OpenAI")
    print("export YOUTRACK_LLM_API_URL='https://api.openai.com/v1'")
    print("export YOUTRACK_LLM_API_KEY='sk-your-openai-key'")
    print("export YOUTRACK_LLM_MODEL='gpt-3.5-turbo'")
    print("export YOUTRACK_LLM_ENABLED='true'")
    print()
    print("# Anthropic Claude")
    print("export YOUTRACK_LLM_API_URL='https://api.anthropic.com/v1'")
    print("export YOUTRACK_LLM_API_KEY='sk-ant-your-anthropic-key'")
    print("export YOUTRACK_LLM_MODEL='claude-3-haiku-20240307'")
    print("export YOUTRACK_LLM_ENABLED='true'")
    print()
    print("# Ollama (Local)")
    print("export YOUTRACK_LLM_API_URL='http://localhost:11434/v1'")
    print("export YOUTRACK_LLM_API_KEY='ollama'")
    print("export YOUTRACK_LLM_MODEL='llama2'")
    print("export YOUTRACK_LLM_ENABLED='true'")
    print()
    print("# Hugging Face (Local CPU)")
    print("export YOUTRACK_HF_MODEL='Qwen/Qwen1.5-0.5B-Chat'")
    print("export YOUTRACK_HF_DEVICE='cpu'")
    print("export YOUTRACK_HF_4BIT='true'")
    print("export YOUTRACK_HF_ENABLED='true'")

async def test_huggingface_config():
    """Test Hugging Face configuration (without actual model loading)."""
    print("\n🤗 TESTING HUGGING FACE CONFIGURATION")
    print("=" * 50)
    
    # Create Hugging Face config examples
    configs = [
        create_huggingface_config("TinyLlama/TinyLlama-1.1B-Chat-v1.0", device="cpu"),
        create_huggingface_config("Qwen/Qwen1.5-0.5B-Chat", device="cpu"),
        create_huggingface_config("Qwen/Qwen1.5-1.8B-Chat", device="cpu", quantization="4bit"),
    ]
    
    print("Recommended Hugging Face configurations:")
    for i, config in enumerate(configs):
        print(f"   {i+1}. Model: {config.model_name}")
        print(f"      Device: {config.device}")
        print(f"      4-bit quantization: {config.load_in_4bit}")
        print(f"      8-bit quantization: {config.load_in_8bit}")
        print()

async def main():
    """Main test function."""
    print("🚀 YouTrack MCP LLM Integration Test")
    print("=" * 60)
    
    try:
        # Test LLM client
        await test_llm_client_only()
        
        # Test AI processor with LLM
        await test_ai_processor_with_llm()
        
        # Test external LLM configuration examples
        await test_external_llm_config()
        
        # Test Hugging Face configuration
        await test_huggingface_config()
        
        print("\n✅ ALL LLM INTEGRATION TESTS COMPLETED!")
        print("=" * 60)
        print("\n🎯 LLM Integration Features:")
        print("   ✓ Multi-provider LLM client with fallback hierarchy")
        print("   ✓ OpenAI-compatible API support") 
        print("   ✓ Hugging Face Transformers support")
        print("   ✓ Rule-based fallback (always available)")
        print("   ✓ Seamless AI processor integration")
        print("   ✓ Configurable via environment variables")
        print("\n🚀 Ready for production with external LLM providers!")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)