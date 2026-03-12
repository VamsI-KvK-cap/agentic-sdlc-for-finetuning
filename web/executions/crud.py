from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from web.executions.models import Execution, ExecutionStatus
from web.executions.schemas import ExecutionCreate


async def create_execution(db: AsyncSession, payload: ExecutionCreate) -> Execution:
    """
    Insert a new Execution row into the database with an initial PENDING status.

    Called by POST /executions immediately before the background task is enqueued,
    ensuring the record exists in the DB before the agent starts and can update it.

    Args:
        db:      Active async SQLAlchemy session, injected via FastAPI's get_db dependency.
        payload: Validated request body containing `agent_name` and `task`.

    Returns:
        The newly created Execution ORM instance with all server-side fields
        (id, created_at, updated_at) populated after refresh.

    Raises:
        SQLAlchemyError: If the INSERT or COMMIT fails (e.g. DB unavailable,
                         constraint violation).
    """
    execution = Execution(
        agent_name=payload.agent_name,
        task=payload.task,
        status=ExecutionStatus.PENDING,   # explicit default; background task will transition this forward
    )
    db.add(execution)                     # stage the new instance in the session's identity map
    await db.commit()                     # flush + commit; assigns the DB-generated `id` to the instance
    await db.refresh(execution)           # re-fetch from DB so all server-side defaults (timestamps, id) are populated
    return execution


async def get_execution(db: AsyncSession, execution_id: int) -> Execution | None:
    """
    Fetch a single Execution record by its primary key.

    Returns None instead of raising so callers can decide how to handle
    a missing record (e.g. the router raises HTTPException 404, the background
    task silently bails out).

    Args:
        db:           Active async SQLAlchemy session.
        execution_id: Primary key of the target Execution row.

    Returns:
        The matching Execution ORM instance, or None if no row with
        the given ID exists.

    Raises:
        MultipleResultsFound: If somehow more than one row matches (should
                              never happen with a PK lookup).
    """
    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    # scalar_one_or_none: unwraps the single-column result safely;
    # returns None on zero rows, raises MultipleResultsFound on >1
    return result.scalar_one_or_none()


async def list_executions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    agent_name: str | None = None,
    status: ExecutionStatus | None = None,
) -> tuple[int, list[Execution]]:
    """
    Return a paginated, optionally filtered page of Execution records alongside
    the total matched count so clients can calculate page numbers without issuing
    a separate COUNT request.

    Filters are applied identically to both the data query and the count query
    to guarantee consistency between `total` and the returned rows.

    Args:
        db:         Active async SQLAlchemy session.
        skip:       Number of rows to skip before returning results (pagination offset).
                    Must be >= 0.
        limit:      Maximum number of rows to return. Enforced upstream at max=100
                    by the Query() validator in the router.
        agent_name: Optional exact-match filter on Execution.agent_name.
                    Pass None to include all agents.
        status:     Optional filter on Execution.status.
                    Pass None to include all lifecycle states.

    Returns:
        A tuple of:
          - total (int):            Count of all rows matching the filters,
                                    regardless of skip/limit.
          - executions (list):      Current page of Execution ORM instances,
                                    ordered newest-first by id (descending).

    Raises:
        SQLAlchemyError: If the SELECT queries fail.
    """
    query = select(Execution)                       # base data query; filters appended conditionally below
    count_query = select(func.count(Execution.id))  # mirrors the data query; must always share identical WHERE clauses

    if agent_name:
        # Apply the same filter to both queries so `total` reflects
        # only rows for the requested agent, not the entire table
        query = query.where(Execution.agent_name == agent_name)
        count_query = count_query.where(Execution.agent_name == agent_name)
    if status:
        # Same rationale: count and data must stay in sync
        query = query.where(Execution.status == status)
        count_query = count_query.where(Execution.status == status)

    # func.count always returns exactly one row, so scalar_one() is safe here
    total = (await db.execute(count_query)).scalar_one()

    rows = (
        await db.execute(
            query
            .offset(skip)                  # skip N rows for the requested page
            .limit(limit)                  # cap page size; prevents unbounded result sets
            .order_by(Execution.id.desc()) # newest-first; `id` is monotonic so it's a stable, index-friendly sort key
        )
    ).scalars().all()
    # .scalars() unwraps Row tuples into bare ORM instances
    # .all()     materialises the cursor into a list in memory

    return total, list(rows)  # list() converts ScalarResult → plain list expected by ExecutionListResponse


async def update_execution_status(
    db: AsyncSession,
    execution: Execution,
    status: ExecutionStatus,
    error_message: str | None = None,
) -> Execution:
    """
    Transition an Execution to a new lifecycle status and persist the change.

    Handles all forward status transitions driven by the background task:
      - PENDING  → RUNNING    (agent picked up the task)
      - RUNNING  → COMPLETED  (agent finished without error)
      - RUNNING  → FAILED     (agent raised an exception)

    Sets `completed_at` automatically for terminal states (COMPLETED, FAILED)
    and records `error_message` when the FAILED path is taken.

    Args:
        db:            Active async SQLAlchemy session. Must already contain
                       `execution` in its identity map (i.e. loaded in this session).
        execution:     Live ORM instance to mutate. Caller is responsible for
                       fetching it in the same session before calling this function.
        status:        Target ExecutionStatus to transition into.
        error_message: Human-readable error detail, populated only on the FAILED
                       path via str(exc) in the background task. Defaults to None.

    Returns:
        The updated Execution ORM instance, refreshed from the DB after commit.

    Raises:
        SQLAlchemyError: If the UPDATE or COMMIT fails.
    """
    execution.status = status
    # Explicitly set updated_at rather than relying solely on the column's
    # onupdate hook, ensuring accuracy regardless of SQLAlchemy flush timing
    execution.updated_at = datetime.now(timezone.utc)

    if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
        # completed_at is only set for terminal states; stays NULL while RUNNING
        execution.completed_at = datetime.now(timezone.utc)

    if error_message:
        # Only written on the FAILED path; COMPLETED leaves error_message as NULL
        execution.error_message = error_message

    await db.commit()          # persist all mutations above atomically
    await db.refresh(execution) # sync in-memory instance with DB state after commit
    return execution