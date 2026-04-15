"""Planner node: create a file-level plan for the coding task.

This node synthesizes a scoped plan based on the task description,
work directory and existing repository structure. The returned ``Plan``
object is expected to be serializable to a mapping for downstream
consumers.
"""

from langchain_core.output_parsers import PydanticOutputParser
from src.agents.python_coding_agent.prompt.planner_prompt import planner_prompt
from src.base_workflows.base_coding_agent_workflow.pydantic_models import Plan
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.llm_config import llm
from src.config.logging_config import logger

parser = PydanticOutputParser(pydantic_object=Plan)


def planner_node(state: BaseAgentState):
    """Create a high-level plan for the provided task.

    Args:
        state (BaseAgentState): Agent-level state. Expected keys include
            ``task``, ``work_dir``, ``file_structure`` and optionally
            ``existing_files``.

    Returns:
        dict: A mapping containing the serialized plan under the
            ``plan`` key.
    """

    logger.info("Executing Planner Node")

    formatted_prompt = planner_prompt.format_messages(
        task=state["task"],
        work_dir=state["work_dir"],
        file_structure=state["file_structure"],
        existing_files=state.get("existing_files"),
        format_instructions=parser.get_format_instructions(),
    )

    # Log the final prompt for debugging and reproducibility.
    logger.debug(f"Python Planner Prompt: \n{formatted_prompt}")

    # Request a structured Plan object from the LLM and return its dict
    # representation (model_dump) so downstream nodes receive a plain
    # serializable mapping.
    plan = llm.with_structured_output(Plan).invoke(formatted_prompt)
    return {"plan": plan.model_dump()}