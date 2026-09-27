"""Adopt the original schema without dropping existing tables or data.

Revision ID: 20260928_01
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "20260928_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if "products" not in existing:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("price", sa.Numeric(10, 2), nullable=False),
            sa.Column("stock", sa.Integer(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("image_url", sa.String(500), nullable=True),
        )
        op.create_index("ix_products_id", "products", ["id"])

    if "orders" not in existing:
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("customer_name", sa.String(150), nullable=False),
            sa.Column("customer_phone", sa.String(30), nullable=False),
            sa.Column("customer_email", sa.String(150), nullable=True),
            sa.Column("receiver_name", sa.String(150), nullable=False),
            sa.Column("receiver_phone", sa.String(30), nullable=False),
            sa.Column("delivery_address", sa.String(500), nullable=False),
            sa.Column("delivery_area", sa.String(100), nullable=False),
            sa.Column("delivery_date", sa.Date(), nullable=False),
            sa.Column("delivery_slot", sa.String(100), nullable=False),
            sa.Column("card_message", sa.String(500), nullable=True),
            sa.Column("sender_name_on_card", sa.String(150), nullable=True),
            sa.Column("customer_note", sa.String(500), nullable=True),
            sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_orders_id", "orders", ["id"])

    if "order_items" not in existing:
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        )


def downgrade() -> None:
    raise RuntimeError("Automatic downgrade would delete existing shop data")
