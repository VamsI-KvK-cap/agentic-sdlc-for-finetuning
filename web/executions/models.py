import enum
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from web.database import Base  # declarative base shared across all ORM models


class ExecutionStatus(str, enum.Enum):
    """
    Lifecycle states for an Execution record.

    Inherits from both `str` and `enum.Enum` so that:
      - Values serialize to plain strings in JSON responses (e.g. "pending")
        without needing a custom encoder.
      - SQLAlchemy stores them as VARCHAR-compatible values with no extra mapping.
      - FastAPI Query() parameters accept the string form directly for filtering.

    Valid transitions driven by the background task in router.py:
        PENDING → RUNNING → COMPLETED
                          → FAILED

    Members:
        PENDING:   Row created; background task has not yet started the agent.
        RUNNING:   Background task picked up the execution and the agent is active.
        COMPLETED: Agent returned successfully without raising an exception.
        FAILED:    Agent raised an exception; details stored in Execution.error_message.
    """
    PENDING = "pending"       # initial state on INSERT; set by crud.create_execution
    RUNNING = "running"       # set by background task immediately before invoking the agent
    COMPLETED = "completed"   # set by background task after agent returns successfully
    FAILED = "failed"         # set by background task on exception; see Execution.error_message


class Execution(Base):
    """
    ORM model representing a single agent execution request.
    Maps 1-to-1 with a row in the ``executions`` table.

    Lifecycle:
        Created by crud.create_execution() with status=PENDING.
        Updated by crud.update_execution_status() as the background task progresses.
        Queried by crud.get_execution() and crud.list_executions().

    Attributes:
        id (int):
            Auto-incrementing surrogate primary key. Assigned by the DB on INSERT;
            use this value to poll GET /executions/{id} for status updates.

        agent_name (str):
            Identifier of the agent to invoke (max 100 chars). Indexed in the DB
            to support efficient filtering in list_executions(agent_name=...).

        status (ExecutionStatus):
            Current lifecycle state of the execution. Stored as a DB ENUM column
            and validated against ExecutionStatus values on write. Defaults to
            PENDING on creation; updated by the background task as it progresses.

        task (str):
            Free-form task description passed to the agent. Uses an unbounded Text
            column instead of VARCHAR because task prompts and instructions can be
            arbitrarily long.

        error_message (str | None):
            Human-readable error detail captured from str(exc) when the agent fails.
            NULL for all non-FAILED executions. Populated exclusively by
            crud.update_execution_status() on the FAILED path.

        created_at (datetime):
            UTC timestamp recorded when the row is first inserted. Set via a lambda
            default so each INSERT gets its own evaluation of datetime.now(utc)
            rather than a single value frozen at class-definition time. Never
            changes after creation.

        updated_at (datetime):
            UTC timestamp refreshed on every status transition. Set on INSERT via
            `default` and on every subsequent UPDATE via SQLAlchemy's `onupdate`
            hook. Use this field to detect stale executions or measure queue lag.

        completed_at (datetime | None):
            UTC timestamp recorded when the execution reaches a terminal state
            (COMPLETED or FAILED). NULL while the execution is still PENDING or
            RUNNING. Set explicitly by crud.update_execution_status(); not managed
            by a DB trigger or column default.
    """
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,   # DB assigns the value on INSERT; never set manually
    )
    agent_name: Mapped[str] = mapped_column(
        String(100),          # 100-char cap sufficient for agent identifiers; use Text if names grow unbounded
        nullable=False,
        index=True,           # B-tree index; speeds up WHERE agent_name = ? in list_executions
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus),          # DB-level ENUM; rejects any value not in ExecutionStatus at the DB layer
        nullable=False,
        default=ExecutionStatus.PENDING # Python-side default applied by SQLAlchemy before INSERT; not a DB DEFAULT
    )
    task: Mapped[str] = mapped_column(
        Text,                 # unbounded; avoids truncation for long task prompts or multi-step instructions
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,                 # unbounded; exception tracebacks can be long
        nullable=True,        # NULL for PENDING / RUNNING / COMPLETED rows; only populated on FAILED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),                    # timezone=True stores as TIMESTAMPTZ (Postgres) or with UTC offset
        nullable=False,
        default=lambda: datetime.now(timezone.utc), # lambda: deferred per-INSERT evaluation; a bare call would freeze
                                                    # at class-definition time, giving all rows the same timestamp
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),    # evaluated on INSERT (same rationale as created_at)
        onupdate=lambda: datetime.now(timezone.utc),   # evaluated automatically by SQLAlchemy on every UPDATE;
                                                       # distinct from `default` which only fires on INSERT
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,        # NULL while PENDING or RUNNING; set on first terminal state transition
                              # by crud.update_execution_status(); no DB DEFAULT or trigger involved
    )