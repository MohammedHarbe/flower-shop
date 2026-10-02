import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier, Event
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.order_status import OrderStatus
from backend.time_utils import CAIRO_TZ, cairo_now, cairo_today
from tests.db_support import isolated_database, postgres_requested
from tests.http_support import order_api, request_json


@unittest.skipUnless(postgres_requested(), "Set TEST_DATABASE_URL for real PostgreSQL concurrency tests")
class PostgresConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.engine = self.enterContext(isolated_database())
        self.assertEqual(self.engine.dialect.name, "postgresql")
        with self.engine.connect() as connection:
            self.assertEqual(connection.get_isolation_level(), "READ COMMITTED")
        self.base, self.notification = self.enterContext(order_api(self.engine))

    def seed(self, stock, count=1):
        with Session(self.engine) as db:
            db.add_all([
                Product(name=f"Product {index + 1}", price=Decimal("75.50"), stock=stock, active=True)
                for index in range(count)
            ])
            db.commit()

    def payload(self, *, quantity=1, items=None):
        return {
            "idempotency_key": str(uuid4()),
            "customer_name": "PostgreSQL Test",
            "customer_phone": "01012345678",
            "customer_email": "customer@example.com",
            "receiver_name": "Receiver",
            "receiver_phone": "01112345678",
            "governorate": "Cairo",
            "delivery_area": "Nasr City",
            "delivery_address": "1 Flower Street",
            "delivery_date": (cairo_today() + timedelta(days=1)).isoformat(),
            "delivery_slot": "morning",
            "items": items or [{"product_id": 1, "quantity": quantity}],
        }

    def post(self, body):
        return request_json(self.base, "/orders", body)

    def listen(self, name, callback):
        event.listen(self.engine, name, callback)
        self.addCleanup(event.remove, self.engine, name, callback)

    def test_simultaneous_orders_ignore_legacy_stock_values(self):
        self.seed(0)
        barrier = Barrier(6)

        def submit(_):
            barrier.wait(timeout=10)
            return self.post(self.payload())

        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(submit, range(6)))
        self.assertEqual([code for code, _ in results], [201] * 6)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Product, 1).stock, 0)
            self.assertEqual(db.query(Order).count(), 6)
            self.assertEqual(db.query(OrderItem).count(), 6)

    def test_opposite_product_order_twelve_overlapping_pairs(self):
        rounds = 12
        self.seed(rounds * 2, count=2)
        for iteration in range(rounds):
            with self.subTest(iteration=iteration):
                barrier = Barrier(2)
                items = [{"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1}]

                def submit(body):
                    barrier.wait(timeout=10)
                    return self.post(body)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(submit, [
                        self.payload(items=items), self.payload(items=list(reversed(items))),
                    ]))
                self.assertEqual([code for code, _ in results], [201, 201])
        with Session(self.engine) as db:
            self.assertEqual([db.get(Product, item).stock for item in (1, 2)], [rounds * 2] * 2)
            self.assertEqual(db.query(Order).count(), rounds * 2)

    def test_confirmed_order_two_overlapping_cancellations(self):
        self.seed(10)
        code, order = self.post(self.payload(quantity=2))
        self.assertEqual(code, 201)
        path = f"/orders/{order['id']}/status"
        self.assertEqual(request_json(self.base, path, {"status": "confirmed"}, "PATCH")[0], 200)
        with Session(self.engine) as db:
            self.assertEqual(db.get(Product, 1).stock, 10)
        barrier = Barrier(2)

        def overlap(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("UPDATE orders"):
                barrier.wait(timeout=10)

        self.listen("before_cursor_execute", overlap)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda _: request_json(self.base, path, {"status": "cancelled"}, "PATCH"), range(2),
            ))
        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        with Session(self.engine) as db:
            self.assertEqual(db.get(Product, 1).stock, 10)
            self.assertEqual(db.get(Order, order["id"]).status, OrderStatus.cancelled)

    def test_simultaneous_same_key_replays_and_changed_payload_conflicts(self):
        self.seed(2)
        body = self.payload(quantity=2)
        barrier = Barrier(2)

        def overlap(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO orders"):
                barrier.wait(timeout=10)

        self.listen("before_cursor_execute", overlap)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.post, [body, body]))
        self.assertEqual(sorted(code for code, _ in results), [200, 201])
        self.assertEqual(results[0][1]["id"], results[1][1]["id"])
        self.assertEqual(self.post({**body, "delivery_address": "Maadi"})[0], 409)
        self.assertEqual(self.post({**body, "items": [{"product_id": 1, "quantity": 1}]})[0], 409)
        with Session(self.engine) as db:
            self.assertEqual(db.query(Order).count(), 1)
            self.assertEqual(db.get(Product, 1).stock, 2)
        self.assertEqual(self.notification.call_count, 1)

    def test_replay_when_winner_exhausts_stock_after_initial_key_lookup(self):
        self.seed(1)
        body = self.payload()
        lookup_done = Event()
        release_lookup = Event()

        def hold_first_lookup(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith("SELECT orders.") and "WHERE orders.idempotency_key" in statement:
                if not lookup_done.is_set():
                    lookup_done.set()
                    if not release_lookup.wait(10):
                        raise RuntimeError("Competing order did not commit")

        self.listen("after_cursor_execute", hold_first_lookup)
        with ThreadPoolExecutor(max_workers=2) as pool:
            delayed = pool.submit(self.post, body)
            try:
                self.assertTrue(lookup_done.wait(10))
                winner_code, winner = self.post(body)
                self.assertEqual(winner_code, 201)
            finally:
                release_lookup.set()
            replay_code, replay = delayed.result(timeout=30)
        self.assertEqual(replay_code, 200)
        self.assertEqual(replay["id"], winner["id"])
        with Session(self.engine) as db:
            self.assertEqual(db.query(Order).count(), 1)
            self.assertEqual(db.get(Product, 1).stock, 1)

    def test_inactive_product_is_rejected_without_stock_mutation(self):
        self.seed(5, count=2)
        with Session(self.engine) as db:
            db.get(Product, 2).active = False
            db.commit()
        code, _ = self.post(self.payload(items=[
            {"product_id": 1, "quantity": 1}, {"product_id": 2, "quantity": 1},
        ]))
        self.assertEqual(code, 400)
        with Session(self.engine) as db:
            self.assertEqual(db.query(Order).count(), 0)
            self.assertEqual(db.query(OrderItem).count(), 0)
            self.assertEqual(db.get(Product, 1).stock, 5)
            self.assertEqual(db.get(Product, 2).stock, 5)

    def test_postgres_numeric_and_cairo_timestamps_serialize_through_api(self):
        self.seed(10)
        code, order = self.post(self.payload(quantity=3))
        self.assertEqual(code, 201)
        self.assertEqual(order["total_price"], "226.50")
        with Session(self.engine) as db:
            saved = db.get(Order, order["id"])
            self.assertEqual(saved.total_price, Decimal("226.50"))
            self.assertEqual(saved.items[0].unit_price, Decimal("75.50"))
            saved.notified_at = cairo_now()
            db.commit()
            stored = db.execute(text("SELECT created_at, notified_at FROM orders WHERE id = :id"), {"id": saved.id}).one()
            self.assertTrue(all(value.tzinfo is not None for value in stored))
        code, fetched = request_json(self.base, f"/orders/{order['id']}")
        self.assertEqual(code, 200)
        for field in ("created_at", "notified_at"):
            parsed = datetime.fromisoformat(fetched[field])
            self.assertEqual(parsed.utcoffset(), parsed.astimezone(CAIRO_TZ).utcoffset())
            self.assertLess(abs((parsed.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds()), 30)


if __name__ == "__main__":
    unittest.main()
