"""
Agent Task Execution Module.

This module provides a command-line interface to execute coding tasks using specialized agents.
It supports multiple programming languages through a pluggable agent architecture, allowing
tasks to be processed by language-specific agents (e.g., Python, JavaScript).

The module can be used programmatically via the run() function or as a standalone CLI script
through the __main__ entry point.

Example:
    >>> from main import run
    >>> run("Create a FastAPI endpoint")
"""

# Import typing constructs for type hints
from typing import Type, Dict, Any


# Import the Python coding agent implementation
from src.agents.python_coding_agent.agent import PythonCodingAgent

# Mapping of supported programming languages to their corresponding agent classes.
# This allows language selection to be handled dynamically by the run() function.
AGENTS: Dict[str, Type] = {
    "python": PythonCodingAgent,
    # "javascript": JavaScriptCodingAgent,  # TODO: add JavaScript support when available
}


def run(task: str, language: str = "python") -> Any:
    """
    Execute a coding task using the specified language agent.

    Args:
        task (str): The natural language description or prompt for the coding task.
        language (str, optional): Target language key for the task. Defaults to "python".
            The value must exist in the AGENTS mapping.

    Returns:
        Any: The result returned by the selected agent implementation.

    Raises:
        ValueError: If the provided language is not supported.
    """
    # Retrieve the configured agent class for the selected language
    agent_cls: Type = AGENTS.get(language)

    # Validate the requested language is supported by the mapping
    if not agent_cls:
        supported_languages: list[str] = list(AGENTS.keys())
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Choose from {supported_languages}"
        )

    # Instantiate the selected agent with default configuration
    agent: object = agent_cls(config={})

    # Execute the task and return the raw agent result
    return agent.run(task=task)


if __name__ == "__main__":
    """
    Execute a sample task when the module is run as a script.

    This block is useful for local testing and demonstration of the agent.
    """
    # Prepare a sample task describing a store manager workflow
    input_state: str = """As a store manager, I want to add a new product to the inventory so that I can track its availability and manage its stock levels.
As a store manager, I want to remove a product from the inventory so that I can discontinue its sale and update its availability status.
As a store manager, I want to edit the details of an existing product in the inventory so that I can update its information or correct any errors.
"""

    # Execute the default Python agent against the sample task
    run(task=input_state)