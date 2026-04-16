from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState, BaseFileAgentState
from src.config.logging_config import logger
def make_process_files_node(file_subgraph):
    """
    Factory function to create a file-processing node with an injected subgraph.

    Wraps the compiled file-level subgraph into a main-graph-compatible node.
    This allows each file in the execution plan to be processed independently
    using the same reusable workflow.

    CONCEPT: This is a higher-order function (factory) that enables dependency
    injection of the file subgraph into the main workflow. It bridges the gap
    between file-level execution and task-level orchestration.

    Args:
        file_subgraph: Compiled LangGraph subgraph for per-file processing.

    Returns:
        function: A process_files_node function bound to the provided subgraph.
    """
    
    def process_files_node(state: BaseAgentState):
        """
        Process all planned files sequentially using the file subgraph.

        Iterates over each file in the execution plan, constructs an isolated
        file-level state, and runs the subgraph to generate, review, and write code.

        CONCEPT: Each file is treated as an independent unit of work with its own
        mini state machine. Results are aggregated back into the main state.

        Args:
            state (BaseAgentState): Current workflow state containing file plan.

        Returns:
            BaseAgentState: Updated state with aggregated code changes and written files.
        """
        logger.info(f"Processing {len(state['plan']['files'])} files sequentially")
        
        # Collect outputs across all files
        all_code_changes = []
        all_written_files = []

        # Iterate through each file defined in the plan
        for file_plan in state["plan"]["files"]:
            logger.info(f"Processing file: {file_plan['path']}")
            
            # Build isolated state for this specific file
            # This prevents cross-file contamination of state
            file_state = BaseFileAgentState(
                execution_id=state["execution_id"],
                work_dir=state["work_dir"],
                task=state["task"],
                feedback=state.get("feedback"),

                # Retry counters are reset per file
                retry_count={},

                # File-specific plan (path, action, etc.)
                file_plan=file_plan,

                # Load existing file content only if updating
                existing_file_content=(
                    (state.get("existing_files") or {}).get(file_plan["path"])
                    if file_plan["action"] == "update"
                    else None
                ),

                # Initialize file-level outputs
                code_change=None,
                review=None,
                written_files=[],
                static_check_success=None,
                static_check_output=None,
            )

            # Execute file-level workflow (coder → reviewer → writer → static check)
            result = file_subgraph.invoke(file_state)

            # Collect generated code changes (if any)
            if result.get("code_change"):
                all_code_changes.append(result["code_change"])

            # Deduplicate written files per iteration
            final_written = list(set(result.get("written_files", [])))
            if final_written:
                all_written_files.extend(final_written)

            logger.info(f"Finished processing: {file_plan['path']}")

        # Return updated state with aggregated results
        return {
            **state,
            "code_changes": all_code_changes,
            "written_files": all_written_files,
        }

    return process_files_node