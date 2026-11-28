"""scan client_ip for rate limits

Revision ID: 20251128_0005
Revises: 20251127_0004
Create Date: 2025-11-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20251128_0005"
down_revision: Union[str, None] = "20251127_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("client_ip", sa.String(length=45), nullable=True),
    )
    op.create_index("ix_scans_client_ip", "scans", ["client_ip"], unique=False)
    op.create_index(
        "ix_scans_client_ip_created_at",
        "scans",
        ["client_ip", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scans_client_ip_created_at", table_name="scans")
    op.drop_index("ix_scans_client_ip", table_name="scans")
    op.drop_column("scans", "client_ip")