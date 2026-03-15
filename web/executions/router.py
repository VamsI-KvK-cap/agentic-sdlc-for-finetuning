import asyncio
import io
import zipfile
import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import json
from sqlalchemy.ext.asyncio import AsyncSession
from web.database import get_db
from web.executions.models import ExecutionStatus
from web.executions.schemas import (
    ExecutionCreate,
    ExecutionFromGitCreate,
    ExecutionResponse,
    ExecutionListResponse,
)
from web.executions import crud
from web.executions.source import extract_zip, clone_git
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
# Zip helper
# ---------------------------------------------------------------------------

def _zip_execution_artifacts(execution_id: int) -> io.BytesIO:
    """
    Walk output/{execution_id}/ and zip all files into an in-memory buffer.

    CONCEPT: io.BytesIO is an in-memory file-like object - it behave exactly
    like a file on disk but lives in RAM. We write the zip into this buffer
    instead of creating a temp file, which means:
        - No disk I/O for the zip itself
        - No cleanup required (garbage collected when response is sent)
        - Works even if the output/ directory is a Docker bind mount

    Returns:
        io.ByteIO: Buffer positioned at byte 0, ready to stream.

    Raises: 
        FileNotFoundError: If output/{execution_id}/ doestn't exist or is empty.
    """
    artifact_dir = os.path.join(working_dir, str(execution_id))

    if not os.path.isdir(artifact_dir):
        raise FileNotFoundError(f"No artifact directory for execution {execution_id}")
    
    # collect all files recursively
    all_files = []
    for root, _, files in os.walk(artifact_dir):
        for filename in files:
            all_files.append(os.path.join(root, filename))

    if not all_files:
        raise FileNotFoundError(f"No artifact found for execution {execution_id}")
    
    # Build the zip in memory
    buffer = io.BytesIO()

    # CONCEPT: zipfile.ZIP_DEFLATED is the standard compression algorithm.
    # It typically reduce the file size by 60-80% for text/code files.
    # ZIP_STORED (no_compression) would be faster but produces larger downloads.
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files:
            # arcname is the path INSIDE the zip file.
            # os.path.relpath strips the leading output/{id}/ prefix so the zip
            # contains clean relative paths like "src/main.py" not
            # "/app/output/42/src/main.py"
            arcname = os.path.relpath(file_path, artifact_dir)
            zf.write(file_path, arcname=arcname)

    # Rewind buffer to the start so StreamingResponse reads from byte 0
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Shared pre-flight helper
# ---------------------------------------------------------------------------

def _prepare_work_dir(execution_id: int) -> str:
    """
    Create and return output/{execution_id}/ ready to receive source files.

    Called by both brownfield endpoints before DB row creation.
    If work_dir already exists (shouldn't happen, but defensive), it's
    cleared first to avoid mixing artifacts from a previous run.
    """
    work_dir = os.path.join(working_dir, str(execution_id))
    if os.path.exists(work_dir):
        import shutil
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


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


@router.post("/executions/from-zip", response_model=ExecutionResponse, status_code=202)
async def create_execution_from_zip(
    agent_name: str = Form(..., description="Agent to run (e.g. 'PythonCodingAgent')"),
    task:       str = Form(..., description="What to change in the codebase"),
    file:       UploadFile = File(..., description="Zip archive of the existing codebase"),
    db: AsyncSession = Depends(get_db), 
) -> ExecutionResponse:
    """
    Brownfield execution from a zip archive.

    CONCEPT: multipart/form-data vs JSON body.
    File uploads require multipart/form-data encoding - JSON cannot 
    carry binary data. FastAPI's Form() and File() handle this automatically. The client sends one request with:
        - agent_name and task as form fields (text)
        - file as a file part(binary)

    Flow:
      1. Validate the upload is a zip
      2. Create DB row to get an execution_id
      3. Extract zip into output/{execution_id}/
      4. Enqueue Celery task - agent finds pre-populated work_dir
      5. Retrun 202

    CONCEPT: Why create a DB row BEFORE extraction here?
    We need execution_id to know where to extract (output/{id}/).
    If extraction fails we mark the execution as FAILED immediately 
    rather than leaving a ghost PENDING row.

    Args:
        agent_name: Form field - agent identifier.
        task:       Form field - what to change in the existing code.
        file:       Uploaded zip archive of the existing codebase.
        db:         Request-scoped DB session.

        Returns:
            ExecutionResponse with status=PENDING
        
        Raises:
            HTTPException 400: If the file upload is not a valid zip or is empty.
            HTTPExecption 500: if extraction fails due to system error.
    """
    # Validate file extension early - before reading the whole file
    if file.content_type not in ("application/zip", "application/x-zip-compressed") \
        and not (file.filename or "").endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Only .zip files are accepted",
        )
    
    # Create DB row first to get execution_id for the work_dir path
    payload = ExecutionCreate(agent_name=agent_name, task=task)
    execution = await crud.create_execution(db, payload)

    # Prepare work_dir using the new execution_id
    work_dir = _prepare_work_dir(execution.id)

    try:
        file_count = await extract_zip(file, work_dir)
    except ValueError as e:
        # User error - bad zip, path traversal attempt etc.
        # Mark executoin FAILED and return 400 so the UI shows a clear error.
        await crud.update_execution_status(
            db, execution, ExecutionStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status=400, detail=str(e))
    except RuntimeError as e:
        # System error - disk full, corrupted archive etc.
        await crud.update_execution_status(
            db, execution, ExecutionStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
    
    # Enqueue the agent - work_dir is already populated with the repo
    run_agent_task.delay(
        execution_id=execution.id,
        agent_name=execution.agent_name,
        task=execution.task,
    )

    return execution


@router.post("/executions/from-git", response_model=ExecutionResponse, status_code=202)
async def create_execution_from_git(
    payload: ExecutionFromGitCreate,
    db: AsyncSession = Depends(get_db),
) -> ExecutionResponse:
    """
    Brownfield execution from a public Git repository.

    CONCEPT: Why run git clone synchronously in the request handler?
    Git clones can take 5-30s for large repos. We clone synchronously here (blocking the request) rather than in the 
    Celery task because:

        1. We want to return 4xx immediately if the URL is invalid
            or the repo doesn't exist - not discover this inside the worker.
        2. The clone result needs to exist in work_dir before the
            worker starts, so the timing must be: clone -> enqueue.

    For very large repos (>100MB) this could be slow. A future
    improvement would be a two-step API: POST to validate/start clone,
    GET to check clone status, then the execution auto-starts.
    For now, the 120s timeout in clone_git() prevents indefinite hangs.

    CONCEPT: run_in_executor for blocking calls.
    clone_git() calls subprocess (blocking I/O). We run it in a thread
    via run_in_executor so the asyncio loop stays free to handle
    other requests during the clone.

    Args:
        payload: JSON body with agent_name, task, git_url.
        db:      Request-scoped DB session.

    Returns:
        ExecutionResponse with status=PENDING.

    Raises:
        HTTPException 400: If git_url is invalid, repo not found, private.
        HTTPException 500: If git is not installed or cloned fails.
    """
    # Create DB row first to get the execution_id
    exec_payload = ExecutionCreate(
        agent_name=payload.agent_name,
        task=payload.task,
    )
    execution = await crud.create_execution(db, exec_payload)

    work_dir = _prepare_work_dir(execution.id)

    try:
        # Run the blocking git clone in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,           # default ThreadPoolExecutor
            clone_git,      # blocking function
            payload.git_url,
            work_dir,
        )
    except ValueError as e:
        # User error - bad URL, private repo, repo not found
        await crud.update_execution_status(
            db, execution, ExecutionStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # System error - git not installed, network failure
        await crud.update_execution_status(
            db, execution, ExecutionStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

    # work_dir is populated - enqueue the agent
    run_agent_task.delay(
        execution_id=execution.id,
        agent_name=execution.agent_name,
        task=execution.task,
    )

    return execution


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


@router.get("/executions/{execution_id}/download")
async def download_execution_artifacts(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Zip and stream all agent-generated artifact for a completed execution.

    Wals output/{execution_id}/, zips all files in memory, and return
    the zip as a stream download with filename execution_{id}_artifacts.zip.

    CONCEPT: StreamingResponse with an io.BytesIO buffer streams the zip
    directly from RAM to the client wihtout writing anything to disk.
    The Content-Disposition header tells the browser to save it as a file
    rather than trying to  display it inline.

    Args:
        execution_id (int): Primary key for the target execution.
        db (AsyncSession): Request-scoped DB session.

    Returns:
        StreamResponse: ZIP file stream.

    Raises:
        HTTPException 404: If execution doesn't exist.
        HTTPExecution 404: If no artifact exist yet (agent hasn't run).
        HTTPException 404: If execution hasn't completed yet.
    """
    # Verify execution exist
    execution = await crud.get_execution(db, execution_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found",
        )
    
    # Only allow downloads for completed executions.
    # Partial artifacts from running/failed execution could be inconsistent.
    # We allow FAILED too - partial artifacrs can still be useful for debugging.
    if execution.status == ExecutionStatus.PENDING:
        raise HTTPException(
            status_code=404,
            detail="Execution is still pending - no artifacts available yet",
        )
    if execution.status == ExecutionStatus.RUNNING:
            raise HTTPException(
                status_code=404,
                detail="Execution is still running - artifacts not ready yet",
        )
    
    # Build the zip
    try:
        zip_buffer = _zip_execution_artifacts(execution_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    filename = f"execution_{execution_id}_artifacts.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            # Content-Disposition: attachment tells the browser to download
            # the file rather than render it. filename= sets the default
            # save-as name the user sees in thier download dialog.
            "Content-Disposition": f"attachment; filename={filename}",
        }
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