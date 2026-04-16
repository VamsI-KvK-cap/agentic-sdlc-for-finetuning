import os
import shutil
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from src.config.logging_config import logger


def writer_node(state: BaseFileAgentState, backup: bool = True):
    """
    Persist generated code changes to the filesystem.

    This node takes the code changes produced by the coding agent and writes them 
    to their respective paths on disk. It handles directory creation and can 
    optionally create backups of existing files before overwriting them.

    CONCEPT: Acts as the final 'commit' phase of the local file workflow, 
    transforming in-memory code representations into persistent files. It includes 
    safety checks to ensure files are written within the designated workspace.

    Args:
        state (BaseFileAgentState): Current state containing the code change to persist.
        backup (bool): If True, creates a .bak file for existing files before updating.

    Returns:
        dict: Updated state with the list of successfully written file paths.

    Raises:
        OSError: If there are permission issues or disk failures during writing.
    """
    logger.info("Executing Writer Node")
    written_files = []

    # Extract the code change object from the state
    code_change = state.get("code_change")
    if not code_change:
        logger.warning("No code_change found in the state, skipping writer.")
        return {**state, "written_files": [], "code_changes": []}
    
    work_dir = state["work_dir"]
    path = code_change["path"]
    content = code_change["content"]
    action = code_change["action"]    

    # Security check: Ensure the path is relative to the work directory
    if not path.startswith(work_dir):
        if path[0] == "/" :
            logger.critical(f"Skipping file due to absolute path security violation: {path}")
            return {**state, "written_files": [], "code_changes": []}
        path = os.path.join(work_dir, path)
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Optional backup for updates to prevent accidental data loss
    if backup and action == "update" and os.path.exists(path):
        backup_path = path + ".bak"
        shutil.copyfile(path, backup_path)
        logger.debug(f"Backup created: {backup_path}")

    # Persist the content to disk
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    written_files.append(path)

    logger.debug(f"Successfully written: {path}")
    
    # Return updated state tracking the changes made
    return {
        **state,
        "written_files": [path],
        "code_changes": [code_change] 
    }
