"""
LangGraph Platform authentication handler for MCP server integration.

This module demonstrates best practices for authenticating users and 
propagating their credentials to MCP servers.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
import requests
from datetime import datetime, timedelta

from langgraph_sdk import Auth
from secret_management import SecretStore, UserTokens

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize authentication
auth = Auth()

# Initialize secret store
secret_store = SecretStore(
    url=os.getenv("SECRET_STORE_URL"),
    token=os.getenv("SECRET_STORE_TOKEN")
)


def is_valid_langsmith_key(api_key: str) -> bool:
    """
    Validate API key against LangSmith API.
    
    Args:
        api_key: The LangSmith API key to validate
        
    Returns:
        True if key is valid, False otherwise
    """
    try:
        resp = requests.get(
            "https://api.smith.langchain.com/v1/whoami",
            headers={"x-api-key": api_key},
            timeout=5,
        )
        if resp.status_code == 200:
            logger.info("LangSmith API key validation successful")
            return True
        else:
            logger.warning(f"LangSmith API key validation failed: {resp.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Error validating LangSmith API key: {e}")
        return False


async def fetch_user_tokens(api_key: str) -> Optional[UserTokens]:
    """
    Fetch user-specific tokens from secret store.
    
    Args:
        api_key: User's LangSmith API key
        
    Returns:
        UserTokens object with all user credentials, or None if not found
    """
    try:
        # Get user identity from LangSmith
        user_info = await get_user_info_from_langsmith(api_key)
        if not user_info:
            return None
        
        # Fetch tokens from secret store
        tokens = await secret_store.get_user_tokens(user_info["user_id"])
        
        if tokens:
            logger.info(f"Successfully fetched tokens for user {user_info['user_id']}")
        else:
            logger.warning(f"No tokens found for user {user_info['user_id']}")
            
        return tokens
        
    except Exception as e:
        logger.error(f"Error fetching user tokens: {e}")
        return None


async def get_user_info_from_langsmith(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Get user information from LangSmith API.
    
    Args:
        api_key: LangSmith API key
        
    Returns:
        User information dictionary or None
    """
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None,
            lambda: requests.get(
                "https://api.smith.langchain.com/v1/whoami",
                headers={"x-api-key": api_key},
                timeout=5,
            )
        )
        
        if resp.status_code == 200:
            user_data = resp.json()
            return {
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "org_id": user_data.get("organization", {}).get("id"),
                "workspace_id": user_data.get("workspace", {}).get("id")
            }
        else:
            logger.error(f"Failed to get user info: {resp.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting user info from LangSmith: {e}")
        return None


@auth.authenticate
async def authenticate(headers: Dict[str, str]) -> Auth.types.MinimalUserDict:
    """
    Main authentication handler for LangGraph Platform.
    
    This function:
    1. Validates the LangSmith API key
    2. Fetches user information
    3. Retrieves user-specific tokens from secret store
    4. Returns user object with all necessary credentials
    
    Args:
        headers: Request headers containing authentication info
        
    Returns:
        MinimalUserDict with user identity and custom fields
        
    Raises:
        HTTPException: If authentication fails
    """
    logger.info("Starting authentication process")
    
    # Extract API key
    api_key = headers.get("x-api-key")
    if not api_key:
        logger.warning("No API key provided in request")
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Missing x-api-key header"
        )
    
    # Validate API key
    if not is_valid_langsmith_key(api_key):
        logger.warning("Invalid API key provided")
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Invalid API key"
        )
    
    # Get user information
    user_info = await get_user_info_from_langsmith(api_key)
    if not user_info:
        logger.error("Failed to get user information")
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Unable to retrieve user information"
        )
    
    # Fetch user tokens
    user_tokens = await fetch_user_tokens(api_key)
    if not user_tokens:
        logger.warning(f"No tokens found for user {user_info['user_id']}")
        # Still allow authentication but with limited capabilities
        user_tokens = UserTokens()
    
    # Build user object for LangGraph Platform
    user_object = {
        "identity": user_info["user_id"],  # Required field
        "api_key": api_key,
        "email": user_info["email"],
        "org_id": user_info["org_id"],
        "workspace_id": user_info["workspace_id"],
        
        # MCP server credentials
        "github_token": user_tokens.github_token,
        "jira_token": user_tokens.jira_token,
        "slack_token": user_tokens.slack_token,
        "confluence_token": user_tokens.confluence_token,
        
        # Additional metadata
        "authenticated_at": datetime.utcnow().isoformat(),
        "token_expiry": user_tokens.expiry_time.isoformat() if user_tokens.expiry_time else None
    }
    
    logger.info(f"Authentication successful for user {user_info['user_id']}")
    return user_object


@auth.on
async def owner_only(ctx, value):
    """
    Resource-level access control.
    
    Ensures resources are tagged with owner information
    for proper access control.
    """
    meta = value.setdefault("metadata", {})
    meta["owner"] = ctx.user.identity
    meta["org_id"] = ctx.user.get("org_id")
    meta["created_at"] = datetime.utcnow().isoformat()
    
    return {"owner": ctx.user.identity, "org_id": ctx.user.get("org_id")}


async def refresh_user_tokens_if_needed(user_identity: str) -> Optional[UserTokens]:
    """
    Refresh user tokens if they're close to expiry.
    
    Args:
        user_identity: User's identity
        
    Returns:
        Refreshed tokens or None if refresh failed
    """
    try:
        current_tokens = await secret_store.get_user_tokens(user_identity)
        if not current_tokens or not current_tokens.expiry_time:
            return current_tokens
        
        # Check if tokens expire within 10 minutes
        if current_tokens.expiry_time < datetime.utcnow() + timedelta(minutes=10):
            logger.info(f"Refreshing tokens for user {user_identity}")
            refreshed_tokens = await secret_store.refresh_user_tokens(user_identity)
            if refreshed_tokens:
                logger.info(f"Successfully refreshed tokens for user {user_identity}")
                return refreshed_tokens
            else:
                logger.warning(f"Failed to refresh tokens for user {user_identity}")
        
        return current_tokens
        
    except Exception as e:
        logger.error(f"Error refreshing tokens for user {user_identity}: {e}")
        return None


def validate_user_permissions(user: Dict[str, Any], required_service: str) -> bool:
    """
    Validate that user has access to required service.
    
    Args:
        user: User object from authentication
        required_service: Service name (e.g., 'github', 'jira')
        
    Returns:
        True if user has access, False otherwise
    """
    service_token_map = {
        "github": "github_token",
        "jira": "jira_token", 
        "slack": "slack_token",
        "confluence": "confluence_token"
    }
    
    token_field = service_token_map.get(required_service)
    if not token_field:
        logger.warning(f"Unknown service: {required_service}")
        return False
    
    has_token = bool(user.get(token_field))
    if not has_token:
        logger.warning(f"User {user.get('identity')} lacks {required_service} token")
    
    return has_token


# Error handlers
@auth.exception_handler(Auth.exceptions.HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions from authentication."""
    logger.error(f"Authentication error: {exc.detail}")
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.utcnow().isoformat()
    }


@auth.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions from authentication."""
    logger.error(f"Unexpected authentication error: {exc}")
    return {
        "error": "Internal authentication error",
        "status_code": 500,
        "timestamp": datetime.utcnow().isoformat()
    }


# Export authentication instance
__all__ = ["auth", "validate_user_permissions", "refresh_user_tokens_if_needed"]