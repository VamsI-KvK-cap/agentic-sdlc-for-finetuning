import asyncio
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from web.database import get_db
from web.executions.models import ExecutionStatus
from web.executions.schemas import ExecutionCreate, ExecutionResponse, ExecutionListResponse
from web.executions import crud


load_dotenv()
working_dir = os.getenv("WORKING_DIR")

# APIRouter instance; mounted under a prefix (e.g. /api/v1) in main.py
# All routes defined here will be prefixed accordingly when included in main.py
router = APIRouter()


# ---------------------------------------------------------------------------
# Background task: runs the agent and updates execution status in DB
# ---------------------------------------------------------------------------

async def _run_agent_task(execution_id: int, agent_name: str, task: str) -> None:
    """
    Background coroutine that drives the full agent execution lifecycle.

    Scheduled by FastAPI's BackgroundTasks after POST /executions returns 202.
    Manages three DB state transitions independently, each in its own
    short-lived session to avoid holding a connection open during the
    (potentially long) agent run.

    Lifecycle managed here:
        PENDING → RUNNING   (Phase 1: before agent is invoked)
        RUNNING → COMPLETED (Phase 2 success path)
        RUNNING → FAILED    (Phase 2 failure path)

    Design decisions:
        - All imports are lazy (inside the function body) to prevent circular
          import issues at module load time and to avoid pulling in heavy
          ML/agent dependencies until they are actually needed.
        - The orchestrator's ``run()`` is synchronous/blocking, so it is
          offloaded to a thread-pool via ``run_in_executor`` to keep the
          asyncio event loop unblocked during agent execution.
        - Each DB interaction opens and closes its own session. Reusing a
          single session across the agent run would hold a connection for the
          entire duration, exhausting the pool under load.

    Args:
        execution_id (int): Primary key of the Execution row to update.
                            Used to re-fetch the record in each session.
        agent_name   (str): Agent identifier forwarded to the orchestrator's
                            ``run(task, agent_name)`` interface.
        task         (str): Free-form task description forwarded to the
                            orchestrator alongside ``agent_name``.

    Returns:
        None. All results are persisted to the DB via status transitions.

    Raises:
        Exception: Re-raises any exception thrown by the orchestrator after
                   persisting the FAILED status, so FastAPI's BackgroundTasks
                   infrastructure can log the full traceback.
    """
    # Lazy imports: deferred until task runs to prevent circular import issues
    # and avoid loading heavy modules at startup
    from web.database import AsyncSessionLocal
    from web.executions import crud as _crud           # scoped alias to avoid shadowing the module-level `crud`
    from web.executions.models import ExecutionStatus

    # --- Phase 1: Transition execution state to RUNNING ---
    async with AsyncSessionLocal() as db:              # short-lived session; closed immediately after status update
        execution = await _crud.get_execution(db, execution_id)
        if not execution:
            return                                     # record deleted between POST and task pickup; bail silently to avoid KeyError
        await _crud.update_execution_status(db, execution, ExecutionStatus.RUNNING)

    try:
        # ----------------------------------------------------------------
        # Delegate to the orchestrator_agent.
        # The orchestrator is expected to expose a `run(task, agent_name)`
        # interface.
        # ----------------------------------------------------------------
        from src.agents.orchestrator_agent.orchestrator_agent import run  # lazy; avoids loading ML deps at startup

        work_dir = os.path.join(working_dir, str(execution_id))
        loop = asyncio.get_event_loop()
        # run() is synchronous (blocking); run_in_executor offloads it to the
        # default ThreadPoolExecutor so the event loop stays free for other
        # requests during the (potentially long) agent execution
        await loop.run_in_executor(None, run, task, agent_name, work_dir, execution_id)  # None → use default ThreadPoolExecutor

        # --- Phase 2 (success path): Agent returned cleanly → mark COMPLETED ---
        async with AsyncSessionLocal() as db:          # fresh session; prior session already closed before agent ran
            execution = await _crud.get_execution(db, execution_id)
            await _crud.update_execution_status(db, execution, ExecutionStatus.COMPLETED)

    except Exception as exc:
        # --- Phase 2 (failure path): Agent raised → persist error → mark FAILED ---
        async with AsyncSessionLocal() as db:          # separate session; guarantees DB write even if agent session was corrupted
            execution = await _crud.get_execution(db, execution_id)
            await _crud.update_execution_status(
                db, execution, ExecutionStatus.FAILED,
                error_message=str(exc),                # str(exc) captures the root cause; full traceback goes to server logs via re-raise
            )
        raise                                          # re-raise so BackgroundTasks infrastructure logs the full traceback


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
    background_tasks: BackgroundTasks,                 # FastAPI's built-in fire-and-forget mechanism; task runs after response is sent
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
        background_tasks (BackgroundTasks):  FastAPI dependency; used to schedule
                                             ``_run_agent_task`` after the response
                                             is sent so the HTTP round-trip is not
                                             blocked by agent execution.
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
    background_tasks.add_task(                             # enqueues task to run AFTER the 202 response is sent to the client
        _run_agent_task,
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