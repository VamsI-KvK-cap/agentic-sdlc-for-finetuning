from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.logging_config import logger
from src.tools.read_file_structure import read_file_structure


def file_structure_node(state: BaseAgentState):
    """
    Read and store the current file structure of the working directory.

    Scans the execution's working directory and captures its structure
    (e.g., files, folders, hierarchy) into the workflow state.

    CONCEPT: This node gives the agent visibility into the existing
    project layout, which is critical for planning, validation, and
    incremental code generation.

    Args:
        state (BaseAgentState): Current workflow state containing work_dir.

    Returns:
        dict: Partial state update containing the file_structure.
    """
    logger.info("Reading File Structure")
    
    # Read the directory structure using the helper tool.
    # This typically returns a tree or serialized representation.
    structure = read_file_structure.invoke(state["work_dir"])
    
    # Store the structure in state for downstream nodes (planner, validator).
    state["file_structure"] = structure
    
    # Debug log to inspect the structure during development/troubleshooting.
    logger.debug(f"Updating File Structure: \n{structure}")
    
    # Return only the updated portion of state (LangGraph merge behavior).
    return {"file_structure": state["file_structure"]}