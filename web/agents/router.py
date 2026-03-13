from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AgentInfo(BaseModel):
    name: str
    # language: str
    description: str

# LANGUAGE_LABELS = {
#     "python": "PythonCodingAgent",
#     "javascript": "JavaScript",
#     "go": "Go",
# }

def get_available_agents() -> list[AgentInfo]:
    """
    Read from Orchestrator's AGENT and AGENTS_DESCRIPTION dict so it stays in sync automatically.
    """
    from src.agents.orchestrator_agent.orchestrator_agent import AGENTS, AGENTS_DESCRIPTIONS
    agents_list = [
        AgentInfo(
            name=name,
            # language=LANGUAGE_LABELS.get(name, name.capitalize()),
            description=AGENTS_DESCRIPTIONS.get(name, f"{name} agent.")
        )
        for name in AGENTS.keys()
    ]

    return agents_list

@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """Return all registered agents."""
    return get_available_agents()