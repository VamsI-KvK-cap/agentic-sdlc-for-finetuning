import os, shutil, json  # OS operations, file backup, JSON parsing
import subprocess  # Used for running static analysis (ruff)
from typing_extensions import TypedDict, Optional, List, Literal, Dict, Any
from typing import Annotated
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import Send
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from src.tools.read_file_structure import read_file_structure
from src.tools.read_file import read_file
from src.config.logging_config import logger

# Load environment variables from .env file
load_dotenv()

# Base working directory (root for all executions)
working_dir = os.getenv("WORKING_DIR")

# Retry limits for different stages
MAX_REVIEW_RETRIES = int(os.getenv("MAX_REVIEW_RETRIES", 3))
MAX_STATIC_CHECK_RETRIES = int(os.getenv("MAX_STATIC_CHECK_RETRIES", 3))


# Initialize LLM (local inference server)
llm = ChatOpenAI(
    base_url="http://localhost:8080/v1",
    model="Qwen2.5-Coder-7B-Instruct.Q4_0.gguf",
    api_key="not_needed",
)


def append_list(existing, new):
    """
    Reducer that accumulates list results from parallel subgraphs.

    Parameters:
        existing (list | None):
            Existing accumulated values.

        new (list | None):
            New values to append.

    Returns:
        list:
            Combined list of existing + new values.

    Notes:
        - Used with LangGraph Annotated fields for merging outputs.
        - Ensures safe handling of None values.
    """
    return (existing or []) + (new or [])


class AgentState(TypedDict):
    """
    Global state shared across the main workflow.

    Fields:
        execution_id (int): Unique ID for execution run
        work_dir (str): Directory where files are generated/modified
        task (str): User input task
        file_structure (str): Directory structure snapshot
        existing_files (dict): File path → content mapping
        plan (dict): Planner output
        code_changes (list): All changes made
        written_files (list): Files written to disk
        review (dict): Review results
        static_check_success (bool): Whether lint passed
        static_check_output (str): Raw lint output
        feedback (str): Feedback from reviewer/static check
        retry_count (dict): Retry counters for stages
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


def setup_node(state: AgentState):
    """
    Initialize execution context.

    Behavior:
        - Assigns execution ID (currently hardcoded)
        - Creates working directory path
        - Initializes retry counters

    Returns:
        AgentState: Updated state with execution metadata
    """
    logger.info("*"*20)
    logger.info("Executing Setup Node")

    state["execution_id"] = 4  # TODO: Replace with DB-generated ID
    state["work_dir"] = os.path.join(working_dir, str(state["execution_id"]))

    # Initialize retry counters
    state["retry_count"] = {"review": 0, "static_check_count": 0}

    return state


def file_structure_node(state: AgentState):
    """
    Reads and stores file structure of working directory.

    Returns:
        dict: {"file_structure": str}
    """
    logger.info("Reading File Strucutre")

    structure = read_file_structure.invoke(state["work_dir"])
    state["file_structure"] = structure

    logger.debug(f"Updating File Structure: \n{structure}")

    return {"file_structure": state["file_structure"]}


class FilePlan(BaseModel):
    """Represents plan for a single file."""
    path: str = Field(description="Absolute file path")
    action: Literal["create", "update"]
    reason: str


class Plan(BaseModel):
    """Planner output containing full execution plan."""
    summary: str
    files: List[FilePlan]


parser = PydanticOutputParser(pydantic_object=Plan)

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
    Generates structured implementation plan using LLM.

    Returns:
        dict: {"plan": structured_plan}

    Behavior:
        - Uses project structure + task input
        - Produces file-level plan
    """
    logger.info("Executing Planner Node")

    formatted_prompt = planner_prompt.format_messages(
        task=state["task"],
        work_dir=state["work_dir"],
        file_structure=state["file_structure"],
        format_instructions=parser.get_format_instructions()
    )

    logger.debug(f"Python Planner Prompt: \n{formatted_prompt}")

    # Use structured output parsing (safe JSON → Pydantic)
    plan = llm.with_structured_output(Plan).invoke(formatted_prompt)

    return {"plan": plan.model_dump()}


def reader_node(state: AgentState):
    """
    Reads contents of files marked for update.

    Returns:
        AgentState: Updated with existing file contents
    """
    logger.info("Executing Reader Node")

    plan = state["plan"]

    # Extract files needing updates
    files_to_update = [
        file["path"] for file in plan["files"]
        if file["action"] == "update"
    ]

    existing_files = {}

    # Read file contents
    for path in files_to_update:
        content = read_file.invoke(path)
        existing_files[path] = content

    state["existing_files"] = existing_files

    logger.debug(f"Existing Files: \n{existing_files}")
    return state

def should_read(state: AgentState) -> Literal["reader", "process_files"]:
    plan = state["plan"]
    try:
        for file in plan["files"]:
            if file["action"] == "update":
                return "reader"
        return "process_files"
    except FileNotFoundError:
        return "process_files"
    except Exception as e:
        print(f"Error occured: {e}")
        return "process_files"
    
# skip_reader is a passthrough node that just returns state
def skip_reader_node(state: AgentState):
    return state

class CodeChange(BaseModel):
    path: str = Field(description="This is an absolute path of file  where work_dir is the parent directory.")
    action: Literal["create", "update"]
    content: str # full new content(safe v1 design)  | In v2, you can move to diff/patch mode.

class CodeOutput(BaseModel):
    summary: str
    changes: List[CodeChange]

class SingleFileOutput(BaseModel):
    summary:str
    change: CodeChange

class FileAgentState(TypedDict):
    # Inherited context
    execution_id: int
    work_dir: str
    task: str
    feedback: Optional[str]
    retry_count: Dict[str, int]
    written_files: Annotated[Optional[List[str]], append_list]
    # Per-file fields
    file_plan: FilePlan                     # single FilePlan (not a list)
    existing_file_content: Optional[str]    # content of file being modified
    code_change: Optional[CodeChange]       # single file output
    review: Optional[Dict[str, str]]
    code_changes: Annotated[Optional[Dict[str, Any]], append_list]
    static_check_success: Optional[bool]
    static_check_output: Optional[str]


coder_parser = PydanticOutputParser(pydantic_object=CodeOutput)
file_coder_parser = PydanticOutputParser(pydantic_object=SingleFileOutput)

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

from langgraph.types import RetryPolicy
def coder_node(state: FileAgentState):
    logger.info("Executing Coder Node")
    formatted_prompt = coder_prompt.format_messages(
        task=state["task"],
        plan=state["file_plan"],
        feedback=state.get("feedback", ""),
        existing_files=state.get("existing_file_content", {}),
        format_instructions=file_coder_parser.get_format_instructions()
    )

    # response = llm.invoke(formatted_prompt)
    llm_structured = llm.with_structured_output(SingleFileOutput)
    try:
        code_output = llm_structured.invoke(formatted_prompt)
        # code_output = coder_parser.parse(response.content)
    except Exception as e:
        logger.error(f"Coder failed for {state['file_plan']['path']}: {e}")
        raise e
    # state["code_changes"] = code_output.model_dump()
    logger.debug(f"Generated CODE: \n {code_output.model_dump()}")
    return {**state, "code_change": code_output.change.model_dump(), "written_files": []} # reset written_files on each coder attempt so writer starts fresh


class ReviewResult(BaseModel):
    status: Literal["approved", "needs_revision"]
    issues: List[str]
    suggestion: List[str]
    confidence: float = Field(description="The value must be between 0.0 - 1.0")

reviewer_parser = PydanticOutputParser(pydantic_object=ReviewResult)


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

def reviewer_node(state: FileAgentState):
    logger.info("Executing Reviewer Node")
    formatted_prompt = reviewer_prompt.format_messages(
        task=state["task"],
        plan=state["file_plan"],              # actual plan for this file
        existing_files=state.get("existing_file_content", ""),  # single file content
        code_changes=state["code_change"],
        format_instructions=reviewer_parser.get_format_instructions()
    )

    llm_structured = llm.with_structured_output(ReviewResult)
    review_result = llm_structured.invoke(formatted_prompt)
    # review_result = reviewer_parser.parse(response.content)

    retry_count = dict(state.get("retry_count") or {})
    if review_result.status.lower() != "approved":
        retry_count["review"] = retry_count.get("review", 0) + 1

    logger.info(f"Review by Reviewer Node:\n{review_result.model_dump()}")
    
    return {
        **state,
        "review": review_result.model_dump(),  # return delta only, not mutated state
        "retry_count": retry_count
    }


def review_decision(state: FileAgentState) -> Literal["approve", "revise", "abort"]:
    review = state.get("review")
    
    if not review:
        logger.warning("No review found in state, defaulting to revise")
        return "revise"

    retry_count = dict(state.get("retry_count") or {})
    current_count = retry_count.get("review", 0)

    if review.get("status", "").lower() == "approved":
        return "approve"

    if current_count >= MAX_REVIEW_RETRIES:
        logger.warning(f"Max review retries ({MAX_REVIEW_RETRIES}) reached, aborting.")
        return "abort"

    return "revise"

def writer_node(state: FileAgentState, backup: bool = True):
    """
    Persist code changes to disk safely.

    Args:
        state (FileAgentState):
            Contains generated code change

        backup (bool):
            Whether to create backup before overwrite

    Returns:
        dict:
            Updated state with:
                - written_files
                - code_changes

    Behavior:
        - Validates path safety
        - Optionally creates .bak backup
        - Writes file content
    """
    logger.info("Executing Writer Node")

    written_files = []
    code_change = state.get("code_change")

    if not code_change:
        logger.warning("No code_change found in the state, skipping writer.")
        return {**state, "written_files": [], "code_changes": []}

    work_dir = state["work_dir"]
    path = code_change["path"]
    content = code_change["content"]
    action = code_change["action"]

    # Safety check: prevent writing outside working_dir
    if not path.startswith(work_dir):
        logger.critical(f"skipping the file due to wrong file path: {path}")
        return {**state, "written_files": [], "code_changes": []}

    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Backup existing file before overwrite
    if backup and action == "update" and os.path.exists(path):
        backup_path = path + ".bak"
        shutil.copyfile(path, backup_path)
        logger.debug(f"Backup created: {backup_path}")

    # Write file content
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    written_files.append(path)

    logger.debug(f"Written Files: \n{written_files}")

    return {
        **state,
        "written_files": [path],
        "code_changes": [code_change]
    }


def static_check_node(state: FileAgentState):
    """
    Run static analysis (Ruff) on modified files.

    Returns:
        dict:
            Updated state with:
                - static_check_success
                - feedback
                - retry_count

    Behavior:
        - Runs `ruff check`
        - Parses output
        - Generates summarized feedback
    """
    logger.info("Executing Static Check Node")

    written_files = state.get("written_files", [])

    if not written_files:
        logger.info("No files written, skipping static check.")
        return {
            **state,
            "static_check_success": True,
            "static_check_output": "No files written.",
            "feedback": None
        }

    # Run linter
    result = subprocess.run(
        ["ruff", "check", "--output-format", "json"] + written_files,
        capture_output=True,
        text=True
    )

    success = result.returncode == 0
    output = result.stdout + result.stderr

    feedback = None

    if not success:
        feedback = summarize_ruff_issue(result.stdout)
        # Increment retry counter
        retry_count = dict(state.get("retry_count") or {})
        retry_count["static_check_count"] = retry_count.get("static_check_count", 0) + 1
        logger.info(f"Static Check FEEDBACK:\n{feedback}")
    else:
        retry_count = dict(state.get("retry_count") or {})

    return {
        **state,
        "static_check_success": success,
        "static_check_output": output,
        "feedback": feedback,
        "retry_count": retry_count
    }


def summarize_ruff_issue(json_output: str) -> str:
    try:
        issues = json.loads(json_output)
        issue_list = [
            f"{i['filename']}:{i['location']['row']} {i['code']} {i['message']}"
            for i in issues
        ]
        return "Ruff reported:\n" + "\n".join(issue_list)
    except Exception:
        return "Ruff reported issues but JSON parsing failed:\n" + json_output

def static_check_decision(state: FileAgentState):
    if state["static_check_success"]:
        state["retry_count"]["static_check_count"] = 0  # reset
        return "pass" 
    state["retry_count"]["static_check_count"] += 1

    if state["retry_count"]["static_check_count"] >= MAX_STATIC_CHECK_RETRIES:
        return "abort"
    return "retry"


def process_files_node(state: AgentState):
    """Process each file sequentially through the subgraph."""
    logger.info(f"Processing {len(state['plan']['files'])} files sequentially")
    
    all_code_changes = []
    all_written_files = []

    for file_plan in state["plan"]["files"]:
        logger.info(f"Processing file: {file_plan['path']}")
        
        # Build per-file initial state
        file_state = FileAgentState(
            execution_id=state["execution_id"],
            work_dir=state["work_dir"],
            task=state["task"],
            feedback=state.get("feedback"),
            retry_count={},
            file_plan=file_plan,
            existing_file_content=(
                (state.get("existing_files") or {}).get(file_plan["path"])
                if file_plan["action"] == "update"
                else None
            ),
            code_change=None,
            review=None,
            written_files=[],
            static_check_success=None,
            static_check_output=None,
        )

        # Run subgraph for this file
        result = file_subgraph.invoke(file_state)

        # Collect results
        if result.get("code_change"):
            all_code_changes.append(result["code_change"])
        final_written = list(set(result.get("written_files", [])))
        if final_written:
            all_written_files.extend(final_written)

        logger.info(f"Finished processing: {file_plan['path']}")

    return {
        **state,
        "code_changes": all_code_changes,
        "written_files": all_written_files,
    }

########## Coder File-Level SUBGRAPH ################

file_workflow = StateGraph(FileAgentState)
file_workflow.add_node("coder", coder_node)
file_workflow.add_node("reviewer", reviewer_node)
file_workflow.add_node("writer", writer_node)
file_workflow.add_node("static_check", static_check_node)

file_workflow.set_entry_point("coder")
file_workflow.add_edge("coder", "reviewer")
file_workflow.add_conditional_edges(
    "reviewer", review_decision,
    {
        "approve": "writer",
        "abort": "writer",
        "revise" : "coder"
    }
)
file_workflow.add_edge("writer", "static_check")
file_workflow.add_conditional_edges(
    "static_check", 
    static_check_decision,
    {
        "pass": END,
        "abort": END,
        "retry": "coder"
    })

file_subgraph = file_workflow.compile()

######### Main Graph ################################
workflow = StateGraph(AgentState)
workflow.add_node("setup", setup_node)
workflow.add_node("file_structure", file_structure_node)
workflow.add_node("planner", planner_node, retry_policy=RetryPolicy(max_attempts=3))
workflow.add_node("reader", reader_node)
workflow.add_node("process_files", process_files_node)
# workflow.add_node("coder", coder_node, retry_policy=RetryPolicy(max_attempts=3))
# workflow.add_node("reviewer", reviewer_node)
# workflow.add_node("writer", writer_node)
# workflow.add_node("static_check", static_check_node, retry_policy=RetryPolicy(max_attempts=3))
# workflow.add_node("fan_out", fan_out_node)
# workflow.add_node("skip_reader", skip_reader_node)


workflow.set_entry_point("setup")

workflow.add_edge("setup", "file_structure")
workflow.add_edge("file_structure", "planner")
workflow.add_conditional_edges("planner", should_read)
# workflow.add_edge("reader", "coder")
# workflow.add_edge("coder", "reviewer")
# workflow.add_conditional_edges(
#     "reviewer", review_decision,
#     {
#         "approve": "writer",
#         "abort": "writer",
#         "revise" : "coder"
#     }
# )
# workflow.add_edge("writer", "static_check")
# workflow.add_conditional_edges(
#     "static_check", 
#     static_check_decision,
#     {
#         "pass": END,
#         "abort": END,
#         "retry": "coder"
#     })
workflow.add_edge("reader", "process_files")
# workflow.add_conditional_edges("skip_reader", fan_out_edges)
# workflow.add_conditional_edges("fan_out", fan_out_edges)
# workflow.add_edge("file_subgraph", "fan_in")
workflow.add_edge("process_files", END)


graph = workflow.compile()
print(graph.get_graph().edges)
# Get binary PNG data
png_data = graph.get_graph().draw_mermaid_png()

# Save to file
output_file = "python_agent_workflow_graph.png"

with open(output_file, "wb") as f:
    f.write(png_data)

print(f"Graph saved to {output_file}")
# Draw main graph only, subgraph as black box
graph.get_graph(xray=False).draw_mermaid_png(output_file_path="main_graph.png")

# Draw with subgraph expanded (will look complex but accurate)
graph.get_graph(xray=True).draw_mermaid_png(output_file_path="full_graph.png")

config = {"recursion_limit": 50}
input_state = {"task": "Write a program for fibonacci series and for scienctific calculator in detail in separate files."}
result = graph.invoke(input_state, config=config)
logger.info("EXECUTION COMPLETED!")
print(result)