"""
Main LangGraph application demonstrating MCP authentication best practices.

This graph shows how to properly integrate with multiple MCP servers
using authenticated user credentials from LangGraph Platform.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from graph_nodes import (
    GraphState,
    authentication_check_node,
    github_integration_node,
    jira_integration_node,
    multi_service_search_node,
    custom_mcp_operation_node,
    summary_node,
    should_continue_to_github,
    should_continue_to_jira
)
from auth_handler import auth


def create_mcp_auth_graph() -> StateGraph:
    """
    Create the MCP authentication demo graph.
    
    This graph demonstrates:
    1. User authentication and service validation
    2. Conditional execution based on available services
    3. Integration with multiple MCP servers
    4. Proper error handling and user feedback
    """
    
    # Create graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("authentication_check", authentication_check_node)
    graph.add_node("github_integration", github_integration_node)
    graph.add_node("jira_integration", jira_integration_node)
    graph.add_node("multi_service_search", multi_service_search_node)
    graph.add_node("custom_mcp_operation", custom_mcp_operation_node)
    graph.add_node("summary", summary_node)
    
    # Set entry point
    graph.set_entry_point("authentication_check")
    
    # Add conditional edges based on available services
    graph.add_conditional_edges(
        "authentication_check",
        should_continue_to_github,
        {
            "github_integration": "github_integration",
            "jira_integration": "jira_integration"
        }
    )
    
    graph.add_conditional_edges(
        "github_integration", 
        should_continue_to_jira,
        {
            "jira_integration": "jira_integration",
            "multi_service_search": "multi_service_search"
        }
    )
    
    # Linear flow after service-specific operations
    graph.add_edge("jira_integration", "multi_service_search")
    graph.add_edge("multi_service_search", "custom_mcp_operation")
    graph.add_edge("custom_mcp_operation", "summary")
    graph.add_edge("summary", END)
    
    return graph.compile()


# Create the compiled graph
app = create_mcp_auth_graph()


async def run_demo(user_request: str = "Search for LangGraph examples") -> dict:
    """
    Run the MCP authentication demo.
    
    Args:
        user_request: User's request to process
        
    Returns:
        Final graph state with results
    """
    
    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=user_request)],
        "user_request": user_request,
        "github_data": {},
        "jira_data": {},
        "search_results": {},
        "available_services": [],
        "errors": []
    }
    
    # Run the graph - authentication will be handled by LangGraph Platform
    final_state = await app.ainvoke(initial_state)
    
    return final_state


if __name__ == "__main__":
    import asyncio
    import json
    
    async def main():
        """Run demo scenarios."""
        
        print("🔐 MCP Authentication Demo")
        print("=" * 50)
        
        scenarios = [
            "Search for LangGraph examples",
            "Show me my GitHub repositories and Jira tickets",
            "Find recent activity across all services"
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\nScenario {i}: {scenario}")
            print("-" * 30)
            
            try:
                result = await run_demo(scenario)
                
                # Print messages
                if result.get("messages"):
                    for msg in result["messages"][-3:]:  # Last 3 messages
                        if hasattr(msg, 'content'):
                            print(f"🤖 {msg.content[:200]}...")
                
                # Print summary stats
                print(f"\nServices used: {result.get('available_services', [])}")
                print(f"Errors: {len(result.get('errors', []))}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    # Note: This won't work without proper LangGraph Platform setup
    # Use langgraph dev to run with authentication
    print("To run this demo:")
    print("1. Deploy to LangGraph Platform or run 'langgraph dev'")
    print("2. Configure authentication with your service tokens") 
    print("3. Make requests with proper x-api-key header")