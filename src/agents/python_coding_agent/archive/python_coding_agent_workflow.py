import os, shutil, json  # OS/file operations, backups, JSON parsing
import subprocess  # For running external tools (e.g., linters)
from typing_extensions import TypedDict, Optional, List, Literal, Dict, Any
from langchain_openai import ChatOpenAI  # LLM interface
from langchain_core.prompts import ChatPromptTemplate  # Prompt builder
from langchain_core.output_parsers import PydanticOutputParser  # Structured parsing
from langgraph.graph import StateGraph, END  # Graph workflow engine
from pydantic import BaseModel, Field  # Data validation
from dotenv import load_dotenv  # Load env variables
from src.tools.read_file_structure import read_file_structure  # Tool: directory tree
from src.tools.read_file import read_file  # Tool: file reader
from src.config.logging_config import logger  # Logging system

# from codecarbon import EmissionsTracker
# (Optional: carbon tracking - currently disabled)

# tracker = EmissionsTracker(
#     project_name="agentic_sdlc",
#     output_dir="/home/wahaj/study/product_WJ/emissions",
#     log_level="info"
# )


# Load environment variables from .env file
load_dotenv()

# Base working directory for all executions
working_dir = os.getenv("WORKING_DIR")

# Retry limits for workflow loops
MAX_REVIEW_RETRIES = int(os.getenv("MAX_REVIEW_RETRIES", 3))
MAX_STATIC_CHECK_RETRIES = int(os.getenv("MAX_STATIC_CHECK_RETRIES", 3))


# Initialize LLM (local inference server)
llm = ChatOpenAI(
    base_url="http://localhost:8080/v1",  # Local API endpoint
    # model="Qwen2.5-7B-Instruct.Q4_0.gguf",  # Alternative model
    model="Qwen2.5-Coder-7B-Instruct.Q4_0.gguf",  # Code-focused model
    api_key="not_needed",  # No API key required locally
    # callbacks=[SimpleLogger()]  # Optional debugging callbacks
)


class AgentState(TypedDict):
    """
    Global state shared across the workflow.

    This state is passed between nodes in the graph and updated
    incrementally as execution progresses.

    Fields:
        execution_id (int):
            Unique identifier for the execution run.

        work_dir (str):
            Directory where files are created/modified.

        task (str):
            User-provided task description.

        file_structure (str):
            Snapshot of repository structure.

        existing_files (Optional[Dict[str, str]]):
            Mapping of file paths to content (for updates).

        plan (Optional[Dict[str, Any]]):
            Planner output defining file operations.

        code_changes (Optional[Dict[str, Any]]):
            Generated code modifications.

        review (Optional[Dict[str, str]]):
            Reviewer feedback and decision.

        written_files (Optional[List[str]]):
            List of files written to disk.

        static_check_success (Optional[bool]):
            Result of static analysis.

        static_check_output (Optional[str]):
            Raw output from static analysis tool.

        feedback (Optional[str]):
            Feedback used for retry loops.

        retry_count (Dict[str, int]):
            Tracks retry attempts for:
                - review
                - static_check_count
    """

    execution_id: int
    work_dir: str
    task: str
    file_structure: str
    existing_files: Optional[Dict[str, str]]  # path -> content
    plan: Optional[Dict[str, Any]]
    code_changes: Optional[Dict[str, Any]]
    review: Optional[Dict[str, str]]
    written_files: Optional[List[str]]
    static_check_success: Optional[bool]
    static_check_output: Optional[str]
    feedback: Optional[str]
    retry_count: Dict[str, int]


def setup_node(state: AgentState):
    """
    Initialize execution environment.

    Parameters:
        state (AgentState):
            Initial state (may only contain task)

    Returns:
        AgentState:
            Updated state with:
                - execution_id
                - work_dir
                - retry_count initialized

    Behavior:
        - Assigns execution ID (currently hardcoded)
        - Creates working directory path
        - Initializes retry counters

    Notes:
        - execution_id should ideally come from a database
        - working_dir isolates execution context
    """

    logger.info("*"*20)
    logger.info("Executing Setup Node")

    # TODO: Replace with DB-generated ID
    state["execution_id"] = 3  # hardcoded temporarily

    # Create working directory for this execution
    state["work_dir"] = os.path.join(working_dir, str(state["execution_id"]))

    # Initialize retry counters
    state["retry_count"] = {"review": 0, "static_check_count": 0}

    return state


def file_structure_node(state: AgentState):
    """
    Read and store repository file structure.

    Parameters:
        state (AgentState):
            Must contain "work_dir"

    Returns:
        dict:
            {"file_structure": str}

    Behavior:
        - Uses read_file_structure tool
        - Captures directory tree as string
        - Stores in state for planner

    Notes:
        - Helps planner understand project layout
        - Important for making correct file decisions
    """

    logger.info("Reading File Strucutre")

    # Read directory tree structure
    structure = read_file_structure.invoke(state["work_dir"])

    # Store structure in state
    state["file_structure"] = structure

    logger.debug(f"Updating File Structure: \n{structure}")

    return {"file_structure": state["file_structure"]}


class FilePlan(BaseModel):
    """
    Represents a single file operation in the execution plan.

    Fields:
        path (str):
            Absolute file path (must be within working_dir)

        action (Literal["create", "update"]):
            Operation type:
                - create → new file
                - update → modify existing file

        reason (str):
            Explanation of why this file is included in the plan
    """

    path: str = Field(description="This is an absolute path of file where work_dir is the parent directory.")
    action: Literal["create", "update"]
    reason: str


class Plan(BaseModel):
    """
    Represents the full execution plan.

    Fields:
        summary (str):
            High-level description of the task and approach

        files (List[FilePlan]):
            List of file-level operations
    """

    summary: str
    files: List[FilePlan]


# Parser to enforce structured LLM output
parser = PydanticOutputParser(pydantic_object=Plan)


# Planner prompt template
planner_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a senior software architect.

Your job is to create a precise implementation plan.

Rules:
- Prefer updating existing files over creating new ones.
- Only create new files if necessary.
- Respect the apparent project structure.
- Keep modifications minimal and modular.
- Return structured JSON only.
"""),
    ("user", """
Task:
{task}

Working Directory:
{work_dir}

Repository file structure:
{file_structure}

{format_instructions}
""")
])



def planner_node(state: AgentState):
    """
    Generate a structured implementation plan using the LLM.

    Parameters:
        state (AgentState):
            Must contain:
                - task (str): user input
                - work_dir (str): execution directory
                - file_structure (str): project layout

    Returns:
        dict:
            {
                "plan": dict  # serialized Plan object
            }

    Behavior:
        - Builds prompt using task + repo context
        - Sends prompt to LLM with structured output enforcement
        - Stores plan in state["plan"]
        - Returns plan for downstream nodes

    Notes:
        - Uses Pydantic model (Plan) for strict schema validation
        - Avoids unsafe JSON parsing
        - Mutates state AND returns delta (hybrid pattern)
    """

    logger.info("Executing Planner Node")

    # Format prompt with dynamic execution context
    formatted_prompt = planner_prompt.format_messages(
        task=state["task"],  # user request
        work_dir=state["work_dir"],  # working directory
        file_structure=state["file_structure"],  # repo structure
        format_instructions=parser.get_format_instructions()  # schema instructions
    )

    logger.debug(f"Python Planner Prompt: \n{formatted_prompt}")

    # OLD approach (manual parsing)
    # response = llm.invoke(formatted_prompt)
    # plan = parser.parse(response.content)

    # NEW approach: enforce structured output via Pydantic
    plan = llm.with_structured_output(Plan).invoke(formatted_prompt)

    # Store plan in state
    state["plan"] = plan.model_dump()

    # Return updated plan
    return {"plan": state["plan"]}


def reader_node(state: AgentState):
    """
    Read contents of files that require updates.

    Parameters:
        state (AgentState):
            Must contain:
                - plan (dict)

    Returns:
        AgentState:
            Updated with:
                - existing_files (dict[path → content])

    Behavior:
        - Extracts files marked as "update"
        - Reads file contents using read_file tool
        - Stores results in state

    Notes:
        - Skips files marked as "create"
        - Prepares context for coder node
    """

    logger.info("Executing Reader Node")

    plan = state["plan"]

    # Identify files that need to be updated
    files_to_update = [
        file["path"] for file in plan["files"]  # ignore type-check
        if file["action"] == "update"
    ]

    existing_files = {}

    # Read content for each file
    for path in files_to_update:
        content = read_file.invoke(path)
        existing_files[path] = content  # store mapping

    # Save in state
    state["existing_files"] = existing_files

    logger.debug(f"Existing Files: \n{existing_files}")

    return state


def should_read(state: AgentState) -> Literal["reader", "coder"]:
    """
    Decide whether reader node should run.

    Parameters:
        state (AgentState):
            Must contain plan

    Returns:
        Literal["reader", "coder"]:
            - "reader" → if any file needs update
            - "coder" → if only new files are created

    Behavior:
        - Iterates through planned files
        - Detects presence of update actions
        - Handles errors gracefully

    Notes:
        - Optimizes workflow by skipping unnecessary reads
        - Prevents redundant file operations
    """

    plan = state["plan"]

    try:
        # Check if any file requires update
        for file in plan["files"]:
            if file["action"] == "update":
                return "reader"

    except FileNotFoundError:
        # Plan missing or invalid
        return "coder"

    except Exception as e:
        print(f"Error occured: {e}")
        return "coder"


class CodeChange(BaseModel):
    """
    Represents a single file modification.

    Fields:
        path (str):
            Absolute path of the file (within working_dir)

        action (Literal["create", "update"]):
            Operation type:
                - create → new file
                - update → modify existing file

        content (str):
            Full content of the file after modification

    Notes:
        - Current design uses full overwrite (v1)
        - Future upgrade: diff/patch-based updates (v2)
    """

    path: str = Field(description="This is an absolute path of file  where work_dir is the parent directory.")
    action: Literal["create", "update"]
    content: str  # full new content (safe v1 design)


class CodeOutput(BaseModel):
    """
    Represents multi-file code generation output.

    Fields:
        summary (str):
            High-level description of changes

        changes (List[CodeChange]):
            List of file modifications
    """

    summary: str
    changes: List[CodeChange]


# Parser for structured LLM output
coder_parser = PydanticOutputParser(pydantic_object=CodeOutput)


# Prompt template for code generation
coder_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a senior software engineer.

Your job:
Generate precise code changes based on the plan.

Rules:
- For "create" → produce complete new file.
- For "update" → modify existing file carefully.
- Preserve unrelated logic.
- Do NOT remove functionality unless required.
- Keep changes minimal and clean.
- Maintain style consistency.
- Return structured JSON only.
"""),
    ("user", """
Task:
{task}

Implementation Plan:
{plan}

Static Analysis Feedback (if any):
{feedback}

Existing Files (only for updates):
{existing_files}

Format Instructions:
{format_instructions}
""")
])

from langgraph.types import RetryPolicy  # Used to configure retry behavior for nodes


def coder_node(state: AgentState):
    """
    Generate code changes using LLM based on the execution plan.

    Parameters:
        state (AgentState):
            Must contain:
                - task (str)
                - plan (dict)
                - existing_files (dict, optional)
                - feedback (str, optional)

    Returns:
        AgentState:
            Updated with:
                - code_changes (dict)

    Behavior:
        - Formats prompt using task, plan, and file context
        - Calls LLM with structured output schema (CodeOutput)
        - Stores generated code changes in state

    Notes:
        - Uses structured output to ensure valid schema
        - Handles multi-file generation
        - Raises exception if LLM fails
    """

    logger.info("Executing Coder Node")

    # Build prompt with all required context
    formatted_prompt = coder_prompt.format_messages(
        task=state["task"],  # user task
        plan=state["plan"],  # structured plan
        feedback=state.get("feedback", ""),  # feedback from previous iteration
        existing_files=state.get("existing_files", {}),  # file contents (for updates)
        format_instructions=coder_parser.get_format_instructions()  # schema enforcement
    )

    # OLD approach:
    # response = llm.invoke(formatted_prompt)

    # Enforce structured output using Pydantic model
    llm_structured = llm.with_structured_output(CodeOutput)

    try:
        # Invoke LLM
        code_output = llm_structured.invoke(formatted_prompt)

        # OLD parsing:
        # code_output = coder_parser.parse(response.content)

    except Exception as e:
        # Log and propagate error
        logger.error(f"Error occured during code generation. {e}")
        raise e

    # Store generated code changes in state
    state["code_changes"] = code_output.model_dump()

    logger.debug(f"Generated CODE: \n {code_output.model_dump()}")

    return state


class ReviewResult(BaseModel):
    """
    Represents structured output of reviewer evaluation.

    Fields:
        status (Literal["approved", "needs_revision"]):
            Final decision on code quality.

        issues (List[str]):
            List of detected issues.

        suggestion (List[str]):
            Suggested improvements.

        confidence (float):
            Confidence score (0.0 to 1.0).
    """

    status: Literal["approved", "needs_revision"]
    issues: List[str]
    suggestion: List[str]
    confidence: float = Field(description="The value must be between 0.0 - 1.0")


# Parser for reviewer output
reviewer_parser = PydanticOutputParser(pydantic_object=ReviewResult)


# Prompt template for reviewer
reviewer_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a senior software reviewer performing static analysis.

Your job:
Evaluate the proposed code changes.

You must:
- Ensure changes align with the task.
- Ensure minimal modifications.
- Ensure no unrelated logic is removed.
- Detect missing imports.
- Detect obvious runtime risks.
- Detect architectural violations.
- Reject incomplete implementations.

Be strict but fair.

Return structured JSON only.
"""),
    ("user", """
Task:
{task}

Implementation Plan:
{plan}

Existing Files (for updates):
{existing_files}

Proposed Code Changes:
{code_changes}

{format_instructions}
""")
])


def reviewer_node(state: AgentState):
    """
    Evaluate generated code using LLM reviewer.

    Parameters:
        state (AgentState):
            Must contain:
                - task
                - plan
                - existing_files
                - code_changes

    Returns:
        AgentState:
            Updated with:
                - review (dict)

    Behavior:
        - Sends code changes + context to LLM
        - Parses structured output into ReviewResult
        - Stores result in state

    Notes:
        - Acts as quality gate before writing files
        - Enables feedback loop for improvements
    """

    logger.info("Executing Reviewer Node")

    # Build prompt with review context
    formatted_prompt = reviewer_prompt.format_messages(
        task=state["task"],  # original task
        plan=["plan"],  # NOTE: placeholder (kept unchanged)
        existing_files=state.get("existing_files", {}),  # file content
        code_changes=state["code_changes"],  # generated changes
        format_instructions=reviewer_parser.get_format_instructions()  # schema enforcement
    )

    # Invoke LLM
    response = llm.invoke(formatted_prompt)

    # Parse structured response
    reviewe_result = reviewer_parser.parse(response.content)

    # Store result
    state["review"] = reviewe_result.model_dump()

    logger.info(f"Review by Reviewer Node: \n{reviewe_result.model_dump()}")

    return state


def review_descision(state: AgentState):
    """
    Determine next step based on review result.

    Parameters:
        state (AgentState):
            Must contain:
                - review (dict)
                - retry_count (dict)

    Returns:
        str:
            One of:
                - "approve"
                - "revise"
                - "abort"

    Behavior:
        - If approved → reset retry counter
        - If not approved:
            → increment retry counter
            → abort if max retries reached
            → otherwise retry
    """

    # If approved → proceed
    if state["review"]["status"].lower() == "approved":
        state["retry_count"]["review"] = 0  # reset
        return "approve"

    # Increment retry counter
    state["retry_count"]["review"] += 1

    # Abort if retry limit reached
    if state["retry_count"]["review"] >= MAX_REVIEW_RETRIES:
        return "abort"

    # Otherwise retry
    return "revise"


def writer_node(state: AgentState, backup: bool = True):
    """
    Persist code changes to disk safely.

    Args:
        state: AgentState containing code_changes
        backup: wheather to backup overwritten files

    Returns:
        AgentState:
            Updated with:
                - written_files (list)

    Behavior:
        - Iterates through all code changes
        - Validates file paths (must be inside working_dir)
        - Creates directories if needed
        - Optionally creates backups
        - Writes updated content to disk

    Notes:
        - Supports multi-file updates
        - Skips invalid paths for safety
    """

    logger.info("Executing Writer Node")

    written_files = []

    # Extract list of changes (multi-file support)
    code_changes = state.get("code_changes", {}).get("changes", [])

    work_dir = state["work_dir"]

    # Process each file change
    for change in code_changes:
        path = change["path"]

        # Safety check: ensure path is inside working directory
        if not path.startswith(work_dir):
            logger.critical(f"skipping the file due to wrong file path: {path}")
            continue

        content = change["content"]
        action = change["action"]

        # Ensure directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Backup existing file before overwrite
        if backup and action == "update" and os.path.exists(path):
            backup_path = path + ".bak"
            shutil.copyfile(path, backup_path)

        # Write new content
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        written_files.append(path)

    # Store written files in state
    state["written_files"] = written_files

    logger.debug(f"Written Files: \n{written_files}")

    return state

def static_check_node(state: AgentState):
    """
    Perform static analysis on written files using Ruff.

    Parameters:
        state (AgentState):
            Must contain:
                - written_files (List[str], optional)
                - retry_count (dict)

    Returns:
        AgentState:
            Updated with:
                - static_check_success (bool)
                - static_check_output (str)
                - feedback (str | None)

    Behavior:
        - If no files are written → skip static check
        - Runs Ruff linter on written files
        - Stores success status and output
        - Generates feedback if issues are found

    Notes:
        - Feedback is used for retry loop in coder node
        - Ruff output is parsed into human-readable format
        - Inline helper function used for summarization
    """

    logger.info("Executing Static Check Node")

    # Get list of written files
    written_files = state.get("written_files", [])

    # If no files were written → skip static analysis
    if not written_files:
        state["static_check_success"] = True
        state["static_check_output"] = "No Files written."
        return state

    # Run Ruff linter with JSON output
    result = subprocess.run(
        ["ruff", "check", "--output-format", "json"] + written_files,
        capture_output=True,
        text=True
    )

    # Store success status
    state["static_check_success"] = result.returncode == 0

    # Store full output (stdout + stderr)
    state["static_check_output"] = result.stdout + result.stderr

    # If linting failed → generate feedback
    if result.returncode != 0:

        # Helper function to summarize Ruff JSON output
        def summarize_ruff_issue(json_output):
            """
            Convert Ruff JSON output into readable format.

            Parameters:
                json_output (str): Raw JSON output from Ruff

            Returns:
                str: Human-readable issue summary
            """
            try:
                # Parse JSON output
                issues = json.loads(json_output)

                # Extract relevant details for each issue
                issue_list = [
                    f"{i['filename']}:{i['location']['row']} {i['code']} {i['message']}"
                    for i in issues
                ]

                return "Ruff reported:\n" + "\n".join(issue_list)

            except Exception as e:
                # Fallback if parsing fails
                return "Ruff reported issues but JSON parsing failed:\n" + json_output

        # Generate feedback for retry loop
        state["feedback"] = summarize_ruff_issue(result.stdout)

    else:
        # No issues → no feedback needed
        state["feedback"] = None

    # Log feedback for debugging
    logger.info(f"Static Check FEEDBACK: \n{state['feedback']}")

    return state


def static_check_decision(state: AgentState):
    """
    Decide next step based on static check results.

    Parameters:
        state (AgentState):
            Must contain:
                - static_check_success (bool)
                - retry_count (dict)

    Returns:
        str:
            One of:
                - "pass" → continue execution
                - "retry" → retry code generation
                - "abort" → stop execution

    Behavior:
        - If static check passes:
            → reset retry counter
            → proceed
        - If fails:
            → increment retry counter
            → retry until limit reached
            → abort if limit exceeded

    Notes:
        - Prevents infinite retry loops
        - Works with coder node in feedback cycle
    """

    # If static check passed → reset retry counter and continue
    if state["static_check_success"]:
        state["retry_count"]["static_check_count"] = 0  # reset
        return "pass"

    # Increment retry count
    state["retry_count"]["static_check_count"] += 1

    # Abort if retry limit exceeded
    if state["retry_count"]["static_check_count"] >= MAX_STATIC_CHECK_RETRIES:
        return "abort"

    # Otherwise retry code generation
    return "retry"


"""
Main Workflow Graph Definition

This file defines the full agent execution pipeline using LangGraph.

Pipeline Overview:
    setup → file_structure → planner → (reader → coder → reviewer → writer → static_check)

Key Concepts:
    - StateGraph: defines execution flow
    - Nodes: individual processing steps
    - Edges: transitions between steps
    - Conditional edges: dynamic branching
    - RetryPolicy: automatic retries for unstable nodes
"""

# Initialize main workflow graph with AgentState
workflow = StateGraph(AgentState)

# ---------------- NODE REGISTRATION ----------------

# Setup node → initializes execution context
workflow.add_node("setup", setup_node)

# Reads repository structure
workflow.add_node("file_structure", file_structure_node)

# Planner node with retry policy (auto-retry on failure)
workflow.add_node(
    "planner",
    planner_node,
    retry_policy=RetryPolicy(max_attempts=3)
)

# Reads existing files (for updates)
workflow.add_node("reader", reader_node)

# Code generation node (with retry support)
workflow.add_node(
    "coder",
    coder_node,
    retry_policy=RetryPolicy(max_attempts=3)
)

# Code review node
workflow.add_node("reviewer", reviewer_node)

# Writes code to disk
workflow.add_node("writer", writer_node)

# Static analysis node (with retry support)
workflow.add_node(
    "static_check",
    static_check_node,
    retry_policy=RetryPolicy(max_attempts=3)
)


# ---------------- ENTRY POINT ----------------

# Define starting node of workflow
workflow.set_entry_point("setup")


# ---------------- GRAPH EDGES ----------------

# Setup → File structure
workflow.add_edge("setup", "file_structure")

# File structure → Planner
workflow.add_edge("file_structure", "planner")

# Planner → conditional (reader or coder)
workflow.add_conditional_edges("planner", should_read)

# TEST (commented)
# workflow.add_edge("reader", END)

# Reader → Coder
workflow.add_edge("reader", "coder")

# Coder → Reviewer
workflow.add_edge("coder", "reviewer")


# ---------------- REVIEW LOOP ----------------

"""
Reviewer decision loop:
    reviewer → (approve | revise | abort)

    approve → writer
    revise → coder (retry)
    abort  → writer (current behavior)
"""
workflow.add_conditional_edges(
    "reviewer",
    review_descision,  # decision function
    {
        "approve": "writer",
        "abort": "writer",
        "revise": "coder"
    }
)


# ---------------- STATIC CHECK LOOP ----------------

# Writer → Static check
workflow.add_edge("writer", "static_check")

"""
Static check loop:
    static_check → (pass | retry | abort)

    pass  → END
    retry → coder (feedback loop)
    abort → END
"""
workflow.add_conditional_edges(
    "static_check",
    static_check_decision,
    {
        "pass": END,
        "abort": END,
        "retry": "coder"
    }
)


# ---------------- GRAPH COMPILATION ----------------

"""
Compile workflow into executable graph.

Returns:
    graph: Compiled LangGraph object
"""

graph = workflow.compile()


# ---------------- GRAPH VISUALIZATION ----------------

"""
Generate visual representation of the workflow.

Output:
    python_agent_workflow_graph.png
"""

# Generate PNG binary using Mermaid rendering
png_data = graph.get_graph().draw_mermaid_png()

# Save PNG to file
output_file = "python_agent_workflow_graph.png"

with open(output_file, "wb") as f:
    f.write(png_data)

print(f"Graph saved to {output_file}")


# ---------------- EXECUTION ----------------

"""
Execute the workflow with initial input.

Configuration:
    recursion_limit: prevents infinite loops

Input:
    task: user-defined instruction

Output:
    Final AgentState after execution
"""

config = {"recursion_limit": 50}

# Initial input state
input_state = {
    "task": "Write a detailed FastAPI endpoint for CRUD ops for a llm application that can take user input in text of file format"
}

# Optional: Start emissions tracking
# tracker.start()

# Execute graph
result = graph.invoke(input_state, config=config)

# Log completion
logger.info("EXECUTION COMPLETED!")

# Print final result
print(result)

# Optional: Stop emissions tracking
# tracker.stop()