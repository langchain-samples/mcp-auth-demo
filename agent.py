"""
Clean LangGraph Agent with MCP Authentication

This demonstrates proper LangGraph patterns with user-scoped MCP authentication.
Following LangGraph best practices for simplicity and maintainability.

Key concepts:
1. Access user via config["configurable"]["langgraph_auth_user"]
2. Create MCP tools with user authentication
3. Use simple, clean LangGraph patterns
4. Proper separation of concerns
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import json
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessagesState
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AgentState(MessagesState):
    """
    State for the agent. Add tools to the state so we know which tools are available to the agent.
    """
    tools: List[Tool]

async def get_mcp_tools_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """
    Node to create MCP tools with user authentication.
    
    This is where the authentication magic happens - we use the user's
    GitHub token to create authenticated MCP tools.
    """
    print("\n" + "="*50)
    print("🔧 GET_MCP_TOOLS_NODE: Starting tool initialization")
    print("="*50)
    
    # Stage 1: Extract user from config
    user = config.get("configurable", {}).get("langgraph_auth_user")
    print(f"📋 Stage 1 - User Auth Check:")
    print(f"   Config keys: {list(config.keys())}")
    print(f"   Configurable keys: {list(config.get('configurable', {}).keys())}")
    print(f"   User object: {user}")
    
    if not user:
        print("❌ ERROR: No user found in config")
        return {"tools": []}
    
    # Stage 2: Check GitHub token
    github_token = user.get("github_token")
    user_email = user.get("email", "Unknown")
    user_id = user.get("identity", "Unknown")
    
    print(f"📋 Stage 2 - Token Check:")
    print(f"   User email: {user_email}")
    print(f"   User ID: {user_id}")
    print(f"   GitHub token present: {bool(github_token)}")
    if github_token:
        print(f"   Token prefix: {github_token[:10]}...")
    
    if not github_token:
        print("❌ ERROR: No GitHub token found for user")
        return {"tools": []}
    
    # Stage 3: Initialize MCP client
    try:
        github_url = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")
        print(f"📋 Stage 3 - MCP Client Initialization:")
        print(f"   GitHub MCP URL: {github_url}")
        
        # Use the official pattern from LangGraph docs
        mcp_client = MultiServerMCPClient({
            "github": {
                "transport": "streamable_http", 
                "url": github_url,
                "headers": {
                    "Authorization": f"Bearer {github_token}"
                }
            }
        })
        print(f"   ✅ MCP client created successfully")
        
        # Stage 4: Get tools from MCP server (No sessions - per LangGraph docs)
        print(f"📋 Stage 4 - Tool Retrieval (Stateless):")
        print(f"   📋 Note: Using stateless approach per LangGraph documentation")
        
        mcp_tools = await mcp_client.get_tools()
        print(f"   Raw MCP tools received: {len(mcp_tools)}")
        
        # Tools are already StructuredTool objects - no additional processing needed
        tools = mcp_tools
        
        if tools:
            print(f"   📋 Available tools:")
            for i, tool in enumerate(tools[:5]):  # Show first 5 tools
                tool_name = getattr(tool, 'name', f'Tool_{i}')
                print(f"     {i+1}. {tool_name}")
            if len(tools) > 5:
                print(f"     ... and {len(tools) - 5} more tools")
        
        print(f"\n✅ SUCCESS: Loaded {len(tools)} MCP tools from GitHub")
        print("="*50)
        return {"tools": tools}
        
    except Exception as e:
        error_msg = str(e)
        print(f"📋 Stage 3-5 - ERROR occurred:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {error_msg}")
        
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("   ℹ️  GitHub Copilot MCP access not available (requires Copilot subscription)")
        else:
            print(f"   ❌ MCP connection failed: {e}")
        
        print("🔄 Falling back to no tools...")
        print("="*50)
        return {"tools": []}


async def agent_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """
    Main agent node that handles user requests with MCP tools.
    """
    print("\n" + "="*50)
    print("🤖 AGENT_NODE: Processing user request")
    print("="*50)
    
    # Get user from LangGraph auth
    user = config.get("configurable", {}).get("langgraph_auth_user")
    user_email = user.get('email', 'Unknown') if user else 'Not authenticated'
    
    # Get MCP tools for this user
    tools = state.get("tools", [])
    
    print(f"📋 Agent State:")
    print(f"   User email: {user_email}")
    print(f"   Tools available: {len(tools)}")
    print(f"   Tool names: {[getattr(t, 'name', 'Unknown') for t in tools]}")
    
    # Create LLM with tools bound
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    if tools:
        llm = llm.bind_tools(tools)
        print(f"   ✅ LLM bound with {len(tools)} tools")
    else:
        print(f"   ⚠️  No tools available - LLM will run without tools")
    
    # Create system message
    system_message = f"""You are a helpful GitHub assistant with access to GitHub tools via MCP.

User Information:
- Email: {user_email}
- Authentication: {'✅ Authenticated' if user and user.get('github_token') else '❌ Not authenticated'}
- Available tools: {len(tools)}

You can help with GitHub-related tasks. When appropriate, use the available tools to get real information."""

    # Prepare messages with system message
    messages = [SystemMessage(content=system_message)] + state["messages"]
    
    print(f"📋 Calling LLM with {len(messages)} messages")
    
    # Call LLM
    response = await llm.ainvoke(messages)
    
    print(f"📋 LLM Response:")
    print(f"   Response type: {type(response)}")
    print(f"   Has tool calls: {hasattr(response, 'tool_calls') and bool(response.tool_calls)}")
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"   Tool calls: {len(response.tool_calls)}")
        for i, tc in enumerate(response.tool_calls):
            print(f"     {i+1}. {tc.get('name', 'Unknown')}")
    
    print("="*50)
    return {"messages": state["messages"] + [response]}

def should_continue(state: AgentState) -> str:
    """Check if we should continue to tools or end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

def create_graph() -> StateGraph:
    """Create the agent graph following LangGraph best practices."""
    
    # Create the graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("get_mcp_tools", get_mcp_tools_node)  # First get tools
    graph.add_node("agent", agent_node)  # Then run agent
    
    # Create a dynamic tool node
    async def tool_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
        print("\n" + "="*50)
        print("🔧 TOOL_NODE: Executing tools")
        print("="*50)
        
        tools = state.get("tools", [])
        
        print(f"📋 Tools available: {len(tools)}")
        
        if not tools:
            print("❌ No tools available in state")
            return {"messages": state["messages"] + [AIMessage(content="No tools available.")]}
        
        print(f"✅ Executing tools with ToolNode")
        tool_node_instance = ToolNode(tools)
        result = await tool_node_instance.ainvoke(state, config)
        
        print(f"📋 Tool execution completed")
        print("="*50)
        return result
    
    graph.add_node("tools", tool_node)
    
    # Set entry point to get tools first
    graph.set_entry_point("get_mcp_tools")
    
    # Flow: get_mcp_tools -> agent -> (tools if needed) -> agent
    graph.add_edge("get_mcp_tools", "agent")
    
    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", END: END}
    )
    
    # Tools go back to agent
    graph.add_edge("tools", "agent")
    
    return graph.compile()

# Create the compiled graph for LangGraph Platform
graph = create_graph()

if __name__ == "__main__":
    print("🔐 Clean MCP Authentication Agent")
    print("This agent demonstrates proper LangGraph patterns with user auth")
    print("Deploy to LangGraph Platform with: langgraph deploy")