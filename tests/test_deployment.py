import asyncio
import json
import logging
import os
import smtplib
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from backend.logging_utils import log_failure
from backend.main import app, lifespan
from backend.services.email_service import send_order_notification
from backend.settings import Settings
from tests.db_support import isolated_database
from tests.http_support import order_api, request_json


class DeploymentSettingsTests(unittest.TestCase):
    def settings(self, **overrides):
        values = dict(
            app_env="production",
            database_url="postgresql+psycopg://toneflowers_app:example%40pass@db.example.com:5432/toneflowers",
            cors_origins="https://toneflowers.example,https://www.toneflowers.example/",
            admin_api_key="test-only-random-key-12345678901234567890",
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


class DeploymentHttpTests(unittest.TestCase):
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
