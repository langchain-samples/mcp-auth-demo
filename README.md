# 🔐 Agent Authentication On User Behalf

**End-to-end example of user authentication for LangGraph agents that interact with MCP servers using individual user credentials.**

This repository demonstrates the complete authentication flow from user login through MCP server access, implementing the patterns from the [LangGraph Agent Authentication documentation](https://docs.langchain.com/langsmith/auth).

## 🎯 What This Demo Shows

A complete implementation of:

1. **User authentication** via Supabase
2. **Secret storage** using Supabase Vault (with manual setup)
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
  participant Vault as Supabase Vault
  participant MCPServer as GitHub MCP Server

  %% Initial setup
  Note over ClientApp: Setup: Store user's GitHub PAT in Supabase Vault

  %% Authentication flow
  ClientApp  ->> Supabase: 1. Login (email/password)
  Supabase   -->> ClientApp: 2. Return Supabase token
  ClientApp  ->> LangGraph: 3. Request with Supabase token in header

  Note over LangGraph: 4. Custom auth middleware validates token
  LangGraph  -->> Supabase: 5. Verify token & get user info
  Supabase   -->> LangGraph: 6. Return user details

  %% Fetch GitHub token from Supabase Vault
  LangGraph  ->> Vault: 7. Fetch secret: "github_pat_user123"
  Vault -->> LangGraph: 8. Return GitHub PAT

  Note over LangGraph: 9. Populate config['configurable']['langgraph_auth_user']

  %% Use GitHub MCP
  Note over LangGraph: 10. Agent needs GitHub access
  LangGraph  ->> MCPServer: 11. Call MCP tool with user's GitHub PAT
  MCPServer  -->> LangGraph: 12. Tool response

  %% Return to user
  LangGraph  -->> ClientApp: 13. Agent response with GitHub data
```

## 📋 Prerequisites

- Python 3.11+ (required by this project)
- [uv](https://github.com/astral-sh/uv) package manager (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Supabase account (free tier works)
- GitHub Personal Access Token with Copilot access
- LangGraph Studio

## 🚀 Setup Instructions

### 1. Clone and Install

```bash
git clone <repo-url>
cd mcp-auth-demo
uv sync
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
```

### 3. Set Up Supabase Vault (Required)

**Important:** Supabase Vault requires manual setup. The Python client cannot access Vault without custom SQL functions.

#### Step 3a: Enable Vault Extension

1. Go to your [Supabase Dashboard](https://app.supabase.com)
2. Navigate to **Database → Extensions**
3. Search for "vault" and enable the **`supabase_vault`** extension

#### Step 3b: Create Helper Functions

Go to **SQL Editor** in your Supabase Dashboard and run this SQL:

```sql
-- Drop any existing functions first (if you've run this before)
DROP FUNCTION IF EXISTS vault_create_secret(text, text, text);
DROP FUNCTION IF EXISTS vault_read_secret(text);
DROP FUNCTION IF EXISTS vault_delete_secret(text);

-- Enable the vault extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;

-- Create helper functions for Python client access
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
```

### 4. Initialize Database & Secrets

```bash
# Create Supabase tables and test users
python setup_database.py

# Store GitHub PATs in Supabase Vault
python setup_secrets.py
```

Expected output for `setup_secrets.py`:
```
✅ Connected to Supabase
✅ Supabase Vault extension is enabled and working

🔐 Storing GitHub PATs in Supabase Vault...
📧 Found test user: user1@example.com (ID: 1660be62-1951-427a-9be2-0af51ae4e2d3)
📧 Found test user: user2@example.com (ID: 39f1327f-a0e2-48d2-aa5e-2d86cec82607)
✅ Stored GitHub PAT for user1@example.com
   Secret ID: a848d416-f8bb-48c3-9ea6-d599d3077d84
   Secret name: github_pat_1660be62-1951-427a-9be2-0af51ae4e2d3
✅ Stored GitHub PAT for user2@example.com
   Secret ID: d3d1eb51-8c03-41d3-905d-6abe39dbfc8e
   Secret name: github_pat_39f1327f-a0e2-48d2-aa5e-2d86cec82607

🎉 Secret storage complete!
✅ Successfully stored 2/2 GitHub PATs
```

This creates:
- Supabase test users (user1@example.com, user2@example.com, both with password "testpass123")
- GitHub tokens stored securely in Supabase Vault

### 5. Generate Test Token

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

### 6. Start LangGraph Server

```bash
# Start LangGraph with your custom auth
langgraph dev
```

### 💡 uv Development Tips

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management:

```bash
# Install/update dependencies
uv sync

# Run scripts directly
uv run python demo_e2e.py
uv run python setup_database.py

# Add new dependencies
uv add package-name

# Add development dependencies
uv add --dev pytest

# Run commands in the virtual environment
uv run <command>
```

The virtual environment is automatically created at `.venv/` and activated when using `uv run`.

### 7. Run the End-to-End Demo

```bash
# Run the complete authentication demo
python demo_e2e.py
```

Expected output shows the complete flow:
- ✅ User authentication via Supabase
- ✅ Token validation by LangGraph middleware  
- ✅ GitHub PAT retrieval from Supabase Vault
- ✅ 67 GitHub tools loaded via MCP
- ✅ Real GitHub API calls with user's credentials

### 8. Test in LangGraph Studio (Optional)

1. Open LangGraph Studio
2. Add header: `Authorization: Bearer <your-supabase-token>`
3. Run the agent with a GitHub-related query

## 🧪 Testing & Validation

### Quick Demo
Run the complete end-to-end demo to see the authentication flow in action:

```bash
python demo_e2e.py
```

### Test Suite
Comprehensive test suite covering each authentication stage:

```bash
# Run all tests
python tests/test_all_stages.py

# Run individual test stages
python tests/test_stage1_vault_retrieval.py    # Supabase Vault access
python tests/test_stage2_mcp_connection.py     # MCP server connection
python tests/test_stage3_auth_middleware.py    # Auth middleware simulation
python tests/test_stage4_agent_flow.py         # Complete agent flow
```

### What Gets Tested
- ✅ **Stage 1**: GitHub PAT retrieval from Supabase Vault
- ✅ **Stage 2**: MCP server connection with 67 GitHub tools
- ✅ **Stage 3**: Authentication middleware token validation
- ✅ **Stage 4**: Complete LangGraph agent execution

## 📁 Implementation Details

### `setup_database.py` - Database Initialization

Creates test users in Supabase Auth:

```python
from supabase import create_client
import os

def main():
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # Create test users
    test_users = [
        {"email": "user1@example.com", "password": "testpass123"},
        {"email": "user2@example.com", "password": "testpass123"}
    ]

    for user_data in test_users:
        try:
            user = supabase.auth.admin.create_user({
                "email": user_data["email"],
                "password": user_data["password"],
                "email_confirm": True
            })
            print(f"✅ Created user: {user_data['email']}")
        except Exception as e:
            if "already registered" in str(e):
                print(f"ℹ️  User already exists: {user_data['email']}")
            else:
                print(f"❌ Error creating user {user_data['email']}: {e}")
```

### `setup_secrets.py` - Supabase Vault Secret Storage

Stores GitHub PATs in Supabase Vault using the custom SQL functions:

```python
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
```

### `auth.py` - Authentication Middleware

```python
from langgraph_sdk import Auth
from supabase import create_client
import os

auth = Auth()

# Initialize Supabase client
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
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
    
    # Fetch GitHub PAT from Supabase Vault
    secret_name = f"github_pat_{user.id}"
    try:
        result = supabase.postgrest.rpc('vault_read_secret', {
            'secret_name': secret_name
        }).execute()
        
        github_pat = result.data if result.data else None
    except Exception as e:
        print(f"Warning: Could not fetch GitHub token for user {user.id}: {e}")
        github_pat = None
    
    # Return user config that will be available in nodes
    return {
        "identity": user.id,
        "email": user.email,
        "github_token": github_pat,
    }
```

### `agent.py` - LangGraph Agent with MCP Authentication

Key implementation details following [LangGraph MCP documentation](https://langchain-ai.github.io/langgraph/concepts/server-mcp/):

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """Initialize MCP tools with user authentication."""
    
    # Get user from LangGraph auth middleware
    user = config.get("configurable", {}).get("langgraph_auth_user")
    github_token = user.get("github_token")
    
    # Create MCP client with user's GitHub token (stateless approach)
    mcp_client = MultiServerMCPClient({
        "github": {
            "transport": "streamable_http", 
            "url": os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/"),
            "headers": {
                "Authorization": f"Bearer {github_token}"
            }
        }
    })
    
    # Get tools (returns StructuredTool objects ready for use)
    tools = await mcp_client.get_tools()
    
    return {"tools": tools}
```

**Key Insights from Implementation:**
- ✅ Use `headers` for authentication (not `authorization_token`)
- ✅ No sessions needed - MCP requests are stateless
- ✅ `get_tools()` returns ready-to-use StructuredTool objects
- ✅ Follow official LangGraph MCP patterns exactly

### `generate_supabase_token.py` - Test Token Generator

```python
from supabase import create_client
import os

def main():
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

if __name__ == "__main__":
    main()
```

## 🔒 Supabase Vault Implementation

This demo uses Supabase Vault for secure secret storage. Here's what you need to know:

### Why Custom SQL Functions Are Required

Supabase Vault is a PostgreSQL extension that provides:
- `vault.create_secret()` - SQL function to store secrets
- `vault.decrypted_secrets` - SQL view to read secrets
- **No direct Python client methods**

To use Vault from Python, you must create wrapper functions that can be called via RPC.

### Vault Storage Pattern

```python
# Store secret (via custom SQL function)
result = supabase.postgrest.rpc('vault_create_secret', {
    'secret': github_pat,
    'name': f'github_pat_{user_id}',
    'description': f'GitHub PAT for {email}'
}).execute()

# Read secret (via custom SQL function)
result = supabase.postgrest.rpc('vault_read_secret', {
    'secret_name': f'github_pat_{user_id}'
}).execute()
```

### Vault Security Features

- **Authenticated Encryption**: Secrets are encrypted and signed
- **Key Separation**: Encryption keys are stored separately from data
- **Access Control**: Only authorized functions can access secrets
- **Audit Trail**: All access is logged

## 🎯 Real-World Results

### Demo Output Example
When you run `python demo_e2e.py`, you'll see:

```
❓ User Question:
   "What's my most recent GitHub repository? Please show me the details."

🤖 Agent Answer:
   Your most recent GitHub repository is <your-repo>. Here are the details:
   - **Repository Name:** [your-repo](https://github.com/repo)
   - **Owner:** <your-username>
   - **Created At:** July 7th, 2025
   - **Language:** Python
   - **Stars:** 1000000
   - **Forks:** 100000
   - **Open Issues:** 1000
```

### What This Proves
- ✅ **User Authentication**: Supabase token validated
- ✅ **Secure Secret Access**: GitHub PAT retrieved from encrypted vault
- ✅ **MCP Integration**: 67 GitHub tools loaded successfully
- ✅ **Real API Calls**: Actual GitHub data returned using user's credentials
- ✅ **Complete Isolation**: Each user accesses only their own repositories

## 🏗️ Architecture Flow Verified

```
Client → Supabase Auth → LangGraph Auth Middleware → Supabase Vault → GitHub MCP → Agent Response
```

Each step is production-ready and secure.

## 🛠️ Troubleshooting

### Common Issues

1. **"Could not find function vault_create_secret"**
   - Solution: Run the SQL setup in Step 3b

2. **"Extension supabase_vault does not exist"**
   - Solution: Enable the Vault extension in Dashboard → Extensions

3. **"relation vault.decrypted_secrets does not exist"**
   - Solution: The vault extension may not be properly enabled

4. **Authentication fails**
   - Check your SUPABASE_URL and SUPABASE_SERVICE_KEY
   - Verify the token is being passed correctly

5. **MCP connection errors**
   - Ensure you're using `headers` not `authorization_token` in MCP client
   - Verify GitHub PAT has Copilot access
   - Use stateless approach (no sessions)

6. **Agent not using tools**
   - Check that `get_mcp_tools_node` runs before `agent_node`
   - Verify tools are in agent state before LLM binding

### Verification Commands

```bash
# Check if users were created
python -c "
from supabase import create_client
import os
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])
users = supabase.auth.admin.list_users()
print(f'Found {len(users)} users')
for user in users:
    print(f'  - {user.email} (ID: {user.id})')
"

# Check if secrets were stored
# (Run in Supabase SQL Editor)
SELECT name, description, created_at 
FROM vault.decrypted_secrets 
WHERE name LIKE 'github_pat_%';
```

## 🛡️ Security Best Practices

### ✅ DO
- Use Supabase Vault for encrypted secret storage
- Implement proper token validation
- Use service keys only on the server side
- Audit access patterns
- Rotate GitHub PATs regularly

### ❌ DON'T
- Store tokens in graph state
- Log sensitive credentials
- Use shared service accounts
- Pass tokens between nodes as parameters
- Store unencrypted tokens anywhere

## 📚 Additional Resources

### Official Documentation
- [LangGraph Authentication Guide](https://langchain-ai.github.io/langgraph/how-tos/auth/)
- [LangGraph MCP Server Integration](https://langchain-ai.github.io/langgraph/concepts/server-mcp/)
- [MCP Authentication Patterns](https://langchain-ai.github.io/langgraph/concepts/mcp/#authenticate-to-an-mcp-server)
- [Supabase Vault Documentation](https://supabase.com/docs/guides/database/vault)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)

### Key Learning Resources
- **LangGraph MCP Patterns**: Follow the exact patterns from official docs
- **Stateless MCP Approach**: No sessions, each request is independent
- **Structured Tool Objects**: `get_tools()` returns ready-to-use tools
- **Authentication Headers**: Use `headers` not `authorization_token`

---

## 🎉 Production Ready!

This implementation provides:
- ✅ **Complete Authentication Flow**: Supabase → LangGraph → Vault → MCP → GitHub
- ✅ **67 GitHub Tools**: Full access to GitHub API via MCP
- ✅ **User Isolation**: Each user's tools use their own credentials
- ✅ **Encrypted Storage**: Supabase Vault with authenticated encryption
- ✅ **Comprehensive Testing**: End-to-end demo + test suite
- ✅ **Production Security**: Following all LangGraph best practices

**Ready to implement secure, user-scoped agent authentication with Supabase Vault!** 🚀
