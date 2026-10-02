import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import EmailStr, SecretStr, field_validator
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
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    admin_api_key: SecretStr = SecretStr("")
    admin_login_email: EmailStr | str = ""
    admin_password_hash: str = ""
    admin_session_secret: SecretStr = SecretStr("")
    admin_session_cookie_name: str = "toneflowers_admin_session"
    admin_session_ttl_seconds: int = 8 * 60 * 60
    admin_login_rate_limit_per_minute: int = 5
    order_rate_limit_per_minute: int = 30
    whatsapp_number: str = ""
    vodafone_cash_number: str = ""
    media_dir: Path = Path(__file__).resolve().parents[1] / "media"
    media_base_url: str = "/media"
    media_persistent_storage: bool = False

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    shop_notification_emails: str = ""

    @field_validator("media_base_url")
    @classmethod
    def validate_media_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value.startswith("/") and not value.startswith("//"):
            parsed = urlsplit(value)
            segments = parsed.path.strip("/").split("/")
            reserved = {"admin", "delivery-zones", "docs", "health", "openapi.json", "orders", "products", "public-config"}
            if (parsed.path == "/" or parsed.query or parsed.fragment
                    or not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", parsed.path)
                    or segments[0].lower() in reserved):
                raise ValueError("MEDIA_BASE_URL must be a safe root-relative URL path")
            return value
        try:
            parsed = urlsplit(value)
            port = parsed.port
            segments = parsed.path.strip("/").split("/") if parsed.path.strip("/") else []
            reserved = {"admin", "delivery-zones", "docs", "health", "openapi.json", "orders", "products", "public-config"}
            valid = (
                parsed.scheme in {"http", "https"} and parsed.hostname
                and parsed.username is None and parsed.password is None
                and re.fullmatch(r"/(?:[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*)?", parsed.path or "/")
                and (port is None or 1 <= port <= 65535)
                and (not segments or segments[0].lower() not in reserved)
                and not parsed.query and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("MEDIA_BASE_URL must be a root-relative path or an absolute HTTP(S) origin")
        base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        return f"{base}/media" if parsed.path in {"", "/"} else base

    @property
    def resolved_media_dir(self) -> Path:
        return self.media_dir if self.media_dir.is_absolute() else Path(__file__).resolve().parents[1] / self.media_dir

    @property
    def media_route_path(self) -> str:
        parsed = urlsplit(self.media_base_url)
        if parsed.scheme:
            return parsed.path.rstrip("/") or "/media"
        return self.media_base_url

    @property
    def media_uploads_enabled(self) -> bool:
        return self.app_env == "development" or self.media_persistent_storage

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
        if self.admin_session_secret.get_secret_value() and (
            len(self.admin_session_secret.get_secret_value()) < 32
            or len(self.admin_session_secret.get_secret_value().strip()) != len(self.admin_session_secret.get_secret_value())
        ):
            raise ValueError("ADMIN_SESSION_SECRET must contain at least 32 characters without surrounding whitespace")
        if self.admin_password_hash:
            parts = self.admin_password_hash.split("$")
            if (
                len(parts) != 3
                or parts[0] != "pbkdf2_sha256"
                or len(parts[1]) != 32
                or len(parts[2]) != 64
                or any(character not in "0123456789abcdef" for character in parts[1] + parts[2])
            ):
                raise ValueError("ADMIN_PASSWORD_HASH must use the supported PBKDF2-SHA256 format")
        if self.admin_session_ttl_seconds <= 0:
            raise ValueError("ADMIN_SESSION_TTL_SECONDS must be positive")
        if self.admin_login_rate_limit_per_minute <= 0 or self.order_rate_limit_per_minute <= 0:
            raise ValueError("Admin login and order rate limits must be positive")
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
        if not self.admin_login_email or not self.admin_password_hash or not self.admin_session_secret.get_secret_value():
            raise ValueError("ADMIN_LOGIN_EMAIL, ADMIN_PASSWORD_HASH, and ADMIN_SESSION_SECRET are required in staging/production")
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
