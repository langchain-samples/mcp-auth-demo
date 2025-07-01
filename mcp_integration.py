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
            service: Service name (github)
            
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
        all_services = ["github"]
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
            "available_services": []  # Use separate call to get async services
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


async def github_search(config: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Search GitHub repositories.
    
    Args:
        config: LangGraph configuration
        query: Search query
        
    Returns:
        GitHub search results
    """
    mcp = AuthenticatedMCPClient(config)
    
    results = {
        "query": query,
        "service": "github",
        "results": {}
    }
    
    try:
        github_results = await mcp.call_tool("github", "search_repos", {
            "q": query,
            "sort": "stars"
        })
        results["results"]["github"] = github_results
        results["success"] = True
    except Exception as e:
        logger.error(f"GitHub search failed: {e}")
        results["success"] = False
        results["error"] = str(e)
    
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
            "examples": ["GitHub API", "REST APIs", "Web services"]
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