"""add connected account id to calendar events

Revision ID: 0003_calendar_account
Revises: 0002_multi_calendar_sources
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_calendar_account"
down_revision = "0002_multi_calendar_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {col["name"] for col in inspect(bind).get_columns("calendar_events")}
    if "connected_account_id" not in columns:
        op.add_column("calendar_events", sa.Column("connected_account_id", sa.UUID(), nullable=True))
    indexes = {idx["name"] for idx in inspect(bind).get_indexes("calendar_events")}
    if "ix_calendar_events_connected_account_id" not in indexes:
        op.create_index("ix_calendar_events_connected_account_id", "calendar_events", ["connected_account_id"])
    fks = {fk["name"] for fk in inspect(bind).get_foreign_keys("calendar_events")}
    if "fk_calendar_events_connected_account_id" not in fks:
        op.create_foreign_key(
            "fk_calendar_events_connected_account_id",
            "calendar_events",
            "connected_accounts",
            ["connected_account_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    fks = {fk["name"] for fk in inspect(bind).get_foreign_keys("calendar_events")}
    if "fk_calendar_events_connected_account_id" in fks:
        op.drop_constraint("fk_calendar_events_connected_account_id", "calendar_events", type_="foreignkey")
    indexes = {idx["name"] for idx in inspect(bind).get_indexes("calendar_events")}
    if "ix_calendar_events_connected_account_id" in indexes:
        op.drop_index("ix_calendar_events_connected_account_id", table_name="calendar_events")
    columns = {col["name"] for col in inspect(bind).get_columns("calendar_events")}
    if "connected_account_id" in columns:
        op.drop_column("calendar_events", "connected_account_id")
