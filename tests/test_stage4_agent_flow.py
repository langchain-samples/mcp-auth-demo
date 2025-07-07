#!/usr/bin/env python3
"""
Test Stage 4: Complete Agent Flow

This test runs the complete agent flow using the LangGraph client,
verifying that all components work together with proper logging.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv
from langgraph_sdk import get_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

email1 = "user1@example.com"
password = "testpass123"

async def login(email: str, password: str):
    """Get an access token for an existing user."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={
                "email": email,
                "password": password
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
        )
        assert response.status_code == 200
        return response.json()["access_token"]

async def test_agent_flow():
    """Test complete agent flow"""
    
    print("🤖 Testing complete agent flow with improved logging")
    print("=" * 60)
    
    # Step 1: Generate user token
    print("📋 Step 1: Generating User Token")
    
    try:
        print(f"   Logging in as: {email1}")
        
        # Use the working login method from test.ipynb
        user_token = await login(email1, password)
        print(f"   ✅ User token generated successfully")
        print(f"   Token prefix: {user_token[:20]}...")
                
    except Exception as e:
        print(f"   ❌ Error generating user token: {e}")
        return False
    
    # Step 2: Create LangGraph client
    print("\n📋 Step 2: Creating LangGraph Client")
    
    try:
        client = get_client(
            url="http://localhost:2024", 
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print(f"   ✅ LangGraph client created successfully")
        
    except Exception as e:
        print(f"   ❌ Error creating LangGraph client: {e}")
        return False
    
    # Step 3: Create thread
    print("\n📋 Step 3: Creating Thread")
    
    try:
        thread = await client.threads.create()
        thread_id = thread['thread_id']
        print(f"   ✅ Thread created successfully: {thread_id}")
        
    except Exception as e:
        print(f"   ❌ Error creating thread: {e}")
        return False
    
    # Step 4: Test agent with GitHub-specific query
    print("\n📋 Step 4: Testing Agent with GitHub Query")
    
    try:
        # Use a GitHub-specific question to trigger tool usage
        input_data = {
            "messages": [
                {
                    "role": "human", 
                    "content": "What's my most recent GitHub repository? Please use the GitHub tools to check."
                }
            ]
        }
        
        print(f"   Query: {input_data['messages'][0]['content']}")
        print(f"   🔧 Starting agent with detailed logging...")
        print(f"   Expected to see logging for:")
        print(f"     1. get_mcp_tools_node execution")
        print(f"     2. GitHub PAT retrieval from vault")
        print(f"     3. MCP server connection")
        print(f"     4. Tool initialization")
        print(f"     5. Agent decision making")
        
        # Track the flow
        nodes_executed = []
        tool_calls_made = []
        responses_received = []
        
        # Stream the response
        async for event in client.runs.stream(
            thread_id=thread_id,
            assistant_id="agent",
            input=input_data,
            stream_mode="updates",
        ):
            if event.event == "metadata":
                run_id = event.data.get('run_id', 'Unknown')
                print(f"   📋 Run started (ID: {run_id[:8]}...)")
                
            elif event.event == "updates":
                # Track different node executions
                for node_name, node_data in event.data.items():
                    if node_name not in nodes_executed:
                        nodes_executed.append(node_name)
                        print(f"   🔧 Node executed: {node_name}")
                
                # Handle get_mcp_tools updates
                if "get_mcp_tools" in event.data:
                    print(f"   🔧 MCP Tools Node executed - Check server logs for detailed output")
                    
                # Handle agent updates
                elif "agent" in event.data:
                    for msg in event.data["agent"]["messages"]:
                        if msg["type"] == "ai":
                            # Check for tool calls
                            if msg.get("tool_calls"):
                                for tool_call in msg["tool_calls"]:
                                    tool_name = tool_call.get("name", "Unknown")
                                    tool_calls_made.append(tool_name)
                                    print(f"   🔧 Agent calling tool: {tool_name}")
                                    
                                    if "args" in tool_call and tool_call["args"]:
                                        args_str = str(tool_call["args"])
                                        if len(args_str) > 100:
                                            args_str = args_str[:100] + "..."
                                        print(f"      └─ Args: {args_str}")
                            
                            # Check for response content
                            elif msg.get("content") and msg["content"].strip():
                                responses_received.append(msg["content"])
                                print(f"   💬 Agent Response:")
                                content = msg["content"]
                                # Show first 200 chars of response
                                if len(content) > 200:
                                    print(f"      {content[:200]}...")
                                else:
                                    print(f"      {content}")
                
                # Handle tool execution updates
                elif "tools" in event.data:
                    for msg in event.data["tools"]["messages"]:
                        if msg["type"] == "tool":
                            tool_name = msg.get("name", "Unknown tool")
                            print(f"   ✅ Tool '{tool_name}' executed")
                            
                            content = msg.get("content", "")
                            if content:
                                # Show brief summary
                                if len(content) > 150:
                                    print(f"      └─ Result: {content[:150]}...")
                                else:
                                    print(f"      └─ Result: {content}")
        
        print(f"   🎉 Agent execution completed!")
        
    except Exception as e:
        print(f"   ❌ Error during agent execution: {e}")
        return False
    
    # Step 5: Summary
    print("\n📊 Execution Summary:")
    print(f"   Nodes executed: {', '.join(nodes_executed)}")
    print(f"   Tool calls made: {len(tool_calls_made)}")
    if tool_calls_made:
        print(f"   Tools called: {', '.join(tool_calls_made)}")
    print(f"   Responses received: {len(responses_received)}")
    
    # Check if we got the expected flow
    expected_nodes = ["get_mcp_tools", "agent"]
    success = True
    
    for expected_node in expected_nodes:
        if expected_node in nodes_executed:
            print(f"   ✅ {expected_node} executed successfully")
        else:
            print(f"   ❌ {expected_node} was not executed")
            success = False
    
    if success:
        print(f"   🎉 All expected nodes executed!")
    else:
        print(f"   ⚠️  Some expected nodes were not executed")
    
    print(f"\n💡 Additional Notes:")
    print(f"   • Check the LangGraph server logs for detailed MCP connection output")
    print(f"   • The get_mcp_tools_node should show extensive logging")
    print(f"   • Look for GitHub PAT retrieval and MCP server connection details")
    
    return success

def main():
    """Run the agent flow test"""
    try:
        success = asyncio.run(test_agent_flow())
        return success
    except Exception as e:
        print(f"❌ Fatal error during agent flow test: {e}")
        return False
    finally:
        print("=" * 60)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)