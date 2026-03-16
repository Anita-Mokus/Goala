"""
Messenger history persistence.
Stores per-conversation threads and message-level transcript in PostgreSQL.
"""
import hashlib
import re
from typing import Dict, List, Optional

from sqlalchemy import text

from src.models.database import get_db_session

_CONVERSATION_ID_REGEX = re.compile(r"/t/([0-9]+)")


def normalize_conversation_url(url: str) -> str:
    """Normalize Messenger conversation URLs to a stable DB key."""
    if not url:
        return ""
    normalized = url.strip()
    if "?" in normalized:
        normalized = normalized.split("?", 1)[0]
    if "#" in normalized:
        normalized = normalized.split("#", 1)[0]
    return normalized.rstrip("/")


def extract_conversation_id(conversation_url: str) -> str:
    """Extract numeric conversation id from messenger URL (/t/<id>)."""
    match = _CONVERSATION_ID_REGEX.search(conversation_url or "")
    if not match:
        fallback = hashlib.sha256((conversation_url or "unknown").encode("utf-8", errors="replace")).hexdigest()
        return f"fallback_{fallback[:24]}"
    return match.group(1)


def _build_thread_key(conversation_id: str) -> str:
    """Build a stable thread key from the unique Messenger conversation id."""
    return f"messenger:{conversation_id}"


def get_or_create_thread(conversation_url: str, display_name: str, metadata: Optional[dict] = None) -> Dict:
    """
    Upsert and return messenger thread row.

    Returns dict with keys: id, conversation_id, thread_key, bootstrapped_from_dom.
    """
    normalized_url = normalize_conversation_url(conversation_url)
    conversation_id = extract_conversation_id(normalized_url)
    thread_key = _build_thread_key(conversation_id)

    with get_db_session() as session:
        row = session.execute(
            text(
                """
                INSERT INTO messenger_threads (
                    conversation_url,
                    conversation_id,
                    thread_key,
                    display_name,
                    metadata,
                    last_seen_at
                ) VALUES (
                    :conversation_url,
                    :conversation_id,
                    :thread_key,
                    :display_name,
                    CAST(:metadata AS jsonb),
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (conversation_url) DO UPDATE
                SET
                    display_name = EXCLUDED.display_name,
                    metadata = COALESCE(EXCLUDED.metadata, messenger_threads.metadata),
                    last_seen_at = CURRENT_TIMESTAMP
                RETURNING id, conversation_id, thread_key, bootstrapped_from_dom
                """
            ),
            {
                "conversation_url": normalized_url,
                "conversation_id": conversation_id,
                "thread_key": thread_key,
                "display_name": display_name,
                "metadata": _to_json(metadata),
            },
        ).mappings().first()

        if not row:
            raise RuntimeError("Failed to create or load messenger thread")

        return dict(row)


def mark_thread_bootstrapped(thread_id: int) -> None:
    """Mark thread as bootstrapped from DOM."""
    with get_db_session() as session:
        session.execute(
            text(
                """
                UPDATE messenger_threads
                SET bootstrapped_from_dom = TRUE,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE id = :thread_id
                """
            ),
            {"thread_id": thread_id},
        )


def count_thread_messages(thread_id: int) -> int:
    """Count non-deleted messages for a thread."""
    with get_db_session() as session:
        count = session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM messenger_messages
                WHERE thread_id = :thread_id
                  AND is_deleted = FALSE
                """
            ),
            {"thread_id": thread_id},
        ).scalar_one()
    return int(count or 0)


def save_message(
    thread_id: int,
    role: str,
    direction: str,
    content: str,
    source: str,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Persist one message.

    Returns:
        True if inserted, False if content was empty.
    """
    normalized_content = (content or "").strip()
    if not normalized_content:
        return False

    content_hash = hashlib.sha256(normalized_content.encode("utf-8", errors="replace")).hexdigest()

    with get_db_session() as session:
        session.execute(
            text(
                """
                INSERT INTO messenger_messages (
                    thread_id,
                    role,
                    direction,
                    content,
                    content_hash,
                    source,
                    metadata,
                    observed_at
                ) VALUES (
                    :thread_id,
                    :role,
                    :direction,
                    :content,
                    :content_hash,
                    :source,
                    CAST(:metadata AS jsonb),
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "thread_id": thread_id,
                "role": role,
                "direction": direction,
                "content": normalized_content,
                "content_hash": content_hash,
                "source": source,
                "metadata": _to_json(metadata),
            },
        )

    return True


def get_recent_messages(thread_id: int, limit: int = 60) -> List[Dict]:
    """Load recent non-deleted messages ordered oldest -> newest."""
    with get_db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT id, role, direction, content, source, created_at
                FROM messenger_messages
                WHERE thread_id = :thread_id
                  AND is_deleted = FALSE
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"thread_id": thread_id, "limit": limit},
        ).mappings().all()

    ordered = list(reversed(rows))
    return [dict(row) for row in ordered]


def _to_json(data: Optional[dict]) -> Optional[str]:
    """Serialize dict to JSON text for CAST(:metadata AS jsonb)."""
    if data is None:
        return None
    import json
    return json.dumps(data, ensure_ascii=True)
