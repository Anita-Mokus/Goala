"""
Messenger message extraction: get message content from the open conversation.
Handles single latest message and combined unanswered client messages.
"""
import time
from typing import List, Dict, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from src.integrations.messenger.message_ownership import is_message_from_us
from src.integrations.messenger.message_sender import extract_sender_name


def extract_latest_message(bot) -> Optional[Dict]:
    """
    Extract the latest message from the currently open conversation.

    Args:
        bot: MessengerBot instance

    Returns:
        Dictionary with 'sender', 'text', and 'element' keys, or None.
    """
    try:
        time.sleep(1)
        message_selectors = [
            'div[dir="auto"]',
            'span.x1lliihq',
            'div[role="row"] div[dir="auto"]',
        ]
        for selector in message_selectors:
            try:
                messages = bot.driver.find_elements(By.CSS_SELECTOR, selector)
                if messages:
                    latest = messages[-1]
                    text = latest.text.strip()
                    if text:
                        return {
                            'sender': extract_sender_name(bot),
                            'text': text,
                            'element': latest,
                        }
            except NoSuchElementException:
                continue
    except Exception as e:
        print(f"ERROR extracting message: {e}")
    return None


def extract_unanswered_client_messages(bot, conv_id: str = "") -> Optional[Dict]:
    """
    Extract all unanswered client messages since our last reply and combine them.

    Gets all message elements, marks ours vs theirs, finds last "ours", then
    collects all "theirs" after that and joins with newlines.

    Args:
        bot: MessengerBot instance
        conv_id: Conversation ID for logging

    Returns:
        Dict with 'sender', 'text', 'element', or None if no client messages.
    """
    try:
        time.sleep(1)
        message_selectors = ['div[role="row"] div[dir="auto"]', 'div[dir="auto"]']
        all_messages: List[Tuple[object, str, bool]] = []

        for selector in message_selectors:
            try:
                message_elements = bot.driver.find_elements(By.CSS_SELECTOR, selector)
                if not message_elements:
                    continue
                print(f"  [DEBUG] Found {len(message_elements)} message elements with selector '{selector}'")
                for elem in message_elements:
                    text = elem.text.strip()
                    if not text:
                        continue
                    all_messages.append((elem, text, is_message_from_us(bot, elem)))
                if all_messages:
                    break
            except NoSuchElementException:
                continue

        if not all_messages:
            print(f"  [DEBUG] No messages found in conversation {conv_id}")
            return None

        _log_message_ownership(all_messages)

        last_our_index = -1
        for i in range(len(all_messages) - 1, -1, -1):
            if all_messages[i][2]:
                last_our_index = i
                print(f"  [DEBUG] Last message from us at index {i}")
                break

        start = last_our_index + 1 if last_our_index >= 0 else 0
        client_texts = [
            all_messages[i][1]
            for i in range(start, len(all_messages))
            if not all_messages[i][2]
        ]

        if not client_texts:
            print(f"  [DEBUG] No new client messages after our last reply in {conv_id}")
            return None

        combined = "\n".join(client_texts)
        print(f"  [DEBUG] Combined {len(client_texts)} client message(s): {combined[:100]}...")

        return {
            'sender': extract_sender_name(bot),
            'text': combined,
            'element': all_messages[-1][0],
        }
    except Exception as e:
        print(f"  ERROR extracting unanswered messages: {e}")
        import traceback
        traceback.print_exc()
        return None


def _log_message_ownership(all_messages: List[Tuple[object, str, bool]]) -> None:
    """Log each message index, owner (us/client), and text snippet."""
    print(f"  [DEBUG] Total messages in conversation: {len(all_messages)}")
    for i, (_, text, is_ours) in enumerate(all_messages):
        owner = "us" if is_ours else "client"
        print(f"  [DEBUG]   [{i}] {owner}: {text[:50]}...")
