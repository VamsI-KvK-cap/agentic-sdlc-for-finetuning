from fastapi import APIRouter
from pydantic import BaseModel

# Initialize the router for agent-related endpoints
router = APIRouter()


class AgentInfo(BaseModel):
    """
    Data model representing metadata for a registered agent.

    CONCEPT: Provides a standardized schema for describing agents to the frontend, 
    allowing the UI to dynamically list and describe available AI personas.

    Attributes:
        name (str): The unique identifier of the agent.
        description (str): A human-readable description of the agent's capabilities.
    """
    name: str
    description: str


def get_available_agents() -> list[AgentInfo]:
    """
    Dynamically fetches the list of available agents from the Orchestrator.

    Reads directly from the Orchestrator's agent registry to ensure that the 
    API and the agent system remain in sync automatically without manual updates.

    CONCEPT: Centralizes agent discovery by sourcing truth from the agent 
    implementation itself rather than a separate configuration file.

    Returns:
        list[AgentInfo]: A collection of metadata for all active agents.

    Raises:
        ImportError: If the orchestrator agent module cannot be found.
    """
    from src.agents.orchestrator_agent.orchestrator_agent import AGENTS, AGENTS_DESCRIPTIONS
    
    # Construct the list of AgentInfo objects using the registry and descriptions
    agents_list = [
        AgentInfo(
            name=name,
            description=AGENTS_DESCRIPTIONS.get(name, f"{name} agent.")
        )
        for name in AGENTS.keys()
    ]

    return agents_list


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """
    Endpoint to retrieve all registered agents in the system.

    This GET endpoint serves as the primary discovery mechanism for the UI to 
    determine which agents are available for task execution.

    CONCEPT: Facilitates dynamic UI generation by providing a manifest of 
    available backend agents and their respective descriptions.

    Returns:
        list[AgentInfo]: List of available agents with names and descriptions.
    """
    return get_available_agents()
