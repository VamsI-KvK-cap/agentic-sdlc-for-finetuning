from langchain_core.tools import tool
from pathlib import Path
import os, subprocess

def _safe_path(path: str, working_dir: str) -> str:
    """Resolve path and ensure it stays within working_dir."""
    resolved = (Path(working_dir) / Path(path)).resolve()
    if not str(resolved).startswith(str(Path(working_dir).resolve())):
        raise ValueError(f"Access denied: {path} is outside working directory {working_dir}")
    return str(resolved)


def make_tools(working_dir: str):
    """Create all tools pre-bound to working_dir."""

    # ── PLANNER TOOLS (read-only, exploration) ────────────────────────
    @tool
    def list_directory(path: str) -> str:
        """Recursively list project files. Path is relative to working directory."""
        safe = _safe_path(path, working_dir)
        result = []
        for root, dirs, files in os.walk(safe):
            dirs[:] = [d for d in dirs if d not in
                       ['.git', 'node_modules', '__pycache__', '.venv', 'dist']]
            level = root.replace(safe, '').count(os.sep)
            indent = '  ' * level
            result.append(f"{indent}{os.path.basename(root)}/")
            for file in files:
                result.append(f"  {indent}{file}")
        return "\n".join(result)

    @tool
    def search_code(pattern: str) -> str:
        """Search for a pattern across all code files in working directory."""
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "-l", pattern, working_dir],
            capture_output=True, text=True
        )
        return result.stdout[:2000]

    # ── EXECUTOR TOOLS (read + write) ─────────────────────────────────
    @tool
    def read_file(path: str) -> str:
        """Read full contents of a file."""
        safe = _safe_path(path, working_dir)
        with open(safe, "r", encoding="utf-8") as f:
            return f.read()

    @tool
    def apply_diff(path: str, old_str: str, new_str: str) -> str:
        """Replace exact string in a file. Preferred for targeted edits."""
        safe = _safe_path(path, working_dir)
        with open(safe, "r", encoding="utf-8") as f:
            content = f.read()
        if old_str not in content:
            return f"ERROR: Target string not found in {path}"
        updated = content.replace(old_str, new_str, 1)
        with open(safe, "w", encoding="utf-8") as f:
            f.write(updated)
        return f"OK: Updated {path}"

    @tool
    def write_file(path: str, content: str) -> str:
        """Fully overwrite a file. Use only for new files or full rewrites."""
        safe = _safe_path(path, working_dir)
        os.makedirs(os.path.dirname(safe), exist_ok=True)
        with open(safe, "w", encoding="utf-8") as f:
            f.write(content)
        return f"OK: Wrote {path}"

    # ── REVIEWER TOOLS (read-only, verify) ────────────────────────────
    @tool
    def read_file_for_review(path: str) -> str:
        """Read a file to verify changes look correct."""
        safe = _safe_path(path, working_dir)
        with open(safe, "r", encoding="utf-8") as f:
            return f.read()

    @tool
    def run_syntax_check(path: str) -> str:
        """Run Python syntax check on a file."""
        safe = _safe_path(path, working_dir)
        result = subprocess.run(
            ["python", "-m", "py_compile", safe],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"OK: {path} has valid syntax"
        return f"SYNTAX ERROR in {path}:\n{result.stderr}"

    return {
        "planner": [list_directory, search_code],
        "executor": [read_file, apply_diff, write_file],
        "reviewer": [read_file_for_review, run_syntax_check]
    }