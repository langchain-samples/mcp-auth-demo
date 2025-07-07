#!/usr/bin/env python3
"""
Test Stage 2: Direct MCP Server Connection

This test verifies that we can successfully connect to the GitHub MCP server
using a GitHub Personal Access Token and retrieve tools.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv
from supabase import create_client
from langchain_mcp_adapters.client import MultiServerMCPClient

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

async def test_mcp_connection():
    """Test direct MCP server connection"""
    
    print("🔗 Testing direct MCP server connection")
    print("=" * 60)
    
    # Step 1: Login as user1 and get their user ID
    print("📋 Step 1: Login as user1 and get user ID")
    
    try:
        user1_token = await login(email1, password)
        print(f"✅ User1 logged in successfully")
        print(f"   Token prefix: {user1_token[:20]}...")
        
        # Get user info using the token
        supabase_service = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )
        
        user_response = supabase_service.auth.get_user(user1_token)
        if user_response.user:
            user_id = user_response.user.id
            print(f"✅ Retrieved user ID: {user_id}")
        else:
            print("❌ Could not get user info")
            return False
            
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return False
    
    # Step 2: Get GitHub PAT from Supabase Vault
    print("\n📋 Step 2: Retrieving GitHub PAT from Supabase Vault")
    
    try:
        secret_name = f"github_pat_{user_id}"
        print(f"   Retrieving secret: {secret_name}")
        
        result = supabase_service.postgrest.rpc('vault_read_secret', {
            'secret_name': secret_name
        }).execute()
        
        if not result.data:
            print("   ❌ No GitHub PAT found in vault")
            return False
            
        github_pat = result.data
        print(f"   ✅ GitHub PAT retrieved: {github_pat[:10]}...")
        
    except Exception as e:
        print(f"   ❌ Error retrieving GitHub PAT: {e}")
        return False
    
    # Step 3: Test MCP Client Creation
    print("\n📋 Step 3: Creating MCP Client")
    
    try:
        github_url = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")
        print(f"   GitHub MCP URL: {github_url}")
        
        # Use the official pattern from LangGraph docs
        mcp_client = MultiServerMCPClient({
            "github": {
                "transport": "streamable_http", 
                "url": github_url,
                "headers": {
                    "Authorization": f"Bearer {github_pat}"
                }
            }
        })
        
        print("   ✅ MCP client created successfully")
        
    except Exception as e:
        print(f"   ❌ Error creating MCP client: {e}")
        return False
    
    # Step 4: Test Tool Retrieval (No Sessions - Per LangGraph Docs)
    print("\n📋 Step 4: Testing Tool Retrieval (Stateless - No Sessions)")
    
    try:
        # Per LangGraph docs: "Current implementation does not support sessions"
        # Each MCP request is stateless and independent
        print("   📋 Note: Using stateless approach per LangGraph documentation")
        
        mcp_tools = await mcp_client.get_tools()
        print(f"   ✅ Retrieved {len(mcp_tools)} tools from MCP server")
        
        if mcp_tools:
            print(f"   📋 Available tools:")
            for i, tool in enumerate(mcp_tools):
                # These are already StructuredTool objects, not dictionaries
                tool_name = getattr(tool, 'name', f'Tool_{i}')
                tool_desc = getattr(tool, 'description', 'No description')
                print(f"     {i+1}. {tool_name}")
                print(f"        Description: {tool_desc[:100]}...")
        else:
            print("   ⚠️  No tools available")
        
        # Step 5: Test Individual Tool Retrieval
        print("\n📋 Step 5: Testing Individual Tool Retrieval")
        
        if mcp_tools:
            first_tool = mcp_tools[0]
            first_tool_name = getattr(first_tool, 'name', 'Unknown')
            print(f"   Testing tool: {first_tool_name}")
            
            print(f"   ✅ Tool already available: {type(first_tool).__name__}")
            print(f"   Tool object: {first_tool}")
            
            # Show tool info
            if hasattr(first_tool, 'name'):
                print(f"   Tool name: {first_tool.name}")
            if hasattr(first_tool, 'description'):
                print(f"   Tool description: {first_tool.description[:200]}...")
            if hasattr(first_tool, 'args_schema'):
                print(f"   Tool args schema: {first_tool.args_schema}")
                
        else:
            print("   ⚠️  No tools to test individual retrieval")
        
        # Store tools count for summary
        tools_count = len(mcp_tools)
            
    except Exception as e:
        print(f"   ❌ Error retrieving tools: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False
    
    
    # Step 6: Summary
    print("\n📊 Summary:")
    print(f"   ✅ User login: Success")
    print(f"   ✅ GitHub PAT retrieval: Success")
    print(f"   ✅ MCP client creation: Success")
    print(f"   ✅ Stateless tool retrieval: Success ({tools_count} tools)")
    print(f"   ✅ Individual tool retrieval: Success")
    print(f"   🎉 All MCP connection tests passed!")
    
    return True

def main():
    """Run the MCP connection test"""
    try:
        success = asyncio.run(test_mcp_connection())
        return success
    except Exception as e:
        print(f"❌ Fatal error during MCP connection test: {e}")
        return False
    finally:
        print("=" * 60)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)