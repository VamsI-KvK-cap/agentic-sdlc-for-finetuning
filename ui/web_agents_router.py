from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentInfo(BaseModel):
    name: str
    language: str
    description: str


def get_available_agents() -> list[AgentInfo]:
    """
    Reads from orchestrator's AGENTS dict so it stays in sync automatically.
    """
    from src.agents.orchestrator_agent.orchestrator_agent import AGENTS

    DESCRIPTIONS = {
        "python": "Generates Python code with ruff linting",
        "javascript": "Generates JavaScript/TypeScript with eslint",
        "go": "Generates Go code with golangci-lint",
    }
    LANGUAGE_LABELS = {
        "python": "Python",
        "javascript": "JavaScript",
        "go": "Go",
    }

    return [
        AgentInfo(
            name=name,
            language=LANGUAGE_LABELS.get(name, name.capitalize()),
            description=DESCRIPTIONS.get(name, f"{name} coding agent"),
        )
        for name in AGENTS.keys()
    ]


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """Return all registered coding agents."""
    return get_available_agents()
