"""scan context_json

Revision ID: 20251121_0002
Revises: 20251121_0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20251121_0002"
down_revision = "20251121_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("context_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "context_json")