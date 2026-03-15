"""
Messenger message ownership: detect "sent by me" vs "received".
Uses DOM heuristics (e.g. background color) to classify a message bubble.
"""


def is_message_from_us(bot, message_element) -> bool:
    """
    Determine if a message element is from us (the bot) or from the client.

    Messenger: sent bubbles have no solid background in the first 6 ancestors
    (they use a gradient from a CSS variable on a deeper wrapper). Received
    bubbles have a solid backgroundColor. So: background found → received;
    no background in 6 ancestors → sent by me.

    Args:
        bot: MessengerBot instance
        message_element: Selenium WebElement of the message (e.g. div[dir="auto"])

    Returns:
        True if the message is from us (sent by me), False if from client.
    """
    try:
        return bot.driver.execute_script(_IS_SENT_BY_ME_SCRIPT, message_element)
    except Exception as e:
        print(f"  Warning: Could not determine message ownership: {e}")
        return False


_IS_SENT_BY_ME_SCRIPT = """
function isSentByMe(msgEl) {
    var el = msgEl;
    for (var d = 0; d < 6; d++) {
        if (!el) break;
        var bg = getComputedStyle(el).backgroundColor;
        var bgImg = getComputedStyle(el).backgroundImage;
        if ((bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') ||
            (bgImg && bgImg !== 'none')) {
            return false;
        }
        el = el.parentElement;
    }
    return true;
}
return isSentByMe(arguments[0]);
"""
