#!/usr/bin/env python3
"""
Database Setup for MCP Auth Demo

This script creates the necessary Supabase database setup including:
1. Test users for authentication

Run this after setting up your Supabase project and adding credentials to .env
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        sys.exit(1)
    
    # Initialize Supabase client with service key (for admin operations)
    supabase: Client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )
    
    print("🔐 Setting up Supabase database for MCP Auth Demo...")
    
    # Create test users
    test_users = [
        {
            "email": "user1@example.com",
            "password": "testpass123",
            "email_confirm": True,
            "user_metadata": {
                "name": "Test User 1",
                "role": "demo_user"
            }
        },
        {
            "email": "user2@example.com", 
            "password": "testpass456",
            "email_confirm": True,
            "user_metadata": {
                "name": "Test User 2",
                "role": "demo_user"
            }
        }
    ]
    
    print("\n📝 Creating test users...")
    created_users = []
    
    for user_data in test_users:
        try:
            # Create user using admin API
            user_response = supabase.auth.admin.create_user({
                "email": user_data["email"],
                "password": user_data["password"],
                "email_confirm": user_data["email_confirm"],
                "user_metadata": user_data["user_metadata"]
            })
            
            if user_response.user:
                created_users.append(user_response.user)
                print(f"✅ Created user: {user_data['email']} (ID: {user_response.user.id})")
            else:
                print(f"❌ Failed to create user: {user_data['email']}")
                
        except Exception as e:
            if "already_registered" in str(e).lower() or "already exists" in str(e).lower():
                print(f"ℹ️  User already exists: {user_data['email']}")
                
                # Try to get existing user
                try:
                    users_list = supabase.auth.admin.list_users()
                    existing_user = next(
                        (u for u in users_list if u.email == user_data['email']), 
                        None
                    )
                    if existing_user:
                        created_users.append(existing_user)
                        print(f"📋 Found existing user: {user_data['email']} (ID: {existing_user.id})")
                except Exception as list_error:
                    print(f"⚠️  Could not verify existing user {user_data['email']}: {list_error}")
            else:
                print(f"❌ Error creating user {user_data['email']}: {e}")
    
    print(f"\n🎉 Database setup complete!")
    print(f"📧 Created {len(created_users)} test users")
    
    if created_users:
        print("\n📋 Test User Details:")
        for user in created_users:
            print(f"   Email: {user.email}")
            print(f"   ID: {user.id}")
            print()
    
    print("🔄 Next steps:")
    print("1. Run `python setup_secrets.py` to store GitHub tokens")
    print("2. Run `python generate_supabase_token.py` to get test tokens")
    print("3. Start LangGraph with `langgraph dev`")

if __name__ == "__main__":
    main()