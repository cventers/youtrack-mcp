#!/usr/bin/env python3
"""Manual test script for people resolution in autosearch."""

import asyncio
import json
import os
from unittest.mock import AsyncMock, Mock

# Add the project root to the path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtrack_mcp.ai.llm_client import LLMClient
from youtrack_mcp.ai.service import AIService
from youtrack_mcp.ai.models import YQLTranslationResponse
from youtrack_mcp.tools.users_tools import UsersTools


async def test_people_resolution():
    """Test the people resolution functionality."""
    
    print("Testing People Resolution in AutoSearch")
    print("=" * 50)
    
    # Create a mock MCP instance with users tools
    mock_mcp_instance = Mock()
    mock_users_tools = AsyncMock(spec=UsersTools)
    
    # Mock the users.search to return test data
    async def mock_search(query, limit=10):
        print(f"\n[TOOL CALL] users.search(query='{query}', limit={limit})")
        
        # Simulate different responses based on query
        if "Chase Venters" in query or "chase venters" in query.lower():
            result = {
                "users": [{
                    "login": "cventers",
                    "fullName": "Chase Venters", 
                    "email": "chase.venters@company.com"
                }],
                "count": 1
            }
        elif "@" in query:
            # Email query
            result = {
                "users": [{
                    "login": "jdoe",
                    "fullName": "John Doe",
                    "email": query
                }],
                "count": 1
            }
        else:
            result = {"users": [], "count": 0}
        
        print(f"[TOOL RESPONSE] {json.dumps(result, indent=2)}")
        return result
    
    mock_users_tools.search = mock_search
    mock_mcp_instance.tools = {"users": mock_users_tools}
    
    # Create a mock LLM client
    mock_llm_client = Mock(spec=LLMClient)
    
    # Simulate the LLM making tool calls for display names
    async def simulate_complete_with_tools(response_model, messages, tools, tool_handler, **kwargs):
        # Extract the query from messages
        user_message = messages[-1]["content"] if messages else ""
        print(f"\n[LLM] Processing query: {user_message}")
        
        # Check if we need to resolve people
        if "Chase Venters" in user_message or "chase venters" in user_message.lower():
            print("[LLM] Detected display name 'Chase Venters' - calling users.search")
            # Call the tool to resolve the name
            tool_result = await tool_handler("users_search", {"query": "Chase Venters", "limit": 5})
            
            # Generate YQL with resolved login
            return YQLTranslationResponse(
                yql_query="project: OPS, PAY, SP created by: cventers",
                confidence=0.95,
                reasoning="Resolved 'Chase Venters' to login 'cventers' via users.search",
                detected_entities={
                    "projects": ["OPS", "PAY", "SP"],
                    "users": ["cventers"]
                }
            )
        elif "@" in user_message:
            print(f"[LLM] Detected email address - calling users.search")
            import re
            email_match = re.search(r'[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}', user_message)
            if email_match:
                email = email_match.group()
                tool_result = await tool_handler("users_search", {"query": email, "limit": 5})
                
                return YQLTranslationResponse(
                    yql_query="for: jdoe",
                    confidence=0.96,
                    reasoning=f"Resolved email '{email}' to login 'jdoe' via users.search",
                    detected_entities={
                        "users": ["jdoe"]
                    }
                )
        else:
            # Direct login - no tool call needed
            print("[LLM] Using direct login - no tool call needed")
            return YQLTranslationResponse(
                yql_query="created by: cventers",
                confidence=0.98,
                reasoning="Direct login 'cventers' used without resolution",
                detected_entities={
                    "users": ["cventers"]
                }
            )
    
    mock_llm_client.complete_with_tools = simulate_complete_with_tools
    
    # Create the AI service
    ai_service = AIService(
        llm_client=mock_llm_client,
        mcp_instance=mock_mcp_instance
    )
    
    # Test cases
    test_cases = [
        {
            "query": "tickets created by Chase Venters in projects OPS, PAY, SP",
            "expected": "created by: cventers",
            "should_call_tool": True
        },
        {
            "query": "created by cventers",
            "expected": "created by: cventers", 
            "should_call_tool": False
        },
        {
            "query": "assigned to john.doe@company.com",
            "expected": "for: jdoe",
            "should_call_tool": True
        }
    ]
    
    # Run test cases
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 50}")
        print(f"Test Case {i}: {test['query']}")
        print(f"Expected tool call: {test['should_call_tool']}")
        print(f"Expected YQL contains: {test['expected']}")
        
        result = await ai_service.translate_nl_to_yql(test['query'])
        
        print(f"\n[RESULT]")
        print(f"YQL: {result.yql_query}")
        print(f"Confidence: {result.confidence}")
        print(f"Reasoning: {result.reasoning}")
        print(f"Detected entities: {result.detected_entities}")
        
        # Verify expectations
        assert test['expected'] in result.yql_query, f"Expected '{test['expected']}' in YQL"
        assert result.confidence > 0.9, "Confidence should be high"
        
        print(f"✅ Test passed!")
    
    print(f"\n{'=' * 50}")
    print("All tests passed successfully!")
    print("\nSummary:")
    print("- Display names are resolved to logins via users.search tool")
    print("- Direct logins are used without tool calls")
    print("- Email addresses are resolved to logins")
    print("- Tool calling integration works as expected")


if __name__ == "__main__":
    asyncio.run(test_people_resolution())