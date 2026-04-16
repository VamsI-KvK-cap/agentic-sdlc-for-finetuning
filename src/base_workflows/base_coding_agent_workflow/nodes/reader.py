from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.logging_config import logger
from src.tools.read_file import read_file

def reader_node(state: BaseAgentState):
    """
    Load existing file contents for files marked for update.

    Iterates through the execution plan and reads the contents of files
    that are marked with action="update". The contents are stored in the
    workflow state for use by downstream nodes (e.g., coder).

    CONCEPT: This node enables incremental code generation by providing
    the agent with the current state of files, allowing it to modify
    existing code instead of blindly overwriting it.

    Args:
        state (BaseAgentState): Current workflow state containing plan.

    Returns:
        BaseAgentState: Updated state with existing file contents.
    """
    logger.info("Executing Reader Node")

    # Extract execution plan from state
    plan = state["plan"]

    # Identify files that need to be updated (not newly created)
    files_to_update = [
        file["path"] for file in plan["files"]  # ignore type-check
        if file["action"] == "update"
    ]

    # Dictionary to store file path → file content mapping
    existing_files = {}

    # Read each file's content from disk
    for path in files_to_update:
        content = read_file.invoke(path)
        existing_files[path] = content

    # Store loaded files in state for downstream processing
    state["existing_files"] = existing_files

    # Debug log for visibility during development/troubleshooting
    logger.debug(f"Existing Files: \n{existing_files}")

    # Return full updated state
    return state