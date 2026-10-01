"""Add delivery zones, payment state, and backend-authoritative order totals.

Revision ID: 20261001_05
Revises: 20261001_04
"""

from alembic import op
import sqlalchemy as sa


revision = "20261001_05"
down_revision = "20261001_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("delivery_zones"):
        op.create_table(
            "delivery_zones",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("governorate", sa.String(length=20), nullable=False),
            sa.Column("name_en", sa.String(length=100), nullable=False),
            sa.Column("name_ar", sa.String(length=100), nullable=True),
            sa.Column("fee", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )

    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    for column_name, column_type in {
        "subtotal": sa.Numeric(10, 2),
        "delivery_fee": sa.Numeric(10, 2),
        "payment_method": sa.String(length=30),
        "payment_status": sa.String(length=30),
        "delivery_zone_id": sa.Integer(),
        "delivery_latitude": sa.Float(),
        "delivery_longitude": sa.Float(),
        "google_place_id": sa.String(length=200),
    }.items():
        if column_name not in existing_columns:
            op.add_column("orders", sa.Column(column_name, column_type, nullable=True))

    connection.execute(sa.text("UPDATE orders SET subtotal = total_price WHERE subtotal IS NULL"))
    connection.execute(sa.text("UPDATE orders SET delivery_fee = 0.00 WHERE delivery_fee IS NULL"))
    connection.execute(sa.text("UPDATE orders SET payment_method = 'cash_on_delivery' WHERE payment_method IS NULL"))
    connection.execute(sa.text("UPDATE orders SET payment_status = 'unpaid' WHERE payment_status IS NULL"))

    with op.batch_alter_table("orders") as batch:
        batch.alter_column("subtotal", existing_type=sa.Numeric(10, 2), nullable=False)
        batch.alter_column("delivery_fee", existing_type=sa.Numeric(10, 2), nullable=False)
        batch.alter_column("payment_method", existing_type=sa.String(length=30), nullable=False)
        batch.alter_column("payment_status", existing_type=sa.String(length=30), nullable=False)

    with op.batch_alter_table("orders") as batch:
        if not any(
            fk["name"] == "fk_orders_delivery_zone_id"
            for fk in inspector.get_foreign_keys("orders")
        ):
            batch.create_foreign_key(
                "fk_orders_delivery_zone_id",
                "delivery_zones",
                ["delivery_zone_id"],
                ["id"],
            )


def downgrade() -> None:
    op.drop_constraint("fk_orders_delivery_zone_id", "orders", type_="foreignkey")
    op.drop_column("orders", "google_place_id")
    op.drop_column("orders", "delivery_longitude")
    op.drop_column("orders", "delivery_latitude")
    op.drop_column("orders", "delivery_zone_id")
    op.drop_column("orders", "payment_status")
    op.drop_column("orders", "payment_method")
    op.drop_column("orders", "delivery_fee")
    op.drop_column("orders", "subtotal")
    op.drop_table("delivery_zones")
