"""
Quick start script for MCP Authentication Demo.

This script demonstrates the key concepts customer needs for
authenticating with MCP servers in LangGraph Platform.
"""

import asyncio
import os
from typing import Dict, Any
from langchain_mcp_adapters.client import MultiServerMCPClient


def demonstrate_basic_pattern():
    """
    Demonstrate the basic pattern for MCP authentication.
    
    This is the core pattern customer should implement:
    1. Get user credentials from LangGraph config
    2. Create MCP client with proper headers
    3. Use the client in graph nodes
    """
    
    print("🔑 MCP Authentication Pattern")
    print("=" * 50)
    
    # PATTERN 1: Access user auth in graph node
    print("\n1. Access user authentication in your graph node:")
    print("""
def my_node(state, config):
    # Get authenticated user from LangGraph Platform config
    user = config["configurable"].get("langgraph_auth_user")
    
    # Access user's service tokens
    github_token = user["github_token"]
    jira_token = user["jira_token"]
    user_email = user["email"]
    org_id = user["org_id"]
""")
    
    # PATTERN 2: Create MCP client with auth headers
    print("\n2. Create authenticated MCP client:")
    print("""
def my_node(state, config):
    user = config["configurable"].get("langgraph_auth_user")
    
    client = MultiServerMCPClient({
        "github": {
            "transport": "streamable_http",
            "url": "https://github-mcp-server/mcp", 
            "headers": {
                "Authorization": f"Bearer {user['github_token']}"
            }
        },
        "jira": {
            "transport": "streamable_http",
            "url": "https://jira-mcp-server/mcp",
            "headers": {
                "Authorization": f"Bearer {user['jira_token']}"
            }
        }
    })
    
    # Use the client
    github_tools = client.get_tools("github")
    result = await client.call_tool("github", "get_repo", {"repo": "myorg/myrepo"})
""")
    
    # PATTERN 3: Authentication handler
    print("\n3. Custom authentication handler (populate user object):")
    print("""
from langgraph_sdk import Auth

auth = Auth()

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    api_key = headers.get("x-api-key")
    if not api_key or not is_valid_key(api_key):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid API key")
    
    # Fetch user-specific tokens from your secret store
    user_tokens = await fetch_user_tokens(api_key)
    
    return {
        "identity": api_key,  # Required field
        "github_token": user_tokens.github_token,
        "jira_token": user_tokens.jira_token,
        "email": user_tokens.email,
        "org_id": user_tokens.org_id
    }
""")


async def demonstrate_working_example():
    """
    Demonstrate a working example (simulated).
    """
    
    print("\n🚀 Working Example")
    print("=" * 50)
    
    # Simulate the config that LangGraph Platform provides
    mock_config = {
        "configurable": {
            "langgraph_auth_user": {
                "identity": "user_123",
                "email": "john@att.com",
                "org_id": "att_org",
                "github_token": "ghp_ATT_github_token_123",
                "jira_token": "ATT_jira_token_456"
            }
        }
    }
    
    print("✅ User authenticated with tokens for GitHub and Jira")
    
    # Simulate creating MCP client (would work with real servers)
    print("\n📡 Creating MCP clients...")
    
    # This would be the actual implementation:
    server_config = {
        "github": {
            "transport": "streamable_http",
            "url": "https://att-github-mcp-server/mcp",
            "headers": {
                "Authorization": f"Bearer {mock_config['configurable']['langgraph_auth_user']['github_token']}",
                "X-User-Email": mock_config['configurable']['langgraph_auth_user']['email'],
                "X-Org-ID": mock_config['configurable']['langgraph_auth_user']['org_id']
            }
        },
        "jira": {
            "transport": "streamable_http",
            "url": "https://att-jira-mcp-server/mcp",
            "headers": {
                "Authorization": f"Bearer {mock_config['configurable']['langgraph_auth_user']['jira_token']}",
                "X-User-Email": mock_config['configurable']['langgraph_auth_user']['email'],
                "X-Org-ID": mock_config['configurable']['langgraph_auth_user']['org_id']
            }
        }
    }
    
    print(f"✅ GitHub MCP: {server_config['github']['url']}")
    print(f"✅ Jira MCP: {server_config['jira']['url']}")
    
    # Simulate client usage
    print("\n🔧 Using MCP client in graph node...")
    
    # This demonstrates the pattern customer should use:
    async def att_graph_node(state, config):
        """Example customer graph node using MCP with authentication."""
        
        # Get user from LangGraph Platform config
        user = config["configurable"].get("langgraph_auth_user")
        
        if not user:
            return {"error": "No authenticated user"}
        
        # Create authenticated MCP client
        client = MultiServerMCPClient(server_config)
        
        # Use GitHub MCP server
        try:
            repos = await client.call_tool("github", "list_repos", {
                "org": user["org_id"],
                "type": "private"
            })
            
            # Use Jira MCP server  
            issues = await client.call_tool("jira", "search_issues", {
                "jql": f"assignee = '{user['email']}' AND status = 'In Progress'"
            })
            
            return {
                "github_repos": len(repos),
                "assigned_issues": len(issues),
                "user": user["email"]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # Simulate calling the node
    result = await att_graph_node({}, mock_config)
    print(f"📊 Node result: {result}")


def demonstrate_transport_matrix():
    """Show which transports support authentication headers."""
    
    print("\n📋 MCP Transport Authentication Support")
    print("=" * 50)
    
    transports = {
        "streamable_http": {
            "supports_headers": "✅ YES",
            "use_case": "Most web APIs (GitHub, Jira, Slack)",
            "example": 'headers: {"Authorization": "Bearer token"}'
        },
        "sse": {
            "supports_headers": "✅ YES", 
            "use_case": "Server-sent events, real-time APIs",
            "example": 'headers: {"Authorization": "Bearer token"}'
        },
        "stdio": {
            "supports_headers": "❌ NO",
            "use_case": "Local processes, command-line tools",
            "example": 'env: {"AUTH_TOKEN": "token"}'
        },
        "grpc": {
            "supports_headers": "❌ NO (use metadata)",
            "use_case": "High-performance internal services",
            "example": 'metadata: {"authorization": "bearer token"}'
        }
    }
    
    for transport, info in transports.items():
        print(f"\n{transport.upper()}:")
        print(f"  Headers: {info['supports_headers']}")
        print(f"  Use case: {info['use_case']}")
        print(f"  Auth: {info['example']}")


def show_security_best_practices():
    """Show security best practices for customer."""
    
    print("\n🛡️ Security Best Practices for customer")
    print("=" * 50)
    
    practices = [
        "✅ Store tokens in secure secret management system (not in graph state)",
        "✅ Use HTTPS for all MCP server communication", 
        "✅ Validate tokens before use in authentication handler",
        "✅ Implement token refresh logic for OAuth tokens",
        "✅ Log access patterns (but never log actual tokens)",
        "✅ Use short-lived tokens when possible",
        "✅ Implement proper error handling for expired/invalid tokens",
        "✅ Add rate limiting per user/organization",
        "✅ Use environment-specific configurations",
        "✅ Audit MCP server access regularly"
    ]
    
    for practice in practices:
        print(f"  {practice}")
    
    print("\n❌ What NOT to do:")
    dont_practices = [
        "❌ Store tokens in graph state (gets persisted to database)",
        "❌ Pass tokens as parameters between nodes",
        "❌ Use HITL flows to collect tokens (poor UX)",
        "❌ Hardcode tokens in source code",
        "❌ Log sensitive authentication information",
        "❌ Use HTTP for production MCP servers",
        "❌ Share tokens between different organizations"
    ]
    
    for practice in dont_practices:
        print(f"  {practice}")


async def main():
    """Run the quick start demonstration."""
    
    print("🏢 customer MCP Authentication Quick Start")
    print("=" * 60)
    print("This demo shows how to properly authenticate with MCP servers")
    print("in LangGraph Platform without using HITL or graph state.")
    
    # Show the basic patterns
    demonstrate_basic_pattern()
    
    # Show working example
    await demonstrate_working_example()
    
    # Show transport support
    demonstrate_transport_matrix()
    
    # Show security best practices
    show_security_best_practices()
    
    print("\n🎯 Next Steps for customer:")
    print("=" * 30)
    steps = [
        "1. Implement custom @auth.authenticate handler",
        "2. Integrate with your secret management system",
        "3. Configure MCP servers with proper URLs",
        "4. Update graph nodes to use AuthenticatedMCPClient pattern",
        "5. Test with LangGraph Studio locally",
        "6. Deploy to LangGraph Platform with proper environment variables",
        "7. Monitor and audit MCP server access"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print(f"\n📚 For complete examples, see the files in this demo directory.")
    print(f"📧 Questions? Reference the LangGraph authentication docs.")


if __name__ == "__main__":
    asyncio.run(main())