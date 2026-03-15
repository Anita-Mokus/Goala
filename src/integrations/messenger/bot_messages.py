"""
Messenger bot message detection and extraction.

Public API: use this module for all message-related operations.
Implementation is split into:
  - message_ownership: sent vs received detection
  - message_sender: conversation/sender name
  - message_extraction: single and combined message content
  - unread_messages: sidebar unread list and collection
"""
from src.integrations.messenger.message_ownership import is_message_from_us
from src.integrations.messenger.message_sender import extract_sender_name
from src.integrations.messenger.message_extraction import (
    extract_latest_message,
    extract_unanswered_client_messages,
)
from src.integrations.messenger.unread_messages import get_unread_messages

__all__ = [
    "get_unread_messages",
    "extract_latest_message",
    "extract_sender_name",
    "extract_unanswered_client_messages",
    "is_message_from_us",
]
