from typing_extensions import Literal
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.logging_config import logger


def should_read(state: BaseAgentState) -> Literal["reader", "process_files"]:
    """
    Decision node to determine if any files need to be read before processing.

    Scans the generated plan to identify if any files require an 'update' action. 
    If updates are planned, the workflow routes to the reader node to fetch 
    existing file content. Otherwise, it proceeds directly to file processing.

    CONCEPT: Ensures that the coding agent has the latest file content for any 
    pre-existing files it needs to modify, preventing 'blind' updates and 
    ensuring contextual accuracy during the coding phase.

    Args:
        state (BaseAgentState): The current state of the agent workflow, 
            containing the execution plan.

    Returns:
        Literal["reader", "process_files"]: The name of the next node to execute.
            "reader" if updates are needed, "process_files" if only creations are planned.

    Raises:
        Exception: Logs and defaults to "process_files" if the plan is malformed.
    """
    plan = state["plan"]
    
    try:
        # Check if any file in the plan requires modification of existing content.
        for file in plan["files"]:
            if file["action"] == "update":
                # At least one file needs to be read from disk.
                return "reader"
        
        # All files are new or no updates are required.
        return "process_files"
        
    except FileNotFoundError:
        # Fallback if plan data is missing - proceed to process files (likely empty)
        return "process_files"
    except Exception as e:
        # System error or malformed state - log the error and attempt to continue.
        logger.error(f"Error occurred in should_read decision: {e}")
        return "process_files"
