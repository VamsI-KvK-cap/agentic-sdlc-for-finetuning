import os
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState
from src.config.logging_config import logger
from dotenv import load_dotenv


load_dotenv()
working_dir = os.getenv("WORKING_DIR")

def setup_node(state: BaseAgentState):
    logger.info("*"*20)
    logger.info("Executing Setup Node")
    # To do : last execution id will be fetch from the databse and +1 will be used as next
    # state["execution_id"] = 4 # hard coded temporarily 
    # state["work_dir"] = os.path.join(working_dir, str(state["execution_id"]))
    # state["retry_count"] = {"review" : 0, "static_check_count": 0}
    # return state
    exec_id = str(state.get("execution_id", 6))
    work_dir = os.path.join(working_dir, exec_id)
    return {
    **state,
    "execution_id": exec_id,
    "work_dir": work_dir,
    "retry_count": {"review" : 0, "static_check_count": 0},
    }