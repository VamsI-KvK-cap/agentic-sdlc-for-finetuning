"""Coder node: generate or modify a single file according to the file plan.

This node requests a structured ``SingleFileOutput`` from the LLM. On
success it returns the generated change and resets ``written_files``
so that the writer node (separate responsibility) starts from a
clean slate.
"""

from langchain_core.output_parsers import PydanticOutputParser
from src.agents.python_coding_agent.prompt.coder_prompt import coder_prompt
from src.base_workflows.base_coding_agent_workflow.pydantic_models import CodeOutput, SingleFileOutput
from src.base_workflows.base_coding_agent_workflow.state import BaseFileAgentState
from src.config.llm_config import llm
from src.config.logging_config import logger


coder_parser = PydanticOutputParser(pydantic_object=CodeOutput)
file_coder_parser = PydanticOutputParser(pydantic_object=SingleFileOutput)


def coder_node(state: BaseFileAgentState):
    """Request code generation for a file and return the structured change.

    Args:
        state (BaseFileAgentState): File-scoped state. Expects
            ``file_plan`` and optionally ``existing_file_content`` and
            ``feedback``.

    Returns:
        dict: A mapping with ``code_change`` and reset ``written_files``
            to allow the writer step to control file I/O.
    """

    logger.info("Executing Coder Node")
    file_plan = state["file_plan"]

    # Build the coder prompt with file-scoped instructions.
    formatted_prompt = coder_prompt.format_messages(
        instructions=file_plan["instructions"],  # scoped per-file
        action=file_plan["action"],
        path=file_plan["path"],
        existing_file_content=state.get("existing_file_content", ""),
        feedback=state.get("feedback", ""),
        format_instructions=coder_parser.get_format_instructions(),
    )

    # Ask the LLM for a structured SingleFileOutput and surface errors
    # so the higher-level workflow can react (retry, escalate, etc.).
    llm_structured = llm.with_structured_output(SingleFileOutput)
    try:
        code_output = llm_structured.invoke(formatted_prompt)
    except Exception as e:
        logger.error(f"Coder failed for {state['file_plan']['path']}: {e}")
        raise

    logger.debug(f"Generated CODE: \n {code_output.model_dump()}")

    # Return only the change and reset written_files; writing is handled
    # by a separate node to keep responsibilities isolated.
    return {**state, "code_change": code_output.change.model_dump(), "written_files": []}