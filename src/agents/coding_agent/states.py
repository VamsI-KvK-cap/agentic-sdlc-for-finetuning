from langgraph.graph import StateGraph, END, MessagesState
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

class Plan(TypedDict):
    task_description: str
    files_to_read: list[str]       # Files agent needs to read first
    files_to_edit: list[str]       # Files that will be changed
    steps: list[str]               # Ordered list of what to do

class FileChange(TypedDict):
    path: str
    original_content: str
    new_content: str
    summary: str                   # What changed and why

class GitContext(TypedDict):
    branch: str
    last_commit: str
    changed_files: list[str]   # Modified since last commit
    staged_files: list[str]    # Already staged
    diff_summary: str          # Short diff of what changed

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    working_dir: str
    git_context: GitContext | None  
    
    # Planner output
    plan: Plan | None
    
    # Executor output
    file_changes: list[FileChange]
    
    # Reviewer output
    review_status: Literal["approved", "needs_revision", "pending"]
    review_feedback: str
    
    # Control flow
    revision_count: int            # Prevent infinite loops

    # Strucutred Summary
    planner_summary: Plan
    executor_summary: FileChange