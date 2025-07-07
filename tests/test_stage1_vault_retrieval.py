#!/usr/bin/env python3
"""
Test Stage 1: GitHub PAT Retrieval from Supabase Vault

This test verifies that we can successfully retrieve GitHub Personal Access Tokens
from Supabase Vault for authenticated users.
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
email2 = "user2@example.com"
password2 = "testpass456"  # Note: both users use same password

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

async def test_vault_retrieval():
    """Test GitHub PAT retrieval from Supabase Vault"""
    
    print("🔍 Testing GitHub PAT retrieval from Supabase Vault")
    print("=" * 60)
    
    # Check environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing environment variable: {var}")
            return False
    
    print("✅ Environment variables loaded")
    
    # Step 1: Login as user1 to get their actual user ID
    print("\n📋 Step 1: Login as user1 to get actual user ID")
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
            user1_id = user_response.user.id
            print(f"✅ Retrieved user1 ID: {user1_id}")
        else:
            print("❌ Could not get user1 info")
            return False
            
    except Exception as e:
        print(f"❌ Error during user1 login: {e}")
        return False
    
    # Step 2: Login as user2 to get their actual user ID
    print("\n📋 Step 2: Login as user2 to get actual user ID")
    try:
        user2_token = await login(email2, password2)
        print(f"✅ User2 logged in successfully")
        print(f"   Token prefix: {user2_token[:20]}...")
        
        user_response = supabase_service.auth.get_user(user2_token)
        if user_response.user:
            user2_id = user_response.user.id
            print(f"✅ Retrieved user2 ID: {user2_id}")
        else:
            print("❌ Could not get user2 info")
            return False
            
    except Exception as e:
        print(f"❌ Error during user2 login: {e}")
        return False
    
    # Step 3: Test GitHub PAT retrieval from vault
    print("\n📋 Step 3: Testing GitHub PAT retrieval from vault")
    try:
        # Use actual user IDs from login
        test_users = [
            {
                "id": user1_id,
                "email": email1
            },
            {
                "id": user2_id, 
                "email": email2
            }
        ]
        
        success_count = 0
        
        for user in test_users:
            user_id = user["id"]
            email = user["email"]
            secret_name = f"github_pat_{user_id}"
            
            print(f"\n🔑 Testing user: {email}")
            print(f"   User ID: {user_id}")
            print(f"   Secret name: {secret_name}")
            
            try:
                # Try to retrieve the secret
                result = supabase_service.postgrest.rpc('vault_read_secret', {
                    'secret_name': secret_name
                }).execute()
                
                if result.data:
                    github_pat = result.data
                    print(f"   ✅ GitHub PAT retrieved successfully")
                    print(f"   Token prefix: {github_pat[:10]}...")
                    print(f"   Token length: {len(github_pat)}")
                    
                    # Validate token format (GitHub PATs start with ghp_)
                    if github_pat.startswith("ghp_"):
                        print(f"   ✅ Token format is valid (starts with ghp_)")
                        success_count += 1
                    else:
                        print(f"   ⚠️  Token format may be invalid (doesn't start with ghp_)")
                        
                else:
                    print(f"   ❌ No token found in Supabase Vault")
                    
            except Exception as e:
                print(f"   ❌ Error retrieving GitHub PAT: {e}")
        
        print(f"\n📊 Summary:")
        print(f"   Total users tested: {len(test_users)}")
        print(f"   Successful retrievals: {success_count}")
        print(f"   Success rate: {success_count/len(test_users)*100:.1f}%")
        
        if success_count == len(test_users):
            print(f"   🎉 All tests passed!")
            return True
        else:
            print(f"   ⚠️  Some tests failed")
            return False
            
    except Exception as e:
        print(f"❌ Fatal error during vault retrieval test: {e}")
        return False
    
    finally:
        print("=" * 60)

def main():
    """Run the vault retrieval test"""
    try:
        success = asyncio.run(test_vault_retrieval())
        return success
    except Exception as e:
        print(f"❌ Fatal error during vault retrieval test: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)