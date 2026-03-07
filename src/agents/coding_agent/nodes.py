from typing_extensions import Dict
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from src.config.llm_config import llm
from src.config.logging_config import logger
from .tools import make_tools
from .states import AgentState, END
from .lsp_tools import lsp_find_definition, lsp_find_references, lsp_get_file_symbols
from .git_tools import get_git_context, git_get_file_diff, git_get_recent_commits

import json

# ── PROMPTS (static, no working_dir yet) ──────────────────────────────

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

EXECUTOR_PROMPT = """You are an expert software engineer and execution agent.

You will receive a structured plan. Your job is to execute it precisely:
1. Read all files listed in files_to_read
2. Follow each step in order
3. Make surgical edits using apply_diff (preferred) or write_file for new files
4. Never add markdown fences to file content
5. Preserve all existing code that doesn't need to change

After all edits, summarize what you changed and why.
"""

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

def build_nodes(working_dir: str):
    """Build all nodes with tools locked to working_dir."""

    # Tools are created here — bound to working_dir via closure
    tools = make_tools(working_dir)

    planner_tools = [
        *tools["planner"],
        lsp_find_definition,
        lsp_find_references,
        lsp_get_file_symbols,
        git_get_file_diff,
        git_get_recent_commits,
    ]
    executor_tools = tools["executor"]
    reviewer_tools = [*tools["reviewer"], git_get_file_diff]

    planner_llm = llm.bind_tools(planner_tools)
    executor_llm = llm.bind_tools(executor_tools)
    reviewer_llm = llm.bind_tools(reviewer_tools)

    planner_tool_node = ToolNode(planner_tools)
    executor_tool_node = ToolNode(executor_tools)
    reviewer_tool_node = ToolNode(reviewer_tools)

    constraints = f"""
IMPORTANT CONSTRAINTS:
- Working directory: {working_dir}
- ONLY explore and modify files within this directory
- ALL file paths must be absolute and start with {working_dir}
- Never access files outside this directory
"""

    # ── GIT CONTEXT ───────────────────────────────────────────────────
    def git_context_node(state: AgentState):
        logger.info("Starting GIT Node")
        context = get_git_context(state["working_dir"])

        if context is None:
            return {
                "git_context": None,
                "messages": [HumanMessage(content="=== GIT CONTEXT ===\nNot a git repository.\n===================")]
            }

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

    # ── PLANNER ───────────────────────────────────────────────────────
    def planner_node(state: AgentState):
        logger.info("Starting PLANNER Node")
        response = planner_llm.invoke([
            {"role": "system", "content": PLANNER_PROMPT + constraints},
            *state["messages"]   # includes git context + user request
        ])
        return {"messages": [response]}

    def planner_should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "planner_tools"
        return "extract_plan"

    def extract_plan_node(state: AgentState):
        logger.info("Starting EXTRACT PLAN Node")
        content = state["messages"][-1].content

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            plan = json.loads(content.strip())
        except json.JSONDecodeError:
            plan = {
                "task_description": content,
                "files_to_read": [],
                "files_to_edit": [],
                "steps": [content]
            }

        return {"plan": plan}

    # ── EXECUTOR ──────────────────────────────────────────────────────
    def executor_node(state: AgentState):
        logger.info("Starting EXECUTOR Node")
        plan = state["plan"]

        plan_message = HumanMessage(content=f"""
Here is your plan to execute:

Task: {plan['task_description']}
Files to read first: {plan['files_to_read']}
Files to edit: {plan['files_to_edit']}

Steps:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(plan['steps']))}

Execute this plan now.
        """)

        response = executor_llm.invoke([
            {"role": "system", "content": EXECUTOR_PROMPT + constraints},
            *state["messages"],   # ✅ keep full history (git context etc.)
            plan_message          # ✅ append plan as latest message
        ])
        return {"messages": [response]}

    def executor_should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "executor_tools"
        return "reviewer"

    # ── REVIEWER ──────────────────────────────────────────────────────
    def reviewer_node(state: AgentState):
        logger.info("Starting REVIEWER Node")
        plan = state["plan"]

        review_request = HumanMessage(content=f"""
Original task: {plan['task_description']}
Files that were edited: {plan['files_to_edit']}

Please review the changes now.
        """)

        response = reviewer_llm.invoke([
            {"role": "system", "content": REVIEWER_PROMPT + constraints},
            *state["messages"],   # ✅ full history so reviewer sees what executor did
            review_request
        ])
        return {"messages": [response]}

    def reviewer_should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "reviewer_tools"
        return "process_review"

    def process_review_node(state: AgentState):
        logger.info("Starting PROCESS REVIEW Node")
        content = state["messages"][-1].content

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]

        try:
            review = json.loads(content.strip())
            status = review.get("status", "needs_revision")
            feedback = review.get("feedback", "")
        except Exception:
            status = "needs_revision"
            feedback = content

        return {
            "review_status": status,
            "review_feedback": feedback,
            "revision_count": state.get("revision_count", 0) + 1
        }

    def route_after_review(state: AgentState):
        if state["review_status"] == "approved":
            return END
        if state.get("revision_count", 0) >= 2:
            return END
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