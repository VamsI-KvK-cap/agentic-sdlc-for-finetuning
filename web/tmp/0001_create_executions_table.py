"""create executions table

Revision ID: 0001
Revises: 
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="executionstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_agent_name", "executions", ["agent_name"])


def downgrade() -> None:
    op.drop_index("ix_executions_agent_name", table_name="executions")
    op.drop_table("executions")
    op.execute("DROP TYPE IF EXISTS executionstatus")
