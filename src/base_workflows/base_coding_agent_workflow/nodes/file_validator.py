from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from pathlib import Path
from src.config.logging_config import logger

def file_validator_node(state: BaseAgentState):
    """
    Validate and correct file actions in the execution plan.

    Compares the planned file actions (create/update) against the actual
    filesystem state and overrides incorrect decisions made by the LLM.

    CONCEPT: LLMs can hallucinate file existence. This node acts as a
    guardrail by enforcing ground truth from the filesystem:
    - If file exists → action must be "update"
    - If file does not exist → action must be "create"

    This ensures downstream nodes (reader, writer) operate on valid assumptions.

    Args:
        state (BaseAgentState): Current workflow state containing the plan.

    Returns:
        BaseAgentState: Updated state with corrected file actions.
    """
    plan = state["plan"]

    # Collect corrected file entries
    corrected = []

    # Iterate through planned files and validate each one
    for file in plan["files"]:
        file_path = Path(file["path"])
        action = file["action"]

        # Determine actual action based on filesystem state
        actual_action = "update" if file_path.is_file() else "create"

        # Log mismatch between LLM decision and reality
        if action != actual_action:
            logger.warning(
                f"Action mismatch for '{file_path}': "
                f"LLM said '{action}' but file "
                f"{'exists' if file_path.is_file() else 'does not exist'}. "
                f"Correcting to '{actual_action}'."
            )

        # Append corrected file entry
        corrected.append({**file, "action": actual_action})

    # Return updated state with corrected plan
    return {
        **state,
        "plan": {
            **plan,
            "files": corrected
        }
    }