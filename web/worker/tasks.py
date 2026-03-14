# web/worker/tasks.py
#
# Defines all Celery tasks for the agentic-sdlc worker.
#
# CONCEPT: A Celery task is just a regular Python function decorated
# with @celery_app.task. The decorator registers it with the Celery
# instance so the worker knows how to find and execute it when a
# message arrives from Redis.
#
# Tasks must be:
#   - Importable at the module level (no dynamic definition)
#   - Serialisable arguments only (str, int, list, dict — no ORM objects)
#   - Idempotent where possible (safe to retry if they fail midway)
#
# Celery tasks for agent execution.
#
# FIXED: "Future attached to a different loop" error.
#
# ROOT CAUSE:
#   SQLAlchemy's async engine binds its connection pool to the event loop
#   that was active when the engine was first used. asyncio.run() creates
#   a NEW event loop each time it's called. Calling asyncio.run() multiple
#   times per task meant the engine (bound to loop #1) was being accessed
#   from loop #2, #3, etc. — hence the error.
#
# FIX:
#   Wrap the ENTIRE task lifecycle in a single asyncio.run() call.
#   One task = one event loop = one engine binding. No conflicts.
#   The async helper _run_agent_async() owns the full lifecycle:
#   mark running → run agent → mark completed/failed.

import asyncio
import logging
import os

from dotenv import load_dotenv

from web.worker.celery_app import celery_app

load_dotenv()

logger = logging.getLogger(__name__)

working_dir = os.getenv("WORKING_DIR", "./output")


# ── Main agent task (synchronous entry point) ───────────────────────────────────────────────────────

@celery_app.task(
    name="web.worker.tasks.run_agent_task",   # explicit name — must match task_routes in celery_app.py
                                              # without this, Celery auto-generates a name that can
                                              # change if you refactor, breaking queued messages

    bind=True,                                # CONCEPT: bind=True passes `self` as first arg.
                                              # `self` is the task instance — gives access to:
                                              #   self.retry()       → retry with backoff
                                              #   self.request.id    → unique task ID (UUID)
                                              #   self.request.retries → current retry count

    max_retries=3,                            # CONCEPT: if the task raises an exception and calls
                                              # self.retry(), Celery will re-queue it up to 3 times.
                                              # On the 4th failure it raises MaxRetriesExceededError
                                              # and the task is marked FAILURE in Redis.

    default_retry_delay=60,                   # seconds to wait between retries (exponential backoff
                                              # can be added via countdown= in self.retry() call)
)
def run_agent_task(self, execution_id: int, agent_name: str, task: str) -> dict:
    """
    Celery task that drives the full agent execution lifecycle.
    Celery task — synchronous entry point.

    Delegates immediately to _run_agent_async() via a SINGLE asyncio.run()
    call. This is the key fix — one event loop for the entire task lifetime.

    CONCEPT: Why one asyncio.run() instead of many?

        asyncio.run() does three things:
          1. Creates a new event loop
          2. Runs the coroutine to completion
          3. CLOSES the event loop and all its resources

    Ported from FastAPI's _run_agent_task background coroutine.
    Key differences from the BackgroundTasks version:

      1. Synchronous (def not async def) — Celery manages threading.
        Async DB calls are wrapped in one asyncio.run() = one loop = one engine binding.
        All DB operations (_mark_running, agent run, _mark_completed)
        happen inside the same loop.

      2. Retry support — if the LLM API is down or the agent raises
         a transient error, self.retry() re-queues the task automatically.

      3. Task ID — self.request.id is a UUID assigned by Celery.
         Stored alongside execution_id for cross-referencing in logs.

      4. Survives restarts — the task message lives in Redis until
         acknowledged. If the worker crashes, Redis re-delivers it.

    Args:
        self         (Task):  Celery task instance (injected by bind=True).
        execution_id (int):   Primary key of the Execution row to update.
        agent_name   (str):   Agent identifier for the orchestrator.
        task         (str):   Free-form task description for the agent.

    Returns:
        dict: Summary of the completed execution for Celery's result backend.
              {"execution_id": int, "status": "completed" | "failed"}

    Raises:
        self.retry(): On transient failures (connection errors, timeouts).
        Exception:    On permanent failures — task marked FAILURE in Redis.
    """

    task_id = self.request.id          # Celery-assigned UUID for this task invocation
    retry_count = self.request.retries # 0 on first attempt, 1 on first retry, etc.

    logger.info(
        f"[task={task_id}] Starting agent execution "
        f"execution_id={execution_id} agent={agent_name} retry={retry_count}"
    )


    try:
        # Single asyncio.run() — entire async lifecycle in one event loop
        result = asyncio.run(
            _run_agent_async(execution_id, agent_name, task, task_id)
        )
        return result

    except Exception as exc:
        logger.error(
            f"[task={task_id}] Execution {execution_id} failed "
            f"(retry {retry_count}/{self.max_retries}): {exc}",
            exc_info=True,             # includes full traceback in logs
        )

        # ── Retry logic ───────────────────────────────────────────────────
        # CONCEPT: We distinguish between transient and permanent failures.
        #
        # Transient (worth retrying):
        #   - ConnectionError: Redis/DB temporarily unreachable
        #   - TimeoutError: LLM API slow to respond
        #
        # Permanent (not worth retrying):
        #   - ValueError: bad task input
        #   - Any error on the final retry attempt
        #
        # self.retry() re-queues the task with a delay and raises
        # celery.exceptions.Retry which Celery catches internally —
        # the exception does NOT propagate to the caller.
        # The task state in Redis is set to RETRY, not FAILURE.

        is_transient = isinstance(exc, (ConnectionError, TimeoutError, OSError))

        if is_transient and retry_count < self.max_retries:
            # Exponential backoff: 60s, 120s, 240s
            countdown = self.default_retry_delay * (2 ** retry_count)
            logger.warning(
                f"[task={task_id}] Transient error — retrying in {countdown}s"
            )
            raise self.retry(exc=exc, countdown=countdown)

        # Re-raise so Celery marks this task as FAILURE in Redis result backend
        # and the full traceback appears in worker logs.
        raise


# ── Async lifecycle — runs inside a single event loop ─────────────────────

async def _run_agent_async(
    execution_id: int,
    agent_name: str,
    task: str,
    task_id: str,
) -> dict:
    """
    Full async lifecycle for one agent execution.

    CONCEPT: This coroutine owns the entire execution lifecycle.
    All DB sessions are opened and closed within this single coroutine,
    which runs inside a single event loop (created by asyncio.run() above).

    SQLAlchemy's async engine is created fresh here using
    create_async_engine() — it binds to THIS event loop, not the
    module-level engine that was bound at worker startup.

    Why create a new engine here instead of using the module-level one?
    Because the module-level engine in web/database.py was bound to the
    event loop that existed when the worker first imported it — which is
    a different loop than the one asyncio.run() creates for this task.
    Creating a fresh engine here guarantees it's bound to the correct loop.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from web.executions import crud
    from web.executions.models import ExecutionStatus

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@db:5432/agentic_sdlc"
    )

    # CONCEPT: Fresh engine per task.
    # pool_pre_ping=True tests the connection before using it — prevents
    # "connection closed" errors if the DB restarted between tasks.
    # pool_size=2 is sufficient — this task only needs 1-2 connections.
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=2,
    )

    # Create a session factory bound to this engine (and therefore this loop)
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        # ── Phase 1: Mark RUNNING ──────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            execution = await crud.get_execution(db, execution_id)
            if not execution:
                logger.warning(f"[task={task_id}] Execution {execution_id} not found — aborting")
                return {"execution_id": execution_id, "status": "not_found"}
            await crud.update_execution_status(db, execution, ExecutionStatus.RUNNING)

        logger.info(f"[task={task_id}] Marked execution {execution_id} as RUNNING")

        # ── Phase 2: Run the agent ─────────────────────────────────────────
        # Lazy import — avoids loading heavy ML deps at worker startup
        from src.agents.orchestrator_agent.orchestrator_agent import run

        work_dir = os.path.join(working_dir, str(execution_id))
        os.makedirs(work_dir, exist_ok=True)

        logger.info(f"[task={task_id}] Running agent in {work_dir}")

        # run() is synchronous (blocking). We're already inside an event loop
        # (from asyncio.run()), so we use loop.run_in_executor() to run the
        # blocking function in a thread without blocking this event loop.
        #
        # CONCEPT: run_in_executor(None, fn, *args)
        #   None → use the default ThreadPoolExecutor
        #   Runs fn(*args) in a thread, awaits completion without blocking loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run, task, agent_name, work_dir, execution_id)

        # ── Phase 3 (success): Mark COMPLETED ─────────────────────────────
        async with AsyncSessionLocal() as db:
            execution = await crud.get_execution(db, execution_id)
            await crud.update_execution_status(db, execution, ExecutionStatus.COMPLETED)

        logger.info(f"[task={task_id}] Execution {execution_id} COMPLETED")
        return {"execution_id": execution_id, "status": "completed"}

    except Exception as exc:
        logger.error(
            f"[task={task_id}] Execution {execution_id} FAILED: {exc}",
            exc_info=True,
        )

        # ── Phase 3 (failure): Mark FAILED ────────────────────────────────
        try:
            async with AsyncSessionLocal() as db:
                execution = await crud.get_execution(db, execution_id)
                if execution:
                    await crud.update_execution_status(
                        db, execution,
                        ExecutionStatus.FAILED,
                        error_message=str(exc),
                    )
        except Exception as db_exc:
            # If the DB update itself fails, log it but still re-raise
            # the original exception so Celery marks the task as FAILURE
            logger.error(f"[task={task_id}] Failed to update DB to FAILED state: {db_exc}")

        raise

    finally:
        # CONCEPT: Always dispose the engine when done.
        # This closes all connections in the pool cleanly.
        # Without this, connections leak — each task would leave open
        # DB connections until the OS eventually times them out.
        await engine.dispose()