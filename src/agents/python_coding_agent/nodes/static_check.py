"""Static check node using Ruff.

Runs the ``ruff`` linter against files produced by the coder node and
returns structured feedback consumed by the workflow.
"""

import json
import subprocess
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from src.config.logging_config import logger


def static_check_node(state: BaseFileAgentState):
    """Run ruff on written files and return feedback.

    Args:
        state (BaseFileAgentState): File-scoped state. Expects
            ``written_files`` (list of paths).

    Returns:
        dict: State delta containing ``static_check_success``,
            ``static_check_output``, ``feedback`` and updated
            ``retry_count``.
    """

    logger.info("Executing Static Check Node")
    written_files = state.get("written_files", [])

    # Nothing to check if no files were produced.
    if not written_files:
        logger.info("No files written, skipping static check.")
        return {
            **state,
            "static_check_success": True,
            "static_check_output": "No files written.",
            "feedback": None,
        }

    # Run ruff and capture its JSON output for structured parsing.
    result = subprocess.run(
        ["ruff", "check", "--output-format", "json"] + written_files,
        capture_output=True,
        text=True,
    )

    success = result.returncode == 0
    output = result.stdout + result.stderr
    feedback = None

    if not success:
        feedback = summarize_ruff_issue(result.stdout)

        # Increment a retry counter to allow the workflow to react.
        retry_count = dict(state.get("retry_count") or {})
        retry_count["static_check_count"] = retry_count.get("static_check_count", 0) + 1
        logger.info(f"Static Check FEEDBACK:\n{feedback}")
    else:
        retry_count = dict(state.get("retry_count") or {})

    return {
        **state,
        "static_check_success": success,
        "static_check_output": output,
        "feedback": feedback,
        "retry_count": retry_count,
    }


def summarize_ruff_issue(json_output: str) -> str:
    """Parse ruff JSON output into a human-readable summary.

    Falls back to returning the raw output when parsing fails.
    """
    try:
        issues = json.loads(json_output)
        issue_list = [
            f"{i['filename']}:{i['location']['row']} {i['code']} {i['message']}"
            for i in issues
        ]
        return "Ruff reported:\n" + "\n".join(issue_list)
    except Exception:
        return "Ruff reported issues but JSON parsing failed:\n" + json_output
