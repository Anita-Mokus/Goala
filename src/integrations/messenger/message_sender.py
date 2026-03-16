"""
Messenger conversation metadata: extract sender/contact name from current chat.
"""
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def extract_sender_name(bot) -> str:
    """
    Extract sender name from the current conversation.

    Args:
        bot: MessengerBot instance

    Returns:
        Sender name or 'Unknown'
    """
    try:
        title = (bot.driver.title or "").strip()
        if " | " in title:
            return title.split(" | ")[0].strip()

        header_selectors = [
            'h1[dir="auto"]',
            'span[dir="auto"]',
            '[role="heading"]',
        ]

        for selector in header_selectors:
            try:
                element = bot.driver.find_element(By.CSS_SELECTOR, selector)
                name = element.text.strip()
                if name:
                    return name
            except NoSuchElementException:
                continue

    except Exception as e:
        print(f"Warning: Could not extract sender name: {e}")

    return "Unknown"
