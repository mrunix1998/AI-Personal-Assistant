"""multi calendar sources

Revision ID: 0002_multi_calendar_sources
Revises: 0001_initial
Create Date: 2026-06-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0002_multi_calendar_sources"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'outlook_calendar'")
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'apple_ics'")
    op.execute("ALTER TYPE providername ADD VALUE IF NOT EXISTS 'generic_ics'")

    if "calendar_sources" in inspect(bind).get_table_names():
        return

    op.create_table(
        "calendar_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("provider", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=False, index=True),
        sa.Column("ics_url", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"), index=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", "external_id", name="uq_calendar_source_external"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "calendar_sources" in inspect(bind).get_table_names():
        op.drop_table("calendar_sources")
