"""Tool to produce a human-readable tree of files under a path.

This helper is useful for debugging and for agents that need to
understand repository layout. It prints the ``path`` parameter for
visibility when invoked as a script.
"""

import os
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

working_dir = os.getenv("WORKING_DIR")


@tool
def read_file_structure(path: str | None = working_dir, execution_id: int = 0):
    """Return a simple directory tree string for ``path``.

    Args:
        path (str | None): Path to walk. If None, falls back to the
            ``WORKING_DIR`` environment variable.
        execution_id (int): Optional execution id to scope the path
            (unused by default but retained for compatibility).

    Returns:
        str: A newline-separated directory tree.
    """

    if path is None:
            if working_dir is None:
                raise ValueError("WORKING_DIR_NOT_SET")
            path = working_dir

    # For clarity during interactive runs, show the root being walked.
    print(path)

    tree_lines = []
    for root, dirs, files in os.walk(path):
        level = root.replace(path, "").count(os.sep)
        indent = " " * 2 * level
        tree_lines.append(f"{indent}{os.path.basename(root)}/")

        sub_indent = " " * 2 * (level + 1)
        for f in files:
            tree_lines.append(f"{sub_indent}{f}")

    return "\n".join(tree_lines)


if __name__ == "__main__":
    # Local debug helper. Uses the tool invocation API when available.
    result = read_file_structure(working_dir)
    print(result)