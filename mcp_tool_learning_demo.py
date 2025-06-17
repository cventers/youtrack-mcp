#!/usr/bin/env python3
"""
Focused demo showing how models learn about the YouTrack MCP tools and their schemas.
"""
import json

def show_create_issue_learning():
    """Show what the model learns about the create_issue tool."""
    print("🎯 FOCUS: create_issue Tool - What the Model Learns")
    print("=" * 70)
    
    tool_schema = {
        "name": "create_issue",
        "description": "Create a new issue in YouTrack. Returns created issue information with intelligent attribute suggestions for missing fields to help improve issue completeness and tracking.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string", 
                    "description": "Project key or ID"
                },
                "summary": {
                    "type": "string",
                    "description": "Issue summary/title"
                },
                "description": {
                    "type": "string",
                    "description": "Issue description (optional)"
                }
            },
            "required": ["project", "summary"]
        }
    }
    
    print("\n📋 Tool Schema the Model Receives:")
    print(json.dumps(tool_schema, indent=2))
    
    print("\n🧠 What the Model Understands:")
    print("""
✅ BASIC USAGE:
   • Function: create_issue(project: str, summary: str, description?: str)
   • Required: project and summary
   • Optional: description
   • Purpose: Create new YouTrack issues

🔍 SPECIAL FEATURES (from description):
   • Returns "intelligent attribute suggestions"
   • Helps "improve issue completeness and tracking"
   • More than just basic issue creation

🎯 MODEL'S MENTAL MODEL:
   "This tool creates issues AND provides guidance on how to make them better.
    I should expect suggestions in the response that I can act on."
""")

def show_example_tool_call():
    """Show an example tool call and response."""
    print("\n📞 EXAMPLE: Model Makes a Tool Call")
    print("=" * 70)
    
    # Tool call request
    tool_call = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "create_issue",
            "arguments": {
                "project": "WEBAPP",
                "summary": "Authentication failing on mobile devices",
                "description": "Users report that login attempts fail silently on iOS and Android browsers"
            }
        }
    }
    
    print("\n🔧 Model's Tool Call:")
    print(json.dumps(tool_call, indent=2))
    
    # Simulated enhanced response
    tool_response = {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "id": "2-456",
                        "idReadable": "WEBAPP-789",
                        "summary": "Authentication failing on mobile devices",
                        "description": "Users report that login attempts fail silently on iOS and Android browsers",
                        "project": {
                            "shortName": "WEBAPP",
                            "name": "Web Application"
                        },
                        "created_iso8601": "2024-01-15T10:30:00+00:00",
                        "updated_iso8601": "2024-01-15T10:30:00+00:00",
                        "attribute_suggestions": {
                            "suggestions_available": True,
                            "suggestion_count": 4,
                            "attribute_suggestions": [
                                {
                                    "attribute": "priority",
                                    "prompt": "Consider setting a priority based on the issue severity",
                                    "reason": "Authentication issues typically warrant higher priority",
                                    "suggested_value": "High",
                                    "available_options": ["Critical", "High", "Normal", "Low"]
                                },
                                {
                                    "attribute": "type",
                                    "prompt": "Consider specifying the issue type",
                                    "reason": "No type was specified in the issue creation",
                                    "suggested_value": "Bug",
                                    "available_options": ["Bug", "Feature", "Task", "Epic", "Story"]
                                },
                                {
                                    "attribute": "component",
                                    "prompt": "Consider specifying which component or subsystem this affects",
                                    "reason": "No component was specified in the issue creation"
                                },
                                {
                                    "attribute": "tags",
                                    "prompt": "Consider adding relevant tags to categorize this issue",
                                    "reason": "No tags was specified in the issue creation",
                                    "suggested_value": []
                                }
                            ],
                            "suggested_mcp_calls": [
                                {
                                    "tool": "youtrack.update_issue",
                                    "parameters": {
                                        "issue_id": "WEBAPP-789",
                                        "priority": "High"
                                    },
                                    "description": "Update the issue to set priority to High"
                                },
                                {
                                    "tool": "youtrack.update_issue", 
                                    "parameters": {
                                        "issue_id": "WEBAPP-789",
                                        "type": "Bug"
                                    },
                                    "description": "Update the issue to set type to Bug"
                                }
                            ],
                            "suggestion_note": "These suggestions can help improve the issue completeness and tracking."
                        },
                        "mcp_guidance": {
                            "message": "The issue was created successfully. Consider the suggested improvements below.",
                            "next_steps": "You can use the suggested MCP calls to enhance this issue with missing attributes.",
                            "last_created_issue": "WEBAPP-789"
                        }
                    }, indent=2)
                }
            ]
        }
    }
    
    print("\n📨 Enhanced Tool Response (What Model Receives):")
    print(json.dumps(tool_response, indent=2))

def show_model_learning_process():
    """Show how the model processes and learns from the response."""
    print("\n🧠 MODEL'S LEARNING PROCESS")
    print("=" * 70)
    
    print("""
🔄 STEP 1: Standard Response Processing
   ✅ Issue created successfully: WEBAPP-789
   ✅ Basic fields populated (summary, description, project)
   ✅ Standard YouTrack response format

🎯 STEP 2: Suggestion Analysis  
   📊 Found 4 attribute suggestions
   🔍 Contextual reasoning detected:
       • "Authentication issues" → Priority: High
       • "failing", "report" → Type: Bug
   💡 Available options learned for future use

🚀 STEP 3: Action Planning
   📝 2 ready-to-execute MCP calls identified
   🎯 Exact issue ID available: WEBAPP-789
   ⚡ Can immediately improve the issue if desired

🧭 STEP 4: Workflow Understanding
   💬 Clear guidance on next steps
   🔗 Agentic pattern learned: Create → Analyze → Suggest → Execute
   📚 Educational context for better future performance
""")

def show_agentic_follow_up():
    """Show how a model might follow up based on the suggestions."""
    print("\n🤖 TYPICAL MODEL FOLLOW-UP")
    print("=" * 70)
    
    print("""
MODEL'S RESPONSE TO USER:
"I've successfully created issue WEBAPP-789 for the authentication problem. 

Based on the content analysis, I recommend setting this as a 'High' priority 
issue since authentication failures significantly impact user experience. I can 
also mark it as a 'Bug' type since this is clearly a defect.

Would you like me to apply these improvements? I can run:
• update_issue(issue_id='WEBAPP-789', priority='High')  
• update_issue(issue_id='WEBAPP-789', type='Bug')

This will help with proper issue tracking and prioritization."

[If user agrees, model immediately executes the suggested calls]
""")

def show_configuration_awareness():
    """Show how the model learns about configurability."""
    print("\n⚙️ CONFIGURATION AWARENESS")
    print("=" * 70)
    
    print("""
🎛️ WHAT THE MODEL LEARNS ABOUT SUGGESTIONS:

📋 From Tool Description:
   • "intelligent attribute suggestions" 
   • "help improve issue completeness"
   
🔍 From Response Structure:
   • suggestions_available: true/false
   • suggestion_count: number of suggestions
   • available_options: what values are allowed
   • suggested_value: contextual recommendations

🎯 From MCP Guidance:
   • Clear workflow instructions
   • Ready-to-use tool calls
   • Educational reasoning

💡 MODEL'S UNDERSTANDING:
   "This system is designed for agentic workflows. It doesn't just 
    execute commands—it actively helps me create better issues and
    provides clear paths for improvement. The suggestions are 
    configurable and context-aware."
""")

if __name__ == "__main__":
    print("🎓 MODEL LEARNING DEMO: YouTrack MCP Tool Discovery")
    print("=" * 70)
    
    show_create_issue_learning()
    show_example_tool_call()
    show_model_learning_process()
    show_agentic_follow_up() 
    show_configuration_awareness()
    
    print("\n" + "=" * 70)
    print("🎉 RESULT: Model learns to use YouTrack MCP intelligently!")
    print("=" * 70)
    print("""
KEY TAKEAWAYS FOR THE MODEL:

1. 🔧 TOOLS ARE ENHANCED: Not just basic CRUD operations
2. 🧠 CONTEXT MATTERS: System analyzes content for suggestions  
3. 🔗 WORKFLOWS ARE GUIDED: Clear next steps provided
4. ⚡ ACTIONS ARE READY: Exact MCP calls to execute
5. 📚 LEARNING IS BUILT-IN: Educational reasoning included

The model learns to be an effective YouTrack agent, not just a tool user!
""")