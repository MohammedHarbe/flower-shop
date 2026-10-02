import hashlib
import hmac
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyHeader
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.settings import Settings


_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Admin passwords must contain at least 12 characters")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False
    try:
        _, salt, digest_hex = stored_hash.split("$", 2)
    except ValueError:
        return False
    if not stored_hash.startswith("pbkdf2_sha256$") or len(salt) != 32 or len(digest_hex) != 64:
        return False
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return hmac.compare_digest(expected.hex(), digest_hex)


def _validate_admin_browser_request(request: Request) -> None:
    settings = Settings()
    origin = request.headers.get("origin")
    if origin not in settings.allowed_origins:
        raise HTTPException(403, "Admin request origin is not allowed")
    if request.headers.get("x-requested-with") != "ToneFlowersAdmin":
        raise HTTPException(403, "Admin request token is required")


def require_admin_key(
    provided_key: str | None = Depends(_admin_key_header),
    request: Request = None,
) -> None:
    configured_key = Settings().admin_api_key.get_secret_value()
    if provided_key:
        if not configured_key:
            raise HTTPException(503, "Admin API key is not configured")
        if not secrets.compare_digest(provided_key, configured_key):
            raise HTTPException(403, "Invalid admin API key")
        return
    if request is None:
        if not configured_key:
            raise HTTPException(503, "Admin API key is not configured")
        raise HTTPException(403, "Invalid admin API key")
    require_admin_session(request)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        _validate_admin_browser_request(request)


def require_admin_session(request: Request) -> str:
    settings = Settings()
    secret = settings.admin_session_secret.get_secret_value()
    if not secret:
        raise HTTPException(503, "Admin session is not configured")
    token = request.cookies.get(settings.admin_session_cookie_name)
    if not token:
        raise HTTPException(401, "Admin session required")
    serializer = URLSafeTimedSerializer(secret, salt="toneflowers-admin")
    try:
        payload = serializer.loads(token, max_age=settings.admin_session_ttl_seconds)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Admin session expired or invalid") from None
    if not isinstance(payload, dict):
        raise HTTPException(401, "Admin session invalid")
    email = str(payload.get("email", "")).strip().lower()
    expected = str(settings.admin_login_email).strip().lower()
    if not email or email != expected:
        raise HTTPException(401, "Admin session invalid")
    return email


def set_admin_session(response: Response, email: str) -> None:
    settings = Settings()
    secret = settings.admin_session_secret.get_secret_value()
    if not secret:
        raise HTTPException(503, "Admin session is not configured")
    payload: dict[str, Any] = {
        "email": str(email).strip().lower(),
        "exp": int(time.time()) + settings.admin_session_ttl_seconds,
    }
    serializer = URLSafeTimedSerializer(secret, salt="toneflowers-admin")
    token = serializer.dumps(payload)
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.app_env in {"staging", "production"},
        samesite="none" if settings.app_env in {"staging", "production"} else "lax",
        max_age=settings.admin_session_ttl_seconds,
        path="/",
    )


def clear_admin_session(response: Response) -> None:
    settings = Settings()
    response.delete_cookie(
        key=settings.admin_session_cookie_name,
        path="/",
        secure=settings.app_env in {"staging", "production"},
        httponly=True,
        samesite="none" if settings.app_env in {"staging", "production"} else "lax",
    )
