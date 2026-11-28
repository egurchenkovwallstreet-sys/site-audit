"""queue depth snapshots for admin

Revision ID: 20251128_0007
Revises: 20251128_0006
Create Date: 2025-11-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20251128_0007"
down_revision: Union[str, None] = "20251128_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "queue_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("queued_count", sa.Integer(), nullable=False),
        sa.Column("running_count", sa.Integer(), nullable=False),
        sa.Column("max_concurrent", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_queue_snapshots_recorded_at",
        "queue_snapshots",
        ["recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_queue_snapshots_recorded_at", table_name="queue_snapshots")
    op.drop_table("queue_snapshots")