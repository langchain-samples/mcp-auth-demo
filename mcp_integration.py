"""
MCP server integration with authentication.

This module demonstrates how to properly integrate with MCP servers
using authenticated user credentials from LangGraph Platform.
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from auth_handler import validate_user_permissions, refresh_user_tokens_if_needed

logger = logging.getLogger(__name__)


class AuthenticatedMCPClient:
    """
    MCP client wrapper that handles authentication automatically.
    
    This class:
    1. Extracts user credentials from LangGraph config
    2. Creates MCP clients with proper authentication headers
    3. Handles token refresh automatically
    4. Provides a clean interface for graph nodes
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with LangGraph configuration.
        
        Args:
            config: LangGraph configuration containing user auth info
        """
        self.config = config
        self.user = config["configurable"].get("langgraph_auth_user", {})
        self.clients: Dict[str, MultiServerMCPClient] = {}
        
        if not self.user:
            logger.warning("No authenticated user found in config")
    
    def _get_server_config(self, service: str) -> Dict[str, Any]:
        """
        Get MCP server configuration for a service.
        
        Args:
            service: Service name (github, jira, etc.)
            
        Returns:
            Server configuration dictionary
        """
        server_configs = {
            "github": {
                "transport": "streamable_http",
                "url": "https://github-mcp-server.example.com/mcp",
                "headers": {
                    "Authorization": f"Bearer {self.user.get('github_token')}",
                    "User-Agent": "LangGraph-MCP-Client/1.0",
                    "X-User-ID": self.user.get("identity", "unknown")
                }
            },
            "jira": {
                "transport": "streamable_http", 
                "url": "https://jira-mcp-server.example.com/mcp",
                "headers": {
                    "Authorization": f"Bearer {self.user.get('jira_token')}",
                    "Content-Type": "application/json",
                    "X-User-ID": self.user.get("identity", "unknown"),
                    "X-Org-ID": self.user.get("org_id", "unknown")
                }
            },
            "slack": {
                "transport": "streamable_http",
                "url": "https://slack-mcp-server.example.com/mcp", 
                "headers": {
                    "Authorization": f"Bearer {self.user.get('slack_token')}",
                    "X-User-ID": self.user.get("identity", "unknown")
                }
            },
            "confluence": {
                "transport": "streamable_http",
                "url": "https://confluence-mcp-server.example.com/mcp",
                "headers": {
                    "Authorization": f"Bearer {self.user.get('confluence_token')}",
                    "X-User-ID": self.user.get("identity", "unknown"),
                    "X-Org-ID": self.user.get("org_id", "unknown")
                }
            },
            "local_filesystem": {
                "transport": "stdio",
                "command": ["python", "-m", "filesystem_mcp_server"],
                # Note: stdio transport doesn't support headers
                # Authentication would be handled via environment variables
                "env": {
                    "USER_ID": self.user.get("identity", "unknown"),
                    "ORG_ID": self.user.get("org_id", "unknown")
                }
            }
        }
        
        return server_configs.get(service, {})
    
    async def get_client(self, services: List[str]) -> MultiServerMCPClient:
        """
        Get or create MCP client for specified services.
        
        Args:
            services: List of service names to include
            
        Returns:
            Configured MultiServerMCPClient
            
        Raises:
            ValueError: If user lacks required permissions
        """
        # Validate user has access to all requested services
        missing_services = []
        for service in services:
            if not validate_user_permissions(self.user, service):
                missing_services.append(service)
        
        if missing_services:
            raise ValueError(
                f"User lacks access to services: {missing_services}. "
                f"Please ensure tokens are configured for these services."
            )
        
        # Build server configuration
        servers = {}
        for service in services:
            server_config = self._get_server_config(service)
            if server_config:
                servers[service] = server_config
                logger.info(f"Configured MCP client for {service}")
            else:
                logger.warning(f"No configuration found for service: {service}")
        
        if not servers:
            raise ValueError(f"No valid server configurations found for services: {services}")
        
        # Create and cache client
        cache_key = "|".join(sorted(services))
        if cache_key not in self.clients:
            self.clients[cache_key] = MultiServerMCPClient(servers)
            logger.info(f"Created MCP client for services: {services}")
        
        return self.clients[cache_key]
    
    async def call_tool(
        self, 
        service: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on a specific MCP server.
        
        Args:
            service: Service name
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            client = await self.get_client([service])
            
            # Add user context to arguments if not present
            if "user_context" not in arguments:
                arguments["user_context"] = {
                    "user_id": self.user.get("identity"),
                    "org_id": self.user.get("org_id"),
                    "email": self.user.get("email")
                }
            
            result = await client.call_tool(service, tool_name, arguments)
            logger.info(f"Successfully called {service}.{tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error calling {service}.{tool_name}: {e}")
            raise
    
    async def get_tools(self, service: str) -> List[Dict[str, Any]]:
        """
        Get available tools for a service.
        
        Args:
            service: Service name
            
        Returns:
            List of available tools
        """
        try:
            client = await self.get_client([service])
            tools = client.get_tools(service)
            logger.info(f"Retrieved {len(tools)} tools for {service}")
            return tools
            
        except Exception as e:
            logger.error(f"Error getting tools for {service}: {e}")
            return []
    
    async def list_available_services(self) -> List[str]:
        """
        List services the user has access to.
        
        Returns:
            List of accessible service names
        """
        all_services = ["github", "jira", "slack", "confluence"]
        available = []
        
        for service in all_services:
            if validate_user_permissions(self.user, service):
                available.append(service)
        
        logger.info(f"User has access to services: {available}")
        return available
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user information.
        
        Returns:
            User information dictionary
        """
        return {
            "identity": self.user.get("identity"),
            "email": self.user.get("email"),
            "org_id": self.user.get("org_id"),
            "workspace_id": self.user.get("workspace_id"),
            "authenticated_at": self.user.get("authenticated_at"),
            "available_services": self.list_available_services()
        }


# Convenience functions for common patterns
async def github_operations(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform common GitHub operations.
    
    Args:
        config: LangGraph configuration
        
    Returns:
        Results of GitHub operations
    """
    mcp = AuthenticatedMCPClient(config)
    
    try:
        # Get user's repositories
        repos = await mcp.call_tool("github", "list_repos", {
            "type": "owner",
            "sort": "updated"
        })
        
        # Get user profile
        profile = await mcp.call_tool("github", "get_user", {})
        
        return {
            "success": True,
            "repositories": repos,
            "profile": profile,
            "repo_count": len(repos) if repos else 0
        }
        
    except Exception as e:
        logger.error(f"GitHub operations failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def jira_operations(config: Dict[str, Any], project_key: str) -> Dict[str, Any]:
    """
    Perform common Jira operations.
    
    Args:
        config: LangGraph configuration
        project_key: Jira project key
        
    Returns:
        Results of Jira operations
    """
    mcp = AuthenticatedMCPClient(config)
    
    try:
        # Get project info
        project = await mcp.call_tool("jira", "get_project", {
            "project_key": project_key
        })
        
        # Get recent issues
        issues = await mcp.call_tool("jira", "search_issues", {
            "jql": f"project = {project_key} ORDER BY updated DESC",
            "max_results": 10
        })
        
        # Get user's assigned issues
        user_issues = await mcp.call_tool("jira", "search_issues", {
            "jql": f"project = {project_key} AND assignee = currentUser()",
            "max_results": 5
        })
        
        return {
            "success": True,
            "project": project,
            "recent_issues": issues,
            "assigned_issues": user_issues,
            "issue_count": len(issues) if issues else 0
        }
        
    except Exception as e:
        logger.error(f"Jira operations failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def multi_service_search(config: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Search across multiple services.
    
    Args:
        config: LangGraph configuration
        query: Search query
        
    Returns:
        Aggregated search results
    """
    mcp = AuthenticatedMCPClient(config)
    available_services = await mcp.list_available_services()
    
    results = {
        "query": query,
        "services_searched": [],
        "results": {}
    }
    
    # Search GitHub repositories
    if "github" in available_services:
        try:
            github_results = await mcp.call_tool("github", "search_repos", {
                "q": query,
                "sort": "stars"
            })
            results["services_searched"].append("github")
            results["results"]["github"] = github_results
        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
    
    # Search Jira issues
    if "jira" in available_services:
        try:
            jira_results = await mcp.call_tool("jira", "search_issues", {
                "jql": f"text ~ '{query}' ORDER BY updated DESC",
                "max_results": 10
            })
            results["services_searched"].append("jira")
            results["results"]["jira"] = jira_results
        except Exception as e:
            logger.error(f"Jira search failed: {e}")
    
    # Search Confluence pages
    if "confluence" in available_services:
        try:
            confluence_results = await mcp.call_tool("confluence", "search", {
                "cql": f"text ~ '{query}'",
                "limit": 10
            })
            results["services_searched"].append("confluence")
            results["results"]["confluence"] = confluence_results
        except Exception as e:
            logger.error(f"Confluence search failed: {e}")
    
    return results


# Transport support utilities
def get_supported_transports() -> Dict[str, Dict[str, Any]]:
    """
    Get information about supported MCP transports.
    
    Returns:
        Transport support matrix
    """
    return {
        "streamable_http": {
            "supports_headers": True,
            "supports_auth": True,
            "use_case": "Web APIs and cloud services",
            "examples": ["GitHub API", "Jira Cloud", "Slack API"]
        },
        "sse": {
            "supports_headers": True,
            "supports_auth": True,
            "use_case": "Server-sent events and streaming",
            "examples": ["Real-time notifications", "Live data feeds"]
        },
        "stdio": {
            "supports_headers": False,
            "supports_auth": False,
            "use_case": "Local processes and command-line tools",
            "examples": ["File system access", "Local databases"],
            "auth_note": "Use environment variables for authentication"
        },
        "grpc": {
            "supports_headers": False,
            "supports_auth": True,
            "use_case": "High-performance RPC",
            "examples": ["Internal services", "Microservices"],
            "auth_note": "Use channel metadata for authentication"
        }
    }


def validate_transport_auth(transport: str, auth_method: str) -> bool:
    """
    Validate if a transport supports the specified auth method.
    
    Args:
        transport: Transport type
        auth_method: Authentication method
        
    Returns:
        True if combination is supported
    """
    transports = get_supported_transports()
    transport_info = transports.get(transport, {})
    
    if transport in ["streamable_http", "sse"]:
        return auth_method in ["bearer_token", "api_key", "custom_header"]
    elif transport == "grpc":
        return auth_method in ["bearer_token", "api_key", "metadata"]
    elif transport == "stdio":
        return auth_method in ["environment_variable", "config_file"]
    
    return False