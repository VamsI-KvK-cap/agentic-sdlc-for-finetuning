"""
Graph Module for Coding Agent Workflow.

This module constructs the LangGraph state graph for the coding agent workflow.
It defines the overall flow between nodes such as git context gathering, planning,
execution, review, and final routing.

The graph is built around a working directory and uses AgentState as its state type.
"""

# Import StateGraph and END constant from langgraph.graph for graph construction
from langgraph.graph import StateGraph, END

# Import AgentState TypedDict for graph state typing
from .states import AgentState

# Import build_nodes helper to create nodes, tool nodes, and edges
from .nodes import build_nodes


def build_graph(working_dir: str) -> object:
    """
    Build and compile the LangGraph workflow graph.

    This function creates all nodes and conditional transitions required for the
    coding agent workflow. It binds the graph to the provided working directory,
    ensures the proper entry point is set, and compiles the graph for execution.

    Args:
        working_dir (str): The root directory path for all workflow operations.
            The graph will only reference tools and nodes bound to this directory.

    Returns:
        object: The compiled LangGraph graph instance ready for execution.
    """
    # Build nodes, tool nodes, and edge functions for the working directory
    n = build_nodes(working_dir)
    nodes = n["nodes"]
    tool_nodes = n["tool_nodes"]
    edges = n["edges"]

    # Create a new state graph with the typed AgentState
    graph = StateGraph(AgentState)

    # Add all nodes and tool nodes to the graph
    for name, fn in {**nodes, **tool_nodes}.items():
        graph.add_node(name, fn)

    # Set the entry point for the workflow
    graph.set_entry_point("git_context")
    graph.add_edge("git_context", "planner")

    # Define planner flow transitions based on planner_should_continue
    graph.add_conditional_edges(
        "planner",
        edges["planner_should_continue"],
        {
            "planner_tools": "planner_tools",
            "extract_plan": "extract_plan"
        }
    )
    graph.add_edge("planner_tools", "planner")
    graph.add_edge("extract_plan", "executor")

    # Define executor flow transitions based on executor_should_continue
    graph.add_conditional_edges(
        "executor",
        edges["executor_should_continue"],
        {
            "executor_tools": "executor_tools",
            "reviewer": "reviewer"
        }
    )
    graph.add_edge("executor_tools", "executor")

    # Define reviewer flow transitions based on reviewer_should_continue
    graph.add_conditional_edges(
        "reviewer",
        edges["reviewer_should_continue"],
        {
            "reviewer_tools": "reviewer_tools",
            "process_review": "process_review"
        }
    )
    graph.add_edge("reviewer_tools", "reviewer")

    # Define final routing from review processing to either executor or end state
    graph.add_conditional_edges(
        "process_review",
        edges["route_after_review"],
        {
            "executor": "executor",
            END: END
        }
    )

    # Compile and return the graph for execution
    return graph.compile()