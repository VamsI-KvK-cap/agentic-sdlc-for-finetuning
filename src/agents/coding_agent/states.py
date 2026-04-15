# Module docstring explaining the purpose of this module
"""
States Module for Coding Agent Workflow.

This module defines the TypedDict classes that represent the state structures
used throughout the coding agent workflow. These classes provide type safety
and documentation for the data structures passed between LangGraph nodes.

The state includes:
- Plan: Structured execution plan from planner
- FileChange: Details of code modifications
- GitContext: Repository status information
- AgentState: Complete workflow state with messages and control flow
"""

# Import StateGraph, END, MessagesState from langgraph.graph for graph construction
from langgraph.graph import StateGraph, END, MessagesState

# Import TypedDict, Annotated, Literal from typing for type definitions
from typing import TypedDict, Annotated, Literal

# Import add_messages from langgraph.graph.message for message aggregation
from langgraph.graph.message import add_messages

# Import BaseMessage, HumanMessage, AIMessage from langchain_core.messages for message types
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Import operator module (not used in this version)
import operator

# Define Plan TypedDict for structured execution plans
class Plan(TypedDict):
    # Class docstring
    """
    Represents a structured execution plan created by the planner agent.

    This TypedDict defines the format for plans that outline what files to read,
    what files to edit, and the specific steps to execute the task.
    """
    # Task description string
    task_description: str
    # List of files the agent needs to read first
    files_to_read: list[str]
    # List of files that will be changed
    files_to_edit: list[str]
    # Ordered list of what to do
    steps: list[str]

# Define FileChange TypedDict for tracking code modifications
class FileChange(TypedDict):
    # Class docstring
    """
    Represents a single file modification made during execution.

    This TypedDict captures the before/after state of a file change,
    including the path, original content, new content, and a summary
    of what changed and why.
    """
    # Path to the modified file
    path: str
    # Original content before changes
    original_content: str
    # New content after changes
    new_content: str
    # Summary of what changed and why
    summary: str

# Define GitContext TypedDict for repository status information
class GitContext(TypedDict):
    # Class docstring
    """
    Represents the Git repository context for the working directory.

    This TypedDict contains information about the current Git state,
    including branch, recent commits, changed files, and diff summaries
    to help agents understand the repository status.
    """
    # Current branch name
    branch: str
    # Last commit message
    last_commit: str
    # Files modified since last commit
    changed_files: list[str]
    # Files already staged
    staged_files: list[str]
    # Short diff summary of changes
    diff_summary: str

# Define AgentState TypedDict for complete workflow state
class AgentState(TypedDict):
    # Class docstring
    """
    Complete state structure for the coding agent workflow.

    This TypedDict defines all the data that flows through the LangGraph
    workflow, including messages, working directory, Git context, plans,
    file changes, review status, and control flow variables.
    """
    # List of messages with add_messages reducer
    messages: Annotated[list[BaseMessage], add_messages]
    # Working directory path for all operations
    working_dir: str
    # Git repository context or None if not a repo
    git_context: GitContext | None

    # Planner output section
    # Structured execution plan from planner
    plan: Plan | None

    # Executor output section
    # List of file changes made during execution
    file_changes: list[FileChange]

    # Reviewer output section
    # Review status: approved, needs_revision, or pending
    review_status: Literal["approved", "needs_revision", "pending"]
    # Feedback from reviewer
    review_feedback: str

    # Control flow section
    # Revision count to prevent infinite loops
    revision_count: int

    # Structured Summary section
    # Summary of planner output
    planner_summary: Plan
    # Summary of executor output
    executor_summary: FileChange

    # Iteration tracking
    # Number of planner iterations
    planner_iterations: int
    # Number of executor iterations
    executor_iterations: int