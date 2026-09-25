"""add overdue task status and updated task event

Revision ID: e36b114e6120
Revises: ce8b5c3412ab
Create Date: 2026-09-25 18:28:32.482266

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e36b114e6120"
down_revision: str | Sequence[str] | None = "ce8b5c3412ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add new values to existing PostgreSQL enum types."""

    op.execute(
        """
        ALTER TYPE task_status
        ADD VALUE IF NOT EXISTS 'OVERDUE'
        """
    )

    op.execute(
        """
        ALTER TYPE task_event_type
        ADD VALUE IF NOT EXISTS 'UPDATED'
        """
    )


def downgrade() -> None:
    """
    PostgreSQL does not support removing enum values directly.

    Downgrade is intentionally left empty.
    """
    pass
