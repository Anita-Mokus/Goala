"""Resolve access-gate roles from submitted tokens."""

from __future__ import annotations

import hmac

from src.config import (
    ACCESS_GATE_ADMIN_TOKEN_HASHES,
    ACCESS_GATE_OPERATOR_TOKEN_HASHES,
    hash_access_token,
)

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
VALID_ROLES = {ROLE_ADMIN, ROLE_OPERATOR}


def resolve_role_from_token(token: str) -> str | None:
    """Return the role for a token, checking admin hashes before operator hashes."""
    submitted_hash = hash_access_token(token.strip())

    if any(hmac.compare_digest(submitted_hash, stored_hash) for stored_hash in ACCESS_GATE_ADMIN_TOKEN_HASHES):
        return ROLE_ADMIN

    if any(hmac.compare_digest(submitted_hash, stored_hash) for stored_hash in ACCESS_GATE_OPERATOR_TOKEN_HASHES):
        return ROLE_OPERATOR

    return None
