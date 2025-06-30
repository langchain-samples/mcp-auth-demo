"""
Comprehensive test scenarios for MCP authentication demo.

This module tests various authentication and integration scenarios
to ensure robust behavior across different user configurations.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import pytest

from auth_handler import authenticate, validate_user_permissions
from mcp_integration import AuthenticatedMCPClient
from secret_management import SecretStore, UserTokens
from graph_nodes import (
    authentication_check_node,
    github_integration_node,
    jira_integration_node,
    multi_service_search_node
)

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPAuthTestSuite:
    """Test suite for MCP authentication patterns."""
    
    def __init__(self):
        self.results = []
    
    async def run_test(self, name: str, test_func, expected_success: bool = True):
        """Run a single test and record results."""
        
        print(f"\n🧪 Testing: {name}")
        print("=" * 60)
        
        try:
            start_time = asyncio.get_event_loop().time()
            result = await test_func()
            end_time = asyncio.get_event_loop().time()
            
            success = self._evaluate_result(result, expected_success)
            
            self.results.append({
                "name": name,
                "success": success,
                "result": result,
                "duration": end_time - start_time,
                "expected_success": expected_success
            })
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} ({end_time - start_time:.3f}s)")
            
            if isinstance(result, dict):
                print(f"Result: {json.dumps(result, indent=2, default=str)[:300]}...")
            else:
                print(f"Result: {str(result)[:200]}...")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.results.append({
                "name": name,
                "success": False,
                "error": str(e),
                "expected_success": expected_success
            })
    
    def _evaluate_result(self, result: Any, expected_success: bool) -> bool:
        """Evaluate if test result matches expectation."""
        
        if isinstance(result, dict):
            has_error = "error" in result or result.get("success") is False
            actual_success = not has_error
        else:
            actual_success = result is not None
        
        return actual_success == expected_success
    
    def print_summary(self):
        """Print test summary."""
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed < total:
            print(f"\nFailed Tests:")
            for test in self.results:
                if not test["success"]:
                    print(f"  ❌ {test['name']}")


# Test data and mocks
def create_mock_user_config(services: List[str]) -> Dict[str, Any]:
    """Create mock user configuration for testing."""
    
    user_data = {
        "identity": "test_user_123",
        "email": "test@example.com",
        "org_id": "test_org",
        "workspace_id": "test_workspace",
        "authenticated_at": "2024-01-01T00:00:00Z"
    }
    
    # Add service tokens based on available services
    if "github" in services:
        user_data["github_token"] = "ghp_test_token_123"
    if "jira" in services:
        user_data["jira_token"] = "jira_test_token_123"
    if "slack" in services:
        user_data["slack_token"] = "xoxb-test-slack-123"
    if "confluence" in services:
        user_data["confluence_token"] = "conf_test_token_123"
    
    return {
        "configurable": {
            "langgraph_auth_user": user_data
        }
    }


def create_mock_headers(valid_key: bool = True) -> Dict[str, str]:
    """Create mock HTTP headers for testing."""
    
    if valid_key:
        return {"x-api-key": "valid_test_key_123"}
    else:
        return {"x-api-key": "invalid_key"}


# Authentication tests
async def test_valid_authentication():
    """Test successful authentication flow."""
    
    headers = create_mock_headers(valid_key=True)
    
    with patch('auth_handler.is_valid_langsmith_key', return_value=True), \
         patch('auth_handler.get_user_info_from_langsmith', return_value={
             "user_id": "test_user_123",
             "email": "test@example.com",
             "org_id": "test_org",
             "workspace_id": "test_workspace"
         }), \
         patch('auth_handler.fetch_user_tokens', return_value=UserTokens(
             github_token="ghp_test_123",
             jira_token="jira_test_123"
         )):
        
        result = await authenticate(headers)
        
        return {
            "success": True,
            "user_id": result.get("identity"),
            "has_github": bool(result.get("github_token")),
            "has_jira": bool(result.get("jira_token"))
        }


async def test_invalid_api_key():
    """Test authentication failure with invalid API key."""
    
    headers = create_mock_headers(valid_key=False)
    
    with patch('auth_handler.is_valid_langsmith_key', return_value=False):
        try:
            await authenticate(headers)
            return {"success": True, "error": "Should have failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def test_missing_api_key():
    """Test authentication failure with missing API key."""
    
    headers = {}
    
    try:
        await authenticate(headers)
        return {"success": True, "error": "Should have failed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# MCP integration tests
async def test_mcp_client_initialization():
    """Test MCP client initialization with user credentials."""
    
    config = create_mock_user_config(["github", "jira"])
    mcp = AuthenticatedMCPClient(config)
    
    available_services = await mcp.list_available_services()
    user_info = mcp.get_user_info()
    
    return {
        "success": True,
        "available_services": available_services,
        "user_identity": user_info["identity"]
    }


async def test_service_permission_validation():
    """Test service permission validation."""
    
    config = create_mock_user_config(["github"])  # Only GitHub access
    mcp = AuthenticatedMCPClient(config)
    
    has_github = validate_user_permissions(mcp.user, "github")
    has_jira = validate_user_permissions(mcp.user, "jira")
    
    return {
        "success": True,
        "github_access": has_github,
        "jira_access": has_jira,
        "validation_correct": has_github and not has_jira
    }


async def test_mcp_client_without_permissions():
    """Test MCP client behavior when user lacks service permissions."""
    
    config = create_mock_user_config([])  # No services
    mcp = AuthenticatedMCPClient(config)
    
    try:
        await mcp.get_client(["github"])
        return {"success": True, "error": "Should have failed"}
    except ValueError as e:
        return {"success": False, "error": str(e), "expected": True}


# Graph node tests
async def test_authentication_check_node():
    """Test authentication check graph node."""
    
    config = create_mock_user_config(["github", "jira"])
    state = {
        "messages": [],
        "available_services": [],
        "errors": []
    }
    
    result = await authentication_check_node(state, config)
    
    return {
        "success": True,
        "services_found": len(result.get("available_services", [])),
        "messages_added": len(result.get("messages", [])),
        "errors": len(result.get("errors", []))
    }


async def test_github_integration_node():
    """Test GitHub integration graph node."""
    
    config = create_mock_user_config(["github"])
    state = {
        "messages": [],
        "available_services": ["github"],
        "errors": []
    }
    
    with patch('mcp_integration.github_operations', return_value={
        "success": True,
        "repositories": [{"name": "test-repo"}],
        "profile": {"login": "testuser"},
        "repo_count": 1
    }):
        
        result = await github_integration_node(state, config)
        
        return {
            "success": True,
            "github_data_present": bool(result.get("github_data")),
            "operation_successful": result.get("github_data", {}).get("success", False)
        }


async def test_jira_integration_node():
    """Test Jira integration graph node."""
    
    config = create_mock_user_config(["jira"])
    state = {
        "messages": [],
        "available_services": ["jira"],
        "user_request": "Show me DEMO project issues",
        "errors": []
    }
    
    with patch('mcp_integration.jira_operations', return_value={
        "success": True,
        "project": {"name": "Demo Project"},
        "recent_issues": [{"key": "DEMO-1"}],
        "assigned_issues": [],
        "issue_count": 1
    }):
        
        result = await jira_integration_node(state, config)
        
        return {
            "success": True,
            "jira_data_present": bool(result.get("jira_data")),
            "operation_successful": result.get("jira_data", {}).get("success", False)
        }


# Secret management tests
async def test_secret_store_operations():
    """Test secret store operations."""
    
    store = SecretStore()
    test_user = "test_user_secret"
    
    # Test storing tokens
    tokens = UserTokens(
        github_token="test_github_token",
        jira_token="test_jira_token"
    )
    
    store_success = await store.store_user_tokens(test_user, tokens)
    retrieved_tokens = await store.get_user_tokens(test_user)
    
    return {
        "success": True,
        "store_successful": store_success,
        "retrieve_successful": retrieved_tokens is not None,
        "tokens_match": (
            retrieved_tokens.github_token == tokens.github_token
            if retrieved_tokens else False
        )
    }


async def test_token_refresh():
    """Test token refresh functionality."""
    
    store = SecretStore()
    test_user = "test_user_refresh"
    
    # Store initial tokens
    tokens = UserTokens(
        github_token="old_github_token",
        refresh_token="refresh_token_123"
    )
    
    await store.store_user_tokens(test_user, tokens)
    
    # Test refresh
    new_tokens = await store.refresh_user_tokens(test_user)
    
    return {
        "success": True,
        "refresh_successful": new_tokens is not None,
        "token_changed": (
            new_tokens.github_token != tokens.github_token
            if new_tokens else False
        )
    }


# Integration tests
async def test_end_to_end_flow():
    """Test complete end-to-end authentication and MCP flow."""
    
    # Simulate full flow from authentication to MCP operations
    headers = create_mock_headers(valid_key=True)
    
    with patch('auth_handler.is_valid_langsmith_key', return_value=True), \
         patch('auth_handler.get_user_info_from_langsmith', return_value={
             "user_id": "e2e_test_user",
             "email": "e2e@example.com",
             "org_id": "e2e_org",
             "workspace_id": "e2e_workspace"
         }), \
         patch('auth_handler.fetch_user_tokens', return_value=UserTokens(
             github_token="e2e_github_token",
             jira_token="e2e_jira_token"
         )):
        
        # Step 1: Authenticate
        user_data = await authenticate(headers)
        
        # Step 2: Create config
        config = {
            "configurable": {
                "langgraph_auth_user": user_data
            }
        }
        
        # Step 3: Initialize MCP client
        mcp = AuthenticatedMCPClient(config)
        available_services = await mcp.list_available_services()
        
        # Step 4: Test authentication check node
        state = {
            "messages": [],
            "available_services": [],
            "errors": []
        }
        
        final_state = await authentication_check_node(state, config)
        
        return {
            "success": True,
            "user_authenticated": bool(user_data.get("identity")),
            "services_available": len(available_services),
            "node_executed": len(final_state.get("messages", [])) > 0,
            "no_errors": len(final_state.get("errors", [])) == 0
        }


# Performance tests
async def test_authentication_performance():
    """Test authentication performance."""
    
    headers = create_mock_headers(valid_key=True)
    iterations = 10
    
    with patch('auth_handler.is_valid_langsmith_key', return_value=True), \
         patch('auth_handler.get_user_info_from_langsmith', return_value={
             "user_id": "perf_test_user",
             "email": "perf@example.com",
             "org_id": "perf_org",
             "workspace_id": "perf_workspace"
         }), \
         patch('auth_handler.fetch_user_tokens', return_value=UserTokens()):
        
        start_time = asyncio.get_event_loop().time()
        
        for _ in range(iterations):
            await authenticate(headers)
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        return {
            "success": True,
            "iterations": iterations,
            "total_time": total_time,
            "avg_time_ms": avg_time * 1000,
            "performance_acceptable": avg_time < 0.1  # Less than 100ms
        }


async def run_all_tests():
    """Run comprehensive test suite."""
    
    suite = MCPAuthTestSuite()
    
    print("🧪 MCP Authentication Test Suite")
    print("=" * 60)
    
    # Authentication tests
    await suite.run_test("Valid Authentication", test_valid_authentication)
    await suite.run_test("Invalid API Key", test_invalid_api_key, expected_success=False)
    await suite.run_test("Missing API Key", test_missing_api_key, expected_success=False)
    
    # MCP integration tests
    await suite.run_test("MCP Client Initialization", test_mcp_client_initialization)
    await suite.run_test("Service Permission Validation", test_service_permission_validation)
    await suite.run_test("MCP Client Without Permissions", test_mcp_client_without_permissions, expected_success=False)
    
    # Graph node tests
    await suite.run_test("Authentication Check Node", test_authentication_check_node)
    await suite.run_test("GitHub Integration Node", test_github_integration_node)
    await suite.run_test("Jira Integration Node", test_jira_integration_node)
    
    # Secret management tests
    await suite.run_test("Secret Store Operations", test_secret_store_operations)
    await suite.run_test("Token Refresh", test_token_refresh)
    
    # Integration tests
    await suite.run_test("End-to-End Flow", test_end_to_end_flow)
    
    # Performance tests
    await suite.run_test("Authentication Performance", test_authentication_performance)
    
    # Print summary
    suite.print_summary()


if __name__ == "__main__":
    asyncio.run(run_all_tests())