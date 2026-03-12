from datetime import datetime
from pydantic import BaseModel, Field
from web.executions.models import ExecutionStatus


class ExecutionCreate(BaseModel):
    agent_name: str = Field(..., description="Name of the agent to run (e.g. 'python')")
    task: str = Field(..., description="Task description for the agent")


class ExecutionResponse(BaseModel):
    id: int
    agent_name: str
    status: ExecutionStatus
    task: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    total: int
    executions: list[ExecutionResponse]
