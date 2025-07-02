"""
Agent Authentication Handler

This module implements Supabase authentication + secret storage
following the LangGraph documentation patterns:
https://langchain-ai.github.io/langgraph/how-tos/auth/

Key concepts demonstrated:
1. Supabase token validation via httpx (async)
2. Supabase Vault for secret storage (with fallback options)
3. User-specific GitHub token retrieval
4. Proper error handling and security

Secret Storage Options:
- Supabase Vault (default, alpha feature)
- AWS Secrets Manager (fallback)
- Environment variables (development)
"""

import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langgraph_sdk import Auth

# Load environment variables
load_dotenv()

# Initialize auth handler (following documentation pattern exactly)
auth = Auth()

# Get Supabase configuration from environment
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Helper function to get github user token
async def get_user_github_token(user_id: str) -> Optional[str]:
    """
    Get user's GitHub token from secret storage.
    
    Tries multiple storage options in order:
    1. Supabase Vault (alpha feature)
    2. AWS Secrets Manager (if configured)
    3. Environment variable (development only)
    """
    
    # Option 1: Try Supabase Vault (alpha feature)
    try:
        # Use httpx for async Vault access
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/vault_read_secret",
                json={'secret_name': f'github_pat_{user_id}'},
                headers={
                    "apiKey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data
            
    except Exception as e:
        print(f"Supabase Vault not available: {e}")
    
    # Option 2: Environment variable (development only)
    env_token = os.getenv("GITHUB_PAT")
    if env_token:
        print(f"Warning: Using shared GitHub token from environment for user {user_id}")
        return env_token
    
    return None

# Function to Authenticate user with supabase
@auth.authenticate
async def get_current_user(authorization: str | None):
    """
    Custom authentication handler using Supabase.
    
    This follows the exact pattern from the LangGraph docs:
    - Takes authorization header as string parameter
    - Returns MinimalUserDict with user information
    """
    if not authorization:
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Missing authorization header"
        )
    
    # Parse the authorization header
    try:
        scheme, token = authorization.split()
        assert scheme.lower() == "bearer"
    except Exception:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    
    # Validate token with Supabase using httpx (async)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": authorization,
                    "apiKey": SUPABASE_SERVICE_KEY,
                },
            )
            if response.status_code != 200:
                raise Auth.exceptions.HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            
            user = response.json()
            
    except httpx.HTTPError as e:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )
    
    # Get user's GitHub token (if available)
    github_token = await get_user_github_token(user["id"])
    
    # Return MinimalUserDict as required by LangGraph auth API
    return {
        "identity": user["id"],  # Required: unique user identifier
        "is_authenticated": True,  # Optional but good practice
        "email": user.get("email"),  # Add email if available
        "role": user.get("user_metadata", {}).get("role", "user"),
        "github_token": github_token  # Add GitHub token for the agent to use
    }


# Authorization handler - REQUIRED when disable_studio_auth is true
@auth.on
async def add_owner(ctx: Auth.types.AuthContext, value: dict) -> dict:
    """
    Authorization handler for all resources (assistants, threads, runs, etc).
    
    When disable_studio_auth is true, this handler is REQUIRED to allow
    LangGraph Studio to access internal resources like assistants.
    """
    # Debug logging - use correct AuthContext attributes
    print(f"Auth handler called for resource: {ctx.resource}, action: {ctx.action}")
    print(f"User identity: {ctx.user.identity}")
    print(f"Value type: {type(value)}")
    
    # For assistants endpoint, we may not have a value dict
    # or it might be None for list operations
    if value is None:
        # For list/search operations, just return filter
        return {"owner": ctx.user.identity}
    
    # Add owner metadata to new resources
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    
    # Return filter to restrict access to user's own resources
    # This ensures users can only see/access their own data
    return filters


# Export the auth object for use in langgraph.json
__all__ = ["auth"]