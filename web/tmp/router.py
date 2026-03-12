import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from web.database import get_db
from web.models import ExecutionStatus
from web.schemas import ExecutionCreate, ExecutionResponse, ExecutionListResponse
from web import crud

router = APIRouter()


# ---------------------------------------------------------------------------
# Background task: runs the agent and updates execution status in DB
# ---------------------------------------------------------------------------

async def _run_agent_task(execution_id: int, agent_name: str, task: str):
    """
    Runs in the background after POST /executions.
    Imports the orchestrator lazily to avoid circular imports and
    to keep the HTTP response fast.
    """
    from web.database import AsyncSessionLocal
    from web.executions import crud as _crud
    from web.executions.models import ExecutionStatus

    # Mark as running
    async with AsyncSessionLocal() as db:
        execution = await _crud.get_execution(db, execution_id)
        if not execution:
            return
        await _crud.update_execution_status(db, execution, ExecutionStatus.RUNNING)

    try:
        # ----------------------------------------------------------------
        # Delegate to the orchestrator_agent.
        # The orchestrator is expected to expose a `run(task, agent_name)`
        # interface; 
        # ----------------------------------------------------------------        
        from src.agents.orchestrator_agent.orchestrator_agent import run

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run, task, agent_name)  # run(task, language)

        async with AsyncSessionLocal() as db:
            execution = await _crud.get_execution(db, execution_id)
            await _crud.update_execution_status(db, execution, ExecutionStatus.COMPLETED)

    except Exception as exc:
        async with AsyncSessionLocal() as db:
            execution = await _crud.get_execution(db, execution_id)
            await _crud.update_execution_status(
                db, execution, ExecutionStatus.FAILED, error_message=str(exc)
            )
        raise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/executions", response_model=ExecutionResponse, status_code=202)
async def create_execution(
    payload: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an execution record and trigger the agent asynchronously.
    Returns 202 Accepted immediately; poll GET /executions/{id} for status.
    """
    execution = await crud.create_execution(db, payload)
    background_tasks.add_task(
        _run_agent_task,
        execution_id=execution.id,
        agent_name=execution.agent_name,
        task=execution.task,
    )
    return execution


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    agent_name: str | None = Query(None),
    status: ExecutionStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List executions with optional filters."""
    total, executions = await crud.list_executions(
        db, skip=skip, limit=limit, agent_name=agent_name, status=status
    )
    return ExecutionListResponse(total=total, executions=executions)


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a single execution by ID."""
    execution = await crud.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    return execution
