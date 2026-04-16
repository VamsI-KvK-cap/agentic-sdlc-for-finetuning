import os
from dotenv import load_dotenv
from typing_extensions import Literal
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from src.config.logging_config import logger

# Load environment variables for configuration
load_dotenv()

# Configuration for maximum number of retries for static checks
MAX_STATIC_CHECK_RETRIES = int(os.getenv("MAX_STATIC_CHECK_RETRIES", 3))


def static_check_decision(state: BaseFileAgentState) -> Literal["pass", "abort", "retry"]:
    """
    Evaluates the results of static code analysis and determines the next workflow step.

    This function checks if the static analysis (e.g., linting, type checking) was 
    successful. If it passed, the workflow continues. If it failed, it decides 
    whether to retry the coding task or abort based on the retry limit.

    CONCEPT: Provides an automated quality gate that prevents broken or poorly 
    formatted code from advancing in the pipeline. By allowing retries, the 
    agent can attempt to self-correct based on linter or compiler feedback.

    Args:
        state (BaseFileAgentState): The current state of the file-level agent, 
            including success flags and retry counters.

    Returns:
        Literal["pass", "abort", "retry"]: 
            "pass" if static check succeeded.
            "retry" if it failed but retry limit hasn't been reached.
            "abort" if it failed and maximum retries are exhausted.

    Raises:
        ValueError: If environment variable conversion fails.
    """
    # Check if the last static check operation was successful
    if state["static_check_success"]:
        # Reset the retry counter upon success to ensure a fresh start for future files
        state["retry_count"]["static_check_count"] = 0
        return "pass" 

    # Increment the retry counter following a failure
    state["retry_count"]["static_check_count"] += 1

    # Determine if we should attempt to fix the issues or give up
    if state["retry_count"]["static_check_count"] >= MAX_STATIC_CHECK_RETRIES:
        # Maximum attempts reached; aborting to prevent infinite loops
        logger.warning(f"Static check failed after {MAX_STATIC_CHECK_RETRIES} attempts. Aborting.")
        return "abort"
    
    # Still have retries left; send back to the coder for corrections
    return "retry"
