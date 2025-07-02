"""
Agent Authentication Handler

This module implements Supabase authentication + secret storage
following the LangGraph documentation patterns:
https://langchain-ai.github.io/langgraph/how-tos/auth/

Key concepts demonstrated:
1. Supabase token validation
2. Supabase Vault for secret storage (with fallback options)
3. User-specific GitHub token retrieval
4. Proper error handling and security

Secret Storage Options:
- Supabase Vault (default, alpha feature)
- AWS Secrets Manager (fallback)
- Environment variables (development)
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langgraph_sdk import Auth
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize auth handler (following documentation pattern exactly)
auth = Auth()

# Initialize Supabase client
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

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
        # Supabase Vault API call
        vault_response = supabase.postgrest.rpc(
            'vault_read_secret',
            {'secret_name': f'user_{user_id}_github_pat'}
        ).execute()
        
        if vault_response.data and len(vault_response.data) > 0:
            return vault_response.data[0].get('decrypted_secret')
            
    except Exception as e:
        print(f"Supabase Vault not available: {e}")
    
    # Option 2: Try AWS Secrets Manager (if configured)
    if all(os.getenv(key) for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']):
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            secrets_client = boto3.client(
                'secretsmanager',
                aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                region_name=os.environ['AWS_REGION']
            )
            
            secret_name = f"{user_id}_github_pat"
            response = secrets_client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"AWS Secrets Manager error: {e}")
        except Exception as e:
            print(f"AWS Secrets Manager not available: {e}")
    
    # Option 3: Environment variable (development only)
    env_token = os.getenv("GITHUB_PAT")
    if env_token:
        print(f"Warning: Using shared GitHub token from environment for user {user_id}")
        return env_token
    
    return None

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    """
    Custom authentication handler using Supabase + flexible secret storage.
    
    This is the exact pattern from the LangGraph docs, adapted for:
    - Supabase user authentication
    - Multiple secret storage options (Supabase Vault, AWS, etc.)
    
    The returned object populates config["configurable"]["langgraph_auth_user"]
    """
    # Extract Supabase token from Authorization header
    auth_header = headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    
    if not token:
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Missing authorization token"
        )
    
    # Validate token with Supabase
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise Auth.exceptions.HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        
        user = user_response.user
        
    except Exception as e:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail=f"Token validation failed: {str(e)}"
        )
    
    # Fetch user's GitHub token from secret storage
    github_token = await get_user_github_token(user.id)
    
    if not github_token:
        print(f"Warning: No GitHub token found for user {user.email} ({user.id})")
    
    # Return user config that will be available in graph nodes
    # This populates config["configurable"]["langgraph_auth_user"]
    return {
        "identity": user.id,  # Required field - using Supabase user UUID
        "email": user.email,
        "github_token": github_token,
        "user_metadata": user.user_metadata or {},
        # Additional fields can be added here
    }

# Export the auth object for use in langgraph.json
__all__ = ["auth"]