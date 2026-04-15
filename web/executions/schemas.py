"""
Pydantic schemas for execution API requests and responses.

This module defines request and response models for the execution management
API endpoints. These schemas handle validation, serialization, and documentation
of execution lifecycle data, seamlessly integrating FastAPI request/response
handling with SQLAlchemy ORM models.

Modules:
    - ExecutionCreate: Request schema for creating new executions (greenfield).
    - ExecutionFromGitCreate: Request schema for Git repository cloning (brownfield).
    - ExecutionResponse: Response schema for a single execution record.
    - ExecutionListResponse: Paginated response schema for listing executions.
"""

from datetime import datetime

# Import Pydantic components for schema definition and validation
from pydantic import BaseModel, Field

# Import ExecutionStatus enum from models for API/DB synchronization
# (reuse the same enum so API and DB values stay in sync)
from web.executions.models import ExecutionStatus


class ExecutionCreate(BaseModel):
    """
    Request body schema for POST /executions endpoint (greenfield creation).

    This schema defines the contract for creating a new execution from scratch
    without reference to existing code. Only exposes the fields that callers
    are permitted to set on creation. All other fields (id, status, timestamps)
    are server-assigned and must never be accepted from untrusted client input.

    Validation:
        Pydantic enforces type checking and the `...` (Ellipsis/required)
        constraint on all fields before the request reaches the route handler.
        Invalid payloads are rejected with a 422 Unprocessable Entity response
        automatically by FastAPI middleware.

    Attributes:
        agent_name (str):
            Identifier of the agent to invoke. Must be a non-empty string
            matching a registered agent name in the orchestrator
            (e.g., ``"python"``, ``"javascript"``). Maximum length enforced
            at the database layer (String(100)); Pydantic does not add a length
            constraint here by default.

        task (str):
            Free-form task description or instruction to pass to the agent.
            No length limit enforced at the schema level; the database column
            is unbounded Text type. Should be a clear, self-contained
            description of the work expected from the agent.

    Example:
        >>> payload = {
        ...     "agent_name": "python",
        ...     "task": "Write a function that reverses a linked list"
        ... }
    """

    # Required field: agent identifier; Ellipsis (...) enforces required constraint
    agent_name: str = Field(
        ...,
        description="Name of the agent to run (e.g. 'python')",
    )

    # Required field: task description; Ellipsis (...) enforces required constraint
    task: str = Field(
        ...,
        description="Task description for the agent",
    )


class ExecutionFromGitCreate(BaseModel):
    """
    Request body schema for POST /executions/from-git (brownfield Git repo).

    Brownfield development means working with an existing codebase rather than
    starting from scratch (greenfield). The agent will read the file structure
    from work_dir before planning changes. The specified git_url is cloned
    into output/{execution_id}/ before the Celery task starts, ensuring the
    agent's planner sees the full repository on its first run.

    Attributes:
        agent_name (str):
            Agent to invoke (e.g., ``"python"``). Must match a registered
            agent identifier known to the orchestrator.

        task (str):
            Description of what needs to be changed or added in the existing
            repository. The agent will read the cloned code and implement
            the requested modifications.

        git_url (str):
            Public HTTPS Git URL for cloning. SSH URLs and private
            repositories are not supported. Validated as a proper URL
            structure by Pydantic's HttpUrl type.

    Example:
        >>> payload = {
        ...     "agent_name": "python",
        ...     "task": "Add input validation to all API endpoints",
        ...     "git_url": "https://github.com/user/my-repo"
        ... }
    """

    # Required field: agent identifier for brownfield development
    agent_name: str = Field(
        ...,
        description="Name of the agent to run",
    )

    # Required field: description of changes to make in existing codebase
    task: str = Field(
        ...,
        description="What to change in the existing codebase",
    )

    # Required field: public HTTPS Git URL for repository cloning
    git_url: str = Field(
        ...,
        description="Public HTTPS Git URL to clone",
    )


class ExecutionResponse(BaseModel):
    """
    Response schema for a single Execution record.

    This schema is returned by execution endpoints to represent the current
    state of an execution. It supports ORM-to-Pydantic conversion for seamless
    integration with SQLAlchemy models.

    Returned by endpoints:
        - POST /executions (HTTP 202 Accepted)
            Returns initial snapshot with status=PENDING immediately after
            task submission.
        - GET /executions/{id}
            Returns current execution state; clients poll this to track
            progress asynchronously.
        - GET /executions
            Returned as array elements inside ExecutionListResponse for
            paginated listing.

    Serialization:
        ``model_config = {"from_attributes": True}`` instructs Pydantic to
        populate fields directly from SQLAlchemy ORM instances without manual
        dict conversion. This configuration replaces the deprecated
        orm_mode = True from Pydantic v1.

    Attributes:
        id (int):
            Server-assigned surrogate primary key. Use this value to construct
            the polling URL for status updates: GET /executions/{id}.

        agent_name (str):
            Echoed back from the submitted request to allow callers to confirm
            which agent was scheduled without maintaining the original request
            payload locally.

        status (ExecutionStatus):
            Current lifecycle state of the execution. Changes asynchronously
            as the background task progresses. Typical state transitions:
                PENDING → RUNNING → COMPLETED (success path)
                PENDING → RUNNING → FAILED (failure path)

        task (str):
            Echoed back from the submitted request. Useful when polling for
            status without retaining the original request payload client-side.

        error_message (str | None):
            Human-readable error detail captured when the agent raises an
            exception. None for all non-FAILED executions. Inspect this field
            when status == FAILED to understand the root cause.

        created_at (datetime):
            UTC timestamp (timezone-aware) recorded when the database row was
            first inserted. Never changes after the initial POST request.

        updated_at (datetime):
            UTC timestamp (timezone-aware) refreshed on every status transition.
            Use the time delta between created_at and updated_at to measure
            total queue and execution time.

        completed_at (datetime | None):
            UTC timestamp (timezone-aware) recorded when the execution reaches
            a terminal state (COMPLETED or FAILED). None while the execution
            is still PENDING or RUNNING. Use this with created_at to measure
            end-to-end execution duration.

    Example response:
        >>> response = {
        ...     "id": 42,
        ...     "agent_name": "python",
        ...     "status": "running",
        ...     "task": "Write a function that reverses a linked list",
        ...     "error_message": None,
        ...     "created_at": "2024-01-15T10:30:00Z",
        ...     "updated_at": "2024-01-15T10:30:05Z",
        ...     "completed_at": None
        ... }
    """

    # Server-assigned surrogate primary key; use to construct polling URL
    id: int

    # Echoed from request; helps callers confirm which agent was scheduled
    agent_name: str

    # Current lifecycle state; changes asynchronously as task progresses
    status: ExecutionStatus

    # Echoed from request; provides context when polling without local state
    task: str

    # Populated only when status == FAILED; None for other states
    error_message: str | None = None

    # UTC timezone-aware timestamp; set on INSERT, never changes
    created_at: datetime

    # UTC timezone-aware timestamp; refreshed on each status transition
    updated_at: datetime

    # UTC timezone-aware timestamp; None until reaching terminal state
    completed_at: datetime | None = None

    # ORM configuration: allow direct population from SQLAlchemy instances
    # This replaces orm_mode = True from Pydantic v1
    model_config = {"from_attributes": True}


class ExecutionListResponse(BaseModel):
    """
    Paginated response schema for GET /executions endpoint.

    Wraps a page of ExecutionResponse objects alongside the total matched
    count to allow clients to implement pagination without issuing a separate
    COUNT query. This pattern enables efficient pagination and accurate
    progress tracking for large result sets.

    Attributes:
        total (int):
            Total number of Execution rows matching the applied filters
            (agent_name, status, etc.), regardless of pagination parameters.
            Use this to calculate total page count::

                total_pages = math.ceil(total / limit)

        executions (list[ExecutionResponse]):
            Current page of Execution records, ordered newest-first by id.
            Length is at most the ``limit`` query parameter (maximum 100,
            enforced by the router). May be an empty list if ``skip`` exceeds
            ``total`` or no rows match the applied filters.

    Example response:
        >>> response = {
        ...     "total": 84,
        ...     "executions": [
        ...         {
        ...             "id": 84,
        ...             "agent_name": "python",
        ...             "status": "completed",
        ...             ...
        ...         },
        ...         ...
        ...     ]
        ... }
    """

    # Pre-pagination total count; use with limit to calculate total pages
    total: int

    # Current page of results; length <= limit parameter; ordered newest-first
    executions: list[ExecutionResponse]