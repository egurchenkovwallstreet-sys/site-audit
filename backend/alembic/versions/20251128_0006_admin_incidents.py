"""admin incidents for scan failures

Revision ID: 20251128_0006
Revises: 20251128_0005
Create Date: 2025-11-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20251128_0006"
down_revision: Union[str, None] = "20251128_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_incidents",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scan_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_incidents_scan_id", "admin_incidents", ["scan_id"])
    op.create_index(
        "ix_admin_incidents_created_at", "admin_incidents", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_admin_incidents_created_at", table_name="admin_incidents")
    op.drop_index("ix_admin_incidents_scan_id", table_name="admin_incidents")
    op.drop_table("admin_incidents")