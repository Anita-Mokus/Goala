"""Access gate helpers for the public deployment."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from src.config import (
    ACCESS_GATE_ADMIN_TOKEN_HASHES,
    ACCESS_GATE_COOKIE_NAME,
    ACCESS_GATE_OPERATOR_TOKEN_HASHES,
    ACCESS_GATE_SESSION_SECRET,
    ACCESS_GATE_SESSION_TTL_SECONDS,
)
from src.api.role_resolver import VALID_ROLES, resolve_role_from_token

PUBLIC_HTTP_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def is_auth_enabled() -> bool:
    """Return whether the access gate is configured."""
    has_hashes = bool(ACCESS_GATE_ADMIN_TOKEN_HASHES or ACCESS_GATE_OPERATOR_TOKEN_HASHES)
    return bool(ACCESS_GATE_SESSION_SECRET and has_hashes)


def is_public_http_path(path: str) -> bool:
    """Return whether an HTTP path should bypass the gate."""
    normalized_path = path.rstrip("/") or "/"
    if normalized_path in PUBLIC_HTTP_PATHS:
        return True
    return normalized_path.startswith("/api/auth")


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _decode_verified_payload(cookie_value: str) -> dict | None:
    if not is_auth_enabled() or not cookie_value:
        return None

    try:
        payload_segment, signature_segment = cookie_value.split(".", 1)
        expected_signature = hmac.new(
            ACCESS_GATE_SESSION_SECRET.encode("utf-8"),
            payload_segment.encode("ascii"),
            hashlib.sha256,
        ).digest()
        provided_signature = _base64url_decode(signature_segment)

        if not hmac.compare_digest(expected_signature, provided_signature):
            return None

        payload = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        expires_at = int(payload.get("exp", 0))
        if expires_at <= int(time.time()):
            return None

        return payload
    except Exception:
        return None


def issue_access_cookie_value(role: str) -> str:
    """Create a signed cookie payload for an authenticated browser session."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    issued_at = int(time.time())
    payload = {
        "iat": issued_at,
        "exp": issued_at + ACCESS_GATE_SESSION_TTL_SECONDS,
        "role": role,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_segment = _base64url_encode(payload_bytes)
    signature = hmac.new(
        ACCESS_GATE_SESSION_SECRET.encode("utf-8"),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_base64url_encode(signature)}"


def verify_access_cookie_value(cookie_value: Optional[str]) -> bool:
    """Verify an access cookie signature and expiry."""
    return _decode_verified_payload(cookie_value or "") is not None


def get_role_from_cookie(cookie_value: Optional[str]) -> str | None:
    """Return the role from a valid access cookie."""
    payload = _decode_verified_payload(cookie_value or "")
    if not payload:
        return None

    role = payload.get("role")
    return role if role in VALID_ROLES else None


def get_cookie_expiry_timestamp(cookie_value: Optional[str]) -> Optional[int]:
    """Return the expiry timestamp for a valid access cookie."""
    payload = _decode_verified_payload(cookie_value or "")
    if not payload:
        return None

    expires_at = int(payload.get("exp", 0))
    return expires_at if expires_at > 0 else None


__all__ = [
    "ACCESS_GATE_COOKIE_NAME",
    "is_auth_enabled",
    "is_public_http_path",
    "resolve_role_from_token",
    "issue_access_cookie_value",
    "verify_access_cookie_value",
    "get_role_from_cookie",
    "get_cookie_expiry_timestamp",
]
