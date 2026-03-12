from datetime import datetime
from pydantic import BaseModel, Field
from web.executions.models import ExecutionStatus  # reuse the same enum so API and DB values stay in sync


class ExecutionCreate(BaseModel):
    """
    Request body schema for POST /executions.

    Only exposes the fields the caller is allowed to set on creation.
    All other fields (id, status, timestamps) are server-assigned and
    must not be accepted from untrusted client input.

    Validation:
        Pydantic enforces types and the `...` (required) constraint on
        both fields before the request reaches the route handler. Invalid
        payloads are rejected with a 422 Unprocessable Entity response
        automatically by FastAPI.

    Attributes:
        agent_name (str):
            Identifier of the agent to invoke. Must be a non-empty string
            matching a registered agent name known to the orchestrator
            (e.g. ``"python"``, ``"javascript"``). Max length is enforced
            at the DB layer (String(100)); Pydantic does not add a length
            constraint here by default.

        task (str):
            Free-form task description or instruction to pass to the agent.
            No length limit enforced at the schema level; the DB column is
            unbounded Text. Should be a clear, self-contained description
            of the work the agent is expected to perform.

    Example payload::

        {
            "agent_name": "python",
            "task": "Write a function that reverses a linked list"
        }
    """
    agent_name: str = Field(
        ...,                                                    # `...` (Ellipsis) = required; no default value; omitting raises ValidationError
        description="Name of the agent to run (e.g. 'python')",
    )
    task: str = Field(
        ...,                                                    # `...` (Ellipsis) = required; no default value; omitting raises ValidationError
        description="Task description for the agent",
    )


class ExecutionResponse(BaseModel):
    """
    Response schema for a single Execution record.

    Returned by:
        - POST /executions (HTTP 202 Accepted) — initial snapshot with status=PENDING
        - GET  /executions/{id}                — current state; poll this to track progress
        - GET  /executions                     — as elements inside ExecutionListResponse

    Serialization:
        ``model_config = {"from_attributes": True}`` allows Pydantic to populate
        this schema directly from a SQLAlchemy ORM instance without manually
        converting to a dict first. This replaces ``orm_mode = True`` from
        Pydantic v1.

    Attributes:
        id (int):
            Server-assigned surrogate primary key. Use this value to construct
            the polling URL: GET /executions/{id}.

        agent_name (str):
            Echoed back from the request so callers can confirm which agent
            was scheduled without storing the original payload locally.

        status (ExecutionStatus):
            Current lifecycle state of the execution. Changes asynchronously
            as the background task progresses. Poll GET /executions/{id} to
            observe transitions:
                PENDING → RUNNING → COMPLETED
                                  → FAILED

        task (str):
            Echoed back from the request. Useful when polling for status
            without needing to retain the original request payload client-side.

        error_message (str | None):
            Human-readable error detail captured when the agent raises an
            exception. None for all non-FAILED executions. Inspect this field
            when status == FAILED to understand the root cause.

        created_at (datetime):
            UTC timestamp recorded when the row was first inserted. Timezone-aware.
            Never changes after the initial POST.

        updated_at (datetime):
            UTC timestamp refreshed on every status transition. Timezone-aware.
            Use the delta between created_at and updated_at to measure total
            queue and execution time.

        completed_at (datetime | None):
            UTC timestamp recorded when the execution reaches a terminal state
            (COMPLETED or FAILED). None while the execution is still PENDING
            or RUNNING. Use this alongside created_at to measure end-to-end
            execution duration.

    Example response::

        {
            "id": 42,
            "agent_name": "python",
            "status": "running",
            "task": "Write a function that reverses a linked list",
            "error_message": null,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:05Z",
            "completed_at": null
        }
    """
    id: int                               # server-assigned surrogate key; use this to construct the polling URL
    agent_name: str                       # echoed back so callers can confirm which agent was scheduled
    status: ExecutionStatus               # current lifecycle state; changes asynchronously as background task progresses
    task: str                             # echoed back for context; useful when polling without storing local state
    error_message: str | None = None      # None for PENDING/RUNNING/COMPLETED; populated only when status == FAILED
    created_at: datetime                  # UTC timezone-aware timestamp; set on INSERT, never changes
    updated_at: datetime                  # UTC timezone-aware timestamp; refreshed on every status transition
    completed_at: datetime | None = None  # None while PENDING/RUNNING; set on first terminal state (COMPLETED or FAILED)

    model_config = {"from_attributes": True}  # allows direct population from SQLAlchemy ORM instances;
                                              # replaces orm_mode = True from Pydantic v1


class ExecutionListResponse(BaseModel):
    """
    Paginated response schema for GET /executions.

    Wraps a page of ExecutionResponse objects alongside the total matched
    count so clients can implement pagination without issuing a separate
    COUNT request.

    Attributes:
        total (int):
            Total number of Execution rows matching the applied filters
            (agent_name, status), regardless of the skip/limit pagination
            parameters. Use this to calculate total page count::

                total_pages = math.ceil(total / limit)

        executions (list[ExecutionResponse]):
            Current page of Execution records, ordered newest-first by id.
            Length is at most ``limit`` (max 100, enforced by the router).
            May be an empty list if ``skip`` exceeds ``total`` or no rows
            match the applied filters.

    Example response::

        {
            "total": 84,
            "executions": [
                {
                    "id": 84,
                    "agent_name": "python",
                    "status": "completed",
                    ...
                },
                ...
            ]
        }
    """
    total: int                              # pre-pagination count; use with limit to calculate total pages
    executions: list[ExecutionResponse]     # current page; length <= limit query param; ordered newest-first by id
"""
Key commentary decisions:

- ExecutionStatus import rationale — noted that reusing the ORM enum keeps API and DB values in sync, explaining why it's imported rather than defining a separate enum

- Field(...) — the ... (Ellipsis) meaning "required" isn't obvious to readers unfamiliar with Pydantic, so it's called out explicitly

- from_attributes = True — explains both what it does (read from ORM instances) and the migration context (replaces orm_mode from v1), which is a common source of confusion

- total field — tied directly to its practical use case: avoiding a separate COUNT round-trip when paginating

- error_message / completed_at nullability — cross-referenced with the status values that trigger them, mirroring the same pattern used in models.py
"""