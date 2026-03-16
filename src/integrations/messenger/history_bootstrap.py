"""
Messenger history bootstrap from currently visible DOM messages.
"""
from typing import List

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from src.integrations.messenger.message_ownership import is_message_from_us
from src.integrations.messenger.history_repository import save_message


def bootstrap_thread_from_dom(bot, thread_id: int, conversation_id: str) -> int:
    """
    Persist all currently visible messages for a conversation.

    Returns:
        Number of inserted messages.
    """
    inserted = 0
    elements = _extract_visible_message_elements(bot)

    for elem in elements:
        text = (elem.text or "").strip()
        if not text:
            continue

        ours = is_message_from_us(bot, elem)
        role = "assistant" if ours else "user"
        direction = "outbound" if ours else "inbound"

        saved = save_message(
            thread_id=thread_id,
            role=role,
            direction=direction,
            content=text,
            source="dom_bootstrap",
            metadata={"conversation_id": conversation_id},
        )
        if saved:
            inserted += 1

    return inserted


def _extract_visible_message_elements(bot) -> List:
    selectors = [
        'div[role="row"] div[dir="auto"]',
        'div[dir="auto"]',
    ]

    for selector in selectors:
        try:
            message_elements = bot.driver.find_elements(By.CSS_SELECTOR, selector)
            if message_elements:
                return message_elements
        except NoSuchElementException:
            continue
    return []
