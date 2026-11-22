"""finding penalty_code

Revision ID: 20251122_0003
Revises: 20251121_0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20251122_0003"
down_revision = "20251121_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column("penalty_code", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "penalty_code")