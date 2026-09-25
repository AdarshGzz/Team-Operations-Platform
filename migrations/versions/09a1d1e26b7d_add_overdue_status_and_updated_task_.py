"""add overdue status and updated task event

Revision ID: 09a1d1e26b7d
Revises: e36b114e6120
Create Date: 2026-09-25 20:37:45.389859

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "09a1d1e26b7d"
down_revision: str | Sequence[str] | None = "e36b114e6120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'OVERDUE'")

    op.execute("ALTER TYPE task_event_type ADD VALUE IF NOT EXISTS 'UPDATED'")


def downgrade() -> None:

    # PostgreSQL does not support safely removing individual

    # enum values from an existing enum type.

    pass
