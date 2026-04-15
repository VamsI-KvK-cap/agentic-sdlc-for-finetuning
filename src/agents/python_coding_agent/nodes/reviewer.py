"""Reviewer node: validate generated file-level changes.

This node formats a reviewer prompt, invokes the LLM with a structured
output type (``ReviewResult``) and returns a delta containing the
review and any updated retry counters.

Google style docstring converted: includes Args/Returns.
"""

from langchain_core.output_parsers import PydanticOutputParser
from src.agents.python_coding_agent.prompt.reviewer_prompt import reviewer_prompt
from src.base_workflows.base_coding_agent_workflow.pydantic_models import ReviewResult
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from src.config.llm_config import llm
from src.config.logging_config import logger

reviewer_parser = PydanticOutputParser(pydantic_object=ReviewResult)


def reviewer_node(state: BaseFileAgentState):
    """Run a review pass over a single file change.

    Args:
        state (BaseFileAgentState): File-scoped workflow state. Expected
            keys include ``task``, ``file_plan``, ``existing_file_content``
            and ``code_change``.

    Returns:
        dict: A mapping with the original state plus ``review`` and
            ``retry_count``.
    """

    logger.info("Executing Reviewer Node")

    # Build the LLM prompt using the reviewer prompt template.
    formatted_prompt = reviewer_prompt.format_messages(
        task=state["task"],
        plan=state["file_plan"],              # actual plan for this file
        existing_files=state.get("existing_file_content", ""),  # single file content
        code_changes=state["code_change"],
        format_instructions=reviewer_parser.get_format_instructions()
    )

    # Invoke the LLM and obtain a typed ReviewResult.
    llm_structured = llm.with_structured_output(ReviewResult)
    review_result = llm_structured.invoke(formatted_prompt)

    # Maintain a simple retry counter to allow the workflow to decide
    # whether to re-run generation steps.
    retry_count = dict(state.get("retry_count") or {})
    if review_result.status.lower() != "approved":
        retry_count["review"] = retry_count.get("review", 0) + 1

    logger.info(f"Review by Reviewer Node:\n{review_result.model_dump()}")

    # Return a delta instead of mutating the input state in-place.
    return {
        **state,
        "review": review_result.model_dump(),  # return delta only, not mutated state
        "retry_count": retry_count,
    }
