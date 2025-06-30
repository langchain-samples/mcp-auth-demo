# 🔐 MCP Authentication Best Practices Demo

**Secure integration of Multiple Control Protocol (MCP) servers with LangGraph Platform using proper authentication patterns.**

## 🎯 Problem Statement

Organizations like customer need to integrate with multiple external services (GitHub, Jira, etc.) through MCP servers while maintaining proper authentication and authorization. Current approaches often involve:

- ❌ Passing JWTs as parameters in graph state (security risk)
- ❌ HITL steps for token retrieval (poor UX)
- ❌ Hardcoded credentials (not scalable)

## ✅ Best Practice Solution

This demo shows how to properly authenticate users and propagate their credentials to MCP servers using LangGraph Platform's built-in authentication system.

### Key Benefits

- 🔒 **Secure**: Credentials never stored in graph state or logged
- 🚀 **Seamless**: No HITL flows required
- 🔄 **Scalable**: Works with multiple MCP servers
- 🎯 **Standards-based**: Uses platform authentication config

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │───▶│  LangGraph       │───▶│   MCP Servers   │
│   (API Key)     │    │  Platform        │    │   (GitHub,      │
│                 │    │                  │    │    Jira, etc.)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Custom Auth     │
                       │  Handler         │
                       │  (Fetches        │
                       │   User Tokens)   │
                       └──────────────────┘
```

## 🚀 Quick Start

### 1. Basic Authentication Setup

```python
from langgraph_sdk import Auth
import requests

auth = Auth()

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    api_key = headers.get("x-api-key")
    if not api_key or not is_valid_key(api_key):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid API key")
    
    # Fetch user-specific tokens from your secret store
    user_tokens = await fetch_user_tokens(api_key)
    
    return {
        "identity": api_key,
        "github_token": user_tokens.github_token,
        "jira_token": user_tokens.jira_token,
        "email": user_tokens.email,
        "org_id": user_tokens.org_id
    }
```

### 2. Using in Graph Nodes

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

def my_node(state, config):
    # Access authenticated user info
    user = config["configurable"].get("langgraph_auth_user")
    
    # Create MCP client with user's credentials
    client = MultiServerMCPClient({
        "github": {
            "transport": "streamable_http",
            "url": "https://github-mcp-server/mcp",
            "headers": {
                "Authorization": f"Bearer {user['github_token']}"
            }
        },
        "jira": {
            "transport": "streamable_http", 
            "url": "https://jira-mcp-server/mcp",
            "headers": {
                "Authorization": f"Bearer {user['jira_token']}"
            }
        }
    })
    
    # Use the client
    github_tools = client.get_tools("github")
    result = await client.call_tool("github", "get_repo", {"repo": "myorg/myrepo"})
    
    return {"result": result}
```

## 📊 Transport Support Matrix

| **Transport** | **Supports Headers** | **Use Case** | **Notes** |
|---------------|---------------------|--------------|-----------|
| `streamable_http` | ✅ Yes | Web APIs | Most common for external services |
| `sse` | ✅ Yes | Streaming | Good for long-running operations |
| `stdio` | ❌ No | Local processes | No HTTP layer for headers |
| `grpc` | ❌ No | High performance | Use channel metadata instead |

## 🛡️ Security Best Practices

### ✅ DO

- Store sensitive tokens in your secret management system
- Use HTTPS for all communication
- Validate tokens before use
- Implement token refresh logic
- Log access patterns (not tokens)

### ❌ DON'T

- Store tokens in graph state
- Log or expose user tokens
- Hardcode credentials
- Use HTTP for sensitive data
- Keep expired tokens

## 📁 Demo Files

- `auth_handler.py` - Complete authentication implementation
- `mcp_integration.py` - MCP client integration examples
- `graph_nodes.py` - Graph nodes using MCP with auth
- `secret_management.py` - Token storage and retrieval
- `test_scenarios.py` - Comprehensive test suite
- `deployment/` - Deployment configurations

## 🔧 Configuration

### Environment Variables

```bash
# LangGraph Platform
LANGCHAIN_API_KEY=your_api_key
LANGCHAIN_TRACING_V2=true

# Secret Management
SECRET_STORE_URL=https://your-secret-store
SECRET_STORE_TOKEN=your_secret_token

# MCP Server URLs
GITHUB_MCP_URL=https://github-mcp-server/mcp
JIRA_MCP_URL=https://jira-mcp-server/mcp
```

### LangGraph Configuration

```json
{
  "dependencies": [
    "langgraph",
    "langchain-mcp-adapters",
    "langsmith"
  ],
  "graphs": {
    "mcp_auth_demo": {
      "path": "./graph.py:app",
      "description": "MCP authentication demo"
    }
  },
  "env": {
    "LANGCHAIN_TRACING_V2": "true"
  }
}
```

## 🧪 Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run authentication tests
python test_scenarios.py

# Test individual components
python test_auth_handler.py
python test_mcp_integration.py

# Run integration tests
python test_end_to_end.py
```

## 🚀 Deployment

### Local Development

```bash
# Start with authentication
langgraph dev --auth-config auth_config.json

# Test endpoints
curl -H "x-api-key: your_key" http://localhost:8123/mcp-auth-demo/invoke
```

### Production Deployment

```bash
# Deploy to LangGraph Platform
langgraph deploy --name mcp-auth-demo

# Configure secrets
langgraph env set SECRET_STORE_URL https://your-vault
langgraph env set SECRET_STORE_TOKEN your_token
```

## 📚 Advanced Patterns

### Resource-Level ACLs

```python
@auth.on
async def owner_only(ctx, value):
    meta = value.setdefault("metadata", {})
    meta["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}
```

### Token Refresh

```python
async def refresh_token_if_needed(user_token: str) -> str:
    if is_token_expired(user_token):
        return await refresh_oauth_token(user_token)
    return user_token
```

### Multi-Organization Support

```python
def get_org_specific_tokens(user_identity: str, org_id: str):
    return secret_store.get_tokens(
        user=user_identity,
        organization=org_id
    )
```

## 🔗 References

- [LangGraph Authentication Concepts](https://langchain-ai.github.io/langgraph/concepts/auth/)
- [Custom Authentication Guide](https://langchain-ai.github.io/langgraph/how-tos/auth/custom_auth/)
- [MCP Integration Tutorial](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [LangChain MCP Adapters](https://python.langchain.com/docs/integrations/tools/mcp/)

## 🤝 Support

For questions or issues:
- Check the [troubleshooting guide](./docs/troubleshooting.md)
- Review [common patterns](./docs/patterns.md)
- Open an issue or contact support

---

**Ready to secure your MCP integrations!** 🚀