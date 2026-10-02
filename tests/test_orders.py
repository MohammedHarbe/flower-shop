import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, Response
from pydantic import SecretStr, ValidationError
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.admin_auth import require_admin_key
from backend.models.delivery_zone import DeliveryZone
from backend.models.order import Order
from backend.models.product import Product
from backend.order_status import OrderStatus
from backend.payment_method import PaymentMethod
from backend.payment_status import PaymentStatus
from backend.routers.orders import (
    create_order,
    get_order,
    list_orders,
    update_order_payment_status,
    update_order_status,
)
from backend.routers.products import list_products
from backend.schemas.order import OrderCreate, OrderPaymentStatusUpdate, OrderStatusUpdate
from backend.schemas.product import ProductCreate, ProductUpdate
from backend.services.email_service import send_order_notification
from backend.settings import Settings
from backend.time_utils import CAIRO_TZ, cairo_today
from tests.db_support import isolated_database


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.engine = self.enterContext(isolated_database())
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
            "idempotency_key": str(uuid4()),
            "customer_name": "Customer",
            "customer_phone": "01012345678",
            "customer_email": "customer@example.com",
            "receiver_name": "Receiver",
            "receiver_phone": "01112345678",
            "governorate": governorate,
            "delivery_address": "1 Flower Street",
            "delivery_area": "Nasr City",
            "delivery_date": cairo_today() + timedelta(days=1),
            "delivery_slot": "morning",
            "items": items if items is not None else [{"product_id": 1, "quantity": 2}],
        }

    def test_cairo_and_giza_orders_save_prices_items_without_stock_mutation(self):
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
                self.assertEqual(response.customer_phone, "+201012345678")
                self.assertIsNone(response.notified_at)
                self.assertEqual(len(tasks.tasks), 1)
                self.assertIsInstance(tasks.tasks[0].args[0], dict)
                self.assertEqual(get_order(response.id, self.db).items[0].quantity, 2)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(self.db.query(Order).count(), 2)

    def test_validation_rejects_invalid_bodies(self):
        for changes in (
            {"governorate": "Alexandria"},
            {"items": []},
            {"items": [{"product_id": 1, "quantity": 0}]},
            {"items": [{"product_id": -1, "quantity": 1}]},
            {"items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}]},
            {"delivery_date": cairo_today() - timedelta(days=1)},
            {"idempotency_key": "not-a-uuid"},
            {"total_price": "0.01"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                OrderCreate.model_validate({**self.payload(), **changes})
        missing_key = self.payload()
        del missing_key["idempotency_key"]
        with self.assertRaises(ValidationError):
            OrderCreate.model_validate(missing_key)

    def test_invalid_product_keeps_order_and_stock_unchanged(self):
        for product_id, expected_status in ((999, 404), (3, 400)):
            with self.subTest(product_id=product_id):
                quantity = 1
                body = self.payload(
                    [{"product_id": 1, "quantity": 1}, {"product_id": product_id, "quantity": quantity}]
                )
                with self.assertRaises(HTTPException) as error:
                    create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
                self.assertEqual(error.exception.status_code, expected_status)
                self.assertEqual(self.db.query(Order).count(), 0)
                self.assertEqual(self.db.get(Product, 1).stock, 5)

        body = self.payload([{"product_id": 1, "quantity": 10}, {"product_id": 3, "quantity": 1}])
        with self.assertRaises(HTTPException) as error:
            create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        self.assertEqual(error.exception.status_code, 400)
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

    def test_vodafone_cash_and_cod_payment_fields_are_saved(self):
        zone = DeliveryZone(
            governorate="Cairo",
            name_en="Downtown",
            name_ar="وسط البلد",
            fee=Decimal("40.00"),
            active=True,
            sort_order=1,
        )
        self.db.add(zone)
        self.db.commit()

        created = create_order(
            OrderCreate.model_validate({
                **self.payload(items=[{"product_id": 1, "quantity": 1}]),
                "payment_method": "vodafone_cash",
                "delivery_zone_id": zone.id,
            }),
            BackgroundTasks(),
            self.db,
        )
        self.assertEqual(created.payment_method, PaymentMethod.vodafone_cash)
        self.assertEqual(created.payment_status, PaymentStatus.awaiting_payment)
        self.assertEqual(created.subtotal, Decimal("100.00"))
        self.assertEqual(created.delivery_fee, Decimal("40.00"))
        self.assertEqual(created.total_price, Decimal("140.00"))

        created_cod = create_order(
            OrderCreate.model_validate({
                **self.payload(items=[{"product_id": 2, "quantity": 1}]),
                "payment_method": "cash_on_delivery",
                "delivery_zone_id": zone.id,
            }),
            BackgroundTasks(),
            self.db,
        )
        self.assertEqual(created_cod.payment_method, PaymentMethod.cash_on_delivery)
        self.assertEqual(created_cod.payment_status, PaymentStatus.unpaid)

    def test_delivery_zone_fee_is_backend_authoritative_and_rejects_missing_or_inactive_zone(self):
        zone = DeliveryZone(
            governorate="Cairo",
            name_en="Downtown",
            name_ar="وسط البلد",
            fee=Decimal("50.00"),
            active=True,
            sort_order=1,
        )
        self.db.add(zone)
        self.db.commit()

        created = create_order(
            OrderCreate.model_validate({
                **self.payload(items=[{"product_id": 1, "quantity": 1}]),
                "payment_method": "vodafone_cash",
                "delivery_zone_id": zone.id,
            }),
            BackgroundTasks(),
            self.db,
        )

        self.assertEqual(created.subtotal, Decimal("100.00"))
        self.assertEqual(created.delivery_fee, Decimal("50.00"))
        self.assertEqual(created.total_price, Decimal("150.00"))

        with self.assertRaises(HTTPException) as error:
            create_order(
                OrderCreate.model_validate({
                    **self.payload(items=[{"product_id": 1, "quantity": 1}]),
                    "payment_method": "cash_on_delivery",
                    "delivery_zone_id": 999,
                }),
                BackgroundTasks(),
                self.db,
            )
        self.assertEqual(error.exception.status_code, 404)

        zone.active = False
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            create_order(
                OrderCreate.model_validate({
                    **self.payload(items=[{"product_id": 1, "quantity": 1}]),
                    "payment_method": "cash_on_delivery",
                    "delivery_zone_id": zone.id,
                }),
                BackgroundTasks(),
                self.db,
            )
        self.assertEqual(error.exception.status_code, 400)

    def test_admin_payment_status_updates_only_valid_transitions(self):
        zone = DeliveryZone(
            governorate="Cairo",
            name_en="Downtown",
            name_ar="وسط البلد",
            fee=Decimal("25.00"),
            active=True,
            sort_order=1,
        )
        self.db.add(zone)
        self.db.commit()

        created = create_order(
            OrderCreate.model_validate({
                **self.payload(items=[{"product_id": 1, "quantity": 1}]),
                "payment_method": "cash_on_delivery",
                "delivery_zone_id": zone.id,
            }),
            BackgroundTasks(),
            self.db,
        )
        updated = update_order_payment_status(
            created.id,
            OrderPaymentStatusUpdate(status="paid"),
            self.db,
        )
        self.assertEqual(updated.payment_status, PaymentStatus.paid)

        with self.assertRaises(HTTPException):
            update_order_payment_status(
                created.id,
                OrderPaymentStatusUpdate(status="unpaid"),
                self.db,
            )

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
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertIsNone(self.db.query(Order).first().notified_at)

    def test_create_order_does_not_touch_numeric_stock_even_if_db_listener_fires(self):
        updates = 0

        def fail_if_products_update(conn, cursor, statement, parameters, context, executemany):
            nonlocal updates
            if statement.startswith("UPDATE products"):
                updates += 1
                raise RuntimeError("product stock update should not run")

        event.listen(self.engine, "before_cursor_execute", fail_if_products_update)
        try:
            body = self.payload(
                [{"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1}]
            )
            created = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
            self.assertEqual(created.status, OrderStatus.pending)
            self.assertEqual(self.db.query(Order).count(), 1)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_if_products_update)

        self.assertEqual(updates, 0)
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
            "backend.services.email_service.SessionLocal", sessionmaker(bind=self.engine)
        ), patch("backend.services.email_service.smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value.send_message.return_value = {}
            send_order_notification(tasks.tasks[0].args[0])

        sent = smtp.return_value.__enter__.return_value.send_message
        message = sent.call_args.args[0]
        self.assertEqual(sent.call_args.kwargs["to_addrs"], ["one@example.com", "two@example.com"])
        self.assertEqual(message["To"], "one@example.com, two@example.com")
        self.db.expire_all()
        notified_at = self.db.query(Order).first().notified_at
        self.assertIsNotNone(notified_at)
        self.assertEqual(notified_at.tzinfo, CAIRO_TZ)
        body = message.get_content()
        for expected in (
            "New ToneFlowers Order",
            "Customer",
            "Receiver",
            "Cairo",
            "Nasr City",
            "1 Flower Street",
            "Roses",
            "10:00 AM - 2:00 PM",
            "Payment method: cash_on_delivery",
            "Payment status: unpaid",
            "Subtotal: 200.00",
            "Delivery fee: 0.00",
            "Total: 200.00",
            "100.00",
            "200.00",
        ):
            self.assertIn(expected, body)

    def test_admin_order_list_filters_and_newest_first(self):
        first = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        second = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        update_order_status(second.id, OrderStatusUpdate(status="confirmed"), self.db)

        self.assertEqual([item.id for item in list_orders(db=self.db)], [second.id, first.id])
        self.assertEqual(
            [item.id for item in list_orders(status=OrderStatus.pending, db=self.db)],
            [first.id],
        )
        self.assertEqual(
            [item.id for item in list_orders(delivery_date=cairo_today() + timedelta(days=1), db=self.db)],
            [second.id, first.id],
        )

    def test_refused_recipient_leaves_notification_pending(self):
        tasks = BackgroundTasks()
        created = create_order(OrderCreate.model_validate(self.payload()), tasks, self.db)
        settings = Settings(
            _env_file=None,
            smtp_username="sender@example.com",
            smtp_password=SecretStr("app-password"),
            shop_notification_emails="one@example.com,two@example.com",
        )
        with patch("backend.services.email_service.Settings", return_value=settings), patch(
            "backend.services.email_service.SessionLocal"
        ) as sessions, patch("backend.services.email_service.smtplib.SMTP") as smtp, self.assertLogs(
            "backend.services.email_service", level="ERROR"
        ):
            smtp.return_value.__enter__.return_value.send_message.return_value = {
                "two@example.com": (550, b"refused")
            }
            send_order_notification(tasks.tasks[0].args[0])
            sessions.assert_not_called()
        self.db.expire_all()
        self.assertIsNone(self.db.get(Order, created.id).notified_at)

    def test_email_accepted_but_marker_update_fails_without_undoing_order(self):
        tasks = BackgroundTasks()
        created = create_order(OrderCreate.model_validate(self.payload()), tasks, self.db)
        settings = Settings(
            _env_file=None,
            smtp_username="sender@example.com",
            smtp_password=SecretStr("app-password"),
            shop_notification_emails="one@example.com,two@example.com",
        )
        with patch("backend.services.email_service.Settings", return_value=settings), patch(
            "backend.services.email_service.SessionLocal", side_effect=OSError("database unavailable")
        ), patch("backend.services.email_service.smtplib.SMTP") as smtp, self.assertLogs(
            "backend.services.email_service", level="ERROR"
        ) as logs:
            smtp.return_value.__enter__.return_value.send_message.return_value = {}
            send_order_notification(tasks.tasks[0].args[0])
        self.assertIn("notified_at could not be recorded", "\n".join(logs.output))
        self.db.expire_all()
        self.assertIsNone(self.db.get(Order, created.id).notified_at)
        self.assertEqual(self.db.get(Product, 1).stock, 5)

    def test_idempotency_reuses_order_and_does_not_reduce_stock_twice(self):
        body = self.payload()
        first_tasks = BackgroundTasks()
        first = create_order(OrderCreate.model_validate(body), first_tasks, self.db)
        replay_tasks = BackgroundTasks()
        http_response = Response(status_code=201)
        replay = create_order(OrderCreate.model_validate(body), replay_tasks, self.db, http_response)

        self.assertEqual(replay.id, first.id)
        self.assertEqual(http_response.status_code, 200)
        self.assertEqual(self.db.query(Order).count(), 1)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(len(first_tasks.tasks), 1)
        self.assertEqual(len(replay_tasks.tasks), 0)

    def test_idempotency_rejects_changed_order_payload(self):
        body = self.payload()
        created = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        for changes in (
            {"items": [{"product_id": 1, "quantity": 1}]},
            {"delivery_address": "2 Different Street"},
            {"customer_email": "other@example.com"},
        ):
            with self.subTest(changes=changes):
                tasks = BackgroundTasks()
                with self.assertRaises(HTTPException) as error:
                    create_order(OrderCreate.model_validate({**body, **changes}), tasks, self.db)
                self.assertEqual(error.exception.status_code, 409)
                self.assertEqual(len(tasks.tasks), 0)
        self.assertEqual(self.db.query(Order).count(), 1)
        self.assertEqual(self.db.get(Order, created.id).delivery_address, body["delivery_address"])
        self.assertEqual(self.db.get(Product, 1).stock, 5)

    def test_idempotency_accepts_same_items_in_another_order(self):
        body = self.payload([{"product_id": 2, "quantity": 1}, {"product_id": 1, "quantity": 2}])
        created = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        replay = create_order(
            OrderCreate.model_validate({**body, "items": list(reversed(body["items"]))}),
            BackgroundTasks(), self.db,
        )
        self.assertEqual(replay.id, created.id)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(self.db.get(Product, 2).stock, 3)

    def test_different_idempotency_keys_create_two_orders(self):
        first = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        second = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(self.db.query(Order).count(), 2)
        self.assertEqual(self.db.get(Product, 1).stock, 5)

    def test_unique_index_enforces_idempotency_key(self):
        created = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        indexes = inspect(self.engine).get_indexes("orders")
        self.assertTrue(any(index["name"] == "ix_orders_idempotency_key" and index["unique"] for index in indexes))
        duplicate = Order(
            idempotency_key=str(created.idempotency_key),
            customer_name="Second",
            customer_phone="+201012345678",
            receiver_name="Receiver",
            receiver_phone="+201112345678",
            delivery_address="Another street",
            delivery_area="Giza",
            delivery_date=cairo_today() + timedelta(days=1),
            delivery_slot="morning",
            total_price=Decimal("1.00"),
            status=OrderStatus.pending,
        )
        self.db.add(duplicate)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()
        self.assertEqual(self.db.query(Order).count(), 1)

    def test_unique_key_race_returns_existing_order(self):
        body = self.payload()
        first = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        real_query = self.db.query
        checks = 0

        class MissedConcurrentOrder:
            def filter(self, *args):
                return self

            def one_or_none(self):
                return None

        def query_with_initial_miss(*entities):
            nonlocal checks
            if entities == (Order,) and checks == 0:
                checks += 1
                return MissedConcurrentOrder()
            return real_query(*entities)

        replay_tasks = BackgroundTasks()
        with patch.object(self.db, "query", side_effect=query_with_initial_miss):
            replay = create_order(OrderCreate.model_validate(body), replay_tasks, self.db)
        self.assertEqual(replay.id, first.id)
        self.assertEqual(self.db.query(Order).count(), 1)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(len(replay_tasks.tasks), 0)

    def test_unique_key_race_rejects_changed_payload(self):
        body = self.payload()
        create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        real_query = self.db.query
        checks = 0

        class MissedConcurrentOrder:
            def filter(self, *args):
                return self

            def one_or_none(self):
                return None

        def query_with_initial_miss(*entities):
            nonlocal checks
            if entities == (Order,) and checks == 0:
                checks += 1
                return MissedConcurrentOrder()
            return real_query(*entities)

        tasks = BackgroundTasks()
        changed = {**body, "delivery_address": "2 Different Street"}
        with patch.object(self.db, "query", side_effect=query_with_initial_miss):
            with self.assertRaises(HTTPException) as error:
                create_order(OrderCreate.model_validate(changed), tasks, self.db)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.db.query(Order).count(), 1)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(len(tasks.tasks), 0)

    def test_cancellation_restores_stock_exactly_once(self):
        created = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        cancelled = update_order_status(created.id, OrderStatusUpdate(status="cancelled"), self.db)
        self.assertEqual(cancelled.status, OrderStatus.cancelled)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        for next_status in ("cancelled", "confirmed"):
            with self.subTest(next_status=next_status), self.assertRaises(HTTPException) as error:
                update_order_status(created.id, OrderStatusUpdate(status=next_status), self.db)
            self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.db.get(Product, 1).stock, 5)

    def test_simultaneous_cancellations_restore_stock_once(self):
        with isolated_database(file_backed=True) as engine:
            try:
                with Session(engine) as db:
                    db.add(Product(name="Roses", price=Decimal("100.00"), stock=10, active=True))
                    db.commit()
                    created = create_order(
                        OrderCreate.model_validate(self.payload()), BackgroundTasks(), db,
                    )
                    order_id = created.id
                    self.assertEqual(db.get(Product, 1).stock, 10)
                    confirmed = update_order_status(order_id, OrderStatusUpdate(status="confirmed"), db)
                    self.assertEqual(confirmed.status, OrderStatus.confirmed)

                first_updated = Event()
                second_update_started = Event()
                release_first = Event()

                def before_update(conn, cursor, statement, parameters, context, executemany):
                    if statement.startswith("UPDATE orders") and first_updated.is_set():
                        second_update_started.set()

                def hold_first_update(conn, cursor, statement, parameters, context, executemany):
                    if statement.startswith("UPDATE orders") and not first_updated.is_set():
                        first_updated.set()
                        if not release_first.wait(5):
                            raise AssertionError("Second cancellation did not start")

                event.listen(engine, "before_cursor_execute", before_update)
                event.listen(engine, "after_cursor_execute", hold_first_update)
                try:
                    def cancel():
                        with Session(engine) as db:
                            try:
                                update_order_status(order_id, OrderStatusUpdate(status="cancelled"), db)
                                return 200
                            except HTTPException as error:
                                return error.status_code

                    with ThreadPoolExecutor(max_workers=2) as pool:
                        first = pool.submit(cancel)
                        self.assertTrue(first_updated.wait(5), "First cancellation did not update the order")
                        second = pool.submit(cancel)
                        self.assertTrue(second_update_started.wait(5), "Second cancellation did not reach the update")
                        release_first.set()
                        self.assertEqual(sorted((first.result(timeout=10), second.result(timeout=10))), [200, 409])
                finally:
                    release_first.set()
                    event.remove(engine, "before_cursor_execute", before_update)
                    event.remove(engine, "after_cursor_execute", hold_first_update)

                with Session(engine) as db:
                    self.assertEqual(db.get(Order, order_id).status, OrderStatus.cancelled)
                    self.assertEqual(db.get(Product, 1).stock, 10)
            finally:
                engine.dispose()

    def test_cancellation_does_not_touch_stock_even_if_inventory_updates_fire(self):
        body = self.payload([
            {"product_id": 2, "quantity": 1},
            {"product_id": 1, "quantity": 1},
        ])
        created = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        updates = 0

        def fail_if_products_update(conn, cursor, statement, parameters, context, executemany):
            nonlocal updates
            if statement.startswith("UPDATE products"):
                updates += 1
                raise RuntimeError("product stock updates should not run during cancellation")

        event.listen(self.engine, "before_cursor_execute", fail_if_products_update)
        try:
            cancelled = update_order_status(created.id, OrderStatusUpdate(status="cancelled"), self.db)
            self.assertEqual(cancelled.status, OrderStatus.cancelled)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail_if_products_update)
        self.db.expire_all()
        self.assertEqual(self.db.get(Order, created.id).status, OrderStatus.cancelled)
        self.assertEqual(updates, 0)
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(self.db.get(Product, 2).stock, 3)

    def test_allowed_status_chain_and_invalid_transitions(self):
        created = create_order(OrderCreate.model_validate(self.payload()), BackgroundTasks(), self.db)
        for status in ("confirmed", "preparing", "out_for_delivery", "delivered"):
            result = update_order_status(created.id, OrderStatusUpdate(status=status), self.db)
            self.assertEqual(result.status.value, status)
        with self.assertRaises(HTTPException) as error:
            update_order_status(created.id, OrderStatusUpdate(status="pending"), self.db)
        self.assertEqual(error.exception.status_code, 409)
        with self.assertRaises(ValidationError):
            OrderStatusUpdate(status="made_up")

    def test_phone_normalization_and_rejection(self):
        variants = ("01012345678", "+201012345678", "00201012345678", "٠١٠١٢٣٤٥٦٧٨")
        for phone in variants:
            with self.subTest(phone=phone):
                parsed = OrderCreate.model_validate({**self.payload(), "customer_phone": phone})
                self.assertEqual(parsed.customer_phone, "+201012345678")
                self.assertEqual(parsed.receiver_phone, "+201112345678")
        for phone in ("123", "abc", "", "01312345678", "0101234567", "010123456789"):
            with self.subTest(phone=phone), self.assertRaises(ValidationError):
                OrderCreate.model_validate({**self.payload(), "customer_phone": phone})

    def test_email_and_delivery_slot_validation(self):
        for slot in ("morning", "afternoon", "evening"):
            parsed = OrderCreate.model_validate({**self.payload(), "delivery_slot": slot})
            self.assertEqual(parsed.delivery_slot.value, slot)
        with self.assertRaises(ValidationError):
            OrderCreate.model_validate({**self.payload(), "delivery_slot": "3 مساء"})
        self.assertIsNone(OrderCreate.model_validate({**self.payload(), "customer_email": None}).customer_email)
        self.assertEqual(
            OrderCreate.model_validate({**self.payload(), "customer_email": "customer@example.com"}).customer_email,
            "customer@example.com",
        )
        with self.assertRaises(ValidationError):
            OrderCreate.model_validate({**self.payload(), "customer_email": "not-an-email"})

    def test_cairo_date_rule_and_aware_utc_storage(self):
        cairo_midnight = datetime(2026, 4, 1, 0, 30, tzinfo=CAIRO_TZ)
        with patch("backend.time_utils.cairo_now", return_value=cairo_midnight):
            self.assertEqual(cairo_today(), date(2026, 4, 1))
            with self.assertRaises(ValidationError):
                OrderCreate.model_validate({**self.payload(), "delivery_date": date(2026, 3, 31)})
            valid = OrderCreate.model_validate({**self.payload(), "delivery_date": date(2026, 4, 1)})
        created = create_order(valid, BackgroundTasks(), self.db)
        self.assertIsNotNone(created.created_at.tzinfo)
        self.assertEqual(created.created_at.tzinfo, CAIRO_TZ)
        stored = self.db.execute(text("SELECT created_at FROM orders WHERE id = :id"), {"id": created.id}).scalar_one()
        if self.engine.dialect.name == "postgresql":
            self.assertIsInstance(stored, datetime)
            self.assertIsNotNone(stored.tzinfo)
            utc_stored = stored.astimezone(timezone.utc)
        else:
            utc_stored = datetime.fromisoformat(stored)
            self.assertIsNone(utc_stored.tzinfo)
            utc_stored = utc_stored.replace(tzinfo=timezone.utc)
        self.assertAlmostEqual(
            (created.created_at.astimezone(timezone.utc) - utc_stored).total_seconds(),
            0,
            places=3,
        )

    def test_stock_updates_follow_product_id_order(self):
        body = self.payload([
            {"product_id": 2, "quantity": 1},
            {"product_id": 1, "quantity": 1},
        ])
        updated_ids = []

        def record_update(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("UPDATE products"):
                updated_ids.append(context.compiled_parameters[0]["id_1"])

        event.listen(self.engine, "before_cursor_execute", record_update)
        try:
            created = create_order(OrderCreate.model_validate(body), BackgroundTasks(), self.db)
        finally:
            event.remove(self.engine, "before_cursor_execute", record_update)
        self.assertEqual(updated_ids, [])
        self.assertEqual([item.product_id for item in created.items], [1, 2])
        self.assertEqual(self.db.get(Product, 1).stock, 5)
        self.assertEqual(self.db.get(Product, 2).stock, 3)


if __name__ == "__main__":
    unittest.main()
