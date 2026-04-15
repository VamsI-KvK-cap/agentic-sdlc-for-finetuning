from langchain_core.tools import tool  # Decorator to expose functions as LangChain tools
from pathlib import Path  # Safer path handling (cross-platform)
import os, subprocess  # OS operations + shell command execution


def _safe_path(path: str, working_dir: str) -> str:
    """
    Resolve path and ensure it stays within working_dir.

    This function protects against directory traversal attacks by ensuring
    that any user-provided path is strictly contained within the allowed
    working directory.

    Parameters:
        path (str):
            Relative or absolute file path provided by the agent or user.
            This may include nested paths like "src/main.py" or "../etc/passwd".

        working_dir (str):
            The root directory that all file operations must be constrained to.
            Any resolved path must remain within this directory.

    Returns:
        str:
            The fully resolved absolute path (as a string) that is guaranteed
            to be inside the working directory.

    Raises:
        ValueError:
            If the resolved path points outside the working directory.
            This prevents unauthorized file access (e.g., system files).

    Notes:
        - Uses pathlib.Path.resolve() to normalize symbolic links and relative paths.
        - The security check ensures that the resolved path starts with working_dir.
        - This function is critical for sandboxing file operations safely.
    """

    # Combine working directory with user-provided path, then resolve to absolute path
    resolved = (Path(working_dir) / Path(path)).resolve()

    # Security check: ensure resolved path is still inside working_dir
    if not str(resolved).startswith(str(Path(working_dir).resolve())):
        raise ValueError(f"Access denied: {path} is outside working directory {working_dir}")

    return str(resolved)


def make_tools(working_dir: str):
    """
    Create and return a collection of LangChain tools bound to a specific working directory.

    This function acts as a factory that generates tool functions used by different
    phases of an agent workflow:
        - Planner (exploration, read-only)
        - Executor (file modification)
        - Reviewer (validation and verification)

    All tools internally use the provided working directory to ensure safe and
    consistent file operations.

    Parameters:
        working_dir (str):
            The root directory where all file operations will be performed.
            This directory acts as a sandbox for the agent.

    Returns:
        dict[str, list]:
            A dictionary containing categorized tool lists:
                {
                    "planner":  [list_directory, search_code],
                    "executor": [read_file, apply_diff, write_file],
                    "reviewer": [read_file_for_review, run_syntax_check]
                }

            Each key corresponds to a phase in the agent workflow.

    Notes:
        - All tools are closures that capture `working_dir`.
        - Ensures consistent and secure file access across all tools.
        - Designed for integration with LangGraph / LangChain agent pipelines.
    """

    # ── PLANNER TOOLS (read-only, exploration) ────────────────────────
    @tool
    def list_directory(path: str) -> str:
        """
        Recursively list project files. Path is relative to working directory.

        Parameters:
            path (str):
                Relative path from working_dir to list files from.
                Example: ".", "src/", "app/utils"

        Returns:
            str:
                A formatted string representing the directory tree structure.
                Includes indentation to reflect folder hierarchy.

        Notes:
            - Skips common non-relevant directories like `.git`, `node_modules`.
            - Useful for giving the agent an overview of the project structure.
        """

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
        """
        Search for a pattern across all Python files in the working directory.

        Parameters:
            pattern (str):
                The string or regex pattern to search for.

        Returns:
            str:
                A truncated string (max ~2000 chars) containing matching file paths
                and line references returned by grep.

        Notes:
            - Uses `grep` for fast recursive searching.
            - Limited output prevents exceeding LLM context window.
            - Only searches `.py` files.
        """

        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "-l", pattern, working_dir],
            capture_output=True, text=True
        )

        return result.stdout[:2000]

    # ── EXECUTOR TOOLS (read + write) ─────────────────────────────────
    @tool
    def read_file(path: str) -> str:
        """
        Read the full contents of a file.

        Parameters:
            path (str):
                Relative path to the file inside working_dir.

        Returns:
            str:
                Entire file content as a string.

        Raises:
            FileNotFoundError:
                If the file does not exist.

        Notes:
            - Uses UTF-8 encoding.
            - Intended for agent inspection before modification.
        """

        safe = _safe_path(path, working_dir)
        with open(safe, "r", encoding="utf-8") as f:
            return f.read()

    @tool
    def apply_diff(path: str, old_str: str, new_str: str) -> str:
        """
        Replace an exact string in a file (single occurrence).

        Parameters:
            path (str):
                Relative path to the file.

            old_str (str):
                The exact string to search for in the file.

            new_str (str):
                The replacement string.

        Returns:
            str:
                Status message indicating success or failure.

        Behavior:
            - Replaces ONLY the first occurrence of old_str.
            - Prevents unintended multiple replacements.

        Notes:
            - Preferred for precise edits instead of rewriting full files.
            - Safer than regex-based replacements in many cases.
        """

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
        """
        Create or overwrite a file with new content.

        Parameters:
            path (str):
                Relative path to the file.

            content (str):
                Full content to write into the file.

        Returns:
            str:
                Status message confirming write operation.

        Notes:
            - Automatically creates parent directories if they do not exist.
            - Overwrites existing files completely.
            - Should be used carefully to avoid accidental data loss.
        """

        safe = _safe_path(path, working_dir)
        os.makedirs(os.path.dirname(safe), exist_ok=True)

        with open(safe, "w", encoding="utf-8") as f:
            f.write(content)

        return f"OK: Wrote {path}"

    # ── REVIEWER TOOLS (read-only, verify) ────────────────────────────
    @tool
    def read_file_for_review(path: str) -> str:
        """
        Read file contents specifically for review/verification.

        Parameters:
            path (str):
                Relative file path.

        Returns:
            str:
                File contents.

        Notes:
            - Functionally similar to read_file.
            - Separated for role clarity in agent workflows.
        """

        safe = _safe_path(path, working_dir)
        with open(safe, "r", encoding="utf-8") as f:
            return f.read()

    @tool
    def run_syntax_check(path: str) -> str:
        """
        Run Python syntax validation on a file.

        Parameters:
            path (str):
                Relative path to the Python file.

        Returns:
            str:
                - Success message if syntax is valid
                - Error details if syntax is invalid

        Notes:
            - Uses `python -m py_compile` internally.
            - Does NOT execute the file, only checks syntax.
            - Useful for catching syntax errors after modifications.
        """

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