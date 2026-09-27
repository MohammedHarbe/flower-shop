import re
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


_EMAIL = re.compile(r"^[^@\s,<>]+@[^@\s,<>]+\.[^@\s,<>]+$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
    )

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
        origins = [value.strip().rstrip("/") for value in self.cors_origins.split(",") if value.strip()]
        if any(not origin.startswith(("http://", "https://")) or "*" in origin for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return origins

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
