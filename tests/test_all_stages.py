#!/usr/bin/env python3
"""
Test All Stages: Complete MCP Authentication Flow

This script runs all test stages in sequence to verify the complete
MCP authentication implementation works correctly.
"""

import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_test_stage(stage_name, script_path):
    """Run a test stage and return success status"""
    
    print(f"\n🚀 Running {stage_name}")
    print("=" * 70)
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,  # Let output go to console
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {stage_name} PASSED")
            return True
        else:
            print(f"❌ {stage_name} FAILED (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {stage_name} TIMED OUT")
        return False
    except Exception as e:
        print(f"❌ {stage_name} ERROR: {e}")
        return False

def check_prerequisites():
    """Check if all required environment variables are set"""
    
    print("🔍 Checking Prerequisites")
    print("=" * 70)
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY", 
        "SUPABASE_ANON_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"❌ Missing: {var}")
        else:
            print(f"✅ Found: {var}")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file before running tests.")
        return False
    
    print(f"✅ All prerequisites met!")
    return True

def main():
    """Run all test stages"""
    
    print("🧪 MCP Authentication Test Suite")
    print("=" * 70)
    print("This will run all test stages to verify the complete authentication flow.")
    print("Make sure your LangGraph server is running: langgraph dev")
    print("=" * 70)
    
    # Check prerequisites
    if not check_prerequisites():
        return False
    
    # Test basic login functionality first
    print(f"\n🔑 Testing Basic Login Functionality")
    print("=" * 70)
    
    try:
        import httpx
        
        SUPABASE_URL = os.environ["SUPABASE_URL"]
        SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
        
        async def test_login():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    json={
                        "email": "user1@example.com",
                        "password": "testpass123"
                    },
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json"
                    },
                )
                return response.status_code == 200
        
        import asyncio
        login_success = asyncio.run(test_login())
        
        if login_success:
            print("✅ Basic login test passed")
        else:
            print("❌ Basic login test failed - check your user credentials")
            return False
            
    except Exception as e:
        print(f"❌ Login test error: {e}")
        return False
    
    # Define test stages
    test_stages = [
        {
            "name": "Stage 1: Vault Retrieval",
            "script": "test_stage1_vault_retrieval.py",
            "description": "Test GitHub PAT retrieval from Supabase Vault"
        },
        {
            "name": "Stage 2: MCP Connection", 
            "script": "test_stage2_mcp_connection.py",
            "description": "Test direct MCP server connection"
        },
        {
            "name": "Stage 3: Auth Middleware",
            "script": "test_stage3_auth_middleware.py", 
            "description": "Test auth middleware simulation"
        },
        {
            "name": "Stage 4: Agent Flow",
            "script": "test_stage4_agent_flow.py",
            "description": "Test complete agent flow with LangGraph"
        }
    ]
    
    # Track results
    results = []
    start_time = time.time()
    
    # Run each test stage
    for stage in test_stages:
        print(f"\n📋 About to run: {stage['description']}")
        
        success = run_test_stage(stage["name"], stage["script"])
        results.append({
            "name": stage["name"],
            "success": success
        })
        
        # Wait between tests
        if stage != test_stages[-1]:  # Not the last test
            print(f"\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n🎯 TEST SUITE SUMMARY")
    print("=" * 70)
    print(f"Total runtime: {duration:.1f} seconds")
    print(f"Tests run: {len(results)}")
    
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print(f"\n📊 Individual Results:")
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"   {status} - {result['name']}")
    
    if failed == 0:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"Your MCP authentication implementation is working correctly.")
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED")
        print(f"Please check the output above to debug the issues.")
    
    # Next steps
    print(f"\n💡 Next Steps:")
    if failed == 0:
        print(f"   • Your implementation is ready for production")
        print(f"   • Consider adding more comprehensive error handling")
        print(f"   • Test with different GitHub repositories and operations")
    else:
        print(f"   • Fix the failing tests before proceeding")
        print(f"   • Check server logs for detailed error information")
        print(f"   • Verify your Supabase and GitHub configurations")
    
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)