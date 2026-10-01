"""Add notification and idempotency tracking; normalize order timestamps.

Revision ID: 20261001_03
Revises: 20260928_02
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from alembic import op
import sqlalchemy as sa


revision = "20261001_03"
down_revision = "20260928_02"
branch_labels = None
depends_on = None

CAIRO_TZ = ZoneInfo("Africa/Cairo")


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # Original datetime.now() values were naive local shop times. Interpret
        # them as Cairo time, then persist naive UTC for the SQLite adapter.
        rows = connection.execute(sa.text("SELECT id, created_at FROM orders")).all()
        for order_id, raw_value in rows:
            value = datetime.fromisoformat(raw_value) if isinstance(raw_value, str) else raw_value
            local = value.replace(tzinfo=CAIRO_TZ) if value.tzinfo is None else value.astimezone(CAIRO_TZ)
            utc_value = local.astimezone(timezone.utc).replace(tzinfo=None)
            connection.execute(
                sa.text("UPDATE orders SET created_at = :created_at WHERE id = :order_id"),
                {
                    "created_at": utc_value.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "order_id": order_id,
                },
            )
    elif connection.dialect.name == "postgresql":
        # Existing naive timestamps represent Cairo wall time; new values use
        # a native timezone-aware PostgreSQL column.
        op.execute(
            "ALTER TABLE orders ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE "
            "USING created_at AT TIME ZONE 'Africa/Cairo'"
        )
    else:
        raise RuntimeError("This migration supports SQLite and PostgreSQL")

    op.add_column("orders", sa.Column("idempotency_key", sa.String(36), nullable=True))
    op.create_index(
        "ix_orders_idempotency_key",
        "orders",
        ["idempotency_key"],
        unique=True,
    )
    op.add_column("orders", sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True))
    # delivery_slot stays VARCHAR so historical free-text values remain readable.


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade would remove order reliability data")
