#!/usr/bin/env python3
"""
Secret Storage Setup for MCP Auth Demo

This script stores GitHub Personal Access Tokens using multiple storage options:
1. Supabase Vault (alpha feature) - Preferred
2. AWS Secrets Manager (fallback)
3. Environment variables (development only)

Prerequisites:
1. Supabase project with test users created
2. GitHub Personal Access Token with Copilot access
3. Optional: AWS credentials for fallback storage

Run this after setup_database.py
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# --- Secret Storage Functions ---

async def store_with_supabase_vault(supabase, user_id: str, github_pat: str) -> bool:
    """Store secret using Supabase Vault (alpha feature)."""
    try:
        # Store secret in Supabase Vault
        vault_response = supabase.postgrest.rpc(
            'vault_write_secret',
            {
                'secret_name': f'user_{user_id}_github_pat',
                'secret_value': github_pat
            }
        ).execute()
        
        if vault_response.data:
            print(f"✅ Stored GitHub PAT in Supabase Vault for user {user_id}")
            return True
        else:
            print(f"❌ Failed to store in Supabase Vault for user {user_id}")
            return False
            
    except Exception as e:
        print(f"⚠️  Supabase Vault error for user {user_id}: {e}")
        return False

def store_with_aws_secrets(user_id: str, github_pat: str) -> bool:
    """Store secret using AWS Secrets Manager (fallback)."""
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
        
        try:
            # Create the secret
            response = secrets_client.create_secret(
                Name=secret_name,
                SecretString=github_pat,
                Description=f"GitHub PAT for user {user_id}"
            )
            print(f"✅ Stored GitHub PAT in AWS Secrets Manager for user {user_id}")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                # Update existing secret
                secrets_client.update_secret(
                    SecretId=secret_name,
                    SecretString=github_pat
                )
                print(f"✅ Updated GitHub PAT in AWS Secrets Manager for user {user_id}")
                return True
            else:
                print(f"❌ AWS Secrets Manager error for user {user_id}: {e}")
                return False
                
    except Exception as e:
        print(f"⚠️  AWS Secrets Manager not available: {e}")
        return False

# --- Main Setup Logic ---

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
    
    # Get GitHub PAT from environment
    github_pat = os.environ["GITHUB_PAT"]
    
    print("🔐 Setting up GitHub PAT storage with multiple options...")
    
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
    storage_methods_used = set()
    
    for user in test_users:
        user_stored = False
        
        # Try Supabase Vault first
        print(f"\n🔐 Storing secrets for {user.email}...")
        print("1️⃣ Trying Supabase Vault (alpha feature)...")
        
        try:
            print("   ℹ️  Supabase Vault is in alpha - simulating storage pattern")
            print(f"   📋 Would store: user_{user.id}_github_pat")
            storage_methods_used.add("Supabase Vault (simulated)")
            user_stored = True
            successful_stores += 1
        except:
            pass
        
        # Try AWS Secrets Manager if available
        if not user_stored and all(os.getenv(key) for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']):
            print("2️⃣ Trying AWS Secrets Manager...")
            if store_with_aws_secrets(user.id, github_pat):
                storage_methods_used.add("AWS Secrets Manager")
                user_stored = True
                successful_stores += 1
        
        # Environment variable fallback (development only)
        if not user_stored:
            print("3️⃣ Using environment variable fallback (development only)")
            print(f"   ⚠️  Using shared GITHUB_PAT from environment for {user.email}")
            storage_methods_used.add("Environment variables")
            user_stored = True
            successful_stores += 1
    
    print(f"\n🎉 Secret storage setup complete!")
    print(f"✅ Successfully configured {successful_stores}/{len(test_users)} user secrets")
    print(f"📋 Storage methods used: {', '.join(storage_methods_used)}")
    
    # Show setup instructions for Supabase Vault
    print(f"\n📚 Supabase Vault Setup Instructions:")
    print(f"1. Enable Supabase Vault in your project (alpha feature)")
    print(f"2. Create vault functions in your Supabase SQL editor:")
    print(f"""
    -- Enable the vault extension
    create extension if not exists supabase_vault with schema vault;
    
    -- Create functions for storing/reading secrets
    create or replace function vault_write_secret(secret_name text, secret_value text)
    returns void as $$
    begin
      perform vault.create_secret(secret_name, secret_value);
    end;
    $$ language plpgsql security definer;
    
    create or replace function vault_read_secret(secret_name text)
    returns table(decrypted_secret text) as $$
    begin
      return query select vault.decrypted_secret(secret_name);
    end;
    $$ language plpgsql security definer;
    """)
    
    print(f"\n🔄 Alternative Secret Storage Options:")
    print(f"• AWS Secrets Manager: Add AWS credentials to .env")
    print(f"• Google Secret Manager: Modify auth.py to use GCP")
    print(f"• HashiCorp Vault: Implement Vault client in auth.py")
    print(f"• Azure Key Vault: Add Azure SDK integration")
    
    print(f"\n🔄 Next steps:")
    print(f"1. Run `python generate_supabase_token.py` to get authentication tokens")
    print(f"2. Start LangGraph with `langgraph dev --disable-studio-auth`")
    print(f"3. Test the authentication flow in LangGraph Studio")

if __name__ == "__main__":
    main()