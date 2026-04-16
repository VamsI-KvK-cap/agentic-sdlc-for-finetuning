from typing_extensions import TypedDict, Optional, List, Literal, Dict, Any
from typing import Annotated
from .pydantic_models import CodeChange, FilePlan


def append_list(existing: Optional[List[Any]], new: Optional[List[Any]]) -> List[Any]:
    """
    Reducer function to accumulate list results from parallel or iterative subgraphs.

    This function is used as an Annotated reducer in LangGraph to ensure that 
    outputs from multiple nodes or subgraph iterations are merged into a single 
    list rather than overwriting each other.

    CONCEPT: Enables state accumulation across asynchronous or branched execution 
    paths, allowing the global state to track all files written or changes made 
    throughout the entire workflow lifecycle.

    Args:
        existing (Optional[List[Any]]): The current list stored in the state.
        new (Optional[List[Any]]): The new items to be added to the state.

    Returns:
        List[Any]: A new list containing both existing and new elements.
    """
    return (existing or []) + (new or [])


class BaseAgentState(TypedDict):
    """
    Global state container for the main coding agent workflow.

    Tracks the overall progress of a task, from initial setup and planning to 
    the final execution of file-level changes. It serves as the single source 
    of truth for the orchestrator graph.

    CONCEPT: Provides a unified context that is shared across all top-level nodes. 
    It manages high-level metadata (execution IDs, work directories) alongside 
    the aggregated results of granular file operations.

    Fields:
        execution_id (int): Primary identifier for the current execution run.
        work_dir (str): Absolute path to the workspace where the agent operates.
        task (str): The raw user instruction or objective for the agent.
        file_structure (str): A string representation of the project's file tree.
        existing_files (Optional[Dict[str, str]]): Map of file paths to their current content.
        plan (Optional[Dict[str, Any]]): The structured high-level execution plan.
        code_changes (Annotated[Optional[Dict[str, Any]], append_list]): Accumulated 
            record of all code changes generated across files.
        written_files (Annotated[Optional[List[str]], append_list]): List of all 
            file paths successfully persisted to disk.
        review (Optional[Dict[str, str]]): Summary feedback from the review phase.
        static_check_success (Optional[bool]): Overall status of static analysis checks.
        static_check_output (Optional[str]): Raw logs/output from static analysis tools.
        feedback (Optional[str]): Human or system feedback for iterative improvement.
        retry_count (Dict[str, int]): Counters tracking attempts for various workflow stages.
    """
    execution_id: int
    work_dir: str
    task: str
    file_structure: str
    existing_files: Optional[Dict[str, str]]
    plan: Optional[Dict[str, Any]]
    code_changes: Annotated[Optional[Dict[str, Any]], append_list]
    written_files: Annotated[Optional[List[str]], append_list]
    review: Optional[Dict[str, str]]
    static_check_success: Optional[bool]
    static_check_output: Optional[str]
    feedback: Optional[str]
    retry_count: Dict[str, int]


class BaseFileAgentState(TypedDict):
    """
    Local state container for the file-specific subgraph workflow.

    Encapsulates the context required to process a single file, including the 
    specific plan for that file and its current content. It is designed to be 
    spawned from the BaseAgentState for parallel or sequential file processing.

    CONCEPT: Isolates file-level operations (coding, reviewing, static checking) 
    to ensure that the agent focuses on one set of instructions at a time, 
    minimizing context leakage and improving generation quality.

    Fields:
        execution_id (int): Inherited execution identifier.
        work_dir (str): Inherited workspace path.
        task (str): Inherited high-level task description.
        feedback (Optional[str]): Specific feedback for the current file's iteration.
        retry_count (Dict[str, int]): Local counters for file-level retries.
        written_files (Annotated[Optional[List[str]], append_list]): Local list 
            of files written during this subgraph's execution.
        file_plan (FilePlan): The specific instruction set for this target file.
        existing_file_content (Optional[str]): Pre-existing content of the file (if updating).
        code_change (Optional[CodeChange]): The generated code change for this file.
        review (Optional[Dict[str, str]]): Detailed review result for this specific file.
        code_changes (Annotated[Optional[Dict[str, Any]], append_list]): Local 
            accumulation of changes (typically one per subgraph run).
        static_check_success (Optional[bool]): Success status of local static check.
        static_check_output (Optional[str]): Raw output from local static check tools.
    """
    execution_id: int
    work_dir: str
    task: str
    feedback: Optional[str]
    retry_count: Dict[str, int]
    written_files: Annotated[Optional[List[str]], append_list]
    file_plan: FilePlan
    existing_file_content: Optional[str]
    code_change: Optional[CodeChange]
    review: Optional[Dict[str, str]]
    code_changes: Annotated[Optional[Dict[str, Any]], append_list]
    static_check_success: Optional[bool]
    static_check_output: Optional[str]
