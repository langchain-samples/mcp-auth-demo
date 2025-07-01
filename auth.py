"""
Agent Authentication Handler

This module implements the exact authentication patterns from the LangGraph documentation:
https://langchain-ai.github.io/langgraph/how-tos/auth/

Key concepts demonstrated:
1. Custom @auth.authenticate handler
2. Populating langgraph_auth_user object
3. Fetching user tokens from secret store
4. Proper error handling
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from langgraph_sdk import Auth

# Import secret management
from secret_management import SecretStore, UserTokens

# Load environment variables
load_dotenv()

# Initialize auth handler (following documentation pattern exactly)
auth = Auth()

def is_valid_key(api_key: str) -> bool:
    """
    Validate API key - simplified for demo.
    
    In production, validate against your auth provider.
    """
    # For demo: accept keys that start with "demo_api_key"
    return api_key and api_key.startswith("demo_api_key")

async def fetch_user_tokens(api_key: str) -> UserTokens:
    """
    Fetch user-specific tokens from your secret store.
    
    This is where you'd integrate with your actual secret management system.
    """
    store = SecretStore("demo_store")
    
    # For demo: map API keys to demo users
    user_id_map = {
        "demo_api_key_123": "user_123",
        "demo_api_key_456": "user_456", 
        "demo_api_key_789": "user_789"
    }
    
    user_id = user_id_map.get(api_key, "user_123")
    
    # Get GitHub token from environment for demo
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        raise Exception("No GitHub token found in environment")
    
    # In production, you'd fetch user-specific tokens from your secret store
    return UserTokens(
        github_token=github_token,
        refresh_token=f"refresh_{user_id}"
    )

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    """
    Custom authentication handler following LangGraph documentation.
    
    This is the exact pattern from the docs:
    https://langchain-ai.github.io/langgraph/how-tos/auth/
    
    The returned object populates config["configurable"]["langgraph_auth_user"]
    """
    api_key = headers.get("x-api-key")
    if not api_key or not is_valid_key(api_key):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid API key")
    
    # Fetch user-specific tokens from your secret store  
    user_tokens = await fetch_user_tokens(api_key)

    return {
        "identity": api_key,  # Required field
        "github_token": user_tokens.github_token,
        "email": f"demo@example.com",
        "org_id": "demo_org"
        # ... custom fields/secrets here
    }

# Export the auth object for use in langgraph.json
__all__ = ["auth"]