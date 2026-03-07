from langgraph.graph import StateGraph, END
from .states import AgentState
from .nodes import build_nodes

def build_graph(working_dir: str):
    n = build_nodes(working_dir)
    nodes = n["nodes"]
    tool_nodes = n["tool_nodes"]
    edges = n["edges"]

    graph = StateGraph(AgentState)

    # Add all nodes
    for name, fn in {**nodes, **tool_nodes}.items():
        graph.add_node(name, fn)

    # Entry
    graph.set_entry_point("git_context")
    graph.add_edge("git_context", "planner")

    # Planner flow
    graph.add_conditional_edges("planner", edges["planner_should_continue"], {
        "planner_tools": "planner_tools",
        "extract_plan": "extract_plan"
    })
    graph.add_edge("planner_tools", "planner")
    graph.add_edge("extract_plan", "executor")

    # Executor flow
    graph.add_conditional_edges("executor", edges["executor_should_continue"], {
        "executor_tools": "executor_tools",
        "reviewer": "reviewer"
    })
    graph.add_edge("executor_tools", "executor")

    # Reviewer flow
    graph.add_conditional_edges("reviewer", edges["reviewer_should_continue"], {
        "reviewer_tools": "reviewer_tools",
        "process_review": "process_review"
    })
    graph.add_edge("reviewer_tools", "reviewer")

    # Final routing
    graph.add_conditional_edges("process_review", edges["route_after_review"], {
        "executor": "executor",
        END: END
    })

    return graph.compile()