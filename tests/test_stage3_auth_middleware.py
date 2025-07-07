#!/usr/bin/env python3
"""
Test Stage 3: Auth Middleware Simulation

This test simulates the authentication middleware functionality,
verifying that we can authenticate users and retrieve their GitHub tokens.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv
from supabase import create_client

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

async def test_auth_middleware():
    """Test auth middleware simulation"""
    
    print("🔐 Testing auth middleware functionality")
    print("=" * 60)
    
    # Step 1: Generate Supabase token for test user
    print("📋 Step 1: Generating Supabase token for test user")
    
    try:
        print(f"   Logging in as: {email1}")
        
        # Use the working login method from test.ipynb
        access_token = await login(email1, password)
        print(f"   ✅ Login successful")
        print(f"   Token prefix: {access_token[:20]}...")
                
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
        return False
    
    # Step 2: Simulate auth middleware token validation
    print("\n📋 Step 2: Simulating Auth Middleware Token Validation")
    
    try:
        # Create service client for token validation
        supabase_service = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )
        
        print(f"   Validating token...")
        
        # This simulates what the auth middleware does
        user_response = supabase_service.auth.get_user(access_token)
        
        if user_response.user:
            user = user_response.user
            print(f"   ✅ Token validation successful")
            print(f"   User ID: {user.id}")
            print(f"   User email: {user.email}")
            print(f"   User created: {user.created_at}")
            
            # Store user info for next step
            user_id = user.id
            user_email = user.email
            
        else:
            print(f"   ❌ Token validation failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error validating token: {e}")
        return False
    
    # Step 3: Simulate GitHub PAT retrieval from vault
    print("\n📋 Step 3: Retrieving GitHub PAT from Supabase Vault")
    
    try:
        secret_name = f"github_pat_{user_id}"
        print(f"   Retrieving secret: {secret_name}")
        
        result = supabase_service.postgrest.rpc('vault_read_secret', {
            'secret_name': secret_name
        }).execute()
        
        if result.data:
            github_pat = result.data
            print(f"   ✅ GitHub PAT retrieved successfully")
            print(f"   Token prefix: {github_pat[:10]}...")
            print(f"   Token length: {len(github_pat)}")
        else:
            print(f"   ❌ Could not retrieve GitHub PAT from vault")
            return False
            
    except Exception as e:
        print(f"   ❌ Error retrieving GitHub PAT: {e}")
        return False
    
    # Step 4: Create user dict for agent (simulating auth middleware output)
    print("\n📋 Step 4: Creating User Dict for Agent")
    
    try:
        user_dict = {
            "identity": user_id,
            "email": user_email,
            "github_token": github_pat,
        }
        
        print(f"   ✅ User dict created successfully:")
        print(f"   Keys: {list(user_dict.keys())}")
        print(f"   Identity: {user_dict['identity']}")
        print(f"   Email: {user_dict['email']}")
        print(f"   Has GitHub token: {bool(user_dict.get('github_token'))}")
        print(f"   GitHub token prefix: {user_dict['github_token'][:10]}...")
        
        # Simulate the config object that would be passed to agent nodes
        config = {
            "configurable": {
                "langgraph_auth_user": user_dict
            }
        }
        
        print(f"   ✅ Config object created:")
        print(f"   Config keys: {list(config.keys())}")
        print(f"   Configurable keys: {list(config.get('configurable', {}).keys())}")
        
        # Test extraction (simulating what happens in agent nodes)
        extracted_user = config.get("configurable", {}).get("langgraph_auth_user")
        if extracted_user:
            print(f"   ✅ User extraction test successful")
            print(f"   Extracted user email: {extracted_user.get('email')}")
            print(f"   Extracted user has GitHub token: {bool(extracted_user.get('github_token'))}")
        else:
            print(f"   ❌ User extraction test failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error creating user dict: {e}")
        return False
    
    # Step 5: Summary
    print("\n📊 Summary:")
    print(f"   ✅ User login: Success")
    print(f"   ✅ Token validation: Success")
    print(f"   ✅ GitHub PAT retrieval: Success")
    print(f"   ✅ User dict creation: Success")
    print(f"   ✅ Config object creation: Success")
    print(f"   ✅ User extraction test: Success")
    print(f"   🎉 All auth middleware tests passed!")
    
    return True

def main():
    """Run the auth middleware test"""
    try:
        success = asyncio.run(test_auth_middleware())
        return success
    except Exception as e:
        print(f"❌ Fatal error during auth middleware test: {e}")
        return False
    finally:
        print("=" * 60)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)