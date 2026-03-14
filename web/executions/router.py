import asyncio
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from web.database import get_db
from web.executions.models import ExecutionStatus
from web.executions.schemas import ExecutionCreate, ExecutionResponse, ExecutionListResponse
from web.executions import crud
from web.worker.tasks import run_agent_task


load_dotenv()
working_dir = os.getenv("WORKING_DIR")

# APIRouter instance; mounted under a prefix (e.g. /api/v1) in main.py
# All routes defined here will be prefixed accordingly when included in main.py
router = APIRouter()


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------
 
async def _stream_execution(execution_id: int):
    """
    Generator that polls the DB every 2 seconds and yields SSE events.
    Closes automatically when execution reaches a terminal state.
    """
    from web.database import AsyncSessionLocal
    from web.executions import crud as _crud
 
    POLL_INTERVAL = 10  # seconds
    TERMINAL = {ExecutionStatus.COMPLETED, ExecutionStatus.FAILED}
 
    while True:
        async with AsyncSessionLocal() as db:
            execution = await _crud.get_execution(db, execution_id)
 
        if not execution:
            yield _sse_event({"error": f"Execution {execution_id} not found"})
            break
 
        payload = {
            "execution_id": execution.id,
            "agent_name": execution.agent_name,
            "status": execution.status.value,
            "error_message": execution.error_message,
            "updated_at": execution.updated_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        }
        yield _sse_event(payload)
 
        if execution.status in TERMINAL:
            break
 
        await asyncio.sleep(POLL_INTERVAL)
 
 
def _sse_event(data: dict) -> str:
    """Format a dict as an SSE message."""
    return f"data: {json.dumps(data)}\n\n"
 

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/executions", response_model=ExecutionResponse, status_code=202)
async def create_execution(
    payload: ExecutionCreate,
    db: AsyncSession = Depends(get_db),                # request-scoped DB session injected via FastAPI dependency
) -> ExecutionResponse:
    """
    Create a new Execution record and enqueue the agent run asynchronously.

    Returns HTTP 202 Accepted immediately with the initial PENDING snapshot.
    The agent runs in the background; clients should poll GET /executions/{id}
    to observe status transitions (PENDING → RUNNING → COMPLETED | FAILED).

    Args:
        payload          (ExecutionCreate):  Validated request body containing
                                             ``agent_name`` and ``task``.
        db               (AsyncSession):     Request-scoped async DB session injected
                                             by FastAPI via the ``get_db`` dependency.

    Returns:
        ExecutionResponse: Initial snapshot of the created Execution with
                           status=PENDING and server-assigned id/timestamps.
                           HTTP status code is 202 (Accepted), not 201 (Created),
                           because processing is deferred.

    Raises:
        SQLAlchemyError: If the INSERT to create the execution record fails.
    """
    execution = await crud.create_execution(db, payload)   # INSERT row with status=PENDING; assigns id and timestamps
    # CONCEPT: .delay() is non-blocking — it sends the task message to Redis
    # and returns immediately with an AsyncResult. We don't await or store it
    # because our source of truth for execution state is PostgreSQL, not Redis.
    #
    # The worker will:
    #   1. Pick up the message from Redis
    #   2. Call run_agent_task(execution_id, agent_name, task)
    #   3. Update PostgreSQL as it progresses (RUNNING → COMPLETED/FAILED)
    #
    # Arguments must be JSON-serialisable (int and str ✓).
    # Do NOT pass ORM objects — they can't be serialised to JSON.
    run_agent_task.delay(
        execution_id=execution.id,
        agent_name=execution.agent_name,
        task=execution.task,
    )

    return execution                                       # serialised as ExecutionResponse; client polls GET /executions/{id}



@router.get("/executions/{execution_id}/stream")
async def stream_execution(execution_id: int):
    """
    SSE endpoint — opens a persistent connection and pushes status updates
    every 2 seconds until the execution completes or fails.
 
    Connect via curl:
        curl -N http://localhost:8000/api/v1/executions/{id}/stream
 
    Connect via browser JS:
        const es = new EventSource("/api/v1/executions/1/stream");
        es.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    return StreamingResponse(
        _stream_execution(execution_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables Nginx buffering if behind a proxy
        },
    )


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    skip: int = Query(0, ge=0),                            # pagination offset; ge=0 rejects negative values with 422
    limit: int = Query(20, ge=1, le=100),                  # page size; le=100 prevents unbounded result sets; ge=1 ensures at least 1 row
    agent_name: str | None = Query(None),                  # optional exact-match filter on agent_name; None = all agents
    status: ExecutionStatus | None = Query(None),          # optional filter on lifecycle state; None = all states
    db: AsyncSession = Depends(get_db),
) -> ExecutionListResponse:
    """
    Return a paginated, optionally filtered list of Execution records.

    Filters are applied server-side and the pre-pagination total is always
    returned so clients can calculate page count without a separate request.

    Args:
        skip       (int):                   Number of rows to skip before
                                            returning results. Used with ``limit``
                                            to implement offset-based pagination.
                                            Validated: must be >= 0.
        limit      (int):                   Maximum rows to return in this page.
                                            Validated: 1 ≤ limit ≤ 100.
                                            Defaults to 20.
        agent_name (str | None):            Exact-match filter on ``agent_name``.
                                            Pass as a query param to narrow results
                                            to a specific agent. Omit for all agents.
        status     (ExecutionStatus | None): Filter on lifecycle state. Accepts any
                                            ExecutionStatus string value (e.g.
                                            ``?status=failed``). Omit for all states.
        db         (AsyncSession):          Request-scoped async DB session.

    Returns:
        ExecutionListResponse: Contains ``total`` (pre-pagination match count)
                               and ``executions`` (current page, newest-first).

    Raises:
        SQLAlchemyError: If the SELECT queries fail.
    """
    total, executions = await crud.list_executions(        # total = pre-pagination count; enables client-side page calculation
        db, skip=skip, limit=limit, agent_name=agent_name, status=status
    )
    return ExecutionListResponse(total=total, executions=executions)


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Fetch a single Execution record by its primary key.

    Primary polling endpoint. Clients call this repeatedly after POST /executions
    to observe status transitions until a terminal state (COMPLETED or FAILED)
    is reached.

    Args:
        execution_id (int):         Primary key of the target Execution row.
                                    Extracted from the URL path by FastAPI.
        db           (AsyncSession): Request-scoped async DB session injected
                                    by FastAPI via the ``get_db`` dependency.

    Returns:
        ExecutionResponse: Current snapshot of the requested Execution,
                           including the latest status, timestamps, and
                           error_message (if FAILED).

    Raises:
        HTTPException (404): If no Execution row exists for ``execution_id``.
                             Detail message includes the missing ID for
                             easier client-side debugging.
        SQLAlchemyError:     If the SELECT query fails.
    """
    execution = await crud.get_execution(db, execution_id)
    if not execution:
        # Raise 404 explicitly rather than returning None or an empty response;
        # detail includes the ID so clients can surface a meaningful error message
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found",
        )
    return execution

    """
    The key commentary decisions made here:

    Lazy imports — explained why (circular imports, startup perf), not just what
    Session management — each async with AsyncSessionLocal() block notes why a fresh session is opened rather than reusing one
    run_in_executor — clarifies that run() is blocking/synchronous and the None argument means default thread pool
    raise after FAILED update — noted that re-raise preserves the traceback for logging
    Query params — constraints like le=100 have their intent spelled out ("prevent large result sets")
    status_code=202 — linked to the polling contract described in the docstring
    """