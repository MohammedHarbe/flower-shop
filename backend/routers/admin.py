from pydantic import BaseModel, ConfigDict, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.admin_auth import (
    _validate_admin_browser_request,
    clear_admin_session,
    require_admin_session,
    set_admin_session,
    verify_password,
)
from backend.rate_limiter import enforce_rate_limit
from backend.settings import Settings

router = APIRouter()


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


@router.post("/admin/login")
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
):
    settings = Settings()
    if not settings.admin_login_email or not settings.admin_password_hash or not settings.admin_session_secret.get_secret_value():
        raise HTTPException(503, "Admin login is not configured")
    _validate_admin_browser_request(request)
    enforce_rate_limit(request, name="admin_login", limit=settings.admin_login_rate_limit_per_minute, window_seconds=60)
    normalized_email = payload.email.strip().lower()
    if normalized_email != str(settings.admin_login_email).lower():
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(payload.password, settings.admin_password_hash):
        raise HTTPException(401, "Invalid email or password")
    set_admin_session(response, normalized_email)
    return {"email": normalized_email}


@router.post("/admin/logout")
def admin_logout(request: Request, response: Response):
    require_admin_session(request)
    _validate_admin_browser_request(request)
    clear_admin_session(response)
    return {"ok": True}


@router.get("/admin/me")
def admin_me(email: str = Depends(require_admin_session)):
    return {"email": email}
