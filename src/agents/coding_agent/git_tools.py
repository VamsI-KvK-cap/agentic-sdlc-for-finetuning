import subprocess
from pathlib import Path
from langchain_core.tools import tool

def _run_git(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def _is_git_repo(working_dir: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=working_dir,
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def get_git_context(working_dir: str) -> dict:
    """Returns None if not a git repo. 
    Else gather full git context — called once before planner runs."""
        
    if not _is_git_repo(working_dir):
        return None
    
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], working_dir)
    last_commit = _run_git(["log", "-1", "--oneline"], working_dir)
    
    # Files modified but not staged
    unstaged = _run_git(["diff", "--name-only"], working_dir)
    
    # Files staged for commit
    staged = _run_git(["diff", "--cached", "--name-only"], working_dir)
    
    # All changed files vs last commit (staged + unstaged)
    changed = _run_git(["diff", "HEAD", "--name-only"], working_dir)

    changed_files = [f for f in changed.splitlines() if f]
    staged_files = [f for f in staged.splitlines() if f]

    # Compact diff summary — what actually changed in those files
    diff_summary = _run_git(
        ["diff", "HEAD", "--stat"],   # e.g. "auth/login.py | 12 ++---"
        working_dir
    )

    return {
        "branch": branch,
        "last_commit": last_commit,
        "changed_files": changed_files,
        "staged_files": staged_files,
        "diff_summary": diff_summary or "No changes since last commit"
    }


# ── Tools for planner/reviewer to use during their loop ───────────────

@tool
def git_get_file_diff(file_path: str, working_dir: str) -> str:
    """Get the full diff of a specific file since last commit."""
    diff = _run_git(["diff", "HEAD", "--", file_path], working_dir)
    return diff or f"No changes in {file_path} since last commit"

@tool
def git_get_recent_commits(working_dir: str, count: int = 5) -> str:
    """Get the last N commit messages for context."""
    log = _run_git(
        ["log", f"-{count}", "--oneline", "--no-merges"],
        working_dir
    )
    return log or "No commits found"

@tool
def git_get_blame(file_path: str, working_dir: str) -> str:
    """See who last changed each line — useful for understanding ownership."""
    blame = _run_git(["blame", "--line-porcelain", file_path], working_dir)
    # Trim to avoid flooding context
    lines = blame.splitlines()[:60]
    return "\n".join(lines)