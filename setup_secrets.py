#!/usr/bin/env python3
"""
Secret Storage Setup for MCP Auth Demo

This script stores GitHub Personal Access Tokens in Supabase Vault.
Vault is a Postgres extension that stores encrypted secrets in your database.

Prerequisites:
1. Supabase project with Vault extension enabled
2. Test users created (run setup_database.py first)
3. GitHub Personal Access Token with Copilot access

Run this after setup_database.py
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client
import time

def setup_vault_extension(supabase):
    """Check if Vault extension is enabled and working."""
    try:
        # Test if vault is working by trying to create a test secret
        result = supabase.postgrest.rpc('vault_create_secret', {
            'secret': 'test_vault_connection',
            'name': 'vault_test_' + str(int(time.time())),
            'description': 'Test secret to verify vault is working'
        }).execute()
        
        if result.data:
            # Vault is working, clean up test secret
            test_name = f'vault_test_{int(time.time())}'
            try:
                supabase.postgrest.rpc('vault_delete_secret', {'secret_name': test_name}).execute()
            except:
                pass  # Ignore cleanup errors
            
            print("✅ Supabase Vault extension is enabled and working")
            return True
        else:
            print("❌ Vault function exists but returned no data")
            return False
            
    except Exception as e:
        print("❌ Vault extension not properly configured")
        print(f"   Error: {e}")
        print("\n📚 Manual setup required:")
        print("1. Go to your Supabase Dashboard → Database → Extensions")
        print("2. Enable the 'supabase_vault' extension")
        print("3. Go to SQL Editor and run this SQL:")
        print("""
-- Drop existing functions first (if any)
DROP FUNCTION IF EXISTS vault_create_secret(text, text, text);
DROP FUNCTION IF EXISTS vault_read_secret(text);
DROP FUNCTION IF EXISTS vault_delete_secret(text);

-- Enable the vault extension
CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;

-- Create helper functions
CREATE OR REPLACE FUNCTION vault_create_secret(secret text, name text default null, description text default null)
RETURNS uuid AS $$
BEGIN
  RETURN vault.create_secret(secret, name, description);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION vault_read_secret(secret_name text)
RETURNS text AS $$
DECLARE
  result text;
BEGIN
  SELECT decrypted_secret INTO result
  FROM vault.decrypted_secrets
  WHERE name = secret_name;
  RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION vault_delete_secret(secret_name text)
RETURNS void AS $$
BEGIN
  DELETE FROM vault.secrets WHERE name = secret_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
        """)
        return False

def store_github_pat(supabase, user_id: str, email: str, github_pat: str):
    """Store GitHub PAT for a user in Supabase Vault."""
    secret_name = f"github_pat_{user_id}"
    description = f"GitHub PAT for {email}"
    
    try:
        # Store the secret using Vault's create_secret function
        result = supabase.postgrest.rpc('vault_create_secret', {
            'secret': github_pat,
            'name': secret_name,
            'description': description
        }).execute()
        
        if result.data:
            secret_id = result.data
            print(f"✅ Stored GitHub PAT for {email}")
            print(f"   Secret ID: {secret_id}")
            print(f"   Secret name: {secret_name}")
            return True
        else:
            print(f"❌ Failed to store GitHub PAT for {email}")
            return False
            
    except Exception as e:
        print(f"❌ Error storing GitHub PAT for {email}: {e}")
        return False

def verify_secrets(supabase, user_emails):
    """Verify that secrets were stored correctly by reading them back."""
    print("\n🔍 Verifying stored secrets...")
    
    try:
        # Get all secrets from vault
        result = supabase.postgrest.from_('vault.decrypted_secrets').select('name, description, decrypted_secret').execute()
        
        if result.data:
            stored_secrets = {secret['name']: secret for secret in result.data}
            
            for email in user_emails:
                # Find user to get their ID
                users = supabase.auth.admin.list_users()
                user = next((u for u in users if u.email == email), None)
                
                if user:
                    secret_name = f"github_pat_{user.id}"
                    if secret_name in stored_secrets:
                        secret = stored_secrets[secret_name]
                        print(f"✅ {email}: Secret found and readable")
                        print(f"   Name: {secret['name']}")
                        print(f"   Description: {secret['description']}")
                        # Don't print the actual secret for security
                    else:
                        print(f"❌ {email}: Secret not found")
        else:
            print("❌ No secrets found in vault")
            
    except Exception as e:
        print(f"⚠️  Error verifying secrets: {e}")

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GITHUB_PAT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        sys.exit(1)
    
    # Initialize Supabase
    try:
        supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    # Setup Vault extension
    if not setup_vault_extension(supabase):
        print("❌ Cannot proceed without Vault extension. Please set it up manually.")
        sys.exit(1)
    
    # Get GitHub PAT from environment
    github_pat = os.environ["GITHUB_PAT"]
    
    print("\n🔐 Storing GitHub PATs in Supabase Vault...")
    
    # Get test users from Supabase
    try:
        test_emails = ["user1@example.com", "user2@example.com"]
        test_users = []
        all_users = supabase.auth.admin.list_users()
        
        for email in test_emails:
            user = next((u for u in all_users if u.email == email), None)
            if user:
                test_users.append(user)
                print(f"📧 Found test user: {email} (ID: {user.id})")
            else:
                print(f"⚠️  Test user not found: {email}")
        
        if not test_users:
            print("❌ No test users found. Please run setup_database.py first.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error getting test users: {e}")
        sys.exit(1)
    
    # Store secrets for each user
    successful_stores = 0
    
    for user in test_users:
        if store_github_pat(supabase, user.id, user.email, github_pat):
            successful_stores += 1
    
    print(f"\n🎉 Secret storage complete!")
    print(f"✅ Successfully stored {successful_stores}/{len(test_users)} GitHub PATs")
    
    # Verify the secrets were stored correctly
    verify_secrets(supabase, [user.email for user in test_users])
    
    print(f"\n🔄 Next steps:")
    print(f"1. Run `python generate_supabase_token.py` to get authentication tokens")
    print(f"2. Start LangGraph with `langgraph dev`")
    print(f"3. Test the authentication flow in LangGraph Studio")

if __name__ == "__main__":
    main()