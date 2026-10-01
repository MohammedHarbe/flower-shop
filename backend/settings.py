import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


_EMAIL = re.compile(r"^[^@\s,<>]+@[^@\s,<>]+\.[^@\s,<>]+$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "staging", "production"] = "development"
    database_url: str = "sqlite:///./flower_shop.dp"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    admin_api_key: SecretStr = SecretStr("")

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    shop_notification_emails: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        origins = []
        for value in self.cors_origins.split(","):
            origin = value.strip()
            if not origin:
                continue
            try:
                parsed = urlsplit(origin)
                port = parsed.port
                valid = (
                    parsed.scheme in {"http", "https"} and parsed.hostname
                    and parsed.username is None and parsed.password is None
                    and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
                    and "?" not in origin and "#" not in origin
                    and "*" not in origin and not any(char.isspace() for char in origin)
                    and (port is None or 1 <= port <= 65535)
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths or credentials")
            origins.append(origin.rstrip("/"))
        return origins

    def validate_runtime(self) -> None:
        """Fail startup with safe messages; never include configuration values."""
        key = self.admin_api_key.get_secret_value()
        if key and (len(key) < 32 or len(key.strip()) != len(key)):
            raise ValueError("ADMIN_API_KEY must contain at least 32 characters without surrounding whitespace")
        origins = self.allowed_origins
        recipients = self.notification_recipients
        if not 1 <= self.smtp_port <= 65535:
            raise ValueError("SMTP_PORT must be between 1 and 65535")
        if self.app_env == "development":
            return

        from sqlalchemy.engine import make_url

        try:
            database = make_url(self.database_url)
            valid_database = (
                database.drivername == "postgresql+psycopg"
                and database.host and database.database and database.username and database.password
            )
        except Exception:
            valid_database = False
        if not valid_database:
            raise ValueError("Staging/production requires a complete PostgreSQL psycopg DATABASE_URL")
        if not key:
            raise ValueError("ADMIN_API_KEY is required in staging/production")
        if not origins or any(urlsplit(origin).scheme != "https" for origin in origins):
            raise ValueError("Staging/production requires exact HTTPS CORS_ORIGINS")
        if not (self.smtp_host.strip() and self.smtp_username.strip()
                and self.smtp_password.get_secret_value().strip() and recipients):
            raise ValueError("SMTP settings and SHOP_NOTIFICATION_EMAILS are required in staging/production")

    @property
    def notification_recipients(self) -> list[str]:
        recipients: list[str] = []
        seen: set[str] = set()
        for value in self.shop_notification_emails.split(","):
            address = value.strip()
            if not address:
                continue
            if not _EMAIL.fullmatch(address):
                raise ValueError("SHOP_NOTIFICATION_EMAILS contains an invalid email address")
            if address.lower() not in seen:
                recipients.append(address)
                seen.add(address.lower())
        return recipients
