"""FastAPI dependencies for role-based access control."""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request

from src.api.auth import (
    ACCESS_GATE_COOKIE_NAME,
    get_role_from_cookie,
    is_auth_enabled,
    verify_access_cookie_value,
)


def require_session_role(*allowed_roles: str) -> Callable[[Request], str]:
    """Return a dependency that enforces an authenticated session role."""

    def dependency(request: Request) -> str:
        if not is_auth_enabled():
            return allowed_roles[0]

        cookie_value = request.cookies.get(ACCESS_GATE_COOKIE_NAME)
        if not verify_access_cookie_value(cookie_value):
            raise HTTPException(status_code=401, detail="Authentication required")

        role = get_role_from_cookie(cookie_value)
        if not role:
            raise HTTPException(status_code=401, detail="Authentication required")

        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return role

    return dependency
