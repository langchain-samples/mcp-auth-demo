#!/usr/bin/env python3
"""
Supabase Token Generator for MCP Auth Demo

This script generates Supabase authentication tokens for testing
the MCP authentication flow in LangGraph Studio.

Prerequisites:
1. Supabase project configured with test users
2. SUPABASE_URL and SUPABASE_ANON_KEY in .env file
3. Test users created via setup_database.py

Usage:
    python generate_supabase_token.py [email]
    
Examples:
    python generate_supabase_token.py user1@example.com
    python generate_supabase_token.py  # defaults to user1@example.com
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please add them to your .env file")
        print("Note: Use SUPABASE_ANON_KEY (not SERVICE_KEY) for client-side auth")
        sys.exit(1)
    
    # Get email from command line or use default
    email = sys.argv[1] if len(sys.argv) > 1 else "user1@example.com"
    password = "testpass123"  # Same password for all test users
    
    # Initialize Supabase client with anon key (for client-side auth)
    try:
        supabase: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_ANON_KEY"]  # Use anon key for sign-in
        )
        print(f"✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    print(f"🔐 Generating Supabase token for {email}...")
    
    try:
        # Sign in as the test user
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.session and response.session.access_token:
            token = response.session.access_token
            user = response.user
            
            print(f"\n✅ Successfully generated Supabase token for {email}")
            print(f"👤 User ID: {user.id}")
            print(f"📧 Email: {user.email}")
            print(f"⏰ Token expires: {response.session.expires_at}")
            
            print(f"\n🎫 Access Token:")
            print(f"{token}")
            
            print(f"\n📋 Use this token in LangGraph Studio:")
            print(f"Header Name:  Authorization")
            print(f"Header Value: Bearer {token}")
            
            print(f"\n🧪 Test with curl:")
            print(f"""curl -X POST http://localhost:2024/runs \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{{"input": {{"messages": [{{"role": "user", "content": "List my GitHub repositories"}}]}}}}'""")
            
            # Verify the token by getting user info
            try:
                verify_response = supabase.auth.get_user(token)
                if verify_response.user:
                    print(f"\n✅ Token verification successful")
                    print(f"   Verified user: {verify_response.user.email}")
                else:
                    print(f"\n⚠️  Token verification failed")
            except Exception as verify_error:
                print(f"\n⚠️  Token verification error: {verify_error}")
                
        else:
            print(f"❌ Failed to generate token: No session returned")
            if response.user is None:
                print("   Check if the user exists and password is correct")
                print(f"   Run `python setup_database.py` to create test users")
            
    except Exception as e:
        print(f"❌ Error generating token: {e}")
        
        # Common error handling
        error_str = str(e).lower()
        if "invalid login credentials" in error_str:
            print("   💡 Try running `python setup_database.py` to create test users")
        elif "email not confirmed" in error_str:
            print("   💡 Email confirmation might be required")
        elif "too many requests" in error_str:
            print("   💡 Rate limited - wait a moment and try again")
        
        sys.exit(1)
    
    print(f"\n🔄 Next steps:")
    print(f"1. Copy the Authorization header above")
    print(f"2. Start LangGraph: `langgraph dev`")
    print(f"3. Open LangGraph Studio and add the header")
    print(f"4. Test with a GitHub-related query")

def show_help():
    print("""
Supabase Token Generator for MCP Auth Demo

Usage:
    python generate_supabase_token.py [email]

Available test users:
    user1@example.com (password: testpass123)
    user2@example.com (password: testpass123)

Examples:
    python generate_supabase_token.py user1@example.com
    python generate_supabase_token.py user2@example.com
    python generate_supabase_token.py  # defaults to user1@example.com

Prerequisites:
    1. Run `python setup_database.py` to create test users
    2. Add SUPABASE_URL and SUPABASE_ANON_KEY to .env file
    """)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_help()
    else:
        main()