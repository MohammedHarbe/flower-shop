import asyncio
import json
import logging
import os
import smtplib
import unittest
from decimal import Decimal
from http.cookies import SimpleCookie
from uuid import uuid4
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import HTTPException, Response
from pydantic import SecretStr, ValidationError
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from starlette.requests import Request as StarletteRequest

from backend.admin_auth import hash_password, require_admin_key, require_admin_session, verify_password
from backend.logging_utils import log_failure
from backend.main import app, lifespan
from backend.models.delivery_zone import DeliveryZone
from backend.models.product import Product
from backend.seed_catalog import seed_catalog
from backend.routers.admin import AdminLoginRequest, admin_login
from backend.services.email_service import send_order_notification
from backend.settings import Settings
from backend.time_utils import cairo_today
from tests.db_support import isolated_database
from tests.http_support import order_api, request_json


class DeploymentSettingsTests(unittest.TestCase):
    def settings(self, **overrides):
        values = dict(
            app_env="production",
            database_url="postgresql+psycopg://toneflowers_app:example%40pass@db.example.com:5432/toneflowers",
            cors_origins="https://toneflowers.example,https://www.toneflowers.example/",
            admin_api_key="test-only-random-key-12345678901234567890",
            admin_login_email="admin@example.com",
            admin_password_hash="pbkdf2_sha256$0123456789abcdef0123456789abcdef$0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            admin_session_secret="test-only-session-secret-12345678901234567890",
            smtp_username="sender@example.com",
            smtp_password="test-only-password",
            shop_notification_emails="one@example.com,two@example.com",
        )
        with patch.dict(os.environ, {}, clear=True):
            return Settings(_env_file=None, **{**values, **overrides})

    def test_production_and_staging_accept_complete_configuration(self):
        for mode in ("production", "staging"):
            settings = self.settings(app_env=mode)
            settings.validate_runtime()
            self.assertEqual(settings.allowed_origins, [
                "https://toneflowers.example", "https://www.toneflowers.example",
            ])

    def test_runtime_rejects_missing_or_weak_production_configuration(self):
        for changes in (
            {"database_url": "sqlite:///test.db"},
            {"database_url": "postgresql+psycopg://db.example.com/toneflowers"},
            {"admin_api_key": ""},
            {"admin_api_key": "short"},
            {"admin_api_key": " " * 40},
            {"admin_login_email": ""},
            {"admin_password_hash": "plaintext-must-not-be-accepted"},
            {"admin_session_secret": ""},
            {"admin_session_ttl_seconds": 0},
            {"admin_login_rate_limit_per_minute": 0},
            {"cors_origins": ""},
            {"cors_origins": "http://localhost:5173"},
            {"smtp_username": ""},
            {"smtp_password": ""},
            {"smtp_host": ""},
            {"smtp_port": 0},
            {"shop_notification_emails": ""},
            {"shop_notification_emails": "invalid"},
        ):
            with self.subTest(fields=list(changes)), self.assertRaises(ValueError):
                self.settings(**changes).validate_runtime()

    def test_cors_rejects_wildcards_credentials_paths_and_queries(self):
        for origin in (
            "*", "https://*.example.com", "https://example.com/path",
            "https://name:password@example.com", "https://example.com?secret=value",
            "https://example.com#fragment", "https://", "https://example.com:bad",
            "https://exa mple.com", "ftp://example.com",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                self.settings(cors_origins=origin).allowed_origins

    def test_development_allows_sqlite_and_local_origins_but_rejects_short_key(self):
        settings = self.settings(app_env="development", database_url="sqlite:///test.db",
                                 cors_origins="http://localhost:5173,http://127.0.0.1:5173",
                                 admin_api_key="", smtp_password="", shop_notification_emails="")
        settings.validate_runtime()
        with self.assertRaises(ValueError):
            self.settings(app_env="development", admin_api_key="short").validate_runtime()

    def test_settings_validation_does_not_echo_environment_values(self):
        sensitive = "do-not-print-this-input"
        with self.assertRaises(ValidationError) as error:
            self.settings(smtp_port=sensitive)
        self.assertNotIn(sensitive, str(error.exception))

    def test_startup_validates_settings_and_logs_without_secrets(self):
        async def start():
            async with lifespan(app):
                pass

        settings = self.settings()
        with patch("backend.main.settings", settings), self.assertLogs("backend.main", "INFO") as logs:
            asyncio.run(start())
        output = "\n".join(logs.output)
        self.assertIn("starting (environment=production)", output)
        self.assertIn("stopping", output)
        self.assertNotIn(settings.database_url, output)
        self.assertNotIn(settings.admin_api_key.get_secret_value(), output)
        self.assertNotIn(settings.smtp_password.get_secret_value(), output)
        with patch("backend.main.settings", self.settings(admin_api_key="short")), self.assertRaises(ValueError):
            asyncio.run(start())


class CatalogSeedTests(unittest.TestCase):
    def test_seed_is_idempotent_and_demo_catalog_is_not_production_data(self):
        with isolated_database() as engine:
            with Session(engine) as db:
                seed_catalog(db, app_env="production")
                db.commit()
                zones = db.query(DeliveryZone).order_by(DeliveryZone.sort_order).all()
                self.assertEqual([(zone.governorate.value, zone.fee, zone.active) for zone in zones], [
                    ("Cairo", Decimal("50.00"), True),
                    ("Giza", Decimal("50.00"), True),
                ])
                self.assertEqual(db.query(Product).count(), 0)

                seed_catalog(db, app_env="staging")
                db.commit()
                self.assertEqual(db.query(DeliveryZone).count(), 2)
                self.assertEqual(db.query(Product).count(), 8)
                self.assertTrue(all(product.name.startswith("DEMO - ") for product in db.query(Product).all()))

                seed_catalog(db, app_env="development")
                db.commit()
                self.assertEqual(db.query(Product).count(), 8)
            with order_api(engine) as (base, _):
                status, public_zones = request_json(base, "/delivery-zones")
                self.assertEqual(status, 200)
                self.assertEqual({zone["governorate"] for zone in public_zones}, {"Cairo", "Giza"})
                self.assertTrue(all(zone["active"] and zone["fee"] == "50.00" for zone in public_zones))
                status, public_config = request_json(base, "/public-config")
                self.assertEqual(status, 200)
                self.assertEqual(set(public_config), {
                    "whatsapp_number", "vodafone_cash_number", "supported_payment_methods",
                })
                self.assertNotIn("admin_api_key", public_config)
                self.assertNotIn("admin_session_secret", public_config)


class AdminSessionTests(unittest.TestCase):
    @staticmethod
    def request(method, headers):
        return StarletteRequest({
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": "/admin/login",
            "raw_path": b"/admin/login",
            "query_string": b"",
            "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
            "client": ("127.0.0.1", 12345),
            "server": ("shop.example", 443),
        })

    def test_hashed_login_sets_secure_cookie_and_cookie_auth_requires_csrf_header(self):
        password_hash = hash_password("long-test-password-value")
        self.assertTrue(verify_password("long-test-password-value", password_hash))
        self.assertFalse(verify_password("long-test-password-value", "long-test-password-value"))
        settings = Settings(
            _env_file=None,
            app_env="production",
            cors_origins="https://shop.example",
            admin_login_email="admin@example.com",
            admin_password_hash=password_hash,
            admin_session_secret=SecretStr("test-only-session-secret-value-123456789"),
        )
        request = self.request("POST", {
            "origin": "https://shop.example",
            "x-requested-with": "ToneFlowersAdmin",
        })
        response = Response()
        with patch("backend.admin_auth.Settings", return_value=settings), \
             patch("backend.routers.admin.Settings", return_value=settings):
            result = admin_login(AdminLoginRequest(email="ADMIN@example.com", password="long-test-password-value"), request, response)
            cookie_header = response.headers["set-cookie"]
            self.assertIn("httponly", cookie_header.lower())
            self.assertIn("secure", cookie_header.lower())
            self.assertIn("samesite=none", cookie_header.lower())
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            cookie_pair = next(iter(cookie.values()))
            authenticated = self.request("PATCH", {
                "origin": "https://shop.example",
                "x-requested-with": "ToneFlowersAdmin",
                "cookie": f"toneflowers_admin_session={cookie_pair.value}",
            })
            self.assertEqual(result, {"email": "admin@example.com"})
            self.assertEqual(require_admin_session(authenticated), "admin@example.com")
            self.assertIsNone(require_admin_key(None, authenticated))
            bad_csrf = self.request("PATCH", {
                "origin": "https://shop.example",
                "cookie": f"toneflowers_admin_session={cookie_pair.value}",
            })
            with self.assertRaises(HTTPException) as error:
                require_admin_key(None, bad_csrf)
            self.assertEqual(error.exception.status_code, 403)


class DeploymentHttpTests(unittest.TestCase):
    def test_public_order_confirmation_does_not_echo_customer_pii(self):
        with isolated_database() as engine:
            with Session(engine) as db:
                db.add(Product(name="Test Roses", price=Decimal("100.00"), stock=2, active=True))
                db.commit()
            with order_api(engine) as (base, _):
                status, body = request_json(base, "/orders", {
                    "idempotency_key": str(uuid4()),
                    "customer_name": "Private Customer",
                    "customer_phone": "01012345678",
                    "customer_email": "customer@example.com",
                    "receiver_name": "Private Receiver",
                    "receiver_phone": "01012345679",
                    "governorate": "Cairo",
                    "delivery_area": "Nasr City",
                    "delivery_address": "Private street address",
                    "delivery_date": str(cairo_today()),
                    "delivery_slot": "morning",
                    "card_message": "Private card message",
                    "customer_note": "Private customer note",
                    "items": [{"product_id": 1, "quantity": 1}],
                })
        self.assertEqual(status, 201)
        self.assertEqual(body["total_price"], "100.00")
        for field in (
            "customer_name", "customer_phone", "customer_email", "receiver_name",
            "receiver_phone", "delivery_address", "card_message", "customer_note",
            "idempotency_key", "delivery_latitude", "delivery_longitude",
        ):
            self.assertNotIn(field, body)

    def test_health_is_public_and_checks_database(self):
        with isolated_database() as engine, order_api(engine) as (base, notification):
            status, body = request_json(base, "/health")
            self.assertEqual((status, body), (200, {"status": "ok"}))
            notification.assert_not_called()
        operation = app.openapi()["paths"]["/health"]["get"]
        self.assertFalse(operation.get("security"))

    def test_health_db_failure_is_503_without_sensitive_details(self):
        sensitive = "password-and-customer-phone-must-stay-private"

        def fail(*args):
            raise OperationalError("SELECT sensitive_data", {"phone": sensitive}, Exception(sensitive))

        with isolated_database() as engine, order_api(engine) as (base, _):
            event.listen(engine, "before_cursor_execute", fail)
            try:
                with self.assertLogs("backend.main", "ERROR") as logs:
                    status, body = request_json(base, "/health")
                self.assertEqual((status, body), (503, {"status": "unavailable"}))
                self.assertNotIn(sensitive, "\n".join(logs.output))
                self.assertIn("OperationalError", "\n".join(logs.output))
            finally:
                event.remove(engine, "before_cursor_execute", fail)

    def test_unexpected_errors_return_safe_json_and_keep_cors(self):
        sensitive = "private-database-url-and-customer-address"

        def fail(*args):
            raise RuntimeError(sensitive)

        with isolated_database() as engine, order_api(engine) as (base, _):
            event.listen(engine, "before_cursor_execute", fail)
            try:
                request = Request(base + "/products", headers={"Origin": "http://localhost:5173"})
                with self.assertLogs("backend.main", "ERROR") as logs:
                    with self.assertRaises(HTTPError) as response:
                        urlopen(request, timeout=10)
                self.assertEqual(response.exception.code, 500)
                self.assertEqual(json.load(response.exception), {"detail": "Internal server error"})
                self.assertEqual(response.exception.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
                self.assertNotIn(sensitive, "\n".join(logs.output))
                self.assertIn("RuntimeError", "\n".join(logs.output))
            finally:
                event.remove(engine, "before_cursor_execute", fail)

    def test_expected_not_found_still_has_useful_message(self):
        with isolated_database() as engine, order_api(engine) as (base, _):
            self.assertEqual(request_json(base, "/products/999"), (404, {"detail": "Product not found"}))

    def test_email_error_does_not_log_server_reply_or_record_success(self):
        sensitive = b"private-smtp-password-and-recipient"
        with patch("backend.services.email_service.Settings", side_effect=smtplib.SMTPAuthenticationError(535, sensitive)), \
             patch("backend.services.email_service.SessionLocal") as sessions, \
             self.assertLogs("backend.services.email_service", "ERROR") as logs:
            send_order_notification({})
        sessions.assert_not_called()
        self.assertNotIn(sensitive.decode(), "\n".join(logs.output))
        self.assertIn("SMTPAuthenticationError", "\n".join(logs.output))

    def test_failure_log_excludes_sql_parameters_and_exception_text(self):
        logger = logging.getLogger("backend.deployment-test")
        try:
            raise OperationalError("INSERT private_sql", {"password": "private-value"}, Exception("private-reply"))
        except OperationalError as error:
            with self.assertLogs(logger, "ERROR") as logs:
                log_failure(logger, "Database operation failed", error)
        output = "\n".join(logs.output)
        self.assertIn("test_deployment.py:", output)
        for value in ("private_sql", "private-value", "private-reply"):
            self.assertNotIn(value, output)
