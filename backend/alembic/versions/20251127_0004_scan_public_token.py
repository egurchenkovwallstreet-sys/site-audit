"""scan public_token for unguessable share links

Revision ID: 20251127_0004
Revises: 20251122_0003
Create Date: 2025-11-27
"""

from __future__ import annotations

import secrets

from alembic import op
import sqlalchemy as sa

revision = "20251127_0004"
down_revision = "20251122_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("public_token", sa.String(length=64), nullable=True),
    )
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM scans WHERE public_token IS NULL"))
    for (scan_id,) in rows:
        token = secrets.token_urlsafe(24)
        conn.execute(
            sa.text("UPDATE scans SET public_token = :t WHERE id = :id"),
            {"t": token, "id": scan_id},
        )
    op.create_index("ix_scans_public_token", "scans", ["public_token"], unique=True)
    op.alter_column("scans", "public_token", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_scans_public_token", table_name="scans")
    op.drop_column("scans", "public_token")