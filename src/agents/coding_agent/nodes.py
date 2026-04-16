# Module docstring explaining the purpose of this module
"""
Nodes Module for Coding Agent Workflow.

This module defines the LangGraph nodes and edges for the coding agent workflow.
It implements a multi-phase process including planning, execution, and review phases
with integrated Git and LSP tools for code analysis and modification.

The workflow consists of:
- Git context gathering
- Planning phase with file exploration and LSP analysis
- Execution phase with surgical code edits
- Review phase with syntax checking and validation

All nodes are pre-bound to a working directory for security and consistency.
"""

# Import os module for file system operations
import os

# Import Dict from typing_extensions for type hints
from typing_extensions import Dict

# Import ToolNode from langgraph.prebuilt for tool execution
from langgraph.prebuilt import ToolNode

# Import HumanMessage from langchain_core.messages for message handling
from langchain_core.messages import HumanMessage

# Import llm from config for language model
from src.config.llm_config import llm

# Import logger from config for logging
from src.config.logging_config import logger

# Import make_tools from local tools module
from .tools import make_tools

# Import AgentState and END from states module
from .states import AgentState, END

# Import init_lsp and make_lsp_tools from lsp_tools module
from .lsp_tools import init_lsp, make_lsp_tools

# Import get_git_context and make_git_tools from git_tools module
from .git_tools import get_git_context, make_git_tools

# Import json module for JSON parsing
import json

# Maximum iterations for planner and executor loops
MAX_ITERATIONS = 3
# ── PROMPTS (static, no working_dir yet) ──────────────────────────────

# Prompt for the planner agent
PLANNER_PROMPT = """You are a senior software architect and planning agent.

At the start of each message you will receive a GIT CONTEXT block showing:
- Which files are already modified in this session
- What the recent commit history looks like

You have access to:
- list_directory: explore project structure
- search_code: grep for patterns
- lsp_find_definition: find exactly where any symbol is defined
- lsp_find_references: find every file that uses a symbol
- lsp_get_file_symbols: list all functions/classes in a file

WORKFLOW:
1. list_directory to understand structure
2. lsp_get_file_symbols on relevant files to see what's inside
3. lsp_find_references on symbols that will be affected by the change
4. Build a precise plan

Your final response MUST be valid JSON:
{{
  "task_description": "...",
  "files_to_read": ["path/to/file.py"],
  "files_to_edit": ["path/to/file.py"],
  "steps": ["step 1", "step 2"]
}}

Do not make any edits yourself. Only plan.
"""

# Prompt for the executor agent
EXECUTOR_PROMPT = """You are an expert software engineer and execution agent.

You will receive a structured plan. Your job is to execute it precisely:
1. Read all files listed in files_to_read
2. Follow each step in order
3. Make surgical edits using apply_diff (preferred) or write_file for new files
4. Never add markdown fences to file content
5. Preserve all existing code that doesn't need to change

After all edits, summarize what you changed and why.
"""

# Prompt for the reviewer agent
REVIEWER_PROMPT = """You are a senior code reviewer agent.

Your job:
1. Read the files that were edited
2. Run syntax checks
3. Verify the changes match the original task
4. Check for: bugs, broken imports, missing edge cases, security issues

Your final response MUST be valid JSON:
{{
  "status": "approved",
  "feedback": "...",
  "issues": []
}}
or
{{
  "status": "needs_revision",
  "feedback": "...",
  "issues": ["issue 1", "issue 2"]
}}
"""

# ── NODE FACTORY — call this with working_dir to get all nodes ─────────

def build_nodes(working_dir: str) -> Dict:
    # Function docstring
    """
    Build all LangGraph nodes with tools locked to a specific working directory.

    This factory function creates all the nodes, tool nodes, and edges needed for the
    coding agent workflow. All tools are pre-bound to the working directory to prevent
    accidental access to files outside the intended scope.

    Args:
        working_dir (str): The root directory path for all operations.
            All file paths will be constrained to this directory.

    Returns:
        Dict: A dictionary containing:
            - "nodes": Dict of node functions
            - "tool_nodes": Dict of ToolNode instances
            - "edges": Dict of edge/conditional functions

    Example:
        >>> components = build_nodes("/path/to/project")
        >>> graph = StateGraph(AgentState)
        >>> for name, node in components["nodes"].items():
        ...     graph.add_node(name, node)
    """
    # Tools are created here — bound to working_dir via closure
    tools = make_tools(working_dir)
    # Create git tools bound to working directory
    git_tools = make_git_tools(working_dir)
    # Create LSP tools bound to working directory
    lsp_tools = make_lsp_tools(working_dir)
    # Unpack git tools into individual variables
    git_get_file_diff, git_get_recent_commits, git_get_blame = git_tools
    # Unpack LSP tools into individual variables
    lsp_find_definition, lsp_find_references, lsp_get_file_symbols = lsp_tools

    # Define tools available to planner agent
    planner_tools = [
        # Include all planner tools from make_tools
        *tools["planner"],
        # Add LSP tools for code analysis
        lsp_find_definition,
        lsp_find_references,
        lsp_get_file_symbols,
        # Add git tools for context
        git_get_file_diff,
        git_get_recent_commits,
    ]
    # Define tools available to executor agent
    executor_tools = tools["executor"]
    # Define tools available to reviewer agent
    reviewer_tools = [*tools["reviewer"], git_get_file_diff]

    # Bind planner LLM with its tools
    planner_llm = llm.bind_tools(planner_tools)
    # Bind executor LLM with its tools
    executor_llm = llm.bind_tools(executor_tools)
    # Bind reviewer LLM with its tools
    reviewer_llm = llm.bind_tools(reviewer_tools)

    # Create ToolNode for planner tools
    planner_tool_node = ToolNode(planner_tools)
    # Create ToolNode for executor tools
    executor_tool_node = ToolNode(executor_tools)
    # Create ToolNode for reviewer tools
    reviewer_tool_node = ToolNode(reviewer_tools)

    # Define security constraints for all agents
    constraints = f"""
IMPORTANT CONSTRAINTS:
- Working directory: {working_dir}
- ONLY explore and modify files within this directory
- ALL file paths must be absolute and start with {working_dir}
- Never access files outside this directory
"""

    # ── GIT CONTEXT ───────────────────────────────────────────────────
    def git_context_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Gather and inject Git repository context into the conversation.

        This node retrieves Git context information including branch, recent commits,
        changed files, and diff summaries. This context helps subsequent agents
        understand the current state of the repository.

        Args:
            state (AgentState): The current agent state containing working_dir and messages.

        Returns:
            Dict: Updated state with git_context and a new HumanMessage containing
                the formatted Git context summary.
        """
        # Log the start of the git context node
        logger.info("Starting GIT Node")
        # Get git context from the working directory
        context = get_git_context(state["working_dir"])

        # If not a git repository, return null context
        if context is None:
            return {
                "git_context": None,
                "messages": [HumanMessage(content="=== GIT CONTEXT ===\nNot a git repository.\n===================")]
            }

        # Format the git context summary
        summary = f"""
=== GIT CONTEXT ===
Branch: {context['branch']}
Last commit: {context['last_commit']}
Files changed since last commit: {context['changed_files'] or 'none'}
Staged files: {context['staged_files'] or 'none'}
Diff summary:
{context['diff_summary']}
===================
"""
        # Return updated state with context and message
        return {
            "git_context": context,
            "messages": [HumanMessage(content=summary)]
        }

    # ── PLANNER ───────────────────────────────────────────────────────
    # Phase 1: exploration only — returns file tree
    # Phase 2: LSP analysis — only on paths from phase 1

    # ── PLANNER ───────────────────────────────────────────────────────
    # Phase 1: exploration only — returns file tree
    # Phase 2: LSP analysis — only on paths from phase 1

    def planner_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Execute the planning phase of the coding workflow.

        The planner analyzes the task, explores the codebase structure, and creates
        a detailed execution plan. It uses Git context and LSP tools to understand
        the current state and dependencies.

        Args:
            state (AgentState): Current agent state with messages and working_dir.

        Returns:
            Dict: Updated state with planner response message and iteration count.
        """
        # Log the start of the planner node
        logger.info("Starting PLANNER Node")

        # Force phase 1: get real file tree first, inject it into context
        file_tree = _get_file_tree(state["working_dir"])

        # Create planner prompt with file tree context
        planner_prompt_with_context = PLANNER_PROMPT + f"""

    IMPORTANT CONSTRAINTS:
    - Working directory: {state['working_dir']}
    - ALL file paths must be absolute and start with {state['working_dir']}
    - Never construct or guess paths — only use paths from the file tree below
    - When calling LSP tools, copy paths EXACTLY from the file tree

    CURRENT FILE TREE (use ONLY these paths):
    {file_tree}
    """
        # Invoke the planner LLM with system prompt and conversation history
        response = planner_llm.invoke([
            {"role": "system", "content": planner_prompt_with_context},
            *state["messages"]
        ])
        # Return updated state with response and incremented iteration count
        return {
            "messages": [response],
            "planner_iterations" : state.get("planner_iterations", 0) + 1 # increment    
        }


    def _get_file_tree(working_dir: str) -> str:
        # Function docstring
        """
        Build a real file tree for the working directory.

        This helper function walks the directory tree and collects all file paths,
        excluding common directories like .git, node_modules, etc. The result is
        injected into the planner context to ensure only valid paths are used.

        Args:
            working_dir (str): The root directory to scan.

        Returns:
            str: Newline-separated list of absolute file paths.
        """
        # Initialize result list
        result = []
        # Walk the directory tree
        for root, dirs, files in os.walk(working_dir):
            # Filter out unwanted directories
            dirs[:] = [d for d in dirs if d not in
                    ['.git', 'node_modules', '__pycache__', '.venv', 'dist']]
            # Add each file with absolute path
            for file in files:
                abs_path = os.path.join(root, file)
                result.append(abs_path)  # ✅ absolute paths only
        # Return newline-separated string
        return "\n".join(result)

    def planner_should_continue(state: AgentState) -> str:
        # Function docstring
        """
        Determine the next step after planner execution.

        Checks if the planner needs to continue using tools or if it's ready
        to extract the plan. Also enforces maximum iteration limits.

        Args:
            state (AgentState): Current agent state.

        Returns:
            str: Next node name ("planner_tools" or "extract_plan").
        """
        # Get the last message
        last = state["messages"][-1]
        # Get current iteration count
        iterations = state.get("planner_iterations", 0)

        # Check if max iterations reached
        if iterations >= MAX_ITERATIONS:
            logger.warning("Planner hit max iterations - forcing extract_plan")
            return "extract_plan"
        
        # Check if there are tool calls to execute
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "planner_tools"
        # Otherwise, extract the plan
        return "extract_plan"

    def extract_plan_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Extract and parse the plan from the planner's response.

        Attempts to parse JSON from the planner's final response. If JSON parsing
        fails, creates a basic plan structure from the text content.

        Args:
            state (AgentState): Current agent state with planner messages.

        Returns:
            Dict: Updated state containing the parsed plan.
        """
        # Log the start of extract plan node
        logger.info("Starting EXTRACT PLAN Node")
        # Get the last message content
        content = state["messages"][-1].content

        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        # Try to parse the content as JSON
        try:
            plan = json.loads(content.strip())
        except json.JSONDecodeError:
            # Fallback to basic plan structure
            plan = {
                "task_description": content,
                "files_to_read": [],
                "files_to_edit": [],
                "steps": [content]
            }

        # Return state with parsed plan
        return {"plan": plan}

    # ── EXECUTOR ──────────────────────────────────────────────────────
    def executor_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Execute the planned code changes.

        The executor follows the plan created by the planner, reading files,
        making surgical edits, and summarizing the changes made.

        Args:
            state (AgentState): Current agent state with plan and messages.

        Returns:
            Dict: Updated state with executor response and iteration count.
        """
        # Log the start of executor node
        logger.info("Starting EXECUTOR Node")
        # Get the plan from state
        plan = state["plan"]

        # Create plan message for the executor
        plan_message = HumanMessage(content=f"""
Here is your plan to execute:

Task: {plan['task_description']}
Files to read first: {plan['files_to_read']}
Files to edit: {plan['files_to_edit']}

Steps:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(plan['steps']))}

Execute this plan now.
        """)

        # Invoke executor LLM with system prompt, history, and plan
        response = executor_llm.invoke([
            {"role": "system", "content": EXECUTOR_PROMPT + constraints},
            *state["messages"],   # keep full history (git context etc.)
            plan_message          # append plan as latest message
        ])
        # Return updated state with response and incremented iteration count
        return {
            "messages": [response],
            "executor_iterations": state.get("executor_iterations", 0) + 1 # increment
            }

    def executor_should_continue(state: AgentState) -> str:
        # Function docstring
        """
        Determine the next step after executor execution.

        Checks if the executor needs to continue using tools or if it's ready
        for review. Also enforces maximum iteration limits.

        Args:
            state (AgentState): Current agent state.

        Returns:
            str: Next node name ("executor_tools" or "reviewer").
        """
        # Get the last message
        last = state["messages"][-1]
        # Get current iteration count
        iterations = state.get("executor_iterations", 0)

        # Check if max iterations reached
        if iterations >= MAX_ITERATIONS:
            logger.warning("Executor hit max iterations - forcing reviewer")
            return "reviewer"
        
        # Check if there are tool calls to execute
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "executor_tools"
        # Otherwise, proceed to reviewer
        return "reviewer"

    # ── REVIEWER ──────────────────────────────────────────────────────
    def reviewer_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Review the executed changes for correctness and quality.

        The reviewer examines the modified files, runs syntax checks, and validates
        that the changes meet the original requirements and coding standards.

        Args:
            state (AgentState): Current agent state with plan and execution messages.

        Returns:
            Dict: Updated state with reviewer response message.
        """
        # Log the start of reviewer node
        logger.info("Starting REVIEWER Node")
        # Get the plan from state
        plan = state["plan"]

        # Create review request message
        review_request = HumanMessage(content=f"""
Original task: {plan['task_description']}
Files that were edited: {plan['files_to_edit']}

Please review the changes now.
        """)

        # Invoke reviewer LLM with system prompt, history, and review request
        response = reviewer_llm.invoke([
            {"role": "system", "content": REVIEWER_PROMPT + constraints},
            *state["messages"],   # ✅ full history so reviewer sees what executor did
            review_request
        ])
        # Return updated state with response
        return {"messages": [response]}

    def reviewer_should_continue(state: AgentState) -> str:
        # Function docstring
        """
        Determine the next step after reviewer execution.

        Checks if the reviewer needs to continue using tools or if it's ready
        to process the review results.

        Args:
            state (AgentState): Current agent state.

        Returns:
            str: Next node name ("reviewer_tools" or "process_review").
        """
        # Get the last message
        last = state["messages"][-1]
        # Check if there are tool calls to execute
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "reviewer_tools"
        # Otherwise, process the review
        return "process_review"

    def process_review_node(state: AgentState) -> Dict:
        # Function docstring
        """
        Process the reviewer's JSON response and determine next actions.

        Parses the review JSON to extract status, feedback, and issues.
        Updates revision count for workflow control.

        Args:
            state (AgentState): Current agent state with reviewer messages.

        Returns:
            Dict: Updated state with review status, feedback, and revision count.
        """
        # Log the start of process review node
        logger.info("Starting PROCESS REVIEW Node")
        # Get the last message content
        content = state["messages"][-1].content

        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]

        # Try to parse the content as JSON
        try:
            review = json.loads(content.strip())
            status = review.get("status", "needs_revision")
            feedback = review.get("feedback", "")
        except Exception:
            # Fallback for parsing errors
            status = "needs_revision"
            feedback = content

        # Return updated state with review results
        return {
            "review_status": status,
            "review_feedback": feedback,
            "revision_count": state.get("revision_count", 0) + 1
        }

    def route_after_review(state: AgentState) -> str:
        # Function docstring
        """
        Route the workflow based on review results.

        Determines whether to end the workflow (approved or max revisions)
        or return to executor for revisions.

        Args:
            state (AgentState): Current agent state with review status.

        Returns:
            str: Next node name (END or "executor").
        """
        # Check if review approved
        if state["review_status"] == "approved":
            return END
        # Check if max revisions reached
        if state.get("revision_count", 0) >= 2:
            return END
        # Return to executor for revisions
        return "executor"

    # ── Return everything graph.py needs ──────────────────────────────
    return {
        "nodes": {
            "git_context": git_context_node,
            "planner": planner_node,
            "extract_plan": extract_plan_node,
            "executor": executor_node,
            "reviewer": reviewer_node,
            "process_review": process_review_node,
        },
        "tool_nodes": {
            "planner_tools": planner_tool_node,
            "executor_tools": executor_tool_node,
            "reviewer_tools": reviewer_tool_node,
        },
        "edges": {
            "planner_should_continue": planner_should_continue,
            "executor_should_continue": executor_should_continue,
            "reviewer_should_continue": reviewer_should_continue,
            "route_after_review": route_after_review,
        }
    }