"""Access gate helpers for the public deployment."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from src.config import (
    ACCESS_GATE_COOKIE_NAME,
    ACCESS_GATE_SESSION_SECRET,
    ACCESS_GATE_SESSION_TTL_SECONDS,
    ACCESS_GATE_TOKEN_HASHES,
    hash_access_token,
)

PUBLIC_HTTP_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def is_auth_enabled() -> bool:
    """Return whether the access gate is configured."""
    return bool(ACCESS_GATE_SESSION_SECRET and ACCESS_GATE_TOKEN_HASHES)


def is_public_http_path(path: str) -> bool:
    """Return whether an HTTP path should bypass the gate."""
    normalized_path = path.rstrip("/") or "/"
    if normalized_path in PUBLIC_HTTP_PATHS:
        return True
    return normalized_path.startswith("/api/auth")


def is_valid_access_token(token: str) -> bool:
    """Check whether a submitted access token matches one of the configured hashes."""
    if not is_auth_enabled():
        return False

    submitted_hash = hash_access_token(token.strip())
    return any(hmac.compare_digest(submitted_hash, stored_hash) for stored_hash in ACCESS_GATE_TOKEN_HASHES)


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def issue_access_cookie_value() -> str:
    """Create a signed cookie payload for an authenticated browser session."""
    issued_at = int(time.time())
    payload = {
        "iat": issued_at,
        "exp": issued_at + ACCESS_GATE_SESSION_TTL_SECONDS,
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
    if not is_auth_enabled() or not cookie_value:
        return False

    try:
        payload_segment, signature_segment = cookie_value.split(".", 1)
        expected_signature = hmac.new(
            ACCESS_GATE_SESSION_SECRET.encode("utf-8"),
            payload_segment.encode("ascii"),
            hashlib.sha256,
        ).digest()
        provided_signature = _base64url_decode(signature_segment)

        if not hmac.compare_digest(expected_signature, provided_signature):
            return False

        payload = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        expires_at = int(payload.get("exp", 0))
        return expires_at > int(time.time())
    except Exception:
        return False


def get_cookie_expiry_timestamp(cookie_value: Optional[str]) -> Optional[int]:
    """Return the expiry timestamp for a valid access cookie."""
    if not cookie_value:
        return None

    try:
        payload_segment, _ = cookie_value.split(".", 1)
        payload = json.loads(_base64url_decode(payload_segment).decode("utf-8"))
        expires_at = int(payload.get("exp", 0))
        return expires_at if expires_at > 0 else None
    except Exception:
        return None


__all__ = [
    "ACCESS_GATE_COOKIE_NAME",
    "is_auth_enabled",
    "is_public_http_path",
    "is_valid_access_token",
    "issue_access_cookie_value",
    "verify_access_cookie_value",
    "get_cookie_expiry_timestamp",
]