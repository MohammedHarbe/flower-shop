"""Remove backfill defaults so catalog columns match their ORM definitions.

Revision ID: 20261001_04
Revises: 20261001_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20261001_04"
down_revision = "20261001_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Revision 02 needed these defaults to populate existing rows. New inserts
    # use the model's Python defaults; existing values are preserved.
    with op.batch_alter_table("products") as batch:
        for name in ("featured", "best_seller"):
            batch.alter_column(name, existing_type=sa.Boolean(), existing_nullable=False, server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("products") as batch:
        for name in ("featured", "best_seller"):
            batch.alter_column(name, existing_type=sa.Boolean(), existing_nullable=False, server_default=sa.false())
