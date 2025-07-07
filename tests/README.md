# 🧪 Test Suite

This directory contains all test files for the MCP authentication implementation.

## Test Files

- **`test_stage1_vault_retrieval.py`** - Test GitHub PAT retrieval from Supabase Vault
- **`test_stage2_mcp_connection.py`** - Test direct MCP server connection  
- **`test_stage3_auth_middleware.py`** - Test auth middleware simulation
- **`test_stage4_agent_flow.py`** - Test complete agent flow with LangGraph
- **`test_all_stages.py`** - Run all tests in sequence

## Running Tests

```bash
# Run individual tests
python tests/test_stage1_vault_retrieval.py
python tests/test_stage2_mcp_connection.py
python tests/test_stage3_auth_middleware.py
python tests/test_stage4_agent_flow.py

# Run all tests
python tests/test_all_stages.py
```

## What Each Test Does

### Stage 1: Vault Retrieval
- Logs in as test users
- Retrieves GitHub PATs from Supabase Vault
- Validates token format and authenticity

### Stage 2: MCP Connection
- Uses retrieved GitHub PAT
- Creates MCP client with proper authentication
- Retrieves 67 GitHub tools from MCP server
- Tests tool functionality

### Stage 3: Auth Middleware
- Simulates LangGraph authentication middleware
- Tests token validation flow
- Verifies user object creation for agent nodes

### Stage 4: Agent Flow
- Creates authenticated LangGraph client
- Tests complete agent execution
- Verifies tool calls and responses
- Confirms end-to-end functionality

### All Stages
- Runs comprehensive test suite
- Provides detailed success/failure reporting
- Validates complete authentication architecture