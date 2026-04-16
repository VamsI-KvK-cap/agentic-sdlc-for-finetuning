import os
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.logging_config import logger
from dotenv import load_dotenv


load_dotenv()
working_dir = os.getenv("WORKING_DIR")

def setup_node(state: BaseAgentState):
    """
    Initialize execution metadata and working directory.

    Sets up the execution context required by downstream nodes:
    - Ensures an execution_id is present
    - Creates a per-execution working directory path
    - Initializes retry counters for review and static checks

    CONCEPT: This node acts as the entry point for the workflow.
    It normalizes and enriches the incoming state so that all
    subsequent nodes can rely on consistent fields.

    Args:
        state (BaseAgentState): Incoming workflow state.

    Returns:
        BaseAgentState: Updated state with execution context initialized.
    """
    logger.info("*" * 20)
    logger.info("Executing Setup Node")

    # Extract execution ID from state.
    # Fallback to a default (temporary) value if not provided.
    # TODO: Replace this with DB-backed auto-increment logic.
    exec_id = str(state.get("execution_id", 6))

    # Build a dedicated working directory for this execution.
    # This keeps artifacts isolated per run.
    work_dir = os.path.join(working_dir, exec_id)

    # Initialize retry counters used in review + static check loops.
    # These help prevent infinite retries and enable debugging.
    retry_count = {
        "review": 0,
        "static_check_count": 0,
    }

    # Return updated state while preserving existing fields.
    return {
        **state,
        "execution_id": exec_id,
        "work_dir": work_dir,
        "retry_count": retry_count,
    }