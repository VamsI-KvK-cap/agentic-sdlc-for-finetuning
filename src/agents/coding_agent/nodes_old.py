from typing_extensions import Dict
from langgraph.prebuilt import ToolNode
from src.config.llm_config import llm
from src.config.logging_config import logger
from .tools import *
from .states import *
from .lsp_tools import lsp_find_definition, lsp_find_references, lsp_get_file_symbols
from .git_tools import get_git_context, git_get_file_diff, git_get_recent_commits, git_get_blame

import json

# ── GIT DIFF ───────────────────────────────────────────────────────────
def git_context_node(state: AgentState) -> AgentState :
    """Runs before planner — injects git awareness into state."""
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting GIT Node")
    context = get_git_context(state["working_dir"])

    if context is None:
    # Not a git repo — skip silently, planner works without git context
        return {
            "git_context": None,
            "messages": [HumanMessage(content="=== GIT CONTEXT ===\nNot a git repository. Proceeding without git awareness.\n===================")]
        }
    # Also inject into messages so planner LLM sees it naturally
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
    return {
        "git_context": context,
        "messages": [HumanMessage(content=summary)]
    }

# ── PLANNER ───────────────────────────────────────────────────────────
planner_tools = [
    list_directory,
    search_code,
    lsp_find_definition,    
    lsp_find_references,
    lsp_get_file_symbols,
    git_get_file_diff, 
    git_get_recent_commits,
]
planner_llm = llm.bind_tools(planner_tools)
planner_tool_node = ToolNode(planner_tools)

PLANNER_PROMPT = """You are a senior software architect and planning agent.

At the start of each message you will receive a GIT CONTEXT block showing:
- Which files are already modified in this session
- What the recent commit history looks like

Use this to:
- Prioritise reading files that are already changed (they are most relevant)
- Avoid re-planning changes that are already made
- Understand the broader intent from recent commit messages

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
4. Build a precise plan — you now know EXACTLY which files need changes

Your final response (after exploring) MUST be valid JSON in this exact format:
{
  "task_description": "...",
  "files_to_read": ["path/to/file.py"],
  "files_to_edit": ["path/to/file.py"],
  "steps": [
    "Read auth/login.py to understand current implementation",
    "Add input validation to the login() function",
    "..."
  ]
}

Do not make any edits yourself. Only plan.
"""

def planner_node(state: AgentState):
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting PLANNER Node")
    # Inject working_dir into system prompt dynamically
    planner_prompt_with_context = PLANNER_PROMPT + f"""

IMPORTANT CONSTRAINTS:
- Working directory: {state['working_dir']}
- ONLY explore and modify files within this directory
- ALL file paths must be absolute and start with {state['working_dir']}
- Never access files outside this directory
"""
    response = planner_llm.invoke([
        {"role": "system", "content": planner_prompt_with_context},
        *state["messages"]
    ])
    return {"messages": [response]}

def planner_should_continue(state: AgentState):
    last = state["messages"][-1]
    # If tool calls exist, keep exploring
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "planner_tools"
    # Otherwise planner is done — extract the plan
    return "extract_plan"

def extract_plan_node(state: AgentState):
    """Parse the planner's final JSON response into structured Plan."""
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting EXTRACT PLAN Node")
    last_message = state["messages"][-1]
    content = last_message.content
    
    # Strip markdown fences if present (defensive)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        plan = json.loads(content.strip())
    except json.JSONDecodeError:
        # Fallback: ask planner to retry
        plan = {"task_description": content, "files_to_read": [], 
                "files_to_edit": [], "steps": [content]}
    
    return {"plan": plan}


# ── EXECUTOR ──────────────────────────────────────────────────────────
executor_tools = [read_file, apply_diff, write_file]
executor_llm = llm.bind_tools(executor_tools)
executor_tool_node = ToolNode(executor_tools)

EXECUTOR_PROMPT = """You are an expert software engineer and execution agent.

You will receive a structured plan. Your job is to execute it precisely:
1. Read all files listed in files_to_read
2. Follow each step in order
3. Make surgical edits using apply_diff (preferred) or write_file for new files
4. Never add markdown fences to file content
5. Preserve all existing code that doesn't need to change

After all edits, respond with a JSON summary:
{
  "changes": [
    {
      "path": "auth/login.py",
      "summary": "Added input validation for username and password fields"
    }
  ]
}
"""

def executor_node(state: AgentState):
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting EXECUTOR Node")
    plan = state["plan"]
    plan_message = HumanMessage(content=f"""
Here is your plan to execute:

Task: {plan['task_description']}

Files to read first: {plan['files_to_read']}
Files to edit: {plan['files_to_edit']}

Steps:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(plan['steps']))}

Working directory: {state['working_dir']}

Execute this plan now.
    """)

    executor_prompt_with_context = EXECUTOR_PROMPT + f"""

IMPORTANT CONSTRAINTS:
- Working directory: {state['working_dir']}
- ONLY read and edit files within {state['working_dir']}
- ALL paths must be absolute starting with {state['working_dir']}
"""
    
    response = executor_llm.invoke([
        {"role": "system", "content": executor_prompt_with_context},
        plan_message
    ])
    return {"messages": [response]}

def executor_should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "executor_tools"
    return "reviewer"


# ── REVIEWER ──────────────────────────────────────────────────────────
reviewer_tools = [read_file_for_review, run_syntax_check, git_get_file_diff]
reviewer_llm = llm.bind_tools(reviewer_tools)
reviewer_tool_node = ToolNode(reviewer_tools)

REVIEWER_PROMPT = """You are a senior code reviewer agent.

Your job:
1. Read the files that were edited
2. Run syntax checks
3. Verify the changes match the original task
4. Check for: bugs, broken imports, missing edge cases, security issues

Your final response MUST be valid JSON:
{
  "status": "approved" or "needs_revision",
  "feedback": "...",
  "issues": ["issue 1", "issue 2"]  // empty list if approved
}

Be strict but fair. Only approve if the changes are correct and complete.
"""

def reviewer_node(state: AgentState):
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting REVIEWER Node")
    plan = state["plan"]
    last_executor_msg = state["messages"][-1].content
    
    review_request = HumanMessage(content=f"""
Original task: {plan['task_description']}
Files that were edited: {plan['files_to_edit']}
Working directory: {state['working_dir']}

Executor summary: {last_executor_msg}

Please review the changes now.
    """)
    
    reviewr_prompt_with_context = REVIEWER_PROMPT + f"""

IMPORTANT CONSTRAINTS:
- Working directory: {state['working_dir']}
- ONLY read and edit files within {state['working_dir']}
- ALL paths must be absolute starting with {state['working_dir']}
"""
    
    response = reviewer_llm.invoke([
        {"role": "system", "content": reviewr_prompt_with_context},
        review_request
    ])
    return {"messages": [response]}

def reviewer_should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "reviewer_tools"
    return "process_review"

def process_review_node(state: AgentState):
    """Parse reviewer decision and decide next step."""
    logger.debug(f"Received STATE:\n{state}")
    logger.info("Starting PROCESS REVIEW Node")
    content = state["messages"][-1].content
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    
    try:
        review = json.loads(content.strip())
        status = review.get("status", "needs_revision")
        feedback = review.get("feedback", "")
    except:
        status = "needs_revision"
        feedback = content
    
    return {
        "review_status": status,
        "review_feedback": feedback,
        "revision_count": state.get("revision_count", 0) + 1
    }

def route_after_review(state: AgentState):
    """Approve or send back to executor for revision."""
    if state["review_status"] == "approved":
        return END
    if state.get("revision_count", 0) >= 2:  # Max 2 revision attempts
        return END
    return "executor"  # Loop back for revision