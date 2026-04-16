import os
from typing_extensions import Literal
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from dotenv import load_dotenv
from src.config.logging_config import logger

# Load environment variables for configuration
load_dotenv()

# Configuration for maximum number of retries for code review feedback
MAX_REVIEW_RETRIES = int(os.getenv("MAX_REVIEW_RETRIES", 3))


def review_decision(state: BaseFileAgentState) -> Literal["approve", "revise", "abort"]:
    """
    Analyzes review feedback and determines if the code changes are acceptable.

    This decision node inspects the 'review' object in the state. It routes the 
    workflow to 'approve' if the reviewer is satisfied, 'revise' if corrections 
    are needed and retries remain, or 'abort' if the retry limit is hit.

    CONCEPT: Implements a human-in-the-loop or agent-to-agent quality control 
    mechanism. It ensures that the generated code meets the specified requirements 
    and architectural standards before being finalized.

    Args:
        state (BaseFileAgentState): The current state of the file-level agent, 
            containing the review result and retry counters.

    Returns:
        Literal["approve", "revise", "abort"]:
            "approve" if the review status is 'approved'.
            "revise" if the review status is not approved and retries remain.
            "abort" if maximum review retries have been reached.

    Raises:
        None explicitly; defaults to 'revise' if review data is missing.
    """
    review = state.get("review")
    
    # If no review is found, we can't approve. Default to revision.
    if not review:
        logger.warning("No review found in state, defaulting to revise")
        return "revise"

    # Fetch and update retry counters
    retry_count = dict(state.get("retry_count") or {})
    current_count = retry_count.get("review", 0)

    # Check for approval status
    if review.get("status", "").lower() == "approved":
        # Reset counter if needed (though usually terminal in this branch)
        return "approve"

    # Evaluate if we have exhausted the allowed revision cycles
    if current_count >= MAX_REVIEW_RETRIES:
        # Prevent infinite back-and-forth between coder and reviewer
        logger.warning(f"Max review retries ({MAX_REVIEW_RETRIES}) reached, aborting.")
        return "abort"

    # Request a revision from the coder
    return "revise"
