import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from backend.settings import Settings


_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin_key(provided_key: str | None = Depends(_admin_key_header)) -> None:
    """Small temporary gate for admin API routes. Replace with real admin auth later."""
    configured_key = Settings().admin_api_key.get_secret_value()
    if not configured_key:
        raise HTTPException(503, "Admin API key is not configured")
    if not provided_key or not secrets.compare_digest(provided_key, configured_key):
        raise HTTPException(403, "Invalid admin API key")
