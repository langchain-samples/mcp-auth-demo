# 🔐 Agent Authentication On User Behalf

**End-to-end example of user authentication for LangGraph agents that interact with MCP servers using individual user credentials.**

This repository demonstrates the complete authentication flow from user login through MCP server access, implementing the patterns from the [LangGraph Agent Authentication documentation](https://langchain-ai.github.io/langgraph/how-tos/auth/).

## 🎯 What This Demo Shows

A complete implementation of:

1. **User authentication** via Supabase
2. **Flexible secret storage** with multiple options (Supabase Vault, AWS, etc.)
3. **Custom LangGraph authentication middleware**
4. **MCP server authentication** using user-specific GitHub tokens
5. **Clean LangGraph agent** with user-scoped GitHub tools

## 🏗️ Architecture

```mermaid
sequenceDiagram
  %% Actors
  participant ClientApp as Client
  participant Supabase as Supabase Auth
  participant LangGraph as LangGraph Platform
  participant SecretStore as Secret Storage (Vault/AWS/etc)
  participant MCPServer as GitHub MCP Server

  %% Initial setup
  Note over ClientApp: Setup: Store user's GitHub PAT in chosen secret store

  %% Authentication flow
  ClientApp  ->> Supabase: 1. Login (email/password)
  Supabase   -->> ClientApp: 2. Return Supabase token
  ClientApp  ->> LangGraph: 3. Request with Supabase token in header

  Note over LangGraph: 4. Custom auth middleware validates token
  LangGraph  -->> Supabase: 5. Verify token & get user info
  Supabase   -->> LangGraph: 6. Return user details

  %% Fetch GitHub token from flexible secret storage
  LangGraph  ->> SecretStore: 7. Fetch secret: "user123_github_pat"
  Note over SecretStore: Tries: Supabase Vault → AWS → Environment
  SecretStore -->> LangGraph: 8. Return GitHub PAT

  Note over LangGraph: 9. Populate config['configurable']['langgraph_auth_user']

  %% Use GitHub MCP
  Note over LangGraph: 10. Agent needs GitHub access
  LangGraph  ->> MCPServer: 11. Call MCP tool with user's GitHub PAT
  MCPServer  -->> LangGraph: 12. Tool response

  %% Return to user
  LangGraph  -->> ClientApp: 13. Agent response with GitHub data
```

## 📋 Prerequisites

- Python 3.8+
- Supabase account (free tier works)
- GitHub Personal Access Token with Copilot access
- LangGraph Studio
- Optional: AWS/GCP/Vault for production secret storage

## 🚀 Setup Instructions

### 1. Clone and Install

```bash
git clone <repo-url>
cd mcp-auth-demo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase (required)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# GitHub (required)
GITHUB_PAT=ghp_your_github_personal_access_token_here

# Optional: AWS (fallback secret storage)
# AWS_ACCESS_KEY_ID=your-aws-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret
# AWS_REGION=us-east-1
```

### 3. Initialize Database & Secrets

```bash
# Create Supabase tables and test users
python setup_database.py

# Set up secret storage (tries Supabase Vault → AWS → Environment)
python setup_secrets.py
```

This creates:
- Supabase test users (user1@example.com, user2@example.com)
- GitHub tokens stored in your chosen secret storage
- Setup instructions for Supabase Vault (alpha feature)

### 4. Generate Test Token

```bash
# Get a Supabase auth token for testing
python generate_supabase_token.py
```

Output:
```
✅ Generated Supabase token for user1@example.com:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Use this token in LangGraph Studio headers:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5. Start LangGraph Server

```bash
# Start with custom auth enabled
langgraph dev --disable-studio-auth
```

### 6. Test in LangGraph Studio

1. Open LangGraph Studio
2. Add header: `Authorization: Bearer <your-supabase-token>`
3. Run the agent with a GitHub-related query

## 📁 Implementation Details

### `setup_database.py` - Database Initialization

```python
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

# Create test users
users = [
    {"email": "user1@example.com", "password": "testpass123"},
    {"email": "user2@example.com", "password": "testpass456"}
]

for user in users:
    supabase.auth.admin.create_user(user)
    print(f"✅ Created user: {user['email']}")
```

### `setup_secrets.py` - Secret Storage Setup

```python
import boto3
import os

secrets_client = boto3.client('secretsmanager')

# Store GitHub PAT for user1
user_id = "user1"  # In production, use actual Supabase user UUID
github_pat = os.environ["GITHUB_PAT"]

secrets_client.create_secret(
    Name=f"{user_id}_github_pat",
    SecretString=github_pat,
    Description=f"GitHub PAT for {user_id}"
)

print(f"✅ Stored GitHub PAT for {user_id}")
```

### `auth.py` - Authentication Middleware

```python
from langgraph_sdk import Auth
from supabase import create_client
import boto3
import os

auth = Auth()

# Initialize clients
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

secrets_client = boto3.client(
    'secretsmanager',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)

@auth.authenticate
async def authenticate(headers: dict) -> Auth.types.MinimalUserDict:
    # Extract Supabase token
    token = headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Missing authorization token"
        )
    
    # Validate with Supabase
    user_response = supabase.auth.get_user(token)
    if not user_response.user:
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    
    user = user_response.user
    
    # Fetch GitHub PAT from AWS Secrets Manager
    secret_name = f"{user.id}_github_pat"
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        github_pat = response['SecretString']
    except secrets_client.exceptions.ResourceNotFoundException:
        github_pat = None
    
    # Return user config that will be available in nodes
    return {
        "identity": user.id,
        "email": user.email,
        "github_token": github_pat,
    }
```

### `agent.py` - ReAct Agent with MCP

```python
from langgraph.graph import StateGraph, MessagesState
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

async def setup_mcp_tools(state: MessagesState, config):
    """Setup MCP tools with user's GitHub token"""
    user = config["configurable"].get("langgraph_auth_user")
    
    if not user or not user.get("github_token"):
        return {"tools": [], "error": "No GitHub token available"}
    
    # Initialize MCP client with user's token
    mcp_client = MultiServerMCPClient({
        "github": {
            "transport": "streamable_http",
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {
                "Authorization": f"Bearer {user['github_token']}"
            }
        }
    })
    
    tools = await mcp_client.get_tools()
    return {"tools": tools}

# Build the graph
builder = StateGraph(MessagesState)

# Add nodes
builder.add_node("setup_tools", setup_mcp_tools)
builder.add_node("agent", ChatOpenAI(model="gpt-4"))
builder.add_node("tools", ToolNode())

# Add edges
builder.set_entry_point("setup_tools")
builder.add_edge("setup_tools", "agent")
builder.add_edge("agent", "tools")
builder.add_edge("tools", "agent")

# Compile
graph = builder.compile()
```

### `langgraph.json` - Configuration

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent.py:graph"
  },
  "env": ".env",
  "auth": {
    "path": "./auth.py:auth"
  }
}
```

### `generate_supabase_token.py` - Test Token Generator

```python
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_ANON_KEY"]  # Use anon key for client-side auth
)

# Login as test user
response = supabase.auth.sign_in_with_password({
    "email": "user1@example.com",
    "password": "testpass123"
})

if response.session:
    print(f"✅ Generated Supabase token for user1@example.com:")
    print(f"\n{response.session.access_token}\n")
    print(f"Use this token in LangGraph Studio headers:")
    print(f"Authorization: Bearer {response.session.access_token}")
else:
    print("❌ Failed to generate token")
```

## 🔒 Flexible Secret Storage

This demo supports multiple secret storage backends that you can swap easily:

### Option 1: Supabase Vault (Alpha Feature) - Default

```sql
-- Enable Supabase Vault in your project
create extension if not exists supabase_vault with schema vault;

-- Create helper functions
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
```

### Option 2: AWS Secrets Manager - Production Ready

```python
# Store secret
secrets_client.create_secret(
    Name=f"{user_id}_github_pat",
    SecretString=github_pat
)

# Retrieve secret (done automatically in auth.py)
response = secrets_client.get_secret_value(SecretId=f"{user_id}_github_pat")
```

### Option 3: Google Secret Manager

```python
# Modify auth.py to add:
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret_name = f"projects/{project_id}/secrets/user_{user_id}_github_pat/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
```

### Option 4: HashiCorp Vault

```python
# Modify auth.py to add:
import hvac
vault_client = hvac.Client(url='https://vault.example.com')
vault_client.secrets.kv.v2.read_secret_version(path=f"users/{user_id}/github_pat")
```

### Option 5: Azure Key Vault

```python
# Modify auth.py to add:
from azure.keyvault.secrets import SecretClient
secret_client = SecretClient(vault_url="https://vault.vault.azure.net/", credential=credential)
secret = secret_client.get_secret(f"user-{user_id}-github-pat")
```

The architecture makes it easy to switch between storage providers by modifying the `get_user_github_token()` function in `auth.py`.

## 🧪 Testing the Complete Flow

1. **Setup**: Run all setup scripts
2. **Get Token**: Generate a Supabase token for testing
3. **Start Server**: Launch LangGraph with custom auth
4. **Make Request**: Use the token in LangGraph Studio
5. **Verify**: Agent should access GitHub using the user's PAT

Expected flow:
```
Client → Supabase Auth → LangGraph Auth Middleware → Secret Storage → GitHub MCP → Agent Response
```

## 🛡️ Security Best Practices

### ✅ DO
- Use dedicated secrets management (Supabase Vault, AWS, Vault, etc.)
- Encrypt tokens at rest
- Implement token rotation
- Use separate service keys for server-side operations
- Audit access patterns
- Choose the right secret store for your environment

### ❌ DON'T
- Store tokens in graph state
- Log sensitive credentials
- Use shared service accounts
- Pass tokens between nodes as parameters
- Store unencrypted tokens in databases

## 📚 Additional Resources

- [LangGraph Authentication Guide](https://langchain-ai.github.io/langgraph/how-tos/auth/)
- [MCP Server Authentication](https://modelcontextprotocol.io/docs/auth)
- [Supabase Vault Documentation](https://supabase.com/docs/guides/database/vault)
- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)

---

**Ready to implement secure, user-scoped agent authentication with MCP servers!** 🚀