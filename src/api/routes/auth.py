"""Authentication routes for the public access gate."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from src.api.auth import (
    ACCESS_GATE_COOKIE_NAME,
    get_cookie_expiry_timestamp,
    is_auth_enabled,
    is_valid_access_token,
    issue_access_cookie_value,
    verify_access_cookie_value,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    token: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    expires_at: str | None = None


def _build_status_response(cookie_value: str | None) -> AuthStatusResponse:
    if verify_access_cookie_value(cookie_value):
        expires_at = get_cookie_expiry_timestamp(cookie_value)
        expires_at_iso = (
            datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat() if expires_at else None
        )
        return AuthStatusResponse(authenticated=True, expires_at=expires_at_iso)

    return AuthStatusResponse(authenticated=False, expires_at=None)


@router.get("/me", response_model=AuthStatusResponse)
def read_auth_status(request: Request):
    return _build_status_response(request.cookies.get(ACCESS_GATE_COOKIE_NAME))


@router.post("/login", response_model=AuthStatusResponse)
def login(request_body: LoginRequest, response: Response):
    if not is_auth_enabled():
        raise HTTPException(status_code=503, detail="Access gate is not configured")

    if not is_valid_access_token(request_body.token):
        raise HTTPException(status_code=401, detail="Invalid access token")

    cookie_value = issue_access_cookie_value()
    response.set_cookie(
        key=ACCESS_GATE_COOKIE_NAME,
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return _build_status_response(cookie_value)


@router.post("/logout", response_model=AuthStatusResponse)
def logout(response: Response):
    response.delete_cookie(key=ACCESS_GATE_COOKIE_NAME, path="/")
    return AuthStatusResponse(authenticated=False, expires_at=None)