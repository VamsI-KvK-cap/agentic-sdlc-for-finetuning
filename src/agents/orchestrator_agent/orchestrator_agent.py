"""
Orchestrator Agent Module.

This module provides a unified interface to execute coding tasks using various language-specific
agents. It acts as an orchestrator/dispatcher that routes tasks to the appropriate agent based on
the specified language. The module loads configuration from environment variables (e.g., WORKING_DIR)
and manages execution context including working directories and execution IDs.

Supported Agents:
    - PythonCodingAgent: Generates Python code with ruff linting
    - JavaScriptCodingAgent: Generates JavaScript/TypeScript with eslint (pending)
    - GoAgent: Generates Go code with golangci-lint (pending)
"""

import os
from typing import Type, Dict, Any

from dotenv import load_dotenv

from src.agents.python_coding_agent.agent import PythonCodingAgent
# from src.agents.javascript_agent.agent import JavaScriptCodingAgent


# Load environment variables from .env file
load_dotenv()

# Retrieve working directory from environment; used as base path for agent execution
working_dir: str = os.getenv("WORKING_DIR", "./output")

# Execution identifier; used to isolate execution artifacts and logs
exec_id: str = "0"

# Construct execution-specific working directory by joining base path with execution ID
working_dir = os.path.join(working_dir, exec_id)


# Mapping of agent names to their corresponding agent classes
# Enables dynamic agent selection and instantiation based on user specification
AGENTS: Dict[str, Type] = {
    "PythonCodingAgent": PythonCodingAgent,  # Python code generation with ruff linting
    # "javascript": JavaScriptCodingAgent,    # TODO: JavaScript/TypeScript support (pending)
}

# Descriptive metadata for each supported agent
# Provides human-readable descriptions for agent capabilities and features
AGENTS_DESCRIPTIONS: Dict[str, str] = {
    "PythonCodingAgent": "Generates Python code with ruff linting",
    "javascript": "Generates JavaScript/TypeScript with eslint",
    "go": "Generates Go code with golangci-lint",
}


def run(
    task: str,
    agent_name: str = "python",
    work_dir: str = working_dir,
    execution_id: int = exec_id,
) -> Any:
    """
    Execute a coding task using the specified agent.

    Routes the provided task to the appropriate agent based on the specified agent name.
    The agent processes the task and generates code within the specified working directory,
    associating the execution with the given execution ID for tracking and artifact isolation.

    Args:
        task (str): The task description or code generation specification.
            Describes what code needs to be generated or implemented.
        agent_name (str, optional): The name of the agent to use for task execution.
            Defaults to "python". Must be a key in the AGENTS mapping.
            Supported values: "PythonCodingAgent".
        work_dir (str, optional): The base working directory for execution artifacts.
            Defaults to concatenated WORKING_DIR environment variable and exec_id.
            The agent will create outputs and logs in this directory.
        execution_id (int, optional): Unique identifier for this execution.
            Defaults to "0". Used to track and isolate execution artifacts, logs, and outputs.

    Returns:
        Any: The execution result from the selected agent. Return type depends on the
            specific agent implementation. Typically contains generated code and metadata.

    Raises:
        ValueError: If the specified agent_name is not found in the AGENTS dictionary
            (i.e., unsupported or non-existent agent).

    Example:
        >>> result = run("Create a FastAPI CRUD endpoint", agent_name="PythonCodingAgent")
        >>> result = run(task="Build inventory management system", work_dir="./custom_out")
    """
    # Retrieve the agent class corresponding to the specified agent name
    agent_cls: Type = AGENTS.get(agent_name)

    # Validate that the requested agent exists in the supported agents mapping
    if not agent_cls:
        supported_agents: list = list(AGENTS.keys())
        raise ValueError(
            f"Unsupported agent_name: {agent_name}. "
            f"Choose from {supported_agents}"
        )

    # Instantiate the agent with empty configuration (uses agent defaults)
    agent: object = agent_cls(config={})

    # Execute the task with the agent, passing working directory and execution tracking info
    return agent.run(
        task=task,
        work_dir=work_dir,
        execution_id=execution_id,
    )


if __name__ == "__main__":
    """
    Command-line entry point for orchestrator agent execution.

    When run as a standalone script, processes predefined tasks using the configured
    orchestrator. Useful for testing, debugging, and batch execution workflows.
    """
    # Example task: Generate FastAPI CRUD endpoints for LLM application
    # input_state = "Write a detailed FastAPI endpoint for CRUD ops for a llm application that can take user input in text of file format"

    # Store manager inventory workflow specification (business requirements)
    input_state: str = (
        "As a store manager, I want to add a new product to the inventory "
        "so that I can track its availability and manage its stock levels."
    )
    # Additional requirements (commented out):
    # As a store manager, I want to remove a product from the inventory so that I can discontinue its sale and update its availability status.
    # As a store manager, I want to edit the details of an existing product in the inventory so that I can update its information or correct any errors.

    # Execute the task using the default Python agent with default working directory
    run(task=input_state)

    # Alternative execution with custom working directory and specific agent:
    # run(
    #     task="Write fibonacci series",
    #     work_dir="output/1",
    #     agent_name="PythonCodingAgent",
    #     execution_id=1,
    # )