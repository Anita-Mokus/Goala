"""
Messenger unread list: find unread conversations and collect their messages.
"""
import time
import hashlib
from typing import List, Dict

from selenium.webdriver.common.by import By

from src.integrations.messenger.message_extraction import extract_unanswered_client_messages


def get_unread_messages(bot) -> List[Dict]:
    """
    Get all unread messages from Messenger.

    Finds unread conversation links in the sidebar, opens each, extracts
    combined unanswered client messages, deduplicates, and returns one
    message dict per conversation.

    Args:
        bot: MessengerBot instance

    Returns:
        List of message dicts with 'sender', 'text', 'element', 'conversation_id', '_msg_hash'.
    """
    unread_messages = []
    try:
        unread_hrefs = _collect_unread_conversation_hrefs(bot)
        print(f"[DEBUG] {len(unread_hrefs)} unread conversation(s) detected")

        for href in unread_hrefs:
            try:
                print(f"[DEBUG] Opening unread conversation: {href}")
                bot.driver.get(href)
                time.sleep(1.5)
                conv_id = bot.driver.current_url
                message = extract_unanswered_client_messages(bot, conv_id)

                if message:
                    msg_hash = hashlib.sha256(message['text'].encode(errors='replace')).hexdigest()[:16]
                    message_key = (conv_id, msg_hash)
                    if message_key in bot._processed_messages:
                        print(f"  [DEBUG] Skipping already processed message set in {conv_id}")
                        continue
                    if bot._last_sent.get(conv_id) == msg_hash:
                        print(f"  [DEBUG] Skipping our own last message in {conv_id}")
                        continue
                    message['conversation_id'] = conv_id
                    message['_msg_hash'] = msg_hash
                    unread_messages.append(message)
                    print(f"[DEBUG] Queued combined message from conversation: {conv_id}")
                else:
                    print(f"[DEBUG] No extractable client messages in conversation: {conv_id}")
            except Exception as e:
                print(f"Warning: Could not process conversation {href}: {type(e).__name__}: {e}")
                continue

        if not unread_messages:
            print("[DEBUG] No new unread messages found")
    except Exception as e:
        print(f"ERROR getting unread messages: {e}")

    return unread_messages


def _collect_unread_conversation_hrefs(bot) -> List[str]:
    """Find conversation links in sidebar and return hrefs that are unread (bold)."""
    conv_links = bot.driver.find_elements(
        By.CSS_SELECTOR,
        'a[href*="/t/"], a[href*="/e2ee/t/"]',
    )
    conversation_links = conv_links[4:]
    print(f"[DEBUG] Found {len(conversation_links)} conversation link(s) in sidebar:")
    for i, link in enumerate(conversation_links):
        label = (link.get_attribute("aria-label") or link.text or "").strip().replace("\n", " | ")
        href = link.get_attribute("href") or ""
        print(f"[DEBUG]   [{i}] {label[:70]}  →  {href}")

    unread_hrefs: List[str] = []
    for link in conversation_links:
        try:
            is_unread = bot.driver.execute_script(_IS_UNREAD_BOLD_SCRIPT, link)
            if is_unread:
                href = _sanitize_href(link.get_attribute("href") or "")
                if href and href not in unread_hrefs:
                    unread_hrefs.append(href)
                    label = link.get_attribute("aria-label") or href
                    print(f"[DEBUG] Unread: {label[:70]}")
        except Exception:
            continue
    return unread_hrefs


def _sanitize_href(raw_href: str) -> str:
    """Remove invisible/control characters from URLs."""
    if not raw_href:
        return ""
    cleaned = "".join(
        ch for ch in raw_href
        if ch.isprintable() and ord(ch) not in {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}
    )
    return cleaned.strip()


_IS_UNREAD_BOLD_SCRIPT = """
var el = arguments[0];
var children = el.querySelectorAll('*');
for (var i = 0; i < children.length; i++) {
    var fw = window.getComputedStyle(children[i]).fontWeight;
    if (fw === '700' || fw === 'bold') { return true; }
}
return false;
"""
