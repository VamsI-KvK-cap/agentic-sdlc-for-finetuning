"""Helper tool to safely read files from disk.

This tool is exposed to agent workflows and therefore is restricted to
the configured ``WORKING_DIR`` to prevent directory traversal. The
function resolves the working directory and ensures the requested
file is a child path of the working directory.
"""

import os
from pathlib import Path
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()


@tool
def read_file(file_path: str) -> str:
    """Read file from disk inside WORKING_DIR only.

    Args:
        file_path (str): Relative path to the file under WORKING_DIR.

    Returns:
        str: File contents, or the string "FILE_NOT_FOUND" when the
            file is missing. Raises ``ValueError`` if ``WORKING_DIR`` is
            not set or if the resolved target path is outside the
            working directory.
    """

    base_path = os.getenv("WORKING_DIR")
    if not base_path:
        raise ValueError("WORKING_DIR_NOT_SET")

    # Narrow type for mypy: base_path is now str
    base_dir = Path(base_path).resolve()
    target_path = (base_dir / file_path).resolve()

    # Prevent directory traversal by ensuring target_path is inside base_path
    try:
        target_path.relative_to(base_path)
    except Exception:
        raise ValueError("INVALID_PATH")

    if not target_path.is_file():
        return "FILE_NOT_FOUND"

    return target_path.read_text(encoding="utf-8")