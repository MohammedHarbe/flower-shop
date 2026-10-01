import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.order_status import OrderStatus
from backend.time_utils import cairo_today
from tests.db_support import isolated_database


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = self.enterContext(isolated_database(file_backed=True, create_tables=False))
        root = Path(__file__).resolve().parents[1]
        self.config = Config(str(root / "alembic.ini"))
        self.config.set_main_option("script_location", str(root / "migrations"))

    def upgrade(self, revision):
        with self.engine.begin() as connection:
            self.config.attributes["connection"] = connection
            command.upgrade(self.config, revision)

    def test_empty_database_migrations_match_models(self):
        self.assertEqual(inspect(self.engine).get_table_names(), [])
        self.upgrade("head")
        with self.engine.connect() as connection:
            drift = compare_metadata(MigrationContext.configure(connection, opts={
                "compare_type": True, "compare_server_default": True,
            }), Base.metadata)
            self.assertEqual(drift, [])
            inspector = inspect(connection)
            self.assertEqual(set(inspector.get_table_names()), {
                "alembic_version",
                "products",
                "orders",
                "order_items",
                "delivery_zones",
            })
            self.assertEqual(len(inspector.get_foreign_keys("order_items")), 2)
            self.assertTrue(any(
                item["unique"] and item["column_names"] == ["idempotency_key"]
                for item in inspector.get_indexes("orders")
            ))
            if connection.dialect.name == "postgresql":
                columns = {item["name"]: item for item in inspector.get_columns("orders")}
                self.assertTrue(columns["created_at"]["type"].timezone)
                self.assertTrue(columns["notified_at"]["type"].timezone)

    def test_catalog_default_migration_preserves_existing_orders_and_products(self):
        self.upgrade("20261001_03")
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO products (name, description, price, stock, active, image_url, featured, best_seller, category, occasion, name_ar, description_ar) "
                    "VALUES (:name, :description, :price, :stock, :active, :image_url, :featured, :best_seller, :category, :occasion, :name_ar, :description_ar)"
                ),
                {
                    "name": "Existing product",
                    "description": "Historical product",
                    "price": float(Decimal("75.50")),
                    "stock": 7,
                    "active": True,
                    "image_url": None,
                    "featured": True,
                    "best_seller": False,
                    "category": None,
                    "occasion": None,
                    "name_ar": None,
                    "description_ar": None,
                },
            )
            product_id = connection.execute(
                text("SELECT id FROM products WHERE name = :name"),
                {"name": "Existing product"},
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO orders (customer_name, customer_phone, receiver_name, receiver_phone, delivery_address, delivery_area, delivery_date, delivery_slot, total_price, status, created_at, governorate, idempotency_key, notified_at) "
                    "VALUES (:customer_name, :customer_phone, :receiver_name, :receiver_phone, :delivery_address, :delivery_area, :delivery_date, :delivery_slot, :total_price, :status, :created_at, :governorate, :idempotency_key, :notified_at)"
                ),
                {
                    "customer_name": "Customer",
                    "customer_phone": "+201012345678",
                    "receiver_name": "Receiver",
                    "receiver_phone": "+201112345678",
                    "delivery_address": "Nasr City",
                    "delivery_area": "Nasr City",
                    "delivery_date": (cairo_today() + timedelta(days=1)).isoformat(),
                    "delivery_slot": "morning",
                    "total_price": float(Decimal("151.00")),
                    "status": "confirmed",
                    "created_at": (cairo_today() + timedelta(days=1)).isoformat(),
                    "governorate": None,
                    "idempotency_key": str(uuid4()),
                    "notified_at": None,
                },
            )
            order_id = connection.execute(
                text("SELECT id FROM orders WHERE customer_phone = :customer_phone ORDER BY id DESC LIMIT 1"),
                {"customer_phone": "+201012345678"},
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) "
                    "VALUES (:order_id, :product_id, :quantity, :unit_price, :subtotal)"
                ),
                {
                    "order_id": order_id,
                    "product_id": product_id,
                    "quantity": 2,
                    "unit_price": float(Decimal("75.50")),
                    "subtotal": float(Decimal("151.00")),
                },
            )
        self.upgrade("head")
        with Session(self.engine) as db:
            product, order = db.get(Product, product_id), db.get(Order, order_id)
            self.assertEqual(product.stock, 7)
            self.assertTrue(product.featured)
            self.assertFalse(product.best_seller)
            self.assertEqual(product.price, Decimal("75.50"))
            self.assertEqual(order.subtotal, Decimal("151.00"))
            self.assertEqual(order.delivery_fee, Decimal("0.00"))
            self.assertEqual(order.total_price, Decimal("151.00"))
            self.assertEqual(order.items[0].product_id, product_id)
            self.assertEqual(order.items[0].quantity, 2)
            self.assertEqual(db.query(OrderItem).count(), 1)


if __name__ == "__main__":
    unittest.main()
