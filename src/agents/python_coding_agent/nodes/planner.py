from langchain_core.output_parsers import PydanticOutputParser
from ..prompt.planner_prompt import planner_prompt
from src.base_workflows.base_coding_agent_workflow.pydantic_models import Plan
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.llm_config import llm
from src.config.logging_config import logger

parser = PydanticOutputParser(pydantic_object=Plan)

def planner_node(state: BaseAgentState):
    logger.info("Executing Planner Node")
    formatted_prompt = planner_prompt.format_messages(
        task=state["task"],
        work_dir=state["work_dir"],
        file_structure=state["file_structure"],
        existing_files=state.get("existing_files"),
        format_instructions=parser.get_format_instructions()
    )
    logger.debug(f"Python Planner Prompt: \n{formatted_prompt}")
    # response = llm.invoke(formatted_prompt)
    # plan = parser.parse(response.content)
    plan = llm.with_structured_output(Plan).invoke(formatted_prompt)
    # state["plan"] = plan.model_dump()
    return {"plan": plan.model_dump()}