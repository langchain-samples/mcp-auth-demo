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

from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessagesState
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode

# Load environment variables
load_dotenv()

async def get_mcp_tools(user: Dict[str, Any]) -> List[Tool]:
    """
    Create MCP tools with user authentication.
    
    This is where the authentication magic happens - we use the user's
    GitHub token to create authenticated MCP tools.
    """
    if not user or not user.get("github_token"):
        print("Warning: No GitHub token found for user")
        return []
    
    try:
        # Create MCP client with user's GitHub token
        github_url = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")
        print(f"Attempting to connect to GitHub MCP at: {github_url}")
        
        mcp_client = MultiServerMCPClient({
            "github": {
                "transport": "streamable_http", 
                "url": github_url,
                "authorization_token": f"Bearer {user['github_token']}"
            }
        })
        
        # Get tools from MCP server and convert to LangChain tools
        print("Getting tools from MCP server...")
        mcp_tools = await mcp_client.get_tools()
        tools = []
        
        for tool_info in mcp_tools:
            tool_name = tool_info["name"]
            tool = mcp_client.get_tool(tool_name)
            tools.append(tool)
        
        print(f"✅ Successfully loaded {len(tools)} real MCP tools from GitHub")
        return tools
        
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("ℹ️  GitHub Copilot MCP access not available (requires Copilot subscription)")
        else:
            print(f"Warning: Could not connect to MCP server: {e}")
        
        print("🔄 Falling back to no tools...")
        return []


async def agent_node(state: MessagesState, config: Dict[str, Any]) -> MessagesState:
    """
    Main agent node that handles user requests with MCP tools.
    """
    # Get user from LangGraph auth
    user = config.get("configurable", {}).get("langgraph_auth_user")
    user_email = user.get('email', 'Unknown') if user else 'Not authenticated'
    
    # Get MCP tools for this user
    tools = await get_mcp_tools(user)
    
    # Create LLM with tools bound
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    if tools:
        llm = llm.bind_tools(tools)
    
    # Create system message
    system_message = f"""You are a helpful GitHub assistant with access to GitHub tools via MCP.

User Information:
- Email: {user_email}
- Authentication: {'✅ Authenticated' if user and user.get('github_token') else '❌ Not authenticated'}
- Available tools: {len(tools)}

You can help with GitHub-related tasks. When appropriate, use the available tools to get real information."""

    # Prepare messages with system message
    messages = [SystemMessage(content=system_message)] + state["messages"]
    
    # Call LLM
    response = await llm.ainvoke(messages)
    
    return {"messages": state["messages"] + [response]}

def should_continue(state: MessagesState) -> str:
    """Check if we should continue to tools or end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

def create_graph() -> StateGraph:
    """Create the agent graph following LangGraph best practices."""
    
    # Create the graph
    graph = StateGraph(MessagesState)
    
    # Add nodes
    graph.add_node("agent", agent_node)
    
    # Create a dynamic tool node
    async def tool_node(state: MessagesState, config: Dict[str, Any]) -> MessagesState:
        user = config.get("configurable", {}).get("langgraph_auth_user")
        tools = await get_mcp_tools(user)
        
        if not tools:
            return {"messages": state["messages"] + [AIMessage(content="No tools available.")]}
        
        tool_node_instance = ToolNode(tools)
        return await tool_node_instance.ainvoke(state, config)
    
    graph.add_node("tools", tool_node)
    
    # Set entry point
    graph.set_entry_point("agent")
    
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