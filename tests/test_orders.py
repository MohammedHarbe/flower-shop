import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.admin_auth import require_admin_key
from backend.database import Base
from backend.models.order import Order
from backend.models.product import Product
from backend.routers.orders import create_order, get_order, update_order_status
from backend.routers.products import list_products
from backend.schemas.order import OrderCreate, OrderStatusUpdate
from backend.schemas.product import ProductCreate, ProductUpdate
from backend.services.email_service import send_order_notification
from backend.settings import Settings


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all(
            [
                Product(name="Roses", price=Decimal("100.00"), stock=5, active=True),
                Product(name="Lilies", price=Decimal("75.50"), stock=3, active=True),
                Product(name="Inactive", price=Decimal("20.00"), stock=2, active=False),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def payload(self, items=None, governorate="Cairo"):
        return {
            "customer_name": "Customer",
            "customer_phone": "123",
            "customer_email": "customer@example.com",
            "receiver_name": "Receiver",
            "receiver_phone": "456",
            "governorate": governorate,
            "delivery_address": "1 Flower Street",
            "delivery_area": "Nasr City",
            "delivery_date": date.today() + timedelta(days=1),
            "delivery_slot": "Morning",
            "items": items if items is not None else [{"product_id": 1, "quantity": 2}],
        }

    def test_cairo_and_giza_orders_save_prices_items_and_stock(self):
        for governorate in ("Cairo", "Giza"):
            with self.subTest(governorate=governorate):
                tasks = BackgroundTasks()
                response = create_order(
                    OrderCreate.model_validate(self.payload(governorate=governorate)),
                    tasks,
                    self.db,
                )
                self.assertEqual(response.governorate.value, governorate)
                self.assertEqual(response.status.value, "pending")
                self.assertEqual(response.total_price, Decimal("200.00"))
                self.assertEqual(response.items[0].unit_price, Decimal("100.00"))
                self.assertEqual(len(tasks.tasks), 1)
                self.assertIsInstance(tasks.tasks[0].args[0], dict)
                self.assertEqual(get_order(response.id, self.db).items[0].quantity, 2)
        self.assertEqual(self.db.get(Product, 1).stock, 1)
        self.assertEqual(self.db.query(Order).count(), 2)

    def test_validation_rejects_invalid_bodies(self):
        for changes in (
            {"governorate": "Alexandria"},
            {"items": []},
            {"items": [{"product_id": 1, "quantity": 0}]},
            {"items": [{"product_id": -1, "quantity": 1}]},
            {"items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}]},
            {"delivery_date": date.today() - timedelta(days=1)},
            {"total_price": "0.01"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                OrderCreate.model_validate({**self.payload(), **changes})

    def test_invalid_product_keeps_order_and_stock_unchanged(self):
        for product_id, expected_status in ((999, 404), (3, 400), (2, 409)):
            with self.subTest(product_id=product_id):
                quantity = 4 if product_id == 2 else 1
                body = self.payload(
                    [{"product_id": 1, "quantity": 1}, {"product_id": product_id, "quantity": quantity}]
                )
                with self.assertRaises(HTTPException) as error:
                    create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
                self.assertEqual(error.exception.status_code, expected_status)
                self.assertEqual(self.db.query(Order).count(), 0)
                self.assertEqual(self.db.get(Product, 1).stock, 5)

    def test_status_update_uses_enum_and_returns_order(self):
        created = create_order(
            OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db
        )
        updated = update_order_status(
            created.id, OrderStatusUpdate(status="confirmed"), self.db
        )
        self.assertEqual(updated.status.value, "confirmed")
        self.assertEqual(updated.items[0].quantity, 2)
        with self.assertRaises(ValidationError):
            OrderStatusUpdate(status="made_up")

    def test_product_list_only_returns_active_products(self):
        self.assertEqual([product.name for product in list_products(self.db)], ["Roses", "Lilies"])

    def test_product_input_validation_and_catalog_fields(self):
        for values in (
            {"name": "  ", "price": "20.00", "stock": 1},
            {"name": "Rose", "price": "0", "stock": 1},
            {"name": "Rose", "price": "1.001", "stock": 1},
            {"name": "Rose", "price": "20", "stock": -1},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ProductCreate.model_validate(values)
        with self.assertRaises(ValidationError):
            ProductUpdate.model_validate({"price": None})
        item = ProductCreate.model_validate({
            "name": "  Rose  ",
            "name_ar": "ورد",
            "price": "125.50",
            "stock": 2,
            "category": "Flowers",
            "occasion": "Birthday",
            "featured": True,
        })
        self.assertEqual(item.name, "Rose")
        self.assertEqual(item.price, Decimal("125.50"))
        self.assertEqual(item.name_ar, "ورد")

    def test_product_image_url_requires_http_and_can_be_cleared(self):
        data = {"name": "Rose", "price": "20.00", "stock": 1}
        valid = "https://example.com/rose.jpg"
        self.assertEqual(ProductCreate.model_validate({**data, "image_url": valid}).image_url, valid)
        self.assertEqual(ProductUpdate.model_validate({"image_url": valid}).image_url, valid)
        self.assertEqual(
            ProductUpdate.model_validate({"image_url": None}).model_dump(exclude_unset=True),
            {"image_url": None},
        )
        for invalid in ("string", "/images/rose.jpg", "ftp://example.com/rose.jpg", "javascript:alert(1)", "http://"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    ProductCreate.model_validate({**data, "image_url": invalid})
                with self.assertRaises(ValidationError):
                    ProductUpdate.model_validate({"image_url": invalid})
    def test_admin_key_denies_unset_missing_and_wrong_key(self):
        unset = Settings(_env_file=None, admin_api_key=SecretStr(""))
        with patch("backend.admin_auth.Settings", return_value=unset):
            with self.assertRaises(HTTPException) as error:
                require_admin_key(None)
            self.assertEqual(error.exception.status_code, 503)
        configured = Settings(_env_file=None, admin_api_key=SecretStr("long-test-secret"))
        with patch("backend.admin_auth.Settings", return_value=configured):
            for key in (None, "wrong"):
                with self.assertRaises(HTTPException) as error:
                    require_admin_key(key)
                self.assertEqual(error.exception.status_code, 403)
            self.assertIsNone(require_admin_key("long-test-secret"))

    def test_email_failure_does_not_undo_committed_order(self):
        tasks = BackgroundTasks()
        create_order(OrderCreate.model_validate(self.payload()), tasks, self.db)
        settings = Settings(
            _env_file=None,
            smtp_username="sender@example.com",
            smtp_password=SecretStr("app-password"),
            shop_notification_emails="one@example.com,two@example.com",
        )
        with patch("backend.services.email_service.Settings", return_value=settings), patch(
            "backend.services.email_service.smtplib.SMTP", side_effect=OSError("offline")
        ), self.assertLogs("backend.services.email_service", level="ERROR"):
            send_order_notification(tasks.tasks[0].args[0])

        self.assertEqual(self.db.query(Order).count(), 1)
        self.assertEqual(self.db.get(Product, 1).stock, 3)

    def test_mid_transaction_failure_rolls_back_stock_and_order(self):
        updates = 0

        def fail_second_stock_update(conn, cursor, statement, parameters, context, executemany):
            nonlocal updates
            if statement.startswith("UPDATE products"):
                updates += 1
                if updates == 2:
                    raise RuntimeError("simulated database failure")

        event.listen(self.engine, "before_cursor_execute", fail_second_stock_update)
        try:
            body = self.payload(
                [{"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1}]
            )
            with self.assertRaises(RuntimeError):
                create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_second_stock_update)

        self.assertEqual(self.db.query(Order).count(), 0)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(self.db.get(Product, 2).stock, 3)

    def test_notification_contains_saved_details_and_two_recipients(self):
        tasks = BackgroundTasks()
        create_order(OrderCreate.model_validate(self.payload()), tasks, self.db)
        settings = Settings(
            _env_file=None,
            smtp_username="sender@example.com",
            smtp_password=SecretStr("app-password"),
            shop_notification_emails="one@example.com, two@example.com",
        )
        with patch("backend.services.email_service.Settings", return_value=settings), patch(
            "backend.services.email_service.smtplib.SMTP"
        ) as smtp:
            send_order_notification(tasks.tasks[0].args[0])

        sent = smtp.return_value.__enter__.return_value.send_message
        message = sent.call_args.args[0]
        self.assertEqual(sent.call_args.kwargs["to_addrs"], ["one@example.com", "two@example.com"])
        self.assertEqual(message["To"], "one@example.com, two@example.com")
        body = message.get_content()
        for expected in (
            "New ToneFlowers Order",
            "Customer",
            "Receiver",
            "Cairo",
            "Nasr City",
            "1 Flower Street",
            "Roses",
            "100.00",
            "200.00",
        ):
            self.assertIn(expected, body)


if __name__ == "__main__":
    unittest.main()
