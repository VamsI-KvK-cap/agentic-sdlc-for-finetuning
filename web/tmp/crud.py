from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from web.executions.models import Execution, ExecutionStatus
from web.executions.schemas import ExecutionCreate


async def create_execution(db: AsyncSession, payload: ExecutionCreate) -> Execution:
    execution = Execution(
        agent_name=payload.agent_name,
        task=payload.task,
        status=ExecutionStatus.PENDING,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


async def get_execution(db: AsyncSession, execution_id: int) -> Execution | None:
    result = await db.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    return result.scalar_one_or_none()


async def list_executions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    agent_name: str | None = None,
    status: ExecutionStatus | None = None,
) -> tuple[int, list[Execution]]:
    query = select(Execution)
    count_query = select(func.count(Execution.id))

    if agent_name:
        query = query.where(Execution.agent_name == agent_name)
        count_query = count_query.where(Execution.agent_name == agent_name)
    if status:
        query = query.where(Execution.status == status)
        count_query = count_query.where(Execution.status == status)

    total = (await db.execute(count_query)).scalar_one()
    rows = (await db.execute(query.offset(skip).limit(limit).order_by(Execution.id.desc()))).scalars().all()
    return total, list(rows)


async def update_execution_status(
    db: AsyncSession,
    execution: Execution,
    status: ExecutionStatus,
    error_message: str | None = None,
) -> Execution:
    execution.status = status
    execution.updated_at = datetime.now(timezone.utc)

    if status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
        execution.completed_at = datetime.now(timezone.utc)

    if error_message:
        execution.error_message = error_message

    await db.commit()
    await db.refresh(execution)
    return execution
