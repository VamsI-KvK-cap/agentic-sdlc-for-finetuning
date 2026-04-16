# Module docstring explaining the purpose of this module
"""
Git Tools Module.

This module provides utilities for interacting with Git repositories in the context of
coding agents. It includes functions to check repository status, gather git context,
and create LangChain tools for git operations that can be used by AI agents during
code generation and review workflows.

The module supports:
- Repository detection and context gathering
- File diff analysis
- Commit history retrieval
- Code blame information
- Integration with LangChain tool framework for agent use
"""

# Import subprocess module for executing external commands
import subprocess

# Import Path from pathlib for handling file paths (though not used in this version)
from pathlib import Path

# Import typing constructs for type hints
from typing import List, Dict, Optional, Any

# Import tool decorator from langchain_core for creating tools
from langchain_core.tools import tool


def _run_git(cmd: List[str], cwd: str) -> str:
    # Function docstring
    """
    Execute a git command and return its stdout output.

    This is a low-level helper function that wraps subprocess.run to execute git commands
    in a specified working directory. It captures stdout and returns it as a stripped string,
    handling the common pattern of running git commands programmatically.

    Args:
        cmd (List[str]): The git command arguments as a list (e.g., ["status", "--porcelain"]).
            Should not include the "git" prefix as it's added automatically.
        cwd (str): The working directory path where the git command should be executed.
            Must be a valid directory path.

    Returns:
        str: The stdout output from the git command, stripped of leading/trailing whitespace.
            Returns empty string if the command produces no output.

    Raises:
        subprocess.CalledProcessError: If the git command fails (non-zero exit code).
            This is propagated from subprocess.run.

    Example:
        >>> output = _run_git(["status", "--porcelain"], "/path/to/repo")
        >>> print(output)  # Shows untracked/modified files
    """
    # Execute the git command using subprocess with output capture
    result = subprocess.run(
        # Prepend "git" to the command arguments
        ["git"] + cmd,
        # Set working directory for command execution
        cwd=cwd,
        # Capture both stdout and stderr
        capture_output=True,
        # Return output as string instead of bytes
        text=True
    )
    # Return stdout stripped of whitespace; stderr is available in result.stderr if needed
    return result.stdout.strip()


def _is_git_repo(working_dir: str) -> bool:
    # Function docstring
    """
    Check if the specified directory is a git repository.

    Uses git's built-in command to determine if the working directory is inside
    a git working tree. This is more reliable than checking for .git directory
    as it handles various git configurations and edge cases.

    Args:
        working_dir (str): The directory path to check for git repository status.
            Should be an absolute path for reliability.

    Returns:
        bool: True if the directory is inside a git working tree, False otherwise.
            Returns False for non-git directories or if git command fails.

    Example:
        >>> is_repo = _is_git_repo("/path/to/project")
        >>> if is_repo:
        ...     print("This is a git repository")
    """
    # Run git rev-parse to check if we're inside a git working tree
    result = subprocess.run(
        # Git command to check repository status
        ["git", "rev-parse", "--is-inside-work-tree"],
        # Directory to check
        cwd=working_dir,
        # Capture output for analysis
        capture_output=True,
        # Text mode for string output
        text=True
    )
    # Return True only if command succeeded (exit code 0)
    return result.returncode == 0


def get_git_context(working_dir: str) -> Optional[Dict[str, Any]]:
    """
    Gather comprehensive git repository context for agent decision-making.

    This function collects essential git information that helps AI agents understand
    the current state of the repository. It's called once before the planning phase
    to provide context about branch, recent commits, and file changes. Returns None
    if the directory is not a git repository.

    Args:
        working_dir (str): The repository directory path to analyze.
            Must be a valid git repository path.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing git context information, or None
            if not a git repository. The dictionary includes:
            - "branch" (str): Current branch name
            - "last_commit" (str): Last commit message (oneline format)
            - "changed_files" (List[str]): Files changed since last commit
            - "staged_files" (List[str]): Files staged for commit
            - "diff_summary" (str): Statistical summary of changes

    Raises:
        subprocess.CalledProcessError: If any git command fails during context gathering.

    Example:
        >>> context = get_git_context("/path/to/repo")
        >>> if context:
        ...     print(f"On branch: {context['branch']}")
        ...     print(f"Changed files: {context['changed_files']}")
    """
    # First check if this is actually a git repository
    if not _is_git_repo(working_dir):
        return None

    # Get current branch name using git rev-parse
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], working_dir)

    # Get the last commit message in oneline format
    last_commit = _run_git(["log", "-1", "--oneline"], working_dir)

    # Get files modified but not staged (working directory changes)
    unstaged = _run_git(["diff", "--name-only"], working_dir)

    # Get files staged for commit (index changes)
    staged = _run_git(["diff", "--cached", "--name-only"], working_dir)

    # Get all changed files vs last commit (staged + unstaged)
    changed = _run_git(["diff", "HEAD", "--name-only"], working_dir)

    # Parse changed files into a clean list, filtering out empty strings
    changed_files = [f for f in changed.splitlines() if f]  # List comprehension to filter non-empty file names

    # Parse staged files into a clean list
    staged_files = [f for f in staged.splitlines() if f]  # List comprehension to filter non-empty file names

    # Get compact diff summary showing what changed in each file
    diff_summary = _run_git(
        # Statistical summary like "file.py | 12 ++---"
        ["diff", "HEAD", "--stat"],
        # Working directory for the command
        working_dir
    )

    # Return comprehensive git context dictionary
    return {
        # Current branch name
        "branch": branch,
        # Last commit message
        "last_commit": last_commit,
        # List of changed files
        "changed_files": changed_files,
        # List of staged files
        "staged_files": staged_files,
        # Summary of changes or default message
        "diff_summary": diff_summary or "No changes since last commit"
    }


# ── Tools for planner/reviewer to use during their loop ───────────────

def make_git_tools(working_dir: str) -> List[Any]:
    """
    Create pre-configured git tools bound to a specific working directory.

    This factory function creates LangChain tool instances that are pre-bound to a
    working directory, preventing the LLM from accidentally modifying the intended
    repository path. The tools provide git operations that agents can use during
    their planning and review loops.

    Args:
        working_dir (str): The repository directory path to bind the tools to.
            All git operations will be executed in this directory.

    Returns:
        List[Any]: A list of LangChain tool objects that can be used by agents.
            Includes tools for file diffs, commit history, and code blame.

    Example:
        >>> tools = make_git_tools("/path/to/repo")
        >>> # tools can now be passed to LangChain agents
    """
    # Create git_get_file_diff tool with working directory pre-bound
    @tool
    def git_get_file_diff(file_path: str) -> str:
        """
        Get the full diff of a specific file since the last commit.

        This tool allows agents to examine what changes have been made to a file
        since the last commit, helping them understand the current state and make
        informed decisions about code modifications.

        Args:
            file_path (str): Relative path to the file within the repository.

        Returns:
            str: The git diff output for the file, or a message if no changes exist.
        """
        # Execute git diff for the specific file against HEAD
        diff = _run_git(["diff", "HEAD", "--", file_path], working_dir)
        # Return diff or informative message if no changes
        return diff or f"No changes in {file_path} since last commit"

    # Create git_get_recent_commits tool with working directory pre-bound
    @tool
    def git_get_recent_commits(count: int = 5) -> str:
        """
        Get the last N commit messages for contextual understanding.

        This tool provides recent commit history to help agents understand the
        evolution of the codebase and recent changes that might affect their work.

        Args:
            count (int, optional): Number of recent commits to retrieve. Defaults to 5.

        Returns:
            str: Oneline commit messages, or a message if no commits found.
        """
        # Get recent commit log excluding merges for cleaner output
        log = _run_git(
            # Log command with count, oneline format, no merges
            ["log", f"-{count}", "--oneline", "--no-merges"],
            # Working directory for the command
            working_dir
        )
        # Return log or informative message if no commits
        return log or "No commits found"

    # Create git_get_blame tool with working directory pre-bound
    @tool
    def git_get_blame(file_path: str) -> str:
        """
        Get blame information showing who last changed each line of a file.

        This tool helps agents understand code ownership and recent modifications
        by showing which author and commit last touched each line of code.

        Args:
            file_path (str): Relative path to the file within the repository.

        Returns:
            str: Blame output showing author/commit info per line (limited to 60 lines).
        """
        # Get detailed blame information in porcelain format
        blame = _run_git(["blame", "--line-porcelain", file_path], working_dir)
        # Limit output to first 60 lines to prevent overwhelming responses
        lines = blame.splitlines()[:60]  # Split into lines and take first 60
        # Return formatted blame output
        return "\n".join(lines)  # Join lines back with newlines

    # Return list of all created tools
    return [git_get_file_diff, git_get_recent_commits, git_get_blame]  # List of tool functions