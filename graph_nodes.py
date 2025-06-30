"""
LangGraph nodes demonstrating MCP integration with authentication.

This module contains graph nodes that show best practices for
integrating with MCP servers using authenticated user credentials.
"""

import logging
from typing import Dict, Any, TypedDict, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from mcp_integration import (
    AuthenticatedMCPClient,
    github_operations,
    jira_operations,
    multi_service_search
)

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State for the MCP authentication demo graph."""
    messages: Annotated[List[Dict[str, Any]], add_messages]
    user_request: str
    github_data: Dict[str, Any]
    jira_data: Dict[str, Any]
    search_results: Dict[str, Any]
    available_services: List[str]
    errors: List[str]


async def authentication_check_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Check user authentication and available services.
    
    This node demonstrates how to:
    1. Access user auth info from config
    2. Validate service access
    3. Set up the foundation for MCP operations
    """
    try:
        # Get authenticated user from config
        user = config["configurable"].get("langgraph_auth_user", {})
        
        if not user:
            error_msg = "No authenticated user found in config"
            logger.error(error_msg)
            return {
                **state,
                "errors": state.get("errors", []) + [error_msg],
                "messages": state["messages"] + [
                    AIMessage(content=f"Authentication Error: {error_msg}")
                ]
            }
        
        # Initialize MCP client to check available services
        mcp = AuthenticatedMCPClient(config)
        available_services = await mcp.list_available_services()
        user_info = mcp.get_user_info()
        
        logger.info(f"User {user.get('identity')} authenticated with services: {available_services}")
        
        return {
            **state,
            "available_services": available_services,
            "messages": state["messages"] + [
                AIMessage(content=f"""
Authentication successful! 

User: {user_info['email']}
Organization: {user_info['org_id']}
Available services: {', '.join(available_services)}

Ready to proceed with MCP operations.
""")
            ]
        }
        
    except Exception as e:
        error_msg = f"Authentication check failed: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "messages": state["messages"] + [
                AIMessage(content=f"Error: {error_msg}")
            ]
        }


async def github_integration_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Demonstrate GitHub integration through MCP.
    
    This node shows how to:
    1. Check if user has GitHub access
    2. Perform authenticated GitHub operations
    3. Handle service-specific errors gracefully
    """
    try:
        if "github" not in state.get("available_services", []):
            logger.info("Skipping GitHub integration - user lacks access")
            return {
                **state,
                "messages": state["messages"] + [
                    AIMessage(content="Skipping GitHub operations - no GitHub token configured")
                ]
            }
        
        logger.info("Performing GitHub operations")
        github_data = await github_operations(config)
        
        if github_data["success"]:
            message = f"""
GitHub Integration Results:
- Profile: {github_data['profile'].get('login', 'N/A')}
- Public repos: {github_data['repo_count']}
- Recent repositories: {[repo['name'] for repo in github_data['repositories'][:3]]}
"""
        else:
            message = f"GitHub integration failed: {github_data['error']}"
        
        return {
            **state,
            "github_data": github_data,
            "messages": state["messages"] + [AIMessage(content=message)]
        }
        
    except Exception as e:
        error_msg = f"GitHub integration error: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "messages": state["messages"] + [
                AIMessage(content=f"GitHub Error: {error_msg}")
            ]
        }


async def jira_integration_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Demonstrate Jira integration through MCP.
    
    This node shows how to:
    1. Check if user has Jira access
    2. Perform authenticated Jira operations
    3. Handle project-specific operations
    """
    try:
        if "jira" not in state.get("available_services", []):
            logger.info("Skipping Jira integration - user lacks access")
            return {
                **state,
                "messages": state["messages"] + [
                    AIMessage(content="Skipping Jira operations - no Jira token configured")
                ]
            }
        
        # Extract project key from user request or use default
        project_key = extract_project_key(state.get("user_request", "")) or "DEMO"
        
        logger.info(f"Performing Jira operations for project {project_key}")
        jira_data = await jira_operations(config, project_key)
        
        if jira_data["success"]:
            message = f"""
Jira Integration Results for project {project_key}:
- Project: {jira_data['project'].get('name', 'N/A')}
- Recent issues: {jira_data['issue_count']}
- Assigned to you: {len(jira_data['assigned_issues'])}
"""
        else:
            message = f"Jira integration failed: {jira_data['error']}"
        
        return {
            **state,
            "jira_data": jira_data,
            "messages": state["messages"] + [AIMessage(content=message)]
        }
        
    except Exception as e:
        error_msg = f"Jira integration error: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "messages": state["messages"] + [
                AIMessage(content=f"Jira Error: {error_msg}")
            ]
        }


async def multi_service_search_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Demonstrate cross-service search using MCP.
    
    This node shows how to:
    1. Search across multiple MCP services
    2. Aggregate results from different sources
    3. Handle partial failures gracefully
    """
    try:
        # Extract search query from user request
        search_query = extract_search_query(state.get("user_request", "")) or "LangGraph"
        
        logger.info(f"Performing multi-service search for: {search_query}")
        search_results = await multi_service_search(config, search_query)
        
        # Build summary message
        services_searched = search_results["services_searched"]
        if services_searched:
            message = f"""
Multi-Service Search Results for "{search_query}":
Services searched: {', '.join(services_searched)}

"""
            for service, results in search_results["results"].items():
                if results:
                    count = len(results) if isinstance(results, list) else 1
                    message += f"- {service.title()}: {count} results found\n"
                else:
                    message += f"- {service.title()}: No results\n"
        else:
            message = "No services available for search"
        
        return {
            **state,
            "search_results": search_results,
            "messages": state["messages"] + [AIMessage(content=message)]
        }
        
    except Exception as e:
        error_msg = f"Multi-service search error: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "messages": state["messages"] + [
                AIMessage(content=f"Search Error: {error_msg}")
            ]
        }


async def custom_mcp_operation_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Demonstrate custom MCP operations.
    
    This node shows how to:
    1. Use the AuthenticatedMCPClient directly
    2. Call specific tools with custom parameters
    3. Handle complex tool interactions
    """
    try:
        mcp = AuthenticatedMCPClient(config)
        user = config["configurable"].get("langgraph_auth_user", {})
        
        # Example: Custom GitHub operation
        results = {}
        
        if "github" in state.get("available_services", []):
            # Get user's GitHub profile with custom parameters
            profile = await mcp.call_tool("github", "get_user", {
                "include_private": True,
                "include_stats": True
            })
            
            # Get recent activity
            activity = await mcp.call_tool("github", "get_user_events", {
                "username": profile.get("login"),
                "per_page": 5
            })
            
            results["github"] = {
                "profile": profile,
                "recent_activity": activity
            }
        
        if "jira" in state.get("available_services", []):
            # Get user's recent activity in Jira
            user_activity = await mcp.call_tool("jira", "get_user_activity", {
                "username": user.get("email"),
                "days": 7
            })
            
            results["jira"] = {
                "recent_activity": user_activity
            }
        
        # Build response message
        message = "Custom MCP Operations Results:\n\n"
        for service, data in results.items():
            message += f"{service.title()}:\n"
            if "profile" in data:
                message += f"  - Profile: {data['profile'].get('name', 'N/A')}\n"
            if "recent_activity" in data:
                activity_count = len(data["recent_activity"]) if data["recent_activity"] else 0
                message += f"  - Recent activities: {activity_count}\n"
            message += "\n"
        
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=message)]
        }
        
    except Exception as e:
        error_msg = f"Custom MCP operation error: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "messages": state["messages"] + [
                AIMessage(content=f"Custom Operation Error: {error_msg}")
            ]
        }


async def summary_node(state: GraphState, config: Dict[str, Any]) -> GraphState:
    """
    Provide a summary of all MCP operations performed.
    
    This node demonstrates how to:
    1. Aggregate results from multiple MCP operations
    2. Provide a comprehensive summary
    3. Include error information if any occurred
    """
    try:
        user = config["configurable"].get("langgraph_auth_user", {})
        
        # Build comprehensive summary
        summary = f"""
MCP Authentication Demo Summary
================================

User: {user.get('email', 'Unknown')}
Organization: {user.get('org_id', 'Unknown')}
Services Available: {', '.join(state.get('available_services', []))}

Operations Performed:
"""
        
        # GitHub summary
        if state.get("github_data"):
            github_data = state["github_data"]
            if github_data["success"]:
                summary += f"✅ GitHub: Retrieved {github_data['repo_count']} repositories\n"
            else:
                summary += f"❌ GitHub: {github_data['error']}\n"
        
        # Jira summary
        if state.get("jira_data"):
            jira_data = state["jira_data"]
            if jira_data["success"]:
                summary += f"✅ Jira: Found {jira_data['issue_count']} recent issues\n"
            else:
                summary += f"❌ Jira: {jira_data['error']}\n"
        
        # Search summary
        if state.get("search_results"):
            search_results = state["search_results"]
            services_count = len(search_results["services_searched"])
            summary += f"✅ Search: Searched across {services_count} services\n"
        
        # Error summary
        errors = state.get("errors", [])
        if errors:
            summary += f"\nErrors encountered: {len(errors)}\n"
            for error in errors:
                summary += f"  - {error}\n"
        else:
            summary += "\nNo errors encountered.\n"
        
        summary += "\nDemo completed successfully! 🎉"
        
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=summary)]
        }
        
    except Exception as e:
        error_msg = f"Summary generation error: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "messages": state["messages"] + [
                AIMessage(content=f"Summary Error: {error_msg}")
            ]
        }


# Utility functions
def extract_project_key(user_request: str) -> str:
    """Extract Jira project key from user request."""
    # Simple extraction logic - in practice, use more sophisticated parsing
    words = user_request.upper().split()
    for word in words:
        if len(word) >= 2 and len(word) <= 10 and word.isalnum():
            return word
    return None


def extract_search_query(user_request: str) -> str:
    """Extract search query from user request."""
    # Simple extraction logic - in practice, use NLP
    if "search for" in user_request.lower():
        parts = user_request.lower().split("search for", 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    # Fallback to using the entire request
    return user_request.strip()


def should_continue_to_github(state: GraphState) -> str:
    """Conditional edge function to determine if GitHub operations should run."""
    if "github" in state.get("available_services", []):
        return "github_integration"
    else:
        return "jira_integration"


def should_continue_to_jira(state: GraphState) -> str:
    """Conditional edge function to determine if Jira operations should run."""
    if "jira" in state.get("available_services", []):
        return "jira_integration"
    else:
        return "multi_service_search"


# Export nodes for graph construction
__all__ = [
    "GraphState",
    "authentication_check_node",
    "github_integration_node", 
    "jira_integration_node",
    "multi_service_search_node",
    "custom_mcp_operation_node",
    "summary_node",
    "should_continue_to_github",
    "should_continue_to_jira"
]