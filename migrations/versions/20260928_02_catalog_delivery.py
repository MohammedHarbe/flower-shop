"""Add catalog browsing fields, Arabic product text, and delivery governorate.

Revision ID: 20260928_02
Revises: 20260928_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260928_02"
down_revision = "20260928_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("name_ar", sa.String(150), nullable=True))
    op.add_column("products", sa.Column("description_ar", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("products", sa.Column("occasion", sa.String(100), nullable=True))
    op.add_column(
        "products",
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "products",
        sa.Column("best_seller", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Historical orders lack enough information for a reliable backfill.
    op.add_column("orders", sa.Column("governorate", sa.String(20), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade would delete catalog and governorate data")
